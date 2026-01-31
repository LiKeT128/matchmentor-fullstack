from fastapi import APIRouter, Depends, HTTPException, Query
import os
import logging
from typing import Optional
from app.services.auth_service import get_db
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/debug", tags=["debug"])

@router.get("/logs")
async def get_logs(
    lines: int = 100, 
    key: str = Query(None), 
    db: Session = Depends(get_db)
):
    """Returns the last N lines of the application log."""
    # Simple hardcoded key for easy browser access
    if key == "matchmentor_debug_2026":
        pass
    else:
        # If no key, we'd normally check JWT, but since browser tabs don't have it, 
        # we'll just require the key for simplicity in this "dummies" mode.
        raise HTTPException(
            status_code=401, 
            detail="Access denied. Add '?key=matchmentor_debug_2026' to the URL."
        )
    
    log_file = "app.log" # Default log file if we are using one
    if not os.path.exists(log_file):
        # Try to find any .log file
        log_files = [f for f in os.listdir('.') if f.endswith('.log')]
        if not log_files:
            return {"message": "No log files found in current directory", "current_dir": os.getcwd(), "files": os.listdir('.')}
        log_file = log_files[0]

    try:
        with open(log_file, "r") as f:
            content = f.readlines()
            return {
                "file": log_file,
                "total_lines": len(content),
                "last_n": content[-lines:]
            }
    except Exception as e:
        return {"error": str(e)}

@router.get("/status")
async def get_status():
    """Basic health check with system info."""
    return {
        "status": "online",
        "env": os.environ.get("RAILWAY_ENVIRONMENT", "local"),
        "cwd": os.getcwd(),
        "files": os.listdir('.')
    }
