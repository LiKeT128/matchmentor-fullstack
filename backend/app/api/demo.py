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
    
    # Determine Status based on parsed_data status
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
    
    # Check parsed_data status (parsing/completed)
    parsed_status = parsed_data.get("status", "parsing")
    
    if parsed_status == "completed":
        # Parsing completed - ready for hero selection OR already analyzed
        # If hero_name is still "pending", parsing is done but hero not selected
        # If hero_name is set, analysis is complete
        if match.hero_name and match.hero_name != "pending":
            status_msg = "completed"
        else:
            # Parsing done, but hero not selected yet (should redirect to hero selection)
            status_msg = "completed"  # Parsing is complete
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
        # 1. Parse with ReplayParser (NO analysis yet - just parsing)
        parser = ReplayParser()
        logger.info(f"[BG] Step 1: Parsing demo file...")
        clarity_output = parser.parse_replay(demo_path)
        logger.info(f"[BG] Step 1 OK: Parsed data keys: {list(clarity_output.keys())}")
        
        # 2. Update Match Record with parsed data (keep hero_name="pending" for selection)
        logger.info(f"[BG] Step 2: Updating match record {match_record_id}...")
        match = db.query(Match).filter(Match.id == match_record_id).first()
        if not match:
            logger.error(f"[BG] Step 2 FAILED: Match record {match_record_id} not found!")
            raise ValueError(f"Match record {match_record_id} not found")
        
        # Extract basic info from parsed data
        real_match_id = clarity_output.get("match_id")
        duration_minutes = clarity_output.get("duration_minutes", 0)
        duration_seconds = clarity_output.get("duration_seconds", clarity_output.get("duration", 0))
        
        # Determine result from parsed data (if available)
        result = clarity_output.get("result", "pending")
        if result == "pending" and duration_seconds > 0:
            # Try to determine from full_data
            full_data = clarity_output.get("full_data", {})
            if full_data.get("radiant_win") is not None:
                result = "WIN" if full_data.get("radiant_win") else "LOSS"
        
        # Update match with parsed data (keep hero_name="pending")
        match.match_id = str(real_match_id) if real_match_id else match.match_id
        match.duration_minutes = duration_minutes
        match.result = result
        
        # Save full parsed data (this contains all heroes)
        parsed_data = clarity_output.copy()
        parsed_data["status"] = "completed"  # Parsing completed, ready for hero selection
        match.parsed_data = parsed_data
        
        # Keep hero_name="pending" - user will select hero via /select-hero endpoint
        # Don't set metrics/advice yet - that happens in /select-hero after user chooses hero
        
        logger.info(f"[BG] Step 3: Committing parsed data (hero_name stays 'pending' for selection)...")
        
        # Commit changes
        db.commit()
        logger.info(f"[BG] ✓ Background parse success for match {real_match_id}. Parsed data saved, awaiting hero selection.")
        print(f"DEBUG: Commit successful! hero_name={match.hero_name}, heroes in data: {len(clarity_output.get('heroes', []))}", flush=True)
            
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
