"""Matches API endpoints for replay upload and analysis."""

import os
import shutil
import tempfile
import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, File, UploadFile, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.match import Match
from app.services.auth_service import get_current_user
from app.services.replay_parser import ReplayParser
from app.services.match_analyzer import MatchAnalyzer
from app.services.match_analyzer import MatchAnalyzer
from app.services.email_service import email_service
from app.services.opendota_client import OpenDotaClient
from app.schemas.matches import (
    MatchResponse, 
    MatchDetailResponse, 
    UploadResponse, 
    UploadResponseWithHeroes, 
    SelectHeroRequest, 
    SelectHeroResponse,
    MatchComparisonResponse,
    HeroInMatch
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/matches", tags=["matches"])


def _extract_heroes_from_match(parsed_data: Optional[dict]) -> List[dict]:
    """
    Extract all 10 heroes from parsed match data.
    
    Args:
        parsed_data: Raw parsed data from Clarity parser.
        
    Returns:
        List of hero dictionaries with player info.
    """
    if not parsed_data:
        logger.warning("_extract_heroes: parsed_data is None or empty")
        return []
    
    heroes = []
    
    # Try 'heroes' key first (from our enhanced parser), then 'players' as fallback
    heroes_raw = parsed_data.get("heroes", [])
    if heroes_raw:
        logger.info(f"_extract_heroes: Found {len(heroes_raw)} entries in 'heroes' key")
    else:
        heroes_raw = parsed_data.get("players", [])
        logger.info(f"_extract_heroes: Falling back to 'players' key, found {len(heroes_raw)} entries")
    
    for idx, entry in enumerate(heroes_raw):
        # Handle both dict entries and simple string entries
        if isinstance(entry, dict):
            raw_hero_name = entry.get("hero_name", entry.get("hero", "unknown"))
            position = entry.get("position", entry.get("lane_role", "unknown"))
            steam_id = entry.get("steam_id", entry.get("account_id"))
            team = entry.get("team", "radiant" if idx < 5 else "dire")
        else:
            # Entry is a string (hero name)
            raw_hero_name = str(entry) if entry else "unknown"
            position = "unknown"
            steam_id = None
            team = "radiant" if idx < 5 else "dire"
        
        # CRITICAL: Strip 'npc_dota_hero_' prefix for OpenDota image URLs!
        # OpenDota expects: 'pudge', not 'npc_dota_hero_pudge'
        short_name = raw_hero_name.replace("npc_dota_hero_", "") if raw_hero_name else "unknown"
        
        # Generate display name from short name
        display_name = short_name.replace("_", " ").title()
        
        heroes.append({
            "player_id": idx,
            "hero_name": short_name,  # Use short name for OpenDota compatibility
            "hero_display_name": display_name,
            "team": team,
            "position": str(position) if position else "unknown",
            "steam_id": str(steam_id) if steam_id else None
        })
    
    logger.info(f"_extract_heroes: Returning {len(heroes)} heroes")
    if heroes:
        logger.info(f"  Sample: {heroes[0]}")
    
    return heroes


@router.post("/lookup", status_code=status.HTTP_200_OK)
async def lookup_match(
    match_id: str = Query(...),
    steam_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Look up a match by Dota 2 match ID without needing .dem file upload.
    """
    logger.info(f"Looking up match {match_id} for user {current_user.id}")
    
    # Check if already analyzed
    existing = db.query(Match).filter(
        Match.match_id == match_id,
        Match.player_id == current_user.id
    ).first()
    
    if existing and existing.parsed_data:
        logger.info(f"Match {match_id} already analyzed by user")
        # Use the helper function which strips prefix correctly
        heroes = _extract_heroes_from_match(existing.parsed_data)
        return {
            "match_id": match_id,
            "status": "already_analyzed",
            "heroes_in_match": heroes,
            "parsed_data": existing.parsed_data
        }
    
    # Fetch from OpenDota API
    try:
        opendota_client = OpenDotaClient()
        match_data = await opendota_client.get_match(match_id)
        
        logger.info(f"Match data fetched from OpenDota")
        
        # Extract heroes from match_data.players
        # CRITICAL: Use SHORT name for OpenDota image compatibility
        heroes = []
        for idx in range(min(10, len(match_data.get('players', [])))):
            player = match_data['players'][idx]
            raw_name = player.get('hero_name', 'unknown')
            # OpenDota API often returns short name like 'pudge', but let's be safe
            short_name = raw_name.replace("npc_dota_hero_", "") if raw_name else "unknown"
            
            heroes.append({
                "player_id": idx,
                "hero_name": short_name,  # Short name for OpenDota
                "hero_display_name": short_name.replace("_", " ").title(),
                "team": "radiant" if idx < 5 else "dire",
                "position": "unknown",
                "steam_id": str(player.get('account_id', '')) or None,
                "player_name": player.get('personaname') # Include player_name from OpenDota
            })
        
        logger.info(f"Extracted {len(heroes)} heroes from OpenDota")
        if heroes:
            logger.info(f"  Sample: {heroes[0]}")
        
        return {
            "match_id": match_id,
            "status": "found",
            "heroes_in_match": heroes,
            "duration_minutes": match_data.get("duration", 0) // 60,
            "radiant_win": match_data.get("radiant_win"),
            "message": "Match found. Select your hero to analyze."
        }
    
    except Exception as e:
        logger.error(f"Failed to lookup match: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Match not found or unavailable: {str(e)}"
        )


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_match(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload and parse a .dem replay file.
    """
    logger.info(f"UPLOAD START: received file {file.filename} from user {current_user.email}")
    # Check file extension
    if not file.filename or not file.filename.endswith('.dem'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Please upload a .dem replay file"
        )
    
    
    # Match limit check removed for MVP
    # Any user can upload unlimited matches

    
    # Save file to temp location
    try:
        temp_dir = tempfile.mkdtemp()
        temp_file = os.path.join(temp_dir, file.filename)
        logger.info(f"Created temp directory: {temp_dir}")
        
        with open(temp_file, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        file_size = os.path.getsize(temp_file)
        logger.info(f"Saved temp file {temp_file} (size: {file_size} bytes)")
        
        # Parse replay
        logger.info("Initializing ReplayParser...")
        parser = ReplayParser()
        
        logger.info(f"Calling parser.parse_replay on {temp_file}...")
        parsed = parser.parse_replay(temp_file)
        logger.info("Parser returned successfully.")
        
        # FALLBACK: If parser found no heroes OR mostly "unknown" heroes, try fetching from OpenDota
        heroes = parsed.get("heroes", [])
        unknown_count = sum(1 for h in heroes if "unknown" in h.get("hero_name", "unknown").lower())
        
        if not heroes or len(heroes) == 0 or unknown_count > 5:
            logger.warning(f"Parser returned {len(heroes)} heroes with {unknown_count} unknown. Attempting OpenDota fallback...")
            try:
                # Use OpenDotaClient to fetch match data
                opendota_client = OpenDotaClient()
                # Ensure match_id is available
                match_id = parsed.get("match_id")
                
                if match_id and str(match_id) != "unknown":
                    od_match = await opendota_client.get_match(str(match_id))
                    
                    if od_match and "players" in od_match:
                        from app.services.hero_mapping import get_hero_name
                        fallback_heroes = []
                        
                        for idx, p in enumerate(od_match["players"]):
                            # CRITICAL FIX: OpenDota might return None for hero_name
                            # e.g. "hero_id": 57, "hero_name": null
                            # So we MUST use our local mapping if name is missing
                            
                            h_name = p.get("hero_name")
                            h_id = p.get("hero_id")
                            
                            if h_id and (not h_name or h_name == "unknown"):
                                # Map ID to name using our local service
                                try:
                                    h_name = get_hero_name(int(h_id))
                                except:
                                    pass
                            
                            # Final cleanup
                            if h_name:
                                # Ensure prefix consistency (matches expected storage format)
                                if not h_name.startswith("npc_dota_hero_"):
                                    h_name = f"npc_dota_hero_{h_name}"
                            else:
                                h_name = "unknown"
                            
                            # Map Lane ID to Position Text
                            # 1: Bot, 2: Mid, 3: Top, 4: Jungle, 5: Roam
                            lane = p.get("lane")
                            is_radiant = idx < 5
                            position_name = "unknown"
                            
                            if lane:
                                if lane == 1: # Bot
                                    position_name = "Safe Lane" if is_radiant else "Off Lane"
                                elif lane == 2: # Mid
                                    position_name = "Mid Lane"
                                elif lane == 3: # Top
                                    position_name = "Off Lane" if is_radiant else "Safe Lane"
                                elif lane == 4 or lane == 5:
                                    position_name = "Jungle" if lane == 4 else "Roaming"
                            
                            # Extract Player Name (persona)
                            p_name = p.get("personaname")
                            
                            hero_entry = {
                                "player_id": idx,
                                "hero_name": h_name,
                                "team": "radiant" if idx < 5 else "dire",
                                "position": position_name, 
                                "player_name": p_name,
                                "steam_id": str(p.get("account_id") or "") or None
                            }
                            fallback_heroes.append(hero_entry)
                        
                        if fallback_heroes:
                            parsed["heroes"] = fallback_heroes
                            logger.info(f"Successfully recovered {len(fallback_heroes)} heroes from OpenDota API (using ID mapping)")
            except Exception as e:
                logger.error(f"OpenDota fallback failed: {str(e)}")
                # Continue execution - we don't want to fail the upload just because fallback failed

        
        # Check if match already analyzed BY THIS USER
        # We allow multiple users to analyze same match, so check strictly by player_id
        existing = db.query(Match).filter(
            Match.match_id == parsed["match_id"],
            Match.player_id == current_user.id
        ).first()
        
        # Analyze match
        analyzer = MatchAnalyzer()
        analysis = analyzer.analyze_match(parsed)
        if "players" in parsed and "heroes" not in parsed:
            parsed["heroes"] = [p.get("hero_name", p.get("hero")) for p in parsed["players"]]
            logger.info(f"Built heroes array: {parsed['heroes']}")
        else:
            logger.info(f"Heroes in parsed: {parsed.get('heroes', 'NOT FOUND')}")
        
        # Prepare full metrics dict
        full_metrics = analysis["metrics"].copy()
        full_metrics.update({
            "overall_score": analysis["overall_score"],
            "strengths": analysis["strengths"],
            "weaknesses": analysis["weaknesses"],
            "power_spikes": analysis["power_spikes"],
            "mistakes": analysis["mistakes"]
        })
        
        if existing:
            logger.info(f"Match {parsed['match_id']} already exists. Updating record with fresh data.")
            match = existing
            match.hero_name = parsed["hero_name"]
            match.duration_minutes = parsed["duration_minutes"]
            match.result = parsed["result"]
            
            # Ensure parsed_data has heroes array and steam_id from normalized data
            final_parsed_data = parsed.get("full_data", {}).copy() if parsed.get("full_data") else {}
            final_parsed_data["heroes"] = parsed.get("heroes", [])
            final_parsed_data["steam_id"] = parsed.get("steam_id")
            
            match.parsed_data = final_parsed_data
            match.metrics = full_metrics
            match.advice = analysis["advice"]
            match.steam_id = parsed.get("steam_id")
            # Ensure player_id matches current user if they are re-uploading
            match.player_id = current_user.id
            
            db.commit()
            db.refresh(match)
            
            # Extract heroes for selection
            heroes_in_match = _extract_heroes_from_match(match.parsed_data)
            
            return {
                "id": match.id,
                "match_id": match.match_id,
                "status": "awaiting_hero_selection" if heroes_in_match else "analyzed",
                "heroes_in_match": heroes_in_match,
                "metrics_count": len(analysis["metrics"]),
                "advice_count": len(analysis["advice"]),
                "overall_score": analysis["overall_score"]
            }
        
        # Ensure parsed_data has heroes array and steam_id from normalized data
        final_parsed_data = parsed.get("full_data", {}).copy() if parsed.get("full_data") else {}
        final_parsed_data["heroes"] = parsed.get("heroes", [])
        final_parsed_data["steam_id"] = parsed.get("steam_id")

        # Create match record
        match = Match(
            match_id=parsed["match_id"],
            player_id=current_user.id,
            steam_id=parsed.get("steam_id"),
            hero_name=parsed["hero_name"],
            duration_minutes=parsed["duration_minutes"],
            result=parsed["result"],
            parsed_data=final_parsed_data,
            metrics=full_metrics,
            advice=analysis["advice"]
        )
        
        db.add(match)
        db.commit()
        db.refresh(match)
        
        # Send notification email (non-blocking)
        try:
            email_service.send_match_analysis_complete(
                to_email=current_user.email,
                match_id=str(match.id),
                hero_name=match.hero_name,
                score=analysis["overall_score"]
            )
        except Exception:
            pass
        
        # Extract heroes for selection
        heroes_in_match = _extract_heroes_from_match(match.parsed_data)
        
        return {
            "id": match.id,
            "match_id": match.match_id,
            "status": "awaiting_hero_selection" if heroes_in_match else "analyzed",
            "heroes_in_match": heroes_in_match,
            "metrics_count": len(analysis["metrics"]),
            "advice_count": len(analysis["advice"]),
            "overall_score": analysis["overall_score"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to analyze replay: {e}")
        error_str = str(e).lower()
        
        # Provide helpful user-facing error messages
        if "memory limit" in error_str or "code -9" in error_str:
            detail = (
                "Replay file is too large for free tier. "
                "Please upload a replay < 50MB or try premium tier."
            )
        elif "timeout" in error_str:
            detail = (
                "Parsing took too long. The replay may be corrupted. "
                "Try uploading a different file."
            )
        elif "parsing_method" in error_str or "manta_fallback" in error_str:
            detail = (
                "Limited analysis available. "
                "For full match analytics, try a smaller replay."
            )
        else:
            detail = (
                "Failed to parse replay. Please try a different .dem file "
                "or contact support."
            )
        
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)
    finally:
        # Cleanup temp files
        try:
            shutil.rmtree(temp_dir)
        except Exception:
            pass


@router.get("", response_model=List[MatchResponse])
async def list_matches(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    hero: Optional[str] = None,
    result: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> List[MatchResponse]:
    """
    List user's analyzed matches.
    
    Args:
        skip: Number of records to skip (pagination).
        limit: Maximum records to return.
        hero: Optional hero name filter.
        result: Optional result filter (WIN/LOSS).
        current_user: Authenticated user.
        db: Database session.
        
    Returns:
        List of matches.
    """
    query = db.query(Match).filter(Match.player_id == current_user.id)
    
    if hero:
        query = query.filter(Match.hero_name.ilike(f"%{hero}%"))
    
    if result:
        query = query.filter(Match.result == result.upper())
    
    matches = query.order_by(Match.created_at.desc()).offset(skip).limit(limit).all()
    
    return [
        MatchResponse(
            id=m.id,
            match_id=m.match_id,
            hero_name=m.hero_name,
            duration_minutes=m.duration_minutes,
            result=m.result,
            overall_score=m.metrics.get("overall_score") if m.metrics else None,
            created_at=m.created_at,
            selected_hero_name=m.selected_hero_name,
            selected_at=m.selected_at
        )
        for m in matches
    ]


@router.get("/{match_id}", response_model=MatchDetailResponse)
async def get_match(
    match_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> MatchDetailResponse:
    """
    Get detailed match analysis.
    
    Args:
        match_id: Internal match ID or Dota Match ID (string).
        current_user: Authenticated user.
        db: Database session.
    """
    logger.info(f"GET /matches/{match_id} - user={current_user.id}")
    
    try:
        # Try finding by Dota match_id first
        logger.info(f"Searching by match_id (Dota ID): {match_id}")
        match = db.query(Match).filter(
            Match.match_id == match_id,
            Match.player_id == current_user.id
        ).first()
        
        if match:
            logger.info(f"✓ Found by Dota match_id: internal_id={match.id}")
        else:
            logger.info(f"✗ Not found by Dota match_id, trying internal ID...")
            
            # Fallback: check if it's an internal ID
            if match_id.isdigit():
                val = int(match_id)
                if val < 100000000:
                    logger.info(f"Searching by internal ID: {val}")
                    match = db.query(Match).filter(
                        Match.id == val,
                        Match.player_id == current_user.id
                    ).first()
                    
                    if match:
                        logger.info(f"✓ Found by internal ID: {val}")
                    else:
                        logger.info(f"✗ Not found by internal ID: {val}")
                else:
                    logger.info(f"ID {val} too large (>{100000000}), skipping internal ID lookup")
        
        if not match:
            logger.warning(f"Match {match_id} not found for user {current_user.id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Match not found"
            )
        
        if match.player_id != current_user.id:
            logger.warning(f"Unauthorized access to match {match.id} by user {current_user.id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this match"
            )
        
        logger.info(f"Loading match data: id={match.id}, hero={match.hero_name}")
        
        metrics = match.metrics or {}
        advice = match.advice or []
        
        # Ensure parsed_data has heroes array
        parsed_data = match.parsed_data or {}
        
        logger.info(f"parsed_data keys: {list(parsed_data.keys())}")
        logger.info(f"Has 'heroes' key: {'heroes' in parsed_data}")
        
        # Check if heroes key is missing or empty
        if not parsed_data.get('heroes'):
            logger.warning("Heroes array missing, rebuilding...")
            heroes = []
            if "players" in parsed_data:
                for idx, p in enumerate(parsed_data["players"]):
                    # Build detailed hero object
                    hero_name = p.get("hero_name", p.get("hero", "unknown"))
                    heroes.append({
                        "player_id": idx,
                        "hero_name": hero_name,
                        "team": "radiant" if idx < 5 else "dire",
                        "position": p.get("position", "unknown"),
                        "steam_id": str(p.get("account_id") or "")
                    })
            
            parsed_data['heroes'] = heroes
            logger.info(f"✓ Rebuilt {len(heroes)} heroes")
        
        # Ensure we have the list for the response
        heroes_list = parsed_data.get('heroes', [])
        logger.info(f"✓ GET Match {match_id}: {len(heroes_list)} heroes")

        # Map to schema if needed (schema expects HeroInMatch)
        # parsed_data heroes don't have hero_display_name usually, schema defines it.
        # We might need to populate it.
        mapped_heroes = []
        for h in heroes_list:
            # Create a copy or new dict to match schema
            h_schema = h.copy() if isinstance(h, dict) else {"hero_name": str(h)}
            
            # CRITICAL: Strip 'npc_dota_hero_' prefix for OpenDota images
            raw_name = h_schema.get("hero_name", "unknown")
            short_name = raw_name.replace("npc_dota_hero_", "") if raw_name else "unknown"
            h_schema["hero_name"] = short_name
            
            if "hero_display_name" not in h_schema:
                 h_schema["hero_display_name"] = short_name.replace("_", " ").title()
            
            # Ensure required fields
            if "player_id" not in h_schema:
                h_schema["player_id"] = heroes_list.index(h)
            if "team" not in h_schema:
                h_schema["team"] = "radiant" if h_schema.get("player_id", 0) < 5 else "dire"
            if "position" not in h_schema:
                h_schema["position"] = "unknown"
                
            mapped_heroes.append(h_schema)


        response = MatchDetailResponse(
            id=match.id,
            match_id=match.match_id,
            hero_name=match.hero_name,
            duration_minutes=match.duration_minutes,
            result=match.result,
            metrics=metrics,
            advice=advice,
            overall_score=metrics.get("overall_score", 0),
            strengths=metrics.get("strengths", []),
            weaknesses=metrics.get("weaknesses", []),
            power_spikes=metrics.get("power_spikes", []),
            mistakes=metrics.get("mistakes", []),
            rank_tier=metrics.get("rank_tier", 0),
            items=match.parsed_data.get("items", []) if match.parsed_data else [],
            parsed_data=parsed_data,
            created_at=match.created_at,
            selected_hero_name=match.selected_hero_name,
            selected_at=match.selected_at,
            steam_id=match.steam_id,
            heroes_in_match=mapped_heroes # Explicit return
        )

        
        logger.info(f"✓ Returning match response")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching match {match_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )



@router.delete("/{match_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_match(
    match_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> None:
    """
    Delete a match analysis.
    
    Args:
        match_id: Internal match ID or Dota Match ID (string).
    """
    match = None
    if match_id.isdigit():
        val = int(match_id)
        if val < 2147483647:
            match = db.query(Match).filter(Match.id == val).first()
    
    if not match:
        match = db.query(Match).filter(Match.match_id == match_id).first()
        
    if not match:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match not found"
        )
    
    if match.player_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this match"
        )
    
    db.delete(match)
    db.commit()


@router.get("/compare/{match1_id}/{match2_id}", response_model=MatchComparisonResponse)
async def compare_matches(
    match1_id: int,
    match2_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> MatchComparisonResponse:
    """
    Compare two matches to show performance delta.
    """
    m1 = db.query(Match).filter(Match.id == match1_id, Match.player_id == current_user.id).first()
    m2 = db.query(Match).filter(Match.id == match2_id, Match.player_id == current_user.id).first()
    
    if not m1 or not m2:
        raise HTTPException(status_code=404, detail="One or both matches not found")
    
    # helper to format response (extract logic from get_match if it grows more complex)
    def to_detail(m):
        metrics = m.metrics or {}
        return MatchDetailResponse(
            id=m.id,
            match_id=m.match_id,
            hero_name=m.hero_name,
            duration_minutes=m.duration_minutes,
            result=m.result,
            metrics=metrics,
            advice=m.advice or [],
            overall_score=metrics.get("overall_score"),
            strengths=metrics.get("strengths", []),
            weaknesses=metrics.get("weaknesses", []),
            power_spikes=metrics.get("power_spikes", []),
            mistakes=metrics.get("mistakes", []),
            created_at=m.created_at
        )

    # Calculate delta for primary metrics
    metrics1 = m1.metrics or {}
    metrics2 = m2.metrics or {}
    
    important_metrics = [
        "combat_kda", "farming_gpm", "farming_xpm", 
        "laning_cs_per_min", "overall_score"
    ]
    
    improvements = {}
    for key in important_metrics:
        val1 = metrics1.get(key, 0)
        val2 = metrics2.get(key, 0)
        improvements[key] = round(val2 - val1, 2)
        
    return MatchComparisonResponse(
        match1=to_detail(m1),
        match2=to_detail(m2),
        improvements=improvements
    )


@router.post("/{match_id}/select-hero", response_model=SelectHeroResponse)
async def select_hero(
    match_id: str,
    request: SelectHeroRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> SelectHeroResponse:
    """
    Select the user's hero from the match and get metrics for that hero.
    
    Args:
        match_id: Dota Match ID or internal ID.
        request: Request body containing hero_name.
        current_user: Authenticated user.
        db: Database session.
        
    Returns:
        Selected hero metrics and match data.
    """
    # Find match by match_id first (Dota ID), then by internal ID
    match = db.query(Match).filter(
        Match.match_id == match_id,
        Match.player_id == current_user.id
    ).first()
    
    if not match and match_id.isdigit():
        val = int(match_id)
        if val < 100000000:
            match = db.query(Match).filter(
                Match.id == val,
                Match.player_id == current_user.id
            ).first()
    
    if not match:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match not found"
        )
    
    if not match.parsed_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Match has no parsed data for hero selection"
        )
    
    # Find the selected hero in parsed_data
    players = match.parsed_data.get("players", [])
    selected_player = None
    
    for player in players:
        player_hero = player.get("hero_name", player.get("hero", ""))
        # Normalize to short names for robust comparison
        # Frontend sends short name (e.g. "pudge"), DB might have "npc_dota_hero_pudge"
        p_short = player_hero.replace("npc_dota_hero_", "")
        r_short = request.hero_name.replace("npc_dota_hero_", "")
        
        if p_short == r_short:
            selected_player = player
            break
    
    if not selected_player:
        # Try finding by display name or loose match as fallback
        for player in players:
             player_hero = player.get("hero_name", player.get("hero", ""))
             if request.hero_name.lower() in player_hero.lower():
                 selected_player = player
                 break
                 
    if not selected_player:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Hero '{request.hero_name}' not found in match"
        )
    
    # Extract ALL metrics for this player
    metrics = {
        # Basic stats
        "kills": selected_player.get("kills", 0),
        "deaths": selected_player.get("deaths", 0),
        "assists": selected_player.get("assists", 0),
        "gpm": selected_player.get("gpm", selected_player.get("gold_per_min", 0)),
        "xpm": selected_player.get("xpm", selected_player.get("xp_per_min", 0)),
        "last_hits": selected_player.get("last_hits", selected_player.get("lh", 0)),
        "denies": selected_player.get("denies", 0),
        
        # Damage stats
        "hero_damage": selected_player.get("hero_damage", 0),
        "tower_damage": selected_player.get("tower_damage", 0),
        "hero_healing": selected_player.get("hero_healing", 0),
        
        # Combat stats
        "teamfight_participation": selected_player.get("teamfight_participation", 0),
        "stuns": selected_player.get("stuns", 0),
        "obs_placed": selected_player.get("obs_placed", selected_player.get("observer_wards_placed", 0)),
        "sen_placed": selected_player.get("sen_placed", selected_player.get("sentry_wards_placed", 0)),
        
        # Lane phase
        "lh_10": selected_player.get("lh_t", [0]*10)[-1] if selected_player.get("lh_t") else 0,
        "gold_10": selected_player.get("gold_t", [0]*10)[-1] if selected_player.get("gold_t") else 0,
        
        # Items
        "items": selected_player.get("items", []),
        "item_timings": selected_player.get("item_timings", selected_player.get("purchase_log", {})),
        
        # Position info
        "lane": selected_player.get("lane", selected_player.get("lane_role", 0)),
        "is_roaming": selected_player.get("is_roaming", False),
        
        # Full player data for advanced metrics
        "player_data": selected_player
    }
    
    # Calculate KDA
    deaths = max(metrics["deaths"], 1)
    metrics["kda"] = round((metrics["kills"] + metrics["assists"]) / deaths, 2)
    
    # Store selection in match
    match.selected_hero_name = request.hero_name
    match.selected_at = datetime.utcnow()
    match.hero_name = request.hero_name  # Update primary hero field
    
    # Re-analyze with the selected player's data
    analyzer = MatchAnalyzer()
    
    # Build analysis input from selected player
    analysis_input = {
        "match_id": match.match_id,
        "duration_minutes": match.duration_minutes,
        "hero_name": request.hero_name,
        "result": match.result,
        "kills": metrics["kills"],
        "deaths": metrics["deaths"],
        "assists": metrics["assists"],
        "gpm": metrics["gpm"],
        "xpm": metrics["xpm"],
        "last_hits": metrics["last_hits"],
        "denies": metrics["denies"],
        "hero_damage": metrics["hero_damage"],
        "tower_damage": metrics["tower_damage"],
        "hero_healing": metrics["hero_healing"],
        "items": metrics["items"],
        "item_timings": metrics["item_timings"],
        "full_data": selected_player
    }
    
    analysis = analyzer.analyze_match(analysis_input)
    
    # Merge analysis metrics with extracted metrics
    full_metrics = analysis["metrics"].copy()
    full_metrics.update({
        "overall_score": analysis["overall_score"],
        "strengths": analysis["strengths"],
        "weaknesses": analysis["weaknesses"],
        "power_spikes": analysis["power_spikes"],
        "mistakes": analysis["mistakes"]
    })
    
    # Update match with new metrics
    match.metrics = full_metrics
    match.advice = analysis["advice"]
    
    db.commit()
    db.refresh(match)
    
    logger.info(f"Hero selected: {request.hero_name} for match {match_id} by user {current_user.id}")
    
    return SelectHeroResponse(
        match_id=match.match_id,
        selected_hero=request.hero_name,
        metrics=full_metrics,
        parsed_data=match.parsed_data
    )
