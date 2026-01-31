from fastapi import APIRouter, Depends, HTTPException
import os
import logging
from app.services.auth_service import get_current_user
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/debug", tags=["debug"])

@router.get("/logs")
async def get_logs(lines: int = 100, current_user: User = Depends(get_current_user)):
    """Returns the last N lines of the application log."""
    # Check if user is admin or authorized (for now just check if logged in)
    # In production, this should be behind strict admin check
    
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
