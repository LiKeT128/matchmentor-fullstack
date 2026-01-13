from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.orm import Session
from pathlib import Path
import shutil
import tempfile
import time
import os
import uuid
import logging

from app.database import get_db, SessionLocal
from app.models.user import User
from app.models.match import Match
from app.services.auth_service import get_current_user
from app.services.replay_parser import ReplayParser
from app.services.demo_converter import DemoConverter
from app.services.email_service import email_service

router = APIRouter(prefix="/api/matches", tags=["demo"])
logger = logging.getLogger(__name__)

# Max file size: 500MB
MAX_FILE_SIZE = 500 * 1024 * 1024

@router.post("/upload-demo", status_code=status.HTTP_200_OK)
async def upload_demo_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """
    Upload and parse a Dota 2 replay (.dem) file asynchronously.
    
    Returns a job ID (match record ID) that can be polled for status.
    """
    # 1. Validate File Extension
    if not file.filename or not file.filename.endswith('.dem'):
        raise HTTPException(
            status_code=400,
            detail="Only .dem files are accepted"
        )
    
    # 2. Check File Size (max 500MB)
    try:
        file.file.seek(0, 2)
        size = file.file.tell()
        file.file.seek(0)
        
        if size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"File size exceeds 500MB limit"
            )
    except HTTPException:
        raise
    except Exception:
        # If seek fails, we'll check during read/save
        pass

    # 3. Create /tmp/demos directory if it doesn't exist
    demos_dir = "/tmp/demos"
    try:
        os.makedirs(demos_dir, exist_ok=True)
    except Exception as e:
        logger.warning(f"Failed to create /tmp/demos, using system temp: {e}")
        demos_dir = os.path.join(tempfile.gettempdir(), "demos")
        os.makedirs(demos_dir, exist_ok=True)

    # 4. Save file with unique name
    try:
        timestamp = int(time.time() * 1000)
        safe_filename = f"{current_user.id}_{timestamp}.dem"
        temp_filepath = os.path.join(demos_dir, safe_filename)
        
        with open(temp_filepath, "wb") as f:
            shutil.copyfileobj(file.file, f)
            
        logger.info(f"Saved demo upload to {temp_filepath}")
        
    except Exception as e:
        logger.error(f"Failed to save uploaded file: {e}")
        raise HTTPException(status_code=500, detail="Failed to save file")

    # 3. Create Pending Match Record
    # Use temporary match_id
    temp_match_id = f"pending_{uuid.uuid4().hex[:12]}"
    
    pending_match = Match(
        match_id=temp_match_id,
        player_id=current_user.id,
        hero_name="pending",
        duration_minutes=0,
        result="pending",
        parsed_data={"status": "parsing", "filename": file.filename},
        metrics={},
        source="dem",
        selected_hero_name=None 
    )
    
    db.add(pending_match)
    db.commit()
    db.refresh(pending_match)
    
    # 4. Queue Background Task
    background_tasks.add_task(
        parse_demo_background,
        demo_path=temp_filepath,
        match_record_id=pending_match.id,
        player_id=current_user.id
    )
    
    return {
        "status": "queued",
        "match_id": pending_match.id,  # Internal DB ID for polling
        "message": "Demo file uploaded. Parsing in progress..."
    }

@router.get("/{match_id}/status")
async def get_match_status(
    match_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get parsing status of a demo file by internal database ID.
    
    Returns:
        status: "parsing" | "completed" | "failed"
        hero_name: "pending" | "npc_dota_hero_..."
        duration_minutes: 0 | actual value
        result: "pending" | "WIN" | "LOSS"
    """
    match = db.query(Match).filter(
        Match.id == match_id,
        Match.player_id == current_user.id
    ).first()
    
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    
    # Determine Status - CRITICAL: Check hero_name first
    parsed_data = match.parsed_data or {}
    
    # Check for failed status first
    if parsed_data.get("status") == "failed" or parsed_data.get("error"):
        return {
            "status": "failed",
            "message": parsed_data.get("error", "Unknown error"),
            "match_id": match.id,
            "hero_name": match.hero_name,
            "duration_minutes": match.duration_minutes,
            "result": match.result
        }
    
    # Check if hero_name is set (not "pending") - indicates completion
    if match.hero_name and match.hero_name != "pending":
        status_msg = "completed"
    else:
        # Still parsing
        status_msg = "parsing"
    
    return {
        "status": status_msg,
        "match_id": match.id,
        "hero_name": match.hero_name,
        "duration_minutes": match.duration_minutes,
        "result": match.result
    }

def parse_demo_background(
    demo_path: str,
    match_record_id: int,
    player_id: int
):
    """Background task to parse demo and update DB."""
    # Force immediate flush of this log
    print(f"DEBUG: Entering parse_demo_background for match {match_record_id}", flush=True)
    logger.info(f"Starting background parse for record {match_record_id}")
    
    # New DB session for thread safety
    db = SessionLocal()
    
    try:
        # 1. Parse with ReplayParser
        parser = ReplayParser()
        print(f"DEBUG: ReplayParser initialized, calling parse_replay for {demo_path}", flush=True)
        # This might take time
        clarity_output = parser.parse_replay(demo_path)
        print("DEBUG: parse_replay returned successfully", flush=True)
        
        # 2. Convert to Match model format
        # This includes analysis
        match_data = DemoConverter.convert_clarity_to_match(
            clarity_data=clarity_output,
            player_id=player_id
        )
        
        # 3. Update Match Record
        match = db.query(Match).filter(Match.id == match_record_id).first()
        if match:
            # Check for existing real match_id to prevent duplicates?
            # User might upload same match twice.
            # Ideally we check if 'match_id' already exists for this user.
            real_match_id = match_data["match_id"]
            
            existing = db.query(Match).filter(
                Match.player_id == player_id,
                Match.match_id == str(real_match_id)
            ).first()
            
            if existing and existing.id != match_record_id:
                # User already has this match!
                # We can either merge or fail. 
                # Let's fail gracefully saying "Already exists" or just update THIS record
                # Update THIS record is safer to avoid confusing the user who just got ID `match_record_id`
                # But we can't have duplicate (player_id, match_id) if there's a constraint (not strictly unique in model, just index)
                # Model: match_id = Column(String(50), index=True, nullable=False) -> Not unique constraint on DB level apparently from class def
                pass

            match.match_id = str(real_match_id)
            # CRITICAL: Must save hero_name - this is how status endpoint detects completion
            match.hero_name = match_data["hero_name"]  # Must not be None/empty
            match.duration_minutes = match_data["duration_minutes"]
            match.result = match_data["result"]
            
            # Enrich parsed data with status
            p_data = match_data["parsed_data"]
            p_data["status"] = "completed"
            match.parsed_data = p_data
            
            match.metrics = match_data["metrics"]
            match.advice = match_data["advice"]
            match.steam_id = match_data.get("steam_id")
            
            # Commit changes
            db.commit()
            logger.info(f"✓ Background parse success for match {real_match_id}, hero_name={match.hero_name}")
            
            # Optional: Email notification
            # try:
            #     email_service.send_match_analysis_complete(...)
            # catch...
            
    except Exception as e:
        logger.error(f"Background parsing failed: {e}")
        match = db.query(Match).filter(Match.id == match_record_id).first()
        if match:
            existing_data = match.parsed_data or {}
            existing_data["status"] = "failed"
            existing_data["error"] = str(e)
            match.parsed_data = existing_data
            db.commit()
            
    finally:
        db.close()
        # Clean up file
        if os.path.exists(demo_path):
            try:
                os.remove(demo_path)
            except:
                pass
