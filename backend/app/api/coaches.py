"""Coaches API endpoints."""

from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.user import User
from app.models.coach import Coach
from app.models.availability import Availability
from app.api.auth import get_current_user

router = APIRouter(prefix="/api/coaches", tags=["coaches"])


class CoachCreate(BaseModel):
    """Schema for registering as a coach."""
    hourly_rate: int  # in cents
    bio: str
    experience_years: int
    specialties: List[str] = []


class CoachResponse(BaseModel):
    """Schema for coach profile response."""
    id: int
    user_id: int
    username: str
    hourly_rate: int
    bio: Optional[str]
    experience_years: int
    rating: float
    total_reviews: int
    verified: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class AvailabilityCreate(BaseModel):
    """Schema for adding availability slot."""
    day_of_week: int  # 0=Monday, 6=Sunday
    start_hour: int   # 0-23
    end_hour: int     # 0-23


class AvailabilityResponse(BaseModel):
    """Schema for availability response."""
    id: int
    day_of_week: int
    start_hour: int
    end_hour: int
    
    class Config:
        from_attributes = True


@router.post("/register", response_model=CoachResponse, status_code=status.HTTP_201_CREATED)
async def register_coach(
    coach_data: CoachCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> CoachResponse:
    """
    Register current user as a coach.
    """
    # Check if already registered
    existing_coach = db.query(Coach).filter(Coach.user_id == current_user.id).first()
    if existing_coach:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already registered as a coach"
        )
    
    # Create new coach profile
    coach = Coach(
        user_id=current_user.id,
        hourly_rate=coach_data.hourly_rate,
        bio=coach_data.bio,
        experience_years=coach_data.experience_years,
        verified=True,  # Auto-verify for MVP
        rating=5.0,     # Default rating
        total_reviews=0
    )
    
    db.add(coach)
    db.commit()
    db.refresh(coach)
    
    # Construct response manually to handle user relationship
    return CoachResponse(
        id=coach.id,
        user_id=coach.user_id,
        username=current_user.email.split("@")[0],
        hourly_rate=coach.hourly_rate,
        bio=coach.bio,
        experience_years=coach.experience_years,
        rating=coach.rating,
        total_reviews=coach.total_reviews,
        verified=coach.verified,
        created_at=coach.created_at
    )


@router.get("", response_model=List[CoachResponse])
async def list_coaches(
    min_rating: Optional[float] = None,
    max_price: Optional[int] = None,
    db: Session = Depends(get_db)
) -> List[CoachResponse]:
    """
    List all coaches with optional filtering.
    """
    query = db.query(Coach).filter(Coach.verified == True)
    
    if min_rating:
        query = query.filter(Coach.rating >= min_rating)
    
    if max_price:
        query = query.filter(Coach.hourly_rate <= max_price)
        
    coaches = query.all()
    
    return [
        CoachResponse(
            id=c.id,
            user_id=c.user_id,
            username=c.user.email.split("@")[0],
            hourly_rate=c.hourly_rate,
            bio=c.bio,
            experience_years=c.experience_years,
            rating=c.rating,
            total_reviews=c.total_reviews,
            verified=c.verified,
            created_at=c.created_at
        )
        for c in coaches
    ]


@router.get("/{coach_id}", response_model=CoachResponse)
async def get_coach(
    coach_id: int,
    db: Session = Depends(get_db)
) -> CoachResponse:
    """
    Get public profile of a coach.
    """
    coach = db.query(Coach).filter(Coach.id == coach_id).first()
    if not coach:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Coach not found"
        )
        
    return CoachResponse(
        id=coach.id,
        user_id=coach.user_id,
        username=coach.user.email.split("@")[0],
        hourly_rate=coach.hourly_rate,
        bio=coach.bio,
        experience_years=coach.experience_years,
        rating=coach.rating,
        total_reviews=coach.total_reviews,
        verified=coach.verified,
        created_at=coach.created_at
    )


@router.post("/availability", response_model=AvailabilityResponse)
async def add_availability(
    slot: AvailabilityCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> AvailabilityResponse:
    """
    Add availability slot for current coach.
    """
    coach = db.query(Coach).filter(Coach.user_id == current_user.id).first()
    if not coach:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must be a registered coach to add availability"
        )
        
    availability = Availability(
        coach_id=coach.id,
        day_of_week=slot.day_of_week,
        start_hour=slot.start_hour,
        end_hour=slot.end_hour
    )
    
    db.add(availability)
    db.commit()
    db.refresh(availability)
    
    return availability


@router.get("/{coach_id}/availability", response_model=List[AvailabilityResponse])
async def get_availability(
    coach_id: int,
    db: Session = Depends(get_db)
) -> List[AvailabilityResponse]:
    """
    Get availability slots for a coach.
    """
    slots = db.query(Availability).filter(Availability.coach_id == coach_id).all()
    return slots
