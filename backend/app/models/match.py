"""Match database model."""

from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base


class Match(Base):
    """
    Match model representing analyzed Dota 2 matches.
    
    Attributes:
        id: Primary key.
        match_id: Unique Dota 2 match ID.
        player_id: Foreign key to User.
        hero_name: Hero played in match.
        duration_minutes: Match duration.
        result: Match outcome (WIN, LOSS, ABANDONED).
        parsed_data: Raw Clarity parser output (JSON).
        metrics: Calculated 60+ performance metrics (JSON).
        advice: Generated coaching advice (JSON).
        created_at: Analysis timestamp.
    """
    __tablename__ = "matches"
    
    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(String(50), index=True, nullable=False)
    player_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    steam_id = Column(String(50), nullable=True, index=True)
    hero_name = Column(String(100), nullable=False)
    duration_minutes = Column(Integer, nullable=False)
    result = Column(String(20), nullable=False)  # WIN, LOSS, ABANDONED
    parsed_data = Column(JSON, nullable=True)  # Raw Clarity output
    metrics = Column(JSON, nullable=True)  # Calculated metrics
    advice = Column(JSON, nullable=True)  # Generated advice
    selected_hero_name = Column(String(100), nullable=True)  # User's selected hero
    selected_at = Column(DateTime, nullable=True)  # When hero was selected
    source = Column(String(20), nullable=True)  # Data source: 'opendota' or 'clarity'
    analysis_logs = Column(JSON, nullable=True)  # Detailed analysis trace
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    player = relationship("User", back_populates="matches")
    
    def __repr__(self) -> str:
        return f"<Match(id={self.id}, match_id={self.match_id}, hero={self.hero_name})>"
