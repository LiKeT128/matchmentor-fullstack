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

    # Pre-process to find GPM/LH for role inference
    radiant_players = []
    dire_players = []
    
    for idx, entry in enumerate(heroes_raw):
        # Extract basic farming metrics
        if isinstance(entry, dict):
             gpm = entry.get("gold_per_min", entry.get("gpm", 0))
             lh = entry.get("last_hits", entry.get("lh", 0))
        else:
             gpm = 0
             lh = 0
             
        info = {"idx": idx, "gpm": gpm or 0, "lh": lh or 0}
        if idx < 5:
            radiant_players.append(info)
        else:
            dire_players.append(info)
            
    # Sort by GPM to find cores (Top 3) vs supports (Bottom 2)
    radiant_players.sort(key=lambda x: x["gpm"], reverse=True)
    dire_players.sort(key=lambda x: x["gpm"], reverse=True)
    
    # Set of indices that are likely cores
    radiant_cores = {p["idx"] for p in radiant_players[:3]}
    dire_cores = {p["idx"] for p in dire_players[:3]}
    
    # Import locally to avoid circular potential
    from app.services.hero_mapping import get_hero_name
    
    for idx, entry in enumerate(heroes_raw):
        # Initialize defaults
        raw_hero_name = "unknown"
        hero_id = None
        position = "unknown"
        steam_id = None
        team = "radiant" if idx < 5 else "dire"
        player_name = None
        
        is_core = (idx in radiant_cores) if idx < 5 else (idx in dire_cores)
        
        # Handle both dict entries and simple string entries
        if isinstance(entry, dict):
            # 1. Get Hero Name & ID
            raw_hero_name = entry.get("hero_name", entry.get("hero"))
            hero_id = entry.get("hero_id")
            
            # Fallback: If name is unknown/missing but we have ID, lookup name
            if (not raw_hero_name or "unknown" in str(raw_hero_name).lower()) and hero_id:
                try:
                    mapped_name = get_hero_name(int(hero_id))
                    if mapped_name and "unknown" not in mapped_name:
                         raw_hero_name = mapped_name
                except Exception:
                    pass
            
            # 2. Get Position/Lane
            p_val = entry.get("position")
            if p_val and str(p_val) != "unknown":
                position = p_val
            else:
                # Infer from 'lane' + Team + Core/Support status
                lane = entry.get("lane")
                if lane is not None:
                    try:
                        lane_val = int(lane)
                        is_radiant = (idx < 5)
                        # Explicit overwrite if available
                        if entry.get("isRadiant") is not None:
                            is_radiant = entry.get("isRadiant")
                        
                        if lane_val == 2: # Mid
                            position = "Mid Lane"
                        elif lane_val == 1: # Bot
                            if is_radiant: # Radiant Safe
                                position = "Safe Lane" if is_core else "Hard Support"
                            else: # Dire Off
                                position = "Off Lane" if is_core else "Soft Support"
                        elif lane_val == 3: # Top
                            if is_radiant: # Radiant Off
                                position = "Off Lane" if is_core else "Soft Support"
                            else: # Dire Safe
                                position = "Safe Lane" if is_core else "Hard Support"
                        elif lane_val in [4, 5]: # Jungle/Roam
                             position = "Roaming"
                    except:
                        pass
                else:
                    # No lane data? fallback to role guess
                    position = "Core" if is_core else "Support"

            # 3. Get User Info
            steam_id = entry.get("steam_id", entry.get("account_id"))
            
            # 4. Get Team String
            if entry.get("isRadiant") is not None:
                 team = "radiant" if entry["isRadiant"] else "dire"
            elif entry.get("team"):
                 team = entry["team"]

        else:
            # Entry is a string (hero name)
            raw_hero_name = str(entry) if entry else "unknown"
            # Basic fallback for strings
            position = "Core" if is_core else "Support"
        
        # CRITICAL: Map internal names to image CDN names
        raw_name = str(raw_hero_name) if raw_hero_name else "unknown"
        
        short_name = raw_name.replace("npc_dota_hero_", "")
        
        # Image mapping (Internal -> CDN Name)
        # Only map exceptions where internal name != CDN name
        image_mapping = {
            "zuus": "zeus",
            "windrunner": "windranger",
            "necrolyte": "necrophos",
            "treant": "treant_protector",
            "obsidian_destroyer": "outworld_destroyer",
            # "furion": "natures_prophet", # REVERTED: Internal 'furion' maps to 'furion.png' correctly
            "rattletrap": "clockwerk", # 'clockwerk.png' is standard? 'rattletrap.png' also exists? Using clockwerk to be safe if common.
            "shredder": "timbersaw",
            "skeleton_king": "wraith_king",
            "doom_bringer": "doom",
            "wisp": "io",
            "magnataur": "magnus",
            "life_stealer": "lifestealer",
            "abyssal_underlord": "underlord",
            #"nevermore": "shadow_fiend", # REMOVED: CDN uses 'nevermore.png'
            "queenofpain": "queen_of_pain",
            "vengefulspirit": "vengeful_spirit",
            "antimage": "antimage", 
            "broodmother": "broodmother",
            "night_stalker": "night_stalker",
            "centaur": "centaur",
        }
        
        image_name = image_mapping.get(short_name, short_name)
        
        # Generate display name from short name
        display_name = image_name.replace("_", " ").title()
        
        heroes.append({
            "player_id": idx,
            "hero_name": image_name,  # Use name compatible with official CDN
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
    Look up a match by Dota 2 match ID using OpenDota API.
    
    Strategy:
    1. Check DB cache first
    2. Fetch from OpenDota API (with retry logic)
    3. Validate heroes are not "unknown"
    4. Save to DB with source='opendota'
    """
    logger.info(f"Looking up match {match_id} for user {current_user.id}")
    
    # Check if already analyzed with valid data
    existing = db.query(Match).filter(
        Match.match_id == match_id,
        Match.player_id == current_user.id
    ).first()
    
    if existing and existing.parsed_data:
        heroes = existing.parsed_data.get("heroes", [])
        
        # Validate cached data has real heroes (not all unknown)
        unknown_count = sum(1 for h in heroes if h.get("hero_name") == "unknown")
        if heroes and unknown_count < 5:
            logger.info(f"Match {match_id} found in cache with valid heroes")
            return {
                "match_id": match_id,
                "status": "already_analyzed",
                "source": existing.source or "cached",
                "heroes_in_match": heroes,
                "parsed_data": existing.parsed_data
            }
        else:
            logger.warning(f"Cached match {match_id} has {unknown_count} unknown heroes, re-fetching...")
            # Delete stale record
            db.delete(existing)
            db.commit()
    
    # Fetch from OpenDota API with retry logic
    try:
        from app.services.opendota_client import get_opendota_client
        
        client = get_opendota_client()
        match_data = await client.get_match(match_id)
        
        logger.info(f"✓ OpenDota returned match {match_id}")
        
        # Heroes are already resolved by the new client
        heroes = match_data.get("heroes", [])
        
        # Validate: check for unknown heroes
        unknown_count = sum(1 for h in heroes if h.get("hero_name") == "unknown")
        if unknown_count > 5:
            logger.warning(f"OpenDota returned {unknown_count} unknown heroes - hero cache may be empty")
        
        # Determine result based on radiant_win (will be refined when user selects hero)
        radiant_win = match_data.get("radiant_win")
        result = "WIN" if radiant_win else "LOSS"  # Placeholder, refined on hero selection
        
        # Create match record with source tracking
        new_match = Match(
            match_id=match_id,
            player_id=current_user.id,
            hero_name="pending",  # Will be set on hero selection
            duration_minutes=match_data.get("duration_minutes", 0),
            result=result,
            parsed_data={
                "heroes": heroes,
                "players": match_data.get("players", []),
                "radiant_win": radiant_win,
                "radiant_score": match_data.get("radiant_score", 0),
                "dire_score": match_data.get("dire_score", 0),
                "game_mode": match_data.get("game_mode"),
                "picks_bans": match_data.get("picks_bans", []),
            },
            metrics={},
            advice=[],
            source="opendota",
            created_at=datetime.utcnow()
        )
        db.add(new_match)
        db.commit()
        db.refresh(new_match)
        
        logger.info(f"✓ Saved match {match_id} (ID={new_match.id}) from OpenDota for user {current_user.id}")

        return {
            "match_id": match_id,
            "status": "found",
            "source": "opendota",
            "heroes_in_match": heroes,
            "duration_minutes": match_data.get("duration_minutes", 0),
            "radiant_win": radiant_win,
            "message": "Match found. Select your hero to analyze."
        }
    
    except Exception as e:
        logger.error(f"OpenDota lookup failed for match {match_id}: {str(e)}")
        
        # Return actionable error message
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Could not fetch match from OpenDota. The match may not exist or OpenDota is temporarily unavailable. Try again in 30 seconds. Error: {str(e)}"
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
        
        # FALLBACK: If parser found no heroes OR mostly "unknown" heroes, OR "unknown" positions (lanes), try fetching from OpenDota
        heroes = parsed.get("heroes", [])
        unknown_name_count = sum(1 for h in heroes if "unknown" in h.get("hero_name", "unknown").lower())
        
        # Check for unknown positions (Clarity parser often misses lanes)
        unknown_pos_count = sum(1 for h in heroes if "unknown" in str(h.get("position", "unknown")).lower())
        
        if not heroes or len(heroes) == 0 or unknown_name_count > 5 or unknown_pos_count > 8:
            logger.warning(f"Parser missing data: {unknown_name_count} unknown names, {unknown_pos_count} unknown positions. Attempting OpenDota enrichment...")
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
            logger.info(f"UploadMatch: Match UPDATED. ID={match.id}, MatchID='{match.match_id}' (Type: {type(match.match_id)}), PlayerID={match.player_id}")
            
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
        logger.info(f"UploadMatch: Match CREATED. ID={match.id}, MatchID='{match.match_id}' (Type: {type(match.match_id)}), PlayerID={match.player_id}")
        
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
            
            # CRITICAL: Strip 'npc_dota_hero_' prefix, then REPAIR stale names, then Re-Prefix
            raw_name = h_schema.get("hero_name", "unknown")
            short_name = raw_name.replace("npc_dota_hero_", "") if raw_name else "unknown"
            
            # Map stale/display names (from old DB cache) back to internal Valve names
            corrections = {
                "zeus": "zuus",
                "magnus": "magnataur",
                "necrophos": "necrolyte",
                "windranger": "windrunner",
                "underlord": "abyssal_underlord",
                "io": "wisp",
                "wraith_king": "skeleton_king",
                "clockwerk": "rattletrap",
                "outworld_destroyer": "obsidian_destroyer",
                "timbersaw": "shredder",
                "nature's_prophet": "furion", "natures_prophet": "furion",
                "treant_protector": "treant",
                "centaur_warrunner": "centaur",
                "lifestealer": "life_stealer",
                "queen_of_pain": "queenofpain",
                "vengeful_spirit": "vengefulspirit",
                "doom": "doom_bringer",
                "shadow_fiend": "nevermore"
            }
            if short_name.lower() in corrections:
                short_name = corrections[short_name.lower()]
                
            # Re-apply prefix for frontend consistency
            h_schema["hero_name"] = f"npc_dota_hero_{short_name}"
            
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


def _extract_heroes_from_match(parsed_data: dict) -> list[dict]:
    """
    Extracts and formats hero data from parsed_data, including mapping to CDN names
    and basic stats.
    """
    heroes = []
    
    # Debug logging to trace structure
    keys = list(parsed_data.keys())
    logger.info(f"_extract_heroes: checking parsed_data keys: {keys}")
    
    # Try standard players list
    players = parsed_data.get("players", [])
    
    # Fallback to OpenDota raw structure
    if not players:
        logger.info("_extract_heroes: 'players' list empty/missing. Checking 'raw.players'.")
        raw_data = parsed_data.get("raw", {})
        players = raw_data.get("players", [])
    
    if not players:
        logger.warning("_extract_heroes: 'players' list empty/missing in parsed_data (checked raw also).")
        return []

    for idx, entry in enumerate(players):
        raw_hero_name = entry.get("hero_name") or entry.get("hero", "unknown")
        
        # Determine team
        team = "radiant"
        if entry.get("isRadiant") is not None:
             team = "radiant" if entry["isRadiant"] else "dire"
        elif idx >= 5: # Fallback based on index
             team = "dire"
             
        position = entry.get("position")
        steam_id = entry.get("account_id")

        # CRITICAL: Map internal names to image CDN names
        raw_name = str(raw_hero_name) if raw_hero_name else "unknown"
        
        short_name = raw_name.replace("npc_dota_hero_", "")
        
        # Image mapping (Internal -> CDN Name)
        # Only map exceptions where internal name != CDN name
        image_mapping = {
            "zuus": "zeus",
            "windrunner": "windranger",
            "necrolyte": "necrophos",
            "treant": "treant_protector",
            "obsidian_destroyer": "outworld_destroyer",
            # "furion": "natures_prophet", # REVERTED: Internal 'furion' maps to 'furion.png' correctly
            "rattletrap": "clockwerk", # 'clockwerk.png' is standard? 'rattletrap.png' also exists? Using clockwerk to be safe if common.
            "shredder": "timbersaw",
            "skeleton_king": "wraith_king",
            "doom_bringer": "doom",
            "wisp": "io",
            "magnataur": "magnus",
            "life_stealer": "lifestealer",
            "abyssal_underlord": "underlord",
            "nevermore": "shadow_fiend", # User confirmed shadow_fiend is needed
            "queenofpain": "queen_of_pain",
            "vengefulspirit": "vengeful_spirit",
            "antimage": "antimage", 
            "broodmother": "broodmother",
            "night_stalker": "night_stalker",
            "centaur": "centaur",
        }
        
        image_name = image_mapping.get(short_name, short_name)
        
        # Generate display name from short name
        display_name = image_name.replace("_", " ").title()
        
        # Extract stats if available (useful for OpenDota lookups)
        gpm = entry.get("gold_per_min") if isinstance(entry, dict) else 0
        xpm = entry.get("xp_per_min") if isinstance(entry, dict) else 0
        kda = 0
        if isinstance(entry, dict):
            k = entry.get("kills", 0)
            d = entry.get("deaths", 0)
            a = entry.get("assists", 0)
            if d == 0:
                kda = k + a
            else:
                 kda = round((k + a) / d, 2)
        
        heroes.append({
            "player_id": idx,
            "hero_name": image_name,  # Use name compatible with official CDN
            "hero_display_name": display_name,
            "team": team,
            "position": str(position) if position else "unknown",
            "steam_id": str(steam_id) if steam_id else None,
            # Basic stats for preview
            "gpm": gpm,
            "xpm": xpm,
            "kda": kda
        })
    
    logger.info(f"_extract_heroes: Returning {len(heroes)} heroes")
    if heroes:
        logger.info(f"  Sample: {heroes[0]}")
    
    return heroes

@router.post("/{match_id}/select-hero", response_model=SelectHeroResponse)
def select_hero_path(
    match_id: str,
    request: SelectHeroRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Selects a hero for a specific match using path parameter.
    This is the preferred endpoint for frontend (path: /api/matches/{match_id}/select-hero).
    """
    # Forward to main logic with match_id from path
    request.match_id = match_id
    return _select_hero_logic(request, current_user, db)


@router.post("/select-hero", response_model=SelectHeroResponse)
def select_hero(
    request: SelectHeroRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Selects a hero for a specific match and triggers analysis (body param version).
    For path param version, use POST /{match_id}/select-hero instead.
    """
    return _select_hero_logic(request, current_user, db)


def _select_hero_logic(
    request: SelectHeroRequest,
    current_user: User,
    db: Session
):
    """Shared logic for hero selection."""
    match_id = request.match_id
    logger.info(f"SelectHero: Entering. match_id='{match_id}', user_id={current_user.id}")

    try:
        # Find match by match_id first (Dota ID), then by internal ID
        match = db.query(Match).filter(
            Match.match_id == match_id,
            Match.player_id == current_user.id
        ).first()
        
        if match:
            logger.info(f"SelectHero: Found match by match_id (Dota ID). ID={match.id}")
        
        if not match and match_id.isdigit():
            val = int(match_id)
            # Verify length to ensure we don't mix up Dota ID (10 chars) with internal ID
            if val < 100000000:
                logger.info(f"SelectHero: Attempting fallback to internal ID lookup for {val}")
                match = db.query(Match).filter(
                    Match.id == val,
                    Match.player_id == current_user.id
                ).first()
                if match:
                     logger.info(f"SelectHero: Found match by Internal ID. MatchID={match.match_id}")
        
        if not match:
            logger.error(f"SelectHero: Match NOT FOUND. match_id='{match_id}', user_id={current_user.id}. Query returned None.")
            # Debug: Check if match exists for ANY user?
            debug_check = db.query(Match).filter(Match.match_id == match_id).first()
            if debug_check:
                logger.error(f"SelectHero: Match DOES exist but for player_id={debug_check.player_id}. Access Denied or ID Mismatch.")
            else:
                logger.error("SelectHero: Match does not exist in DB at all.")
                
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
        # 1. Try to find match in 'heroes' list (which has corrected names/data)
        heroes = match.parsed_data.get("heroes", [])
        matched_hero_entry = None
        
        logger.info(f"SelectHero: Request '{request.hero_name}'. Checking 'heroes' list ({len(heroes)} entries)")
        
        # Try exact match or fuzzy match on 'heroes' list
        for h in heroes:
            h_name = h.get("hero_name", "unknown")
            # Normalize
            h_short = h_name.replace("npc_dota_hero_", "")
            r_short = request.hero_name.replace("npc_dota_hero_", "")
            
            if h_short == r_short:
                matched_hero_entry = h
                break
                
        # If not found data in heroes, maybe try players directly (fallback)
        
        # Handle OpenDota structure: data might be in 'raw' -> 'players'
        players = match.parsed_data.get("players", [])
        if not players:
             logger.info("SelectHero: 'players' list empty/missing. Checking 'raw.players' (OpenDota style).")
             raw_data = match.parsed_data.get("raw", {})
             players = raw_data.get("players", [])
        
        selected_player = None
        
        if matched_hero_entry:
            pid = matched_hero_entry.get("player_id")
            logger.info(f"Found matched hero entry. Player ID: {pid}")
            
            # IMPORTANT: matched_hero_entry from 'heroes' already contains all metrics
            # (kills, deaths, gold_per_min, etc.) from our _normalize_match_data
            selected_player = matched_hero_entry
            
            # Optionally merge any missing fields from raw players array
            if players and pid is not None and 0 <= pid < len(players):
                raw_player = players[pid]
                # Only add fields that are missing from matched_hero_entry
                for key, value in raw_player.items():
                    if key not in selected_player or selected_player.get(key) in (None, 0, ""):
                        selected_player[key] = value
            
            logger.info(f"Selected player data: gpm={selected_player.get('gold_per_min')}, kills={selected_player.get('kills')}")
                 
        else:
            # Fallback: legacy search in 'players' list directly
            logger.info("Hero not found in 'heroes' list. Searching 'players' list directly...")
            for player in players:
                player_hero = player.get("hero_name", player.get("hero", ""))
                
                # Check for OpenDota hero_id if name missing
                if not player_hero and "hero_id" in player:
                     # This would require ID->Name map, skipping for now unless critical
                     pass
                     
                p_short = str(player_hero).replace("npc_dota_hero_", "")
                r_short = request.hero_name.replace("npc_dota_hero_", "")
                
                if p_short == r_short:
                    selected_player = player
                    break
                    
            if not selected_player:
                 # Try finding by display name or loose match as fallback
                for player in players:
                     player_hero = player.get("hero_name", player.get("hero", ""))
                     if player_hero and request.hero_name.lower() in str(player_hero).lower():
                         selected_player = player
                         break
        
        if not selected_player:
            logger.error(f"Hero '{request.hero_name}' NOT found in match {match.match_id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Hero '{request.hero_name}' not found in match"
            )
        
        # Extract ALL metrics for this player
        # Note: OpenDota fields are gold_per_min, xp_per_min, last_hits, denies.
        # Our internal parser fields are gpm, xpm, last_hits, denies.
        
        # Try to get metrics from standard keys, then OpenDota keys
        gpm = selected_player.get("gpm") or selected_player.get("gold_per_min", 0)
        xpm = selected_player.get("xpm") or selected_player.get("xp_per_min", 0)
        last_hits = selected_player.get("last_hits", 0)
        denies = selected_player.get("denies", 0)
        
        kills = selected_player.get("kills", 0)
        deaths = selected_player.get("deaths", 0)
        assists = selected_player.get("assists", 0)
        
        # Calculate KDA
        if deaths == 0:
            kda = kills + assists
        else:
            kda = round((kills + assists) / deaths, 2)

        # Calculate Teamfight Participation
        radiant_score = match.parsed_data.get("radiant_score", 0)
        dire_score = match.parsed_data.get("dire_score", 0)
        
        # OpenDota often puts isRadiant in player object, otherwise infer from slot
        is_radiant = selected_player.get("isRadiant")
        if is_radiant is None:
            # Fallback: slots 0-127 are Radiant
            slot = selected_player.get("player_id", 0) # sometimes player_id is slot index 0-9
            # Wait, normalize_match_data sets player_id=idx (0-9). 
            # Slots are 0-4 (Rad), 128-132 (Dire). 
            # In normalize: 0-4 is Radiant.
            slot = selected_player.get("player_id", 0)
            is_radiant = slot < 5
            
        team_kills = radiant_score if is_radiant else dire_score
        if team_kills > 0:
            tf_participation = round(((kills + assists) / team_kills) * 100, 1)
        else:
            tf_participation = 0.0
            
        metrics = {
            # Basic stats
            "kills": kills,
            "deaths": deaths,
            "assists": assists,
            "kda": kda,
            "teamfight_participation": tf_participation,
            
            # Farming
            "gpm": gpm,
            "xpm": xpm,
            "last_hits": last_hits,
            "denies": denies,
            
            # Damage
            "hero_damage": selected_player.get("hero_damage", 0),
            "tower_damage": selected_player.get("tower_damage", 0),
            "hero_healing": selected_player.get("hero_healing", 0),
            
            # Advanced (Calculated)
            "damage_ratio": 0.0,
            "gold_efficiency": 0.0,
            "lane_efficiency": selected_player.get("lane_efficiency_pct", round(last_hits / (match.duration_minutes if match.duration_minutes > 0 else 30) * 10, 1)), 
            
            # New Metrics requested by user
            "vision_score": selected_player.get("vision_score") or (selected_player.get("obs_placed", 0) * 1.5 + selected_player.get("sen_placed", 0) * 1.5),
            "stuns": round(selected_player.get("stuns", 0), 1),
            "position_safety": max(0, 100 - (deaths * 5)), # Heuristic Survival Rating
            "camp_stacking": selected_player.get("camps_stacked", 0),
            
            # Lists
            "strengths": [],
            "weaknesses": [],
            "power_spikes": [],
            "mistakes": [],
            
            # Items
            "items": selected_player.get("items", []),
            "item_timings": selected_player.get("item_timings", {})
        }
        
        # Simple advice based on stats
        advice = []
        
        # 1. GPM Analysis
        role = selected_player.get("position", "unknown")
        is_core = role in ["Safe Lane", "Mid Lane", "Off Lane", "1", "2", "3"] or "Core" in role
        
        if is_core and gpm < 400:
             metrics["weaknesses"].append("Low GPM for core")
             advice.append({
                 "type": "farming",
                 "severity": "high",
                 "message": f"Your GPM ({gpm}) is very low for a core role.",
                 "suggestion": "Focus on last hitting in lane and taking jungle camps between waves."
             })
        elif is_core and gpm > 600:
             metrics["strengths"].append("Excellent Farming speed")
             advice.append({
                 "type": "farming",
                 "severity": "low",
                 "message": "Excellent farming efficiency!",
                 "suggestion": "Maintain this GPM to secure late game dominance."
             })
             
        # 2. Survival Analysis
        if deaths > 8:
            metrics["weaknesses"].append("High death count")
            advice.append({
                "type": "survival",
                "severity": "critical",
                "message": f"You died {deaths} times. Each death gives gold to enemies.",
                "suggestion": "Play safer when enemies are missing. Buy defensive items like BKB or Linkens."
            })
            
        # 3. Teamfight Analysis
        if tf_participation < 30.0:
            metrics["weaknesses"].append("Low teamfight impact")
            advice.append({
                "type": "fighting",
                "severity": "medium",
                "message": f"You participated in only {tf_participation}% of kills.",
                "suggestion": "Carry a TP scroll and join fights. Don't AFK farm when your team needs you."
            })
        elif tf_participation > 60.0:
            metrics["strengths"].append("High teamfight participation")
            advice.append({
                 "type": "fighting",
                 "severity": "low",
                 "message": "You are a key playmaker.",
                 "suggestion": "Your high participation is winning fights. Keep leading the charge."
             })
             
        # 4. Laning Analysis (Last Hits at 10m would be better, but using total last hits as proxy for now)
        if last_hits < 50 and match.duration_minutes > 20 and is_core:
             advice.append({
                 "type": "laning",
                 "severity": "high",
                 "message": "Very low CS count.",
                 "suggestion": "Practice last hitting in demo mode. Aim for 50 CS by 10 minutes."
             })
             
        if kda < 2.0:
            metrics["weaknesses"].append("Low KDA ratio")
            
        if kills > 10:
            metrics["strengths"].append("High kill participation")
        
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
        
        # Merge analysis metrics with extracted metrics (preserve our TF% and other raw data)
        full_metrics = analysis["metrics"].copy()
        
        # Ensure our calculated TF% is preserved if analyzer didn't calculate it better
        if "teamfight_participation" in metrics:
            full_metrics["teamfight_participation"] = metrics["teamfight_participation"]
            
        full_metrics.update({
            "overall_score": analysis["overall_score"],
            "strengths": analysis["strengths"] + metrics.get("strengths", []), # Merge strengths
            "weaknesses": analysis["weaknesses"] + metrics.get("weaknesses", []), # Merge weaknesses
            "power_spikes": analysis["power_spikes"],
            "mistakes": analysis["mistakes"]
        })
        
        # Update match with new metrics
        match.metrics = full_metrics
        match.advice = analysis["advice"] + advice  # Merge our ruled-based advice with analyzer advice
        
        db.commit()
        db.refresh(match)
        
        logger.info(f"Hero selected: {request.hero_name} for match {match_id} by user {current_user.id}")
        
        return SelectHeroResponse(
            match_id=match.match_id,
            selected_hero=request.hero_name,
            metrics=full_metrics,
            parsed_data=match.parsed_data
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"SelectHero Failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Hero selection failed: {str(e)}"
        )
