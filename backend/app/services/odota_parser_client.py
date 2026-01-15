"""
OpenDota Parser Client - HTTP interface to OpenDota's replay parser service.

This service communicates with the OpenDota parser (running on localhost:5600)
to extract detailed match data from .dem replay files.
"""

import os
import json
import logging
import requests
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class OpenDotaParserClient:
    """Client for OpenDota's replay parser HTTP service."""
    
    def __init__(self, parser_url: str = None):
        """
        Initialize parser client.
        
        Args:
            parser_url: URL of parser service (default: http://localhost:5600)
        """
        parser_port = os.getenv('PARSER_PORT', '5600')
        self.parser_url = parser_url or f"http://localhost:{parser_port}"
        logger.info(f"OpenDota Parser Client initialized: {self.parser_url}")
    
    def parse_replay(self, file_path: str, timeout: int = 300) -> Dict[str, Any]:
        """
        Parse a .dem replay file using OpenDota parser.
        
        Args:
            file_path: Path to .dem file
            timeout: Timeout in seconds (default: 300 = 5 minutes)
            
        Returns:
            Dictionary with parsed match data
            
        Raises:
            Exception: If parsing fails or service is unavailable
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Replay file not found: {file_path}")
        
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        logger.info(f"Parsing replay: {file_path} ({file_size_mb:.1f}MB)")
        
        try:
            # Send .dem file to parser
            with open(file_path, 'rb') as f:
                response = requests.post(
                    self.parser_url,
                    data=f,
                    headers={'Content-Type': 'application/octet-stream'},
                    timeout=timeout
                )
            
            if response.status_code != 200:
                error_msg = f"Parser returned HTTP {response.status_code}"
                logger.error(f"{error_msg}: {response.text[:500]}")
                raise Exception(error_msg)
            
            # Parse line-delimited JSON response
            events = self._parse_response(response.text)
            logger.info(f"✓ Parsed {len(events)} events from replay")
            
            # Convert events to structured match data
            match_data = self._convert_events_to_match(events)
            
            return match_data
            
        except requests.Timeout:
            raise Exception(f"Parser timeout after {timeout}s - file may be too large or complex")
        except requests.ConnectionError:
            raise Exception("Parser service unavailable - is it running?")
        except Exception as e:
            logger.error(f"Parsing failed: {str(e)}")
            raise Exception(f"Replay parsing failed: {str(e)}")
    
    def _parse_response(self, response_text: str) -> List[Dict]:
        """Parse line-delimited JSON response into list of events."""
        events = []
        for line in response_text.strip().split('\n'):
            if line.strip():
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError as e:
                    logger.warning(f"Skipping invalid JSON line: {line[:100]}... ({e})")
        return events
    
    def _convert_events_to_match(self, events: List[Dict]) -> Dict[str, Any]:
        """
        Convert line-delimited events to structured match data.
        
        OpenDota parser outputs events like:
        - {"type": "interval", "slot": 0, "kills": 5, ...}
        - {"type": "DOTA_COMBATLOG_PURCHASE", "slot": 0, "key": "item_blink", "time": 600}
        - etc.
        
        We need to aggregate these into our Match schema.
        """
        match_data = {
            "match_id": None,
            "duration": 0,
            "radiant_win": None,
            "players": [],
            "objectives": [],
            "teamfights": [],
            "raw_events": events  # Store for detailed analysis
        }
        
        # Group events by player slot
        player_events = {}
        for event in events:
            slot = event.get('slot')
            if slot is not None:
                if slot not in player_events:
                    player_events[slot] = []
                player_events[slot].append(event)
        
        # Extract player data from intervals (final stats)
        for slot, slot_events in player_events.items():
            # Find last interval event (contains final stats)
            interval_events = [e for e in slot_events if e.get('type') == 'interval']
            if interval_events:
                final_stats = interval_events[-1]
                
                player_data = {
                    "player_slot": slot,
                    "hero_id": final_stats.get('hero_id'),
                    "hero": final_stats.get('hero'),
                    "kills": final_stats.get('kills', 0),
                    "deaths": final_stats.get('deaths', 0),
                    "assists": final_stats.get('assists', 0),
                    "last_hits": final_stats.get('lh', 0),
                    "denies": final_stats.get('denies', 0),
                    "gold": final_stats.get('gold', 0),
                    "gold_per_min": final_stats.get('gpm', 0),
                    "xp_per_min": final_stats.get('xpm', 0),
                    "level": final_stats.get('level', 0),
                    "hero_damage": final_stats.get('hero_damage', 0),
                    "tower_damage": final_stats.get('tower_damage', 0),
                    "hero_healing": final_stats.get('hero_healing', 0),
                }
                
                match_data["players"].append(player_data)
        
        # Extract match metadata from first event or metadata event
        for event in events:
            if event.get('type') == 'epilogue':
                match_data["duration"] = event.get('duration', 0)
                match_data["radiant_win"] = event.get('radiant_win', False)
                match_data["match_id"] = str(event.get('match_id', ''))
                break
        
        # Validate we have players
        if not match_data["players"]:
            raise Exception("No player data found in parsed events")
        
        logger.info(f"Converted {len(match_data['players'])} players from {len(events)} events")
        
        return match_data
    
    def health_check(self) -> bool:
        """
        Check if parser service is available.
        
        Returns:
            True if service is responding, False otherwise
        """
        try:
            response = requests.get(self.parser_url, timeout=2)
            return True
        except:
            return False
