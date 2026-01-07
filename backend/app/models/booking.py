"""Booking model for coaching sessions."""

from enum import Enum as PyEnum
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base


class BookingStatus(str, PyEnum):
    """Status of a coaching booking."""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    PAID = "paid"


class Booking(Base):
    """
    Model representing a coaching session booking.
    """
    __tablename__ = "bookings"
    
    id = Column(Integer, primary_key=True, index=True)
    coach_id = Column(Integer, ForeignKey("coaches.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    
    status = Column(Enum(BookingStatus), default=BookingStatus.PENDING)
    meeting_link = Column(String, nullable=True)
    notes = Column(String, nullable=True)
    
    payment_id = Column(Integer, ForeignKey("payments.id"), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    coach = relationship("Coach", back_populates="bookings")
    user = relationship("User", back_populates="bookings")
    payment = relationship("Payment", back_populates="booking")
    review = relationship("Review", back_populates="booking", uselist=False)
