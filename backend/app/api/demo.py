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

@router.post("/upload-demo", status_code=status.HTTP_202_ACCEPTED)
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
    # 1. Validate File
    if not file.filename.endswith('.dem'):
        raise HTTPException(
            status_code=400,
            detail="Only .dem files are accepted"
        )
    
    # Check size (approximate via seek if supported, or read chunk)
    # file.file is a SpooledTemporaryFile usually
    try:
        file.file.seek(0, 2)
        size = file.file.tell()
        file.file.seek(0)
        
        if size > MAX_FILE_SIZE:
             raise HTTPException(
                status_code=413,
                detail=f"File size {size / 1024 / 1024:.1f}MB exceeds limit of 500MB"
            )
    except Exception:
        # If seek fails, we'll check during read/save
        pass

    # 2. Save to Temp
    try:
        # Use system temp dir
        temp_dir = tempfile.gettempdir()
        demos_dir = os.path.join(temp_dir, "matchmentor_demos")
        os.makedirs(demos_dir, exist_ok=True)
        
        timestamp = int(time.time() * 1000)
        safe_filename = f"{current_user.id}_{timestamp}_{uuid.uuid4().hex[:8]}.dem"
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
        "match_id": pending_match.id, # Internal DB ID for polling
        "temp_match_id": temp_match_id,
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
    """
    match = db.query(Match).filter(
        Match.id == match_id,
        Match.player_id == current_user.id
    ).first()
    
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    
    # Determine Status
    parsed_data = match.parsed_data or {}
    status_msg = "completed"
    
    if parsed_data.get("status") == "parsing":
        status_msg = "parsing"
    elif parsed_data.get("status") == "failed":
        status_msg = "failed"
        return {
            "status": "failed",
            "message": parsed_data.get("error", "Unknown error"),
            "match_id": match.id
        }
    elif match.hero_name == "pending":
         # Should be caught by 'parsing' check usually, but safer fallback
         status_msg = "parsing"
    
    # If completed
    return {
        "status": status_msg,
        "match_id": match.id,
        "real_match_id": match.match_id if match.match_id and not match.match_id.startswith("pending") else None,
        "hero_name": match.hero_name,
        "result": match.result
    }

async def parse_demo_background(
    demo_path: str,
    match_record_id: int,
    player_id: int
):
    """Background task to parse demo and update DB."""
    logger.info(f"Starting background parse for record {match_record_id}")
    
    # New DB session for thread safety
    db = SessionLocal()
    
    try:
        # 1. Parse with ReplayParser
        parser = ReplayParser()
        # This might take time
        clarity_output = parser.parse_replay(demo_path)
        
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
            match.hero_name = match_data["hero_name"]
            match.duration_minutes = match_data["duration_minutes"]
            match.result = match_data["result"]
            
            # Enrich parsed data with status
            p_data = match_data["parsed_data"]
            p_data["status"] = "completed"
            match.parsed_data = p_data
            
            match.metrics = match_data["metrics"]
            match.advice = match_data["advice"]
            match.steam_id = match_data.get("steam_id")
            
            db.commit()
            logger.info(f"✓ Background parse success for match {real_match_id}")
            
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
