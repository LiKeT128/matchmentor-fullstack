"""Matches API endpoints for replay upload and analysis."""

import os
import shutil
import tempfile
import logging
import time
import json
import asyncio
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
    
    # If we get here, it means we don't have valid cached data
    # Fetch from OpenDota API
    try:
        from app.services.opendota_client import get_opendota_client
        client = get_opendota_client()
        
        # Initial fetch
        match_data = await client.get_match(match_id)
        
        # CHECK: If data is incomplete (not parsed), request parse and POLL
        if not client.is_data_complete(match_data):
            logger.info(f"Match {match_id} data is basic. Requesting deep parse...")
            await client.request_parse(match_id)
            
            # POLLING LOOP: Every 15s for up to 3 minutes (12 attempts)
            max_attempts = 12
            for attempt in range(max_attempts):
                logger.info(f"Polling OpenDota for {match_id} (Attempt {attempt+1}/{max_attempts})...")
                await asyncio.sleep(15)
                
                match_data = await client.get_match(match_id)
                if client.is_data_complete(match_data):
                    logger.info(f"✓ Match {match_id} finally parsed by OpenDota!")
                    break
                
                if attempt == max_attempts - 1:
                    logger.warning(f"! Polling timed out for {match_id}. Proceeding with basic data.")
        else:
            logger.info(f"✓ Match {match_id} is already fully parsed")

        heroes = match_data.get("heroes", [])
        radiant_win = match_data.get("radiant_win")
        result = "WIN" if radiant_win else "LOSS"
        
        # Create match record
        new_match = Match(
            match_id=match_id,
            player_id=current_user.id,
            steam_id=steam_id,
            hero_name="pending",
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
                "teamfights": match_data.get("teamfights", []),
            },
            metrics={},
            advice=[],
            source="opendota",
            created_at=datetime.utcnow()
        )
        db.add(new_match)
        db.commit()
        db.refresh(new_match)
        
        return {
            "match_id": match_id,
            "status": "found",
            "source": "opendota",
            "is_parsed": client.is_data_complete(match_data),
            "heroes_in_match": heroes,
            "duration_minutes": match_data.get("duration_minutes", 0),
            "radiant_win": radiant_win,
            "message": "Match found and parsed. Select your hero to analyze."
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
        
        parsed = {}
        try:
            logger.info(f"Calling parser.parse_replay on {temp_file}...")
            parsed = parser.parse_replay(temp_file)
            logger.info("Parser returned successfully.")
        except Exception as e:
            logger.warning(f"Local parsing failed: {e}. Attempting fallback via filename Match ID.")
            # Try to extract match ID from filename (e.g. 1234567890.dem)
            import re
            basename = os.path.basename(file.filename)
            match_id_match = re.search(r'(\d+)', basename)
            
            if match_id_match:
                extracted_id = match_id_match.group(1)
                logger.info(f"Extracted Match ID from filename: {extracted_id}")
                
                # Fetch from OpenDota
                try:
                    from app.services.opendota_client import OpenDotaClient
                    od_client = OpenDotaClient()
                    od_match = await od_client.get_match(extracted_id)
                    
                    if od_match:
                         # Construct minimal parsed object
                         parsed = {
                             "match_id": str(od_match.get("match_id")),
                             "duration_minutes": od_match.get("duration", 0) / 60,
                             "result": "WIN" if od_match.get("radiant_win") else "LOSS", # simplified
                             "hero_name": "unknown", # Will be fixed by hero selection or recover
                             "heroes": [], # Will be rebuilt
                             "players": [], # Will be rebuilt
                             "radiant_win": od_match.get("radiant_win"),
                             "full_data": od_match # Save full OD response
                         }
                         # We need to adapt 'players' from OD format to what our system expects (which is OD format mostly)
                         parsed["players"] = od_match.get("players", [])
                         logger.info(f"✓ Recovered match data from OpenDota for ID {extracted_id}")
                    else:
                        raise Exception("Match not found in OpenDota")
                except Exception as inner_e:
                    logger.error(f"OpenDota fallback failed: {inner_e}")
                    raise e # Raise original parsing error if fallback fails
            else:
                 raise e 

        # CRITICAL FIX: Validate that parsing actually succeeded
        # Check if we have meaningful data (not just status/filename)
        if not parsed or len(parsed.keys()) < 3:
            raise Exception("Parser returned empty or incomplete data")
        
        # Check for failure indicators
        if parsed.get("match_id") in ["unknown", None]:
            raise Exception("Parser failed to extract basic match information")
        
        # Log what we actually got
        logger.info(f"Parser returned data with keys: {list(parsed.keys())}")
        logger.info(f"Match ID: {parsed.get('match_id')}, Hero: {parsed.get('hero_name')}, Duration: {parsed.get('duration_minutes')}")
        
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
        # Perform initial analysis (broad)
        analysis = MatchAnalyzer().analyze_match(parsed, hero_name=parsed["hero_name"])
        
        # Ensure we construct valid heroes Recovery if missing
        if "heroes" not in parsed or not parsed["heroes"]:
             # Extract detailed heroes
             if "players" in parsed:
                 parsed["heroes"] = _extract_heroes_from_match(parsed)
                 logger.info(f"Rebuilt heroes array via extraction: {len(parsed['heroes'])} heroes")
             else:
                 logger.warning("No players found to rebuild heroes array")

        heroes_log = parsed.get('heroes')
        if heroes_log and len(heroes_log) > 0:
             logger.info(f"Heroes in parsed: Found {len(heroes_log)}")
        else:
             logger.info("Heroes in parsed: NOT FOUND/EMPTY")
        
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
            
            # Ensure parsed_data has all required fields
            final_parsed_data = parsed.copy()
            final_parsed_data["heroes"] = parsed.get("heroes", [])
            final_parsed_data["steam_id"] = parsed.get("steam_id")
            final_parsed_data["duration_seconds"] = parsed.get("duration", 0)
            
            # OOM Prevention: Do not store raw_events in database
            if "raw_events" in final_parsed_data:
                del final_parsed_data["raw_events"]
            
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
        
        # Prepare final_parsed_data from the parser output
        #parsed is the match_data dict from odota_parser_client
        final_parsed_data = parsed.copy()
        
        # Ensure heroes array and steam_id are correctly mapped
        final_parsed_data["heroes"] = parsed.get("heroes", [])
        final_parsed_data["steam_id"] = parsed.get("steam_id")
        
        # CRITICAL: Fix Duration keys for frontend compatibility
        final_parsed_data["duration_seconds"] = parsed.get("duration", 0)
        
        # OOM Prevention: Do not store raw_events in database
        if "raw_events" in final_parsed_data:
            del final_parsed_data["raw_events"]

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
            duration=(m.parsed_data.get("duration_seconds") if m.parsed_data else 0) or (m.duration_minutes * 60),
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
            
            # Ensure required fields and fix Roles
            if "player_id" not in h_schema:
                h_schema["player_id"] = heroes_list.index(h)
            if "team" not in h_schema:
                h_schema["team"] = "radiant" if h_schema.get("player_id", 0) < 5 else "dire"
            
            # Remap numeric positions to readable roles
            pos = str(h_schema.get("position", "unknown"))
            pos_map = {
                "1": "Safe Lane", "2": "Mid Lane", "3": "Off Lane", 
                "4": "Soft Support", "5": "Hard Support"
            }
            if pos in pos_map:
                h_schema["position"] = pos_map[pos]
                
            if "position" not in h_schema:
                h_schema["position"] = "unknown"
                
            mapped_heroes.append(h_schema)


        response = MatchDetailResponse(
            id=match.id,
            match_id=match.match_id,
            hero_name=match.hero_name,
            duration_minutes=match.duration_minutes,
            duration=(match.parsed_data.get("duration_seconds") if match.parsed_data else 0) or (match.duration_minutes * 60),
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



from pydantic import BaseModel

class SelectHeroRequest(BaseModel):
    """Request body for selecting a hero and analyzing match."""
    match_id: Optional[str] = None
    hero_name: str


@router.post("/{match_id}/select-hero", response_model=MatchDetailResponse)
async def select_hero(
    match_id: str,
    request: SelectHeroRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Select a hero from the match and analyze that hero's performance.
    
    This endpoint:
    1. Finds the match in database
    2. Validates the hero exists in parsed match data
    3. Calls MatchAnalyzer.analyze_match() for that specific hero
    4. Saves the analysis results to database
    5. Returns complete metrics and advice to frontend
    """
    
    logger.info(f"[select_hero] START: match_id={match_id}, hero_name={request.hero_name}, user_id={current_user.id}")
    
    try:
        # STEP 1: Validate inputs exist
        if not match_id or not match_id.strip():
            logger.error("[select_hero] FAIL: match_id is empty")
            raise ValueError("match_id is required")
        
        if not request.hero_name or not request.hero_name.strip():
            logger.error("[select_hero] FAIL: hero_name is empty")
            raise ValueError("hero_name is required")
        
        logger.info(f"[select_hero] STEP 1 OK: Inputs validated")
        
        # STEP 2: Find match in database
        logger.info(f"[select_hero] STEP 2: Querying database for match_id={match_id}")
        
        match = db.query(Match).filter(
            Match.match_id == match_id,
            Match.player_id == current_user.id
        ).first()
        
        if not match and match_id.isdigit():
            val = int(match_id)
            if val < 100000000:
                logger.info(f"[select_hero] Fallback: Searching by internal ID: {val}")
                match = db.query(Match).filter(
                    Match.id == val,
                    Match.player_id == current_user.id
                ).first()
        
        if not match:
            logger.error(f"[select_hero] STEP 2 FAIL: Match {match_id} not found for user {current_user.id}")
            raise ValueError(f"Match {match_id} not found")
        
        logger.info(f"[select_hero] STEP 2 OK: Found match (id={match.id})")
        
        # STEP 3: Parse JSON from database
        logger.info(f"[select_hero] STEP 3: Parsing match.parsed_data...")
        
        try:
            # Handle both string and dict formats for robustness
            if isinstance(match.parsed_data, str):
                parsed_data = json.loads(match.parsed_data)
            else:
                parsed_data = match.parsed_data
                
            heroes_count = len(parsed_data.get("heroes", []))
            logger.info(f"[select_hero] STEP 3 OK: Parsed JSON with {heroes_count} heroes")
        except json.JSONDecodeError as e:
            logger.error(f"[select_hero] STEP 3 FAIL: JSON error - {str(e)}")
            raise ValueError(f"Invalid JSON in parsed_data")
        except Exception as e:
            logger.error(f"[select_hero] STEP 3 FAIL: Unexpected parse error - {str(e)}")
            raise ValueError(f"Failed to process match data")
        
        # STEP 4: Validate hero exists in match
        logger.info(f"[select_hero] STEP 4: Searching for hero '{request.hero_name}'...")
        
        heroes_list = parsed_data.get("heroes", [])
        hero_found = False
        
        for hero in heroes_list:
            if isinstance(hero, dict):
                 if hero.get("hero_name") == request.hero_name or hero.get("hero") == request.hero_name:
                    hero_found = True
                    break
            elif isinstance(hero, str):
                 if hero == request.hero_name:
                      hero_found = True
                      break
        
        if not hero_found:
            # Try approximate matching if exact fail
            logger.warning(f"Exact match for {request.hero_name} failed. Checking mapped names...")
            # ... can add mapping logic here if needed
            
            available = [h.get("hero_name", h) if isinstance(h, dict) else h for h in heroes_list][:5]
            logger.error(f"[select_hero] STEP 4 FAIL: Hero '{request.hero_name}' not found. Available: {available}...")
            raise ValueError(f"Hero '{request.hero_name}' not in this match")
        
        logger.info(f"[select_hero] STEP 4 OK: Hero found")

        # STEP 4: Get and clean parsed data
        logger.info(f"[select_hero] STEP 4: Loading parsed_data...")
        parsed_data = match.parsed_data or {}
        
        # SELF-HEALING: If this match has oversized raw_events, clean it up
        if "raw_events" in parsed_data:
            logger.info(f"[select_hero] CLEANUP: Removing oversized raw_events from legacy record")
            new_parsed_data = parsed_data.copy()
            del new_parsed_data["raw_events"]
            match.parsed_data = new_parsed_data
            try:
                db.commit()
                logger.info(f"[select_hero] CLEANUP: Database cleaned and committed")
                parsed_data = new_parsed_data # Use cleaned data for analysis
            except Exception as e:
                db.rollback()
                logger.warning(f"[select_hero] CLEANUP FAIL: {e}")

        # STEP 5: Create MatchAnalyzer
        logger.info(f"[select_hero] STEP 5: Initialize MatchAnalyzer...")
        try:
            analyzer = MatchAnalyzer()
            logger.info(f"[select_hero] STEP 5 OK: Analyzer created")
        except Exception as e:
            logger.error(f"[select_hero] STEP 5 FAIL: {str(e)}", exc_info=True)
            raise ValueError(f"Analyzer initialization failed: {str(e)}")

        # STEP 6: Analyze match
        logger.info(f"[select_hero] STEP 6: Calling analyze_match()...")
        print(f"DEBUG: Starting analyze_match for {request.hero_name}...", flush=True)
        start_time = time.time()
        
        try:
            analysis = analyzer.analyze_match(parsed_data, hero_name=request.hero_name)
            duration = time.time() - start_time
            logger.info(f"[select_hero] STEP 6 OK: Analysis complete in {duration:.2f}s")
            print(f"DEBUG: analyze_match finished in {duration:.2f}s", flush=True)
        except Exception as e:
            logger.error(f"[select_hero] STEP 6 FAIL: {str(e)}", exc_info=True)
            print(f"DEBUG: analyze_match FAILED: {e}", flush=True)
            raise ValueError(f"Analysis failed: {str(e)}")
        
        # STEP 7: Prepare data
        logger.info(f"[select_hero] STEP 7: Preparing data results...")
        metrics = analysis.get("metrics", {})
        advice = analysis.get("advice", [])
        
        # STEP 8: Update match record
        logger.info(f"[select_hero] STEP 8: Updating match record fields...")
        
        match.selected_hero_name = request.hero_name
        match.selected_at = datetime.utcnow()
        match.hero_name = request.hero_name
        match.metrics = metrics
        match.advice = advice
        match.analysis_logs = analysis.get("analysis_logs")
        
        # Explicitly mark as modified for JSON update tracking
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(match, "metrics")
        flag_modified(match, "advice")
        flag_modified(match, "analysis_logs")
        
        logger.info(f"[select_hero] STEP 8 OK: Record updated in session")
        
        # STEP 9: Commit to database
        logger.info(f"[select_hero] STEP 9: Committing to database...")
        
        try:
            db.commit()
            logger.info(f"[select_hero] STEP 9 OK: Commit successful")
        except Exception as e:
            db.rollback()
            logger.error(f"[select_hero] STEP 9 FAIL: {str(e)}", exc_info=True)
            raise ValueError(f"Database commit failed: {str(e)}")
        
        # STEP 10: Refresh and return
        logger.info(f"[select_hero] STEP 10: Refreshing and returning analysis...")
        
        db.refresh(match)
        
        # OPTIMIZATION: Do not send raw_events to frontend
        clean_parsed_data = parsed_data.copy()
        if "raw_events" in clean_parsed_data:
            del clean_parsed_data["raw_events"]

        response = {
            "success": True,
            "id": match.id,
            "match_id": match.match_id,
            "hero_name": match.hero_name,
            "duration_minutes": match.duration_minutes,
            "duration": (match.parsed_data.get("duration_seconds") if match.parsed_data else 0) or (match.duration_minutes * 60),
            "result": match.result,
            "metrics": metrics,
            "advice": advice,
            "overall_score": analysis.get("overall_score", 0),
            "strengths": analysis.get("strengths", []),
            "weaknesses": analysis.get("weaknesses", []),
            "power_spikes": analysis.get("power_spikes", []),
            "mistakes": analysis.get("mistakes", []),
            "rank_tier": metrics.get("rank_tier", 0),
            "items": match.parsed_data.get("items", []) if match.parsed_data else [],
            "parsed_data": clean_parsed_data,
            "created_at": match.created_at,
            "selected_hero_name": match.selected_hero_name,
            "selected_at": match.selected_at,
            "steam_id": match.steam_id,
            "heroes_in_match": _extract_heroes_from_match(match.parsed_data)
        }
        
        logger.info(f"[select_hero] SUCCESS: Endpoint complete for match {match_id}")
        return response
        
    except ValueError as e:
        logger.warning(f"[select_hero] ERROR_400: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[select_hero] ERROR_500: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/select-hero")
async def select_hero_legacy(
    request: SelectHeroRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Legacy support for body-only match_id."""
    return await select_hero(request.match_id, request, current_user, db)

