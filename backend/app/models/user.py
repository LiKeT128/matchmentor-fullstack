"""User database model."""

from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base


class User(Base):
    """
    User model representing registered users.
    
    Attributes:
        id: Primary key.
        email: Unique email address.
        password_hash: Bcrypt hashed password.
        steam_id: Optional Steam ID for linking.
        tier: Subscription tier (FREE, PRO, PREMIUM).
        stripe_customer_id: Stripe customer reference.
        is_active: Whether account is active.
        created_at: Account creation timestamp.
        updated_at: Last update timestamp.
    """
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    steam_id = Column(String(50), unique=True, nullable=True)
    tier = Column(String(20), default="FREE", nullable=False)
    stripe_customer_id = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    matches = relationship("Match", back_populates="player", lazy="dynamic")
    coach_profile = relationship("Coach", back_populates="user", uselist=False)
    payments = relationship("Payment", back_populates="user", lazy="dynamic")
    reviews = relationship("Review", back_populates="user", lazy="dynamic")
    bookings = relationship("Booking", back_populates="user", lazy="dynamic")
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, tier={self.tier})>"
