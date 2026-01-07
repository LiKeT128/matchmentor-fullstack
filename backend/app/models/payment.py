"""Payment database model."""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base


class Payment(Base):
    """
    Payment model representing Stripe transactions.
    
    Attributes:
        id: Primary key.
        user_id: Foreign key to User.
        amount: Amount in cents.
        stripe_id: Stripe payment intent ID.
        status: Payment status (pending, completed, failed, refunded).
        tier: Subscription tier purchased (PRO, PREMIUM).
        description: Optional payment description.
        created_at: Transaction timestamp.
    """
    __tablename__ = "payments"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    amount = Column(Integer, nullable=False)  # in cents
    stripe_id = Column(String(100), unique=True, nullable=False)
    status = Column(String(20), default="pending", nullable=False)
    tier = Column(String(20), nullable=True)  # PRO, PREMIUM
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="payments")
    booking = relationship("Booking", back_populates="payment", uselist=False)
    
    def __repr__(self) -> str:
        return f"<Payment(id={self.id}, amount={self.amount}, status={self.status})>"
