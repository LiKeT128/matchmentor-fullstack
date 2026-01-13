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
        logger.info(f"[BG] Step 1: Parsing demo file...")
        # This might take time
        clarity_output = parser.parse_replay(demo_path)
        print("DEBUG: parse_replay returned successfully", flush=True)
        logger.info(f"[BG] Step 1 OK: Parsed data keys: {list(clarity_output.keys())}")
        
        # 2. Convert to Match model format
        # This includes analysis
        logger.info(f"[BG] Step 2: Converting clarity data to match format...")
        print(f"DEBUG: Calling DemoConverter.convert_clarity_to_match", flush=True)
        try:
            match_data = DemoConverter.convert_clarity_to_match(
                clarity_data=clarity_output,
                player_id=player_id
            )
            logger.info(f"[BG] Step 2 OK: Match data keys: {list(match_data.keys())}")
            logger.info(f"[BG] Step 2 OK: hero_name={match_data.get('hero_name')}, match_id={match_data.get('match_id')}")
            print(f"DEBUG: DemoConverter returned successfully, hero_name={match_data.get('hero_name')}", flush=True)
        except Exception as conv_error:
            logger.error(f"[BG] Step 2 FAILED: DemoConverter error: {conv_error}", exc_info=True)
            print(f"DEBUG: DemoConverter failed: {conv_error}", flush=True)
            raise
        
        # 3. Update Match Record
        logger.info(f"[BG] Step 3: Updating match record {match_record_id}...")
        print(f"DEBUG: Querying match record {match_record_id}", flush=True)
        match = db.query(Match).filter(Match.id == match_record_id).first()
        if not match:
            logger.error(f"[BG] Step 3 FAILED: Match record {match_record_id} not found!")
            raise ValueError(f"Match record {match_record_id} not found")
        
        logger.info(f"[BG] Step 3: Match found, updating fields...")
        # Check for existing real match_id to prevent duplicates?
        real_match_id = match_data.get("match_id")
        if not real_match_id:
            logger.warning(f"[BG] Step 3: No match_id in match_data, using existing")
            real_match_id = match.match_id
        
        # CRITICAL: Must save hero_name - this is how status endpoint detects completion
        hero_name = match_data.get("hero_name")
        if not hero_name or hero_name == "pending":
            logger.error(f"[BG] Step 3 FAILED: Invalid hero_name: {hero_name}")
            raise ValueError(f"Invalid hero_name: {hero_name}")
        
        logger.info(f"[BG] Step 3: Setting hero_name={hero_name}, match_id={real_match_id}")
        match.match_id = str(real_match_id)
        match.hero_name = hero_name  # Must not be None/empty
        match.duration_minutes = match_data.get("duration_minutes", 0)
        match.result = match_data.get("result", "LOSS")
        
        # Enrich parsed data with status
        p_data = match_data.get("parsed_data", {})
        if isinstance(p_data, dict):
            p_data["status"] = "completed"
        match.parsed_data = p_data
        
        match.metrics = match_data.get("metrics", {})
        match.advice = match_data.get("advice", [])
        match.steam_id = match_data.get("steam_id")
        
        logger.info(f"[BG] Step 4: Committing changes to database...")
        print(f"DEBUG: About to commit, hero_name={match.hero_name}", flush=True)
        
        # Commit changes
        db.commit()
        logger.info(f"[BG] ✓ Background parse success for match {real_match_id}, hero_name={match.hero_name}")
        print(f"DEBUG: Commit successful! hero_name={match.hero_name}", flush=True)
            
            # Optional: Email notification
            # try:
            #     email_service.send_match_analysis_complete(...)
            # catch...
            
    except Exception as e:
        logger.error(f"[BG] Background parsing failed: {e}", exc_info=True)
        print(f"DEBUG: Exception in background task: {e}", flush=True)
        import traceback
        logger.error(f"[BG] Traceback: {traceback.format_exc()}")
        match = db.query(Match).filter(Match.id == match_record_id).first()
        if match:
            existing_data = match.parsed_data or {}
            existing_data["status"] = "failed"
            existing_data["error"] = str(e)
            match.parsed_data = existing_data
            try:
                db.commit()
                logger.info(f"[BG] Error status saved to match {match_record_id}")
            except Exception as commit_error:
                logger.error(f"[BG] Failed to save error status: {commit_error}")
            
    finally:
        db.close()
        # Clean up file
        if os.path.exists(demo_path):
            try:
                os.remove(demo_path)
            except:
                pass
