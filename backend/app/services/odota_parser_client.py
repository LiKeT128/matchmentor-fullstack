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
            # Read file into memory and send via POST body
            # This is the original method that was working before
            with open(file_path, 'rb') as f:
                file_content = f.read()
            
            logger.info(f"Sending {len(file_content)} bytes to parser...")
            
            # Send raw bytes to root endpoint
            response = requests.post(
                self.parser_url,
                data=file_content,
                headers={'Content-Type': 'application/octet-stream'},
                timeout=timeout
            )
            
            if response.status_code != 200:
                # Read a bit of the error response if possible
                try:
                    error_text = response.text[:500]
                except:
                    error_text = "Unknown error"
                error_msg = f"Parser returned HTTP {response.status_code}"
                logger.error(f"{error_msg}: {error_text}")
                raise Exception(error_msg)
            
            # Parse line-delimited JSON response
            # Since we aren't streaming request anymore, we can just read text
            # But the response is still line-delimited JSON
            events = []
            for line in response.iter_lines():
                if line:
                    try:
                        events.append(json.loads(line))
                    except json.JSONDecodeError as e:
                        logger.warning(f"Skipping invalid JSON line: {line[:100]}... ({e})")
            
            logger.info(f"✓ Parsed {len(events)} events from replay")
            
            # Convert events to structured match data
            match_data = self._convert_events_to_match(events)
            
            return match_data
            
        except requests.exceptions.ChunkedEncodingError:
            raise Exception("Parser connection broken (Response ended prematurely) - likely parser crash")
        except requests.Timeout:
            raise Exception(f"Parser timeout after {timeout}s - file may be too large or complex")
        except requests.ConnectionError:
            raise Exception("Parser service unavailable - failed to connect")
        except Exception as e:
            logger.error(f"Parsing failed: {str(e)}")
            raise Exception(f"Replay parsing failed: {str(e)}")
    
    def _convert_events_to_match(self, events: List[Dict]) -> Dict[str, Any]:
        """
        Convert line-delimited events to structured match data.
        """
        match_data = {
            "match_id": None,
            "duration": 0,
            "radiant_win": None,
            "players": [],
            "heroes": [], # Legacy compatibility: List of found heroes
            "objectives": [],
            "teamfights": [],
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
                
                hero_id = final_stats.get('hero_id')
                
                # 1. Try to use hero_id with canonical mapping if available
                from app.services.hero_mapping import HERO_MAP
                if hero_id and hero_id in HERO_MAP:
                    hero_name = HERO_MAP[hero_id]
                else:
                    # 2. Fallback to 'unit' field (legacy/parser bug workaround)
                    # If hero_name is missing/invalid, try to derive from 'unit' (e.g. CDOTA_Unit_Hero_Name)
                    unit_name = final_stats.get('unit', '')
                    hero_name = final_stats.get('hero') # Preserve original if unit fails
                    
                    if unit_name and unit_name.startswith('CDOTA_Unit_Hero_'):
                        short_name = unit_name[len('CDOTA_Unit_Hero_'):]
                        
                        # Custom mapping for known inconsistencies between internal class names and Web API names
                        # This avoids "Unknown" hero issues in frontend
                        CUSTOM_MAPPINGS = {
                            "AntiMage": "antimage",
                            "OgreMagi": "ogre_magi",
                            "Windrunner": "windrunner", 
                            "Necrolyte": "necrolyte",
                            "QueenOfPain": "queenofpain",
                            "ShadowFiend": "shadow_fiend",
                            "VengefulSpirit": "vengefulspirit",
                            "DoomBringer": "doom_bringer",
                            "SkeletonKing": "wraith_king", 
                            "Zuus": "zuus",
                            "Nevermore": "shadow_fiend",
                            "ObsidianDestroyer": "obsidian_destroyer",
                            "LifeStealer": "life_stealer",
                            "Magnataur": "magnataur", 
                            "WinterWyvern": "winter_wyvern",
                            "Furion": "furion",
                            "Wisp": "wisp", # Io
                        }
                        
                        if short_name in CUSTOM_MAPPINGS:
                            hero_name = f"npc_dota_hero_{CUSTOM_MAPPINGS[short_name]}"
                        else:
                            # Default snake_case conversion: WinterWyvern -> winter_wyvern
                            import re
                            s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', short_name)
                            snake_case = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
                            hero_name = f"npc_dota_hero_{snake_case}"
                
                # --- Metrics Extraction ---
                # 1. Timeline stats (e.g. at 10 mins)
                stat_10m = {}
                gold_t, xp_t, lh_t, dn_t = [], [], [], []
                
                # 2. Advanced Logs
                obs_log, sen_log = [], []
                deaths_log, kills_log = [], []
                action_count = 0
                
                # Filter purchase events and other combat logs
                purchase_log = []
                unique_items = set()
                
                # Sort events by time just in case
                sorted_events = sorted(slot_events, key=lambda x: x.get('time', 0))
                
                for e in sorted_events:
                    e_type = e.get('type')
                    e_time = e.get('time', 0)
                    
                    if e_type == 'interval':
                        if e_time >= 600 and not stat_10m:
                            stat_10m = e
                        # Build time-series (sampled every minute or interval)
                        gold_t.append(e.get('gold', 0))
                        xp_t.append(e.get('xp', 0))
                        lh_t.append(e.get('lh', 0))
                        dn_t.append(e.get('denies', 0))
                        
                    elif e_type == 'actions':
                        action_count += 1
                        
                    elif e_type == 'DOTA_COMBATLOG_PURCHASE':
                        item_key = e.get('valuename')
                        if item_key and item_key not in unique_items:
                            unique_items.add(item_key)
                            purchase_log.append({"key": item_key, "time": e_time})
                            
                    elif e_type == 'obs_placed' or (e_type == 'DOTA_COMBATLOG_WARD_PLACEMENT' and 'observer' in e.get('valuename', '').lower()):
                        obs_log.append({"time": e_time, "x": e.get('x'), "y": e.get('y')})
                        
                    elif e_type == 'sen_placed' or (e_type == 'DOTA_COMBATLOG_WARD_PLACEMENT' and 'sentry' in e.get('valuename', '').lower()):
                        sen_log.append({"time": e_time, "x": e.get('x'), "y": e.get('y')})
                        
                    elif e_type == 'DOTA_COMBATLOG_DEATH':
                        # Hero deaths usually have targets/valuename
                        deaths_log.append({
                            "time": e_time, 
                            "x": e.get('x'), 
                            "y": e.get('y'),
                            "attacker": e.get('attackername'),
                            "nearby_allies": e.get('nearby_allies', 0)
                        })
                        
                    elif e_type == 'DOTA_COMBATLOG_KILL':
                        kills_log.append({"time": e_time, "x": e.get('x'), "y": e.get('y'), "target": e.get('targetname')})

                player_data = {
                    "player_slot": slot,
                    "hero_id": hero_id,
                    "hero": hero_name,
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
                    "net_worth": final_stats.get('net_worth', 0),
                    
                    # Detailed Metrics for Analysis
                    "lh_at_10": stat_10m.get('lh', 0),
                    "item_timings": {item['key']: item['time'] for item in purchase_log},
                    "gold_t": gold_t,
                    "xp_t": xp_t,
                    "lh_t": lh_t,
                    "dn_t": dn_t,
                    "obs_log": obs_log,
                    "sen_log": sen_log,
                    "deaths_log": deaths_log,
                    "kills_log": kills_log,
                    "stuns": final_stats.get('stuns', 0),
                    "actions_per_min": (action_count / (match_data["duration"] / 60)) if match_data["duration"] > 0 else 0,
                    "roshans_killed": final_stats.get('roshans_killed', 0),
                    "towers_killed": final_stats.get('towers_killed', 0),
                    "lane_pos": final_stats.get('lane_pos', {}),
                }
                
                match_data["players"].append(player_data)
                
                # Add to heroes summary list
                if hero_name:
                    match_data["heroes"].append({
                        "hero_name": hero_name,
                        "player_slot": slot,
                        "hero_id": hero_id
                    })
        
        # Extract match metadata and top-level events
        for event in events:
            e_type = event.get('type')
            if e_type == 'epilogue':
                match_data["duration"] = event.get('duration', 0)
                match_data["radiant_win"] = event.get('radiant_win', False)
                match_data["match_id"] = str(event.get('match_id', ''))
            elif e_type == 'teamfight':
                match_data["teamfights"].append(event)
        
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
