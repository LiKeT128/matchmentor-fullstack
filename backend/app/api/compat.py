"""Compatibility API endpoints to match frontend expectations."""

from fastapi import APIRouter, Depends, UploadFile, File, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.services.auth_service import get_current_user
from app.api.auth import register, RegisterRequest, AuthResponse
from app.api.matches import upload_match, UploadResponse, Match
from app.api.payments import get_payment_history, PaymentResponse
from datetime import datetime

router = APIRouter(tags=["compatibility"])

@router.get("/api/subscription")
@router.get("/_api/subscription")
async def get_subscription_info(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's subscription and usage info."""
    # Get first day of current month
    first_of_month = datetime.utcnow().replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )
    
    match_count = db.query(Match).filter(
        Match.player_id == current_user.id,
        Match.created_at >= first_of_month
    ).count()
    
    # Unlimited for MVP
    tier_limit = 999999
    
    return {
        "tier": current_user.tier,
        "limit": tier_limit,
        "used": match_count,
        "remaining": tier_limit,
        "is_pro": True # Treat everyone as pro for UI features
    }

@router.get("/api/billing-history", response_model=list[PaymentResponse])
@router.get("/_api/billing-history", response_model=list[PaymentResponse])
async def billing_history_alias(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Alias for /api/payments/history."""
    return await get_payment_history(current_user, db)

@router.post("/api/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
@router.post("/_api/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register_alias(request: RegisterRequest, db: Session = Depends(get_db)):
    """Alias for /api/auth/register."""
    return await register(request, db)

@router.post("/api/upload", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
@router.post("/_api/upload", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_alias(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Alias for /api/matches/upload."""
    return await upload_match(file, current_user, db)
