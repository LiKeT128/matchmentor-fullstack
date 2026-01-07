"""Availability model for coaches to define their working hours."""

from enum import Enum as PyEnum
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, Time, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base


class DayOfWeek(str, PyEnum):
    """Days of the week."""
    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"
    SATURDAY = "saturday"
    SUNDAY = "sunday"


class Availability(Base):
    """
    Model representing a recurring availability slot for a coach.
    """
    __tablename__ = "coach_availability"
    
    id = Column(Integer, primary_key=True, index=True)
    coach_id = Column(Integer, ForeignKey("coaches.id"), nullable=False)
    
    day_of_week = Column(Enum(DayOfWeek), nullable=False)
    start_time = Column(Time, nullable=False)  # e.g., 09:00:00
    end_time = Column(Time, nullable=False)    # e.g., 17:00:00
    
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    coach = relationship("Coach", back_populates="availabilities")
