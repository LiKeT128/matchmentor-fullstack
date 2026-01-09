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
        return "unknown"
    
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
        return "Unknown"
    
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
            hero_id = player.get("hero_id")
            
            # Resolve hero name from cache
            hero_name_raw = self.get_hero_name(hero_id) if hero_id else "unknown"
            hero_display = self.get_hero_display_name(hero_id) if hero_id else "Unknown"
            
            # Strip prefix for CDN compatibility
            short_name = hero_name_raw.replace("npc_dota_hero_", "") if hero_name_raw else "unknown"
            
            # CDN expects internal Valve names (e.g. "zuus", "magnataur")
            # We do NOT want to map them to "zeus" or "magnus" because the CDN files don't exist under those names.
            # Using short_name directly (raw internal name without prefix).
            image_name = short_name
            
            # Determine team
            is_radiant = player.get("isRadiant", idx < 5)
            team = "radiant" if is_radiant else "dire"
            
            # Determine position: Prefer 'lane' (actual gameplay) over 'slot' (lobby order)
            lane = player.get("lane")
            position = "unknown"
            
            if lane:
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
            
            # Fallback to player_slot if lane info is missing
            if position == "unknown":
                player_slot = player.get("player_slot")
                if player_slot is not None:
                    if 0 <= player_slot <= 4:
                        position = f"Slot {player_slot + 1}"
                    elif 128 <= player_slot <= 132:
                        position = f"Slot {player_slot - 127}"
            
            heroes.append({
                "player_id": idx,
                "hero_id": hero_id,
                "hero_name": f"npc_dota_hero_{image_name}",  # Prefix required by frontend
                "hero_display_name": hero_display,
                "team": team,
                "position": position,
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
            })
        
        # Check for unknown heroes
        unknown_count = sum(1 for h in heroes if h["hero_name"] == "unknown")
        if unknown_count > 0:
            logger.warning(f"Match {data.get('match_id')}: {unknown_count} heroes still unknown after resolution")
        
        return {
            "match_id": str(data.get("match_id")),
            "duration_minutes": (data.get("duration", 0) // 60),
            "duration_seconds": data.get("duration", 0),
            "radiant_win": data.get("radiant_win"),
            "radiant_score": data.get("radiant_score", 0),
            "dire_score": data.get("dire_score", 0),
            "game_mode": data.get("game_mode"),
            "lobby_type": data.get("lobby_type"),
            "start_time": data.get("start_time"),
            "cluster": data.get("cluster"),
            "heroes": heroes,
            "players": players,  # Keep raw players for compatibility
            "picks_bans": data.get("picks_bans", []),
            "od_data": data.get("od_data", {}),
            "source": "opendota",
        }


# Module-level singleton for convenience
_client: Optional[OpenDotaClient] = None


def get_opendota_client() -> OpenDotaClient:
    """Get or create OpenDota client singleton."""
    global _client
    if _client is None:
        _client = OpenDotaClient()
    return _client
