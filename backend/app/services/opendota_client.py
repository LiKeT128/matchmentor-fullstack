"""OpenDota API Client with retry logic and hero caching.

This module provides reliable access to OpenDota API with:
- Hero name caching (loaded once at startup)
- Retry logic with exponential backoff
- Proper timeout handling
- Normalized response format
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List

import httpx

logger = logging.getLogger(__name__)


# Global hero cache - populated at startup
HERO_CACHE: Dict[int, Dict[str, str]] = {}


class OpenDotaClient:
    """
    OpenDota API client with retry logic and hero caching.
    
    Attributes:
        BASE_URL: OpenDota API base URL.
        TIMEOUT: Request timeout in seconds.
        MAX_RETRIES: Maximum retry attempts.
    """
    
    BASE_URL = "https://api.opendota.com/api"
    TIMEOUT = 15.0
    MAX_RETRIES = 3
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize OpenDota client.
        
        Args:
            api_key: Optional OpenDota API key for higher rate limits.
        """
        self.api_key = api_key
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.TIMEOUT)
        return self._client
    
    async def close(self) -> None:
        """Close HTTP client connection."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
    
    @staticmethod
    async def load_heroes() -> int:
        """
        Load hero data from OpenDota API into global cache.
        
        Should be called once at application startup.
        
        Returns:
            Number of heroes loaded.
        """
        global HERO_CACHE
        
        url = f"{OpenDotaClient.BASE_URL}/heroes"
        logger.info(f"Loading heroes from OpenDota: {url}")
        
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(url)
                
                if resp.status_code == 200:
                    heroes = resp.json()
                    
                    for hero in heroes:
                        hero_id = hero.get("id")
                        if hero_id:
                            HERO_CACHE[hero_id] = {
                                "name": hero.get("name", "unknown"),  # e.g., "npc_dota_hero_antimage"
                                "localized_name": hero.get("localized_name", "Unknown"),  # e.g., "Anti-Mage"
                            }
                    
                    logger.info(f"✓ Loaded {len(HERO_CACHE)} heroes into cache")
                    return len(HERO_CACHE)
                else:
                    logger.error(f"Failed to load heroes: HTTP {resp.status_code}")
                    return 0
                    
        except Exception as e:
            logger.error(f"Failed to load heroes from OpenDota: {e}")
            return 0
    
    @staticmethod
    def get_hero_name(hero_id: int) -> str:
        """
        Get hero name from cache by ID.
        
        Args:
            hero_id: Dota 2 hero ID.
            
        Returns:
            Hero name (e.g., "npc_dota_hero_antimage") or "unknown".
        """
        hero = HERO_CACHE.get(hero_id)
        if hero:
            return hero.get("name", "unknown")
        
        # Fallback to static mapping
        from app.services.hero_mapping import HERO_MAP
        return HERO_MAP.get(hero_id, "unknown")
    
    @staticmethod
    def get_hero_display_name(hero_id: int) -> str:
        """
        Get hero localized/display name from cache by ID.
        
        Args:
            hero_id: Dota 2 hero ID.
            
        Returns:
            Hero display name (e.g., "Anti-Mage") or "Unknown".
        """
        hero = HERO_CACHE.get(hero_id)
        if hero:
            return hero.get("localized_name", "Unknown")
        
        # Fallback to static mapping (cleanup internally)
        from app.services.hero_mapping import HERO_MAP
        raw_name = HERO_MAP.get(hero_id, "Unknown")
        return raw_name.replace("npc_dota_hero_", "").replace("_", " ").title()
    
    async def get_match(self, match_id: str) -> Dict[str, Any]:
        """
        Fetch match data from OpenDota API with retry logic.
        
        Args:
            match_id: Dota 2 match ID.
            
        Returns:
            Normalized match data dict with heroes resolved.
            
        Raises:
            httpx.HTTPStatusError: On non-retryable HTTP errors.
            Exception: On all retries exhausted.
        """
        url = f"{self.BASE_URL}/matches/{match_id}"
        client = await self._get_client()
        
        last_error = None
        
        for attempt in range(self.MAX_RETRIES):
            delay = 2 ** attempt  # 1, 2, 4 seconds
            
            try:
                logger.info(f"OpenDota GET {url} (attempt {attempt + 1}/{self.MAX_RETRIES})")
                
                resp = await client.get(url)
                
                if resp.status_code == 200:
                    data = resp.json()
                    logger.info(f"✓ OpenDota returned match {match_id}")
                    
                    # Normalize and resolve heroes
                    return self._normalize_match_data(data)
                
                elif resp.status_code == 404:
                    logger.warning(f"OpenDota 404: Match {match_id} not found")
                    raise httpx.HTTPStatusError(
                        f"Match {match_id} not found",
                        request=resp.request,
                        response=resp
                    )
                
                elif resp.status_code == 429:
                    logger.warning(f"OpenDota 429: Rate limited, waiting {delay}s...")
                    await asyncio.sleep(delay)
                    continue
                
                elif resp.status_code >= 500:
                    logger.warning(f"OpenDota {resp.status_code}: Server error, retrying in {delay}s...")
                    await asyncio.sleep(delay)
                    continue
                
                else:
                    logger.error(f"OpenDota {resp.status_code}: Unexpected error")
                    last_error = Exception(f"OpenDota API error: {resp.status_code}")
                    
            except httpx.TimeoutException:
                logger.warning(f"OpenDota timeout, retrying in {delay}s...")
                await asyncio.sleep(delay)
                last_error = Exception("OpenDota API timeout")
                continue
                
            except httpx.HTTPStatusError:
                raise
                
            except Exception as e:
                logger.error(f"OpenDota request failed: {e}")
                last_error = e
                await asyncio.sleep(delay)
        
        # All retries exhausted
        raise last_error or Exception("OpenDota API request failed after all retries")
    
    async def request_parse(self, match_id: str) -> bool:
        """
        Request OpenDota to parse a match.
        
        Returns:
            True if request was accepted or already in queue.
        """
        url = f"{self.BASE_URL}/request/{match_id}"
        client = await self._get_client()
        
        try:
            logger.info(f"OpenDota POST {url} (requesting deep parse)")
            resp = await client.post(url)
            
            if resp.status_code in (200, 201):
                logger.info(f"✓ OpenDota parse request accepted for {match_id}")
                return True
            elif resp.status_code == 400:
                # 400 often means it's already in the queue or recently parsed
                logger.info(f"! OpenDota parse request for {match_id}: Already in queue or recent")
                return True
            else:
                logger.warning(f"OpenDota parse request failed: HTTP {resp.status_code}")
                return False
        except Exception as e:
            logger.error(f"Failed to request parse from OpenDota: {e}")
            return False

    def is_data_complete(self, match_data: Dict[str, Any]) -> bool:
        """
        Check if the match data contains deep parsed metrics.
        Criteria: Presence of gold_t, purchase_log, or teamfights.
        """
        players = match_data.get("heroes", []) or match_data.get("players", [])
        if not players:
            return False
            
        # Check first couple of players for time-series data
        sample_players = players[:2]
        for p in sample_players:
            if p.get("gold_t") or p.get("purchase_log") or p.get("lane_pos"):
                return True
                
        # Also check if teamfights exist (only in parsed matches)
        if match_data.get("teamfights"):
            return True
            
        return False
    
    def _normalize_match_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize OpenDota match data with resolved hero names.
        
        Args:
            data: Raw OpenDota API response.
            
        Returns:
            Normalized match data with heroes array.
        """
        players = data.get("players", [])
        heroes: List[Dict[str, Any]] = []
        
        for idx, player in enumerate(players):
            if not player:
                continue
            hero_id = player.get("hero_id")
            
            # Resolve hero name from cache
            hero_name_raw = self.get_hero_name(hero_id) if hero_id else "unknown"
            hero_display = self.get_hero_display_name(hero_id) if hero_id else "Unknown"
            
            # Strip prefix for CDN compatibility
            short_name = hero_name_raw.replace("npc_dota_hero_", "") if hero_name_raw else "unknown"
            
            # CDN expects specific names for some heroes that differ from internal Valve names
            image_mapping = {
                # "zuus": "zeus",  # Use internal 'zuus'
                # "windrunner": "windranger", # Use internal 'windrunner'
                # "necrolyte": "necrophos", # Use internal 'necrolyte'
                "treant": "treant_protector", # Check if 'treant' works?
                # "obsidian_destroyer": "outworld_destroyer", # Use internal
                # "rattletrap": "clockwerk", # Use internal 'rattletrap'
                # "shredder": "timbersaw", # Use internal 'shredder'
                "skeleton_king": "wraith_king", # SK might be WK now?
                # "doom_bringer": "doom", # Use internal
                # "wisp": "io", # Use internal
                # "magnataur": "magnus", # Use internal
                # "life_stealer": "life_stealer",
                "abyssal_underlord": "underlord", # Internal is abyssal_underlord
                # "nevermore": "shadow_fiend", # Use internal 'nevermore'
                "queenofpain": "queen_of_pain",
                "vengefulspirit": "vengeful_spirit",
                "antimage": "antimage",
                "broodmother": "broodmother",
                "night_stalker": "night_stalker",
                "centaur": "centaur",
            }
            
            image_name = image_mapping.get(short_name, short_name)
            
            # Determine team
            is_radiant = player.get("isRadiant", idx < 5)
            team = "radiant" if is_radiant else "dire"
            
            # Position Detection Strategy:
            # 1. Use 'lane' and 'lane_role' if available from OpenDota
            # 2. Fallback: Dynamic GPM-based ranking within team
            
            lane = player.get("lane")
            lane_role = player.get("lane_role")
            position = "unknown"
            
            # CRITICAL: Prioritize explicit lane_role if available (1=Safe, 2=Mid, 3=Off)
            # This fixes cases where a hero swaps lanes or lane coordinates are misleading
            if lane_role == 1:
                position = "Safe Lane"  # Semantic role 1 = Safe
            elif lane_role == 2:
                position = "Mid Lane"
            elif lane_role == 3:
                position = "Off Lane"   # Semantic role 3 = Off
            elif lane:
                if lane == 1:  # Bot
                    position = "Safe Lane" if is_radiant else "Off Lane"
                elif lane == 2:  # Mid
                    position = "Mid Lane"
                elif lane == 3:  # Top
                    position = "Off Lane" if is_radiant else "Safe Lane"
                elif lane == 4:
                    position = "Jungle"
                elif lane == 5:
                    position = "Roaming"
            
            # Fallback if position is still unknown
            if position == "unknown" and lane_role:
                role_map = {4: "Support"} # 1,2,3 handled above
                position = role_map.get(lane_role, position)

            # 2. Dynamic Performance Fallback (Crucial for the "Which hero did you play?" modal)
            if position == "unknown":
                # Find all players on the same team
                team_players = [p for i, p in enumerate(players) if p and p.get("isRadiant", i < 5) == is_radiant]
                # Sort by Last Hits (primary) and GPM (secondary) descending
                # This accurately separates Pos 1 (highest LH) from Pos 2 (Mid) and Supports
                sorted_by_perf = sorted(
                    team_players, 
                    key=lambda x: (x.get("last_hits", 0), x.get("gold_per_min", 0)), 
                    reverse=True
                )
                
                # Find this player's rank in the team
                try:
                    rank = sorted_by_perf.index(player)
                    rank_map = {
                        0: "Safe Lane",    # Pos 1
                        1: "Mid Lane",     # Pos 2
                        2: "Off Lane",     # Pos 3
                        3: "Soft Support", # Pos 4
                        4: "Hard Support"  # Pos 5
                    }
                    position = rank_map.get(rank, f"Pos {rank + 1}")
                except (ValueError, IndexError):
                    pass

            # 3. Final Fallback to Slot (Lobby Order) - only if GPM calculation failed
            if position == "unknown":
                player_slot = player.get("player_slot")
                if player_slot is not None:
                    slot_idx = player_slot if player_slot < 128 else player_slot - 128
                    fallback_map = {0: "Safe Lane", 1: "Mid Lane", 2: "Off Lane", 3: "Soft Support", 4: "Hard Support"}
                    position = fallback_map.get(slot_idx, "unknown")
            
            heroes.append({
                "player_id": idx,
                "hero_id": hero_id,
                "hero_name": f"npc_dota_hero_{image_name}",  # Prefix required by frontend
                "hero_display_name": hero_display,
                "team": team,
                "position": position,
                "player_slot": player.get("player_slot", idx),
                "steam_id": str(player.get("account_id")) if player.get("account_id") else None,
                "kills": player.get("kills", 0),
                "deaths": player.get("deaths", 0),
                "assists": player.get("assists", 0),
                "gold_per_min": player.get("gold_per_min", 0),
                "xp_per_min": player.get("xp_per_min", 0),
                "last_hits": player.get("last_hits", 0),
                "denies": player.get("denies", 0),
                "hero_damage": player.get("hero_damage", 0),
                "tower_damage": player.get("tower_damage", 0),
                "hero_healing": player.get("hero_healing", 0),
                "level": player.get("level", 1),
                "net_worth": player.get("net_worth", 0),
                
                # Extended Metrics
                "obs_placed": player.get("obs_placed", 0),
                "sen_placed": player.get("sen_placed", 0),
                "stuns": player.get("stuns", 0),
                "camps_stacked": player.get("camps_stacked", 0),
                "lane_efficiency_pct": player.get("lane_efficiency_pct", 0),
                "purchase_ward_observer": player.get("purchase_ward_observer", 0),
                "purchase_ward_sentry": player.get("purchase_ward_sentry", 0),
                
                # TIME-SERIES DATA (CRITICAL FOR LANING/PHASES)
                # These are minute-by-minute arrays: index 10 = minute 10
                "gold_t": player.get("gold_t", []),
                "xp_t": player.get("xp_t", []),
                "lh_t": player.get("lh_t", []),
                "dn_t": player.get("dn_t", []),
                
                # COMBAT/EVENT LOGS
                "obs_log": player.get("obs_log", []),
                "sen_log": player.get("sen_log", []),
                "kills_log": player.get("kills_log", []),
                "buyback_log": player.get("buyback_log", []),
                "purchase_log": player.get("purchase_log", []),
                "lane_pos": player.get("lane_pos", {}),
                
                # ADDITIONAL METRICS
                "actions_per_min": player.get("actions_per_min", 0),
                "teamfight_participation": player.get("teamfight_participation", 0),
                "gold_spent": player.get("gold_spent", 0),
                "roshans_killed": player.get("roshans_killed", 0),
                "towers_killed": player.get("towers_killed", 0),
                
                # Benchmarks & Computed
                "lh_at_10": ((player.get("benchmarks") or {}).get("lhten") or {}).get("raw", 0),
                "item_timings": self._extract_item_timings(player.get("purchase_log") or []),
            })
        return {
            "match_id": str(data.get("match_id")),
            "duration_minutes": (data.get("duration", 0) // 60),
            "duration_seconds": data.get("duration", 0),
            "duration": data.get("duration", 0),  # Alias for compatibility
            "radiant_win": data.get("radiant_win"),
            "radiant_score": data.get("radiant_score", 0),
            "dire_score": data.get("dire_score", 0),
            "game_mode": data.get("game_mode"),
            "lobby_type": data.get("lobby_type"),
            "start_time": data.get("start_time"),
            "cluster": data.get("cluster"),
            "heroes": heroes,
            "players": players,  # Keep raw players for compatibility
            "teamfights": data.get("teamfights", []),  # CRITICAL: Needed for fight analysis
            "picks_bans": data.get("picks_bans", []),
            "od_data": data.get("od_data", {}),
            "source": "opendota",
        }

    def _extract_item_timings(self, purchase_log: List[Dict[str, Any]]) -> Dict[str, int]:
        """Process purchase log into a dictionary of earliest timings."""
        timings = {}
        if not purchase_log:
            return timings
            
        for entry in purchase_log:
            if not entry:
                continue
            key = entry.get("key")
            time = entry.get("time")
            if key and time is not None:
                # Keep earliest timing
                if key not in timings:
                    timings[key] = time
        return timings


# Module-level singleton for convenience
_client: Optional[OpenDotaClient] = None


def get_opendota_client() -> OpenDotaClient:
    """Get or create OpenDota client singleton."""
    global _client
    if _client is None:
        _client = OpenDotaClient()
    return _client
