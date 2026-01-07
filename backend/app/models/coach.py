"""Coach database model."""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base


class Coach(Base):
    """
    Coach model representing users who offer coaching services.
    
    Attributes:
        id: Primary key.
        user_id: Foreign key to User (one-to-one).
        hourly_rate: Rate in cents.
        bio: Coach biography/description.
        experience_years: Years of Dota 2 experience.
        specialties: JSON array of hero/role specialties.
        verified: Whether coach is verified.
        rating: Average rating (1-5).
        total_reviews: Number of reviews received.
        stripe_account_id: Stripe Connect account for payouts.
        created_at: Profile creation timestamp.
    """
    __tablename__ = "coaches"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    hourly_rate = Column(Integer, nullable=False)  # in cents
    bio = Column(Text, nullable=True)
    experience_years = Column(Integer, default=0, nullable=False)
    verified = Column(Boolean, default=False, nullable=False)
    rating = Column(Float, default=5.0, nullable=False)
    total_reviews = Column(Integer, default=0, nullable=False)
    stripe_account_id = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="coach_profile")
    reviews = relationship("Review", back_populates="coach", lazy="dynamic")
    bookings = relationship("Booking", back_populates="coach", lazy="dynamic")
    availabilities = relationship("Availability", back_populates="coach", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Coach(id={self.id}, user_id={self.user_id}, rating={self.rating})>"
