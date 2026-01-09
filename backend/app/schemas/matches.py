from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class MatchResponse(BaseModel):
    """Response schema for match data."""
    id: int
    match_id: str
    hero_name: str
    duration_minutes: int
    result: str
    overall_score: int = 0
    created_at: datetime
    selected_hero_name: Optional[str] = None
    selected_at: Optional[datetime] = None


class HeroInMatch(BaseModel):
    """Schema for a hero in the match."""
    player_id: int
    hero_name: str
    # hero_display_name: str # Optional or computed? User snippet has hero_name. Logic uses hero_name.
    # User schema in prompt didn't strictly specify HeroInMatch structure but likely needs matching fields.
    # Existing HeroInMatch has hero_display_name. I should keep it or make optional if data might miss it.
    # But for moving, I will just move the class as is.
    hero_display_name: Optional[str] = None 
    team: str
    position: str = "unknown"
    player_name: Optional[str] = None
    steam_id: Optional[str] = None



class MatchDetailResponse(BaseModel):
    """Response schema for detailed match analysis."""
    id: int
    match_id: str
    hero_name: str
    duration_minutes: int
    result: str
    metrics: dict
    advice: list
    overall_score: int = 0
    strengths: list = []
    weaknesses: list = []
    power_spikes: list = []
    mistakes: list = []
    rank_tier: int = 0
    items: list = []
    parsed_data: Optional[dict] = None
    created_at: datetime
    selected_hero_name: Optional[str] = None
    selected_at: Optional[datetime] = None
    steam_id: Optional[str] = None
    heroes_in_match: List[HeroInMatch] = []



class UploadResponse(BaseModel):
    """Response schema for upload endpoint."""
    id: int
    match_id: str
    status: str
    metrics_count: int
    advice_count: int
    overall_score: int




class UploadResponseWithHeroes(BaseModel):
    """Response for upload when hero selection is needed."""
    id: int
    match_id: str
    status: str  # "awaiting_hero_selection"
    heroes_in_match: List[HeroInMatch]


class SelectHeroRequest(BaseModel):
    """Request body for hero selection."""
    match_id: Optional[str] = None  # Optional: can also come from path param
    hero_name: str


class SelectHeroResponse(BaseModel):
    """Response after selecting a hero."""
    match_id: str
    selected_hero: str
    metrics: dict
    parsed_data: Optional[dict] = None


class MatchComparisonResponse(BaseModel):
    """Schema for comparing two matches."""
    match1: MatchDetailResponse
    match2: MatchDetailResponse
    improvements: dict  # metric_name -> change_value
