"""Bookings API endpoints for coaching sessions."""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.coach import Coach
from app.models.booking import Booking, BookingStatus
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/api/bookings", tags=["bookings"])


class BookingCreate(BaseModel):
    """Schema for creating a booking."""
    coach_id: int
    start_time: datetime
    end_time: datetime
    notes: Optional[str] = None


class BookingResponse(BaseModel):
    """Schema for booking response."""
    id: int
    coach_id: int
    user_id: int
    start_time: datetime
    end_time: datetime
    status: BookingStatus
    meeting_link: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime


@router.post("", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
async def create_booking(
    request: BookingCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> BookingResponse:
    """
    Create a new coaching booking.
    """
    # Check if coach exists
    coach = db.query(Coach).filter(Coach.id == request.coach_id).first()
    if not coach:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Coach not found"
        )
    
    # Basic validation: start_time must be in the future
    if request.start_time <= datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Booking must be in the future"
        )
    
    if request.end_time <= request.start_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="End time must be after start time"
        )
    
    # Create booking
    booking = Booking(
        coach_id=request.coach_id,
        user_id=current_user.id,
        start_time=request.start_time,
        end_time=request.end_time,
        notes=request.notes,
        status=BookingStatus.PENDING
    )
    
    db.add(booking)
    db.commit()
    db.refresh(booking)
    
    return booking


@router.get("", response_model=List[BookingResponse])
async def list_bookings(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    role: str = Query("student", pattern="^(student|coach)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> List[BookingResponse]:
    """
    List bookings for current user (as student or as coach).
    """
    if role == "student":
        query = db.query(Booking).filter(Booking.user_id == current_user.id)
    else:
        # Check if user is a coach
        if not current_user.coach_profile:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not registered as a coach"
            )
        query = db.query(Booking).filter(Booking.coach_id == current_user.coach_profile.id)
    
    bookings = query.order_by(Booking.start_time.desc()).offset(skip).limit(limit).all()
    return bookings


@router.get("/{booking_id}", response_model=BookingResponse)
async def get_booking(
    booking_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> BookingResponse:
    """
    Get booking details.
    """
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )
    
    # Check authorization
    is_student = booking.user_id == current_user.id
    is_coach = current_user.coach_profile and booking.coach_id == current_user.coach_profile.id
    
    if not (is_student or is_coach):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this booking"
        )
    
    return booking


@router.patch("/{booking_id}/status", response_model=BookingResponse)
async def update_booking_status(
    booking_id: int,
    new_status: BookingStatus,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> BookingResponse:
    """
    Update booking status (Confirm/Cancel/Complete).
    """
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )
    
    is_coach = current_user.coach_profile and booking.coach_id == current_user.coach_profile.id
    is_student = booking.user_id == current_user.id
    
    # Logic for status transitions
    if new_status == BookingStatus.CONFIRMED:
        if not is_coach:
            raise HTTPException(status_code=403, detail="Only coaches can confirm bookings")
        booking.status = BookingStatus.CONFIRMED
        
    elif new_status == BookingStatus.CANCELLED:
        if not (is_coach or is_student):
            raise HTTPException(status_code=403, detail="Not authorized")
        booking.status = BookingStatus.CANCELLED
        
    elif new_status == BookingStatus.COMPLETED:
        if not is_coach:
            raise HTTPException(status_code=403, detail="Only coaches can complete bookings")
        booking.status = BookingStatus.COMPLETED
    
    db.commit()
    db.refresh(booking)
    return booking
