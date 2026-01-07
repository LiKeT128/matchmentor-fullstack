"""Benchmark service for fetching hero stats from OpenDota API."""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

import httpx

logger = logging.getLogger(__name__)


class BenchmarkService:
    """
    Service for fetching and caching hero benchmarks from OpenDota API.
    
    Uses in-memory caching to reduce API calls.
    """
    
    OPENDOTA_API = "https://api.opendota.com/api"
    CACHE_TTL_HOURS = 24
    
    # In-memory cache: {hero_id: {"data": {...}, "expires": datetime}}
    _cache: Dict[int, Dict[str, Any]] = {}
    
    # Default benchmarks if API fails
    DEFAULT_BENCHMARKS = {
        "gpm": 450,
        "xpm": 500,
        "last_hits": 200,
        "denies": 15,
        "kills": 8,
        "deaths": 5,
        "assists": 12,
        "hero_damage": 20000,
        "tower_damage": 3000,
        "hero_healing": 0,
        "gold_per_min_percentile": {
            "50": 450,
            "75": 550,
            "95": 700
        },
        "xp_per_min_percentile": {
            "50": 500,
            "75": 600,
            "95": 750
        },
        "last_hits_per_min_percentile": {
            "50": 5.5,
            "75": 7.0,
            "95": 9.0
        }
    }
    
    # Pro average item timings (in seconds)
    PRO_ITEM_TIMINGS = {
        "blink": 780,           # 13 min
        "black_king_bar": 1200, # 20 min
        "battle_fury": 840,     # 14 min
        "hand_of_midas": 540,   # 9 min
        "boots": 180,           # 3 min
        "power_treads": 540,    # 9 min
        "phase_boots": 480,     # 8 min
        "arcane_boots": 600,    # 10 min
        "radiance": 1020,       # 17 min
        "desolator": 1080,      # 18 min
        "orchid": 1140,         # 19 min
        "aghanims_scepter": 1320, # 22 min
    }
    
    async def get_hero_benchmarks(self, hero_id: int) -> Dict[str, Any]:
        """
        Get benchmarks for a specific hero from OpenDota API.
        
        Args:
            hero_id: Dota 2 hero ID.
            
        Returns:
            Dictionary with benchmark percentiles.
        """
        # Check cache first
        if hero_id in self._cache:
            cached = self._cache[hero_id]
            if datetime.utcnow() < cached["expires"]:
                return cached["data"]
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.OPENDOTA_API}/benchmarks",
                    params={"hero_id": hero_id}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Cache the result
                    self._cache[hero_id] = {
                        "data": data,
                        "expires": datetime.utcnow() + timedelta(hours=self.CACHE_TTL_HOURS)
                    }
                    
                    return data
                    
        except Exception as e:
            logger.warning(f"Failed to fetch OpenDota benchmarks: {e}")
        
        # Return defaults if API fails
        return self.DEFAULT_BENCHMARKS
    
    def get_hero_benchmarks_sync(self, hero_id: int) -> Dict[str, Any]:
        """
        Synchronous version of get_hero_benchmarks.
        
        Args:
            hero_id: Dota 2 hero ID.
            
        Returns:
            Dictionary with benchmark percentiles.
        """
        # Check cache first
        if hero_id in self._cache:
            cached = self._cache[hero_id]
            if datetime.utcnow() < cached["expires"]:
                return cached["data"]
        
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(
                    f"{self.OPENDOTA_API}/benchmarks",
                    params={"hero_id": hero_id}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Cache the result
                    self._cache[hero_id] = {
                        "data": data,
                        "expires": datetime.utcnow() + timedelta(hours=self.CACHE_TTL_HOURS)
                    }
                    
                    return data
                    
        except Exception as e:
            logger.warning(f"Failed to fetch OpenDota benchmarks: {e}")
        
        # Return defaults if API fails
        return self.DEFAULT_BENCHMARKS
    
    def get_pro_item_timing(self, item_name: str) -> Optional[int]:
        """
        Get pro average timing for an item.
        
        Args:
            item_name: Item internal name (e.g., 'blink', 'black_king_bar').
            
        Returns:
            Timing in seconds, or None if not tracked.
        """
        # Normalize item name
        normalized = item_name.lower().replace("item_", "")
        return self.PRO_ITEM_TIMINGS.get(normalized)
    
    def get_benchmark_for_metric(
        self, 
        benchmarks: Dict[str, Any], 
        metric: str, 
        percentile: str = "50"
    ) -> float:
        """
        Extract a specific benchmark value.
        
        Args:
            benchmarks: Full benchmark data.
            metric: Metric name (e.g., 'gold_per_min').
            percentile: Target percentile ('50', '75', '95').
            
        Returns:
            Benchmark value for the metric at given percentile.
        """
        if isinstance(benchmarks, dict):
            metric_data = benchmarks.get(f"{metric}_percentile", {})
            if isinstance(metric_data, dict):
                return float(metric_data.get(percentile, 0))
        return 0.0


# Singleton instance
benchmark_service = BenchmarkService()
