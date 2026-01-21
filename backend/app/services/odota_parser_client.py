"""
OpenDota Parser Client - HTTP interface to OpenDota's replay parser service.

This service communicates with the OpenDota parser (running on localhost:5600)
to extract detailed match data from .dem replay files.
"""

import os
import json
import logging
import requests
import re
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
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Replay file not found: {file_path}")
        
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        logger.info(f"Parsing replay: {file_path} ({file_size_mb:.1f}MB)")
        
        try:
            # Use streaming for the request to avoid loading large files into memory
            with open(file_path, 'rb') as f:
                logger.info(f"Streaming replay bytes to parser...")
                response = requests.post(
                    self.parser_url,
                    data=f,
                    headers={'Content-Type': 'application/octet-stream'},
                    timeout=timeout,
                    stream=True  # Ensure we stream the response back too
                )
                
                if response.status_code != 200:
                    try:
                        error_text = response.text[:500]
                    except:
                        error_text = "Unknown error"
                    logger.error(f"Parser returned HTTP {response.status_code}: {error_text}")
                    raise Exception(f"Parser returned HTTP {response.status_code}")

                # Parse line-delimited JSON response iteratively
                # This is CRITICAL for handling 500k+ events without OOM
                def event_generator():
                    count = 0
                    for line in response.iter_lines():
                        if line:
                            try:
                                yield json.loads(line)
                                count += 1
                            except json.JSONDecodeError:
                                continue
                    logger.info(f"✓ Streamed {count} events from parser")

                # Convert events to structured match data using the generator
                match_data = self._convert_events_to_match(event_generator())
                return match_data
            
        except requests.exceptions.ChunkedEncodingError:
            raise Exception("Parser connection broken - response ended prematurely")
        except requests.Timeout:
            raise Exception(f"Parser timeout after {timeout}s")
        except Exception as e:
            logger.error(f"Parsing failed: {str(e)}")
            raise Exception(f"Replay parsing failed: {str(e)}")
    
    def _convert_events_to_match(self, events_iter) -> Dict[str, Any]:
        """
        Convert streamed events to structured match data with constant memory usage.
        """
        match_data = {
            "match_id": None,
            "duration": 0,
            "duration_seconds": 0,
            "duration_minutes": 0,
            "radiant_win": None,
            "players": [],
            "heroes": [], 
            "objectives": [],
            "teamfights": [],
        }
        
        player_states = {}
        max_time = 0
        from app.services.hero_mapping import HERO_MAP
        
        # Iterative aggregation
        for event in events_iter:
            try:
                ev_type = event.get('type')
                ev_time = event.get('time', 0)
                
                if ev_time > max_time:
                    max_time = ev_time
                
                # Player-specific data
                slot = event.get('slot')
                if slot is not None:
                    if slot not in player_states:
                        player_states[slot] = {
                            "intervals": [], 
                            "obs_log": [], "sen_log": [],
                            "deaths_log": [], "kills_log": [],
                            "action_count": 0, "purchase_log": [],
                            "unique_items": set(),
                            "final_stats": None,
                            "stat_10m": None
                        }
                    
                    ps = player_states[slot]
                    
                    if ev_type == 'interval':
                        # Sample history every 30s to keep list size manageable
                        if not ps["intervals"] or ev_time >= ps["intervals"][-1].get('time', 0) + 30:
                            ps["intervals"].append(event)
                            if len(ps["intervals"]) > 200: # Safety cap
                                pass
                        
                        if ev_time >= 600 and not ps["stat_10m"]:
                            ps["stat_10m"] = event
                        
                        ps["final_stats"] = event
                             
                    elif ev_type == 'actions':
                        ps["action_count"] += 1
                        
                    elif ev_type == 'DOTA_COMBATLOG_PURCHASE':
                        item_key = event.get('valuename')
                        if item_key and item_key not in ps["unique_items"]:
                            ps["unique_items"].add(item_key)
                            ps["purchase_log"].append({"key": item_key, "time": ev_time})
                            
                    elif ev_type in ['obs_placed', 'sen_placed'] or ev_type == 'DOTA_COMBATLOG_WARD_PLACEMENT':
                        is_obs = 'observer' in event.get('valuename', '').lower() if ev_type == 'DOTA_COMBATLOG_WARD_PLACEMENT' else ev_type == 'obs_placed'
                        log_entry = {"time": ev_time, "x": event.get('x'), "y": event.get('y')}
                        if is_obs: ps["obs_log"].append(log_entry)
                        else: ps["sen_log"].append(log_entry)
                        
                    elif ev_type == 'DOTA_COMBATLOG_DEATH':
                        ps["deaths_log"].append({
                            "time": ev_time, "x": event.get('x'), "y": event.get('y'),
                            "attacker": event.get('attackername'), "nearby_allies": event.get('nearby_allies', 0)
                        })
                        
                    elif ev_type == 'DOTA_COMBATLOG_KILL':
                        ps["kills_log"].append({"time": ev_time, "x": ev_time, "y": ev_time, "target": event.get('targetname')})

                # Top-level match data
                if ev_type == 'epilogue':
                    try:
                        epilogue_data = json.loads(event.get('key', '{}'))
                        game_info = epilogue_data.get('gameInfo', {}).get('dota', {})
                        if game_info:
                            match_data["radiant_win"] = game_info.get('radiantWin', match_data["radiant_win"])
                            match_data["match_id"] = str(game_info.get('matchId', match_data["match_id"]))
                            if "gameDuration" in game_info:
                                 max_time = max(max_time, game_info["gameDuration"])
                    except: pass
                elif ev_type == 'teamfight':
                    match_data["teamfights"].append(event)
            except:
                continue
        
        # Standardize duration
        match_data["duration"] = max_time
        match_data["duration_seconds"] = max_time
        match_data["duration_minutes"] = int(max_time / 60)
        
        # Assemble player data
        for slot, ps in player_states.items():
            final_stats = ps["final_stats"]
            if not final_stats: continue
            
            stat_10m = ps["stat_10m"] or final_stats
            hero_id = final_stats.get('hero_id')
            hero_name = final_stats.get('hero', 'unknown')

            if hero_id and hero_id in HERO_MAP:
                hero_name = HERO_MAP[hero_id]
            else:
                unit_name = final_stats.get('unit', '')
                if unit_name and unit_name.startswith('CDOTA_Unit_Hero_'):
                    short_name = unit_name[len('CDOTA_Unit_Hero_'):]
                    CUSTOM_MAPPINGS = {
                        "AntiMage": "antimage", "OgreMagi": "ogre_magi", "Windrunner": "windrunner", 
                        "Necrolyte": "necrolyte", "QueenOfPain": "queenofpain", "ShadowFiend": "shadow_fiend",
                        "VengefulSpirit": "vengefulspirit", "DoomBringer": "doom_bringer", "SkeletonKing": "wraith_king", 
                        "Zuus": "zuus", "Nevermore": "shadow_fiend", "ObsidianDestroyer": "obsidian_destroyer",
                        "LifeStealer": "life_stealer", "Magnataur": "magnataur", "WinterWyvern": "winter_wyvern",
                        "Furion": "furion", "Wisp": "wisp",
                    }
                    if short_name in CUSTOM_MAPPINGS:
                        hero_name = f"npc_dota_hero_{CUSTOM_MAPPINGS[short_name]}"
                    else:
                        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', short_name)
                        snake_case = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
                        hero_name = f"npc_dota_hero_{snake_case}"

            player_data = {
                "player_slot": slot,
                "team": "radiant" if slot < 5 else "dire",
                "hero_name": hero_name,
                "hero_id": hero_id,
                "gold": final_stats.get('gold', 0),
                "xp": final_stats.get('xp', 0),
                "net_worth": final_stats.get('networth', 0) or final_stats.get('gold', 0),
                "last_hits": final_stats.get('lh', 0),
                "lh": final_stats.get('lh', 0),
                "denies": final_stats.get('denies', 0),
                "kills": final_stats.get('kills', 0),
                "deaths": final_stats.get('deaths', 0),
                "assists": final_stats.get('assists', 0),
                "gold_per_min": int(final_stats.get('gold', 0) / (max_time / 60)) if max_time > 0 else 0,
                "xp_per_min": int(final_stats.get('xp', 0) / (max_time / 60)) if max_time > 0 else 0,
                "gold_at_10": stat_10m.get('gold', 0),
                "xp_at_10": stat_10m.get('xp', 0),
                "lh_at_10": stat_10m.get('lh', 0),
                "level": final_stats.get('level', 1),
                "stuns": final_stats.get('stuns', 0),
                "hero_damage": final_stats.get('hero_damage', 0),
                "tower_damage": final_stats.get('tower_damage', 0),
                "roshans_killed": final_stats.get('roshans_killed', 0),
                "towers_killed": final_stats.get('towers_killed', 0),
                "lane_pos": final_stats.get('lane_pos', {}),
                "items": final_stats.get('hero_inventory', []),
                "item_timings": {item['key']: item['time'] for item in ps["purchase_log"]},
                "obs_log": ps["obs_log"], "sen_log": ps["sen_log"],
                "deaths_log": ps["deaths_log"], "kills_log": ps["kills_log"],
                "gold_t": [i.get('gold', 0) for i in ps["intervals"]],
                "xp_t": [i.get('xp', 0) for i in ps["intervals"]],
                "lh_t": [i.get('lh', 0) for i in ps["intervals"]],
                "dn_t": [i.get('denies', 0) for i in ps["intervals"]],
                "actions_per_min": int(ps["action_count"] / (max_time / 60)) if max_time > 0 else 0,
                "duration": max_time,
                "duration_seconds": max_time,
            }
            
            # Radiant Win determination
            if final_stats.get('win') is not None and match_data["radiant_win"] is None:
                is_radiant = slot < 5
                player_win = final_stats.get('win')
                match_data["radiant_win"] = player_win if is_radiant else not player_win

            match_data["players"].append(player_data)
            match_data["heroes"].append({
                "hero_name": hero_name, "player_slot": slot, "hero_id": hero_id, "items": player_data["items"]
            })
            
        if not match_data["players"]:
            raise Exception("No player data found in parsed events")
            
        logger.info(f"✓ Converted {len(match_data['players'])} players from Stream")
        return match_data
    
    def health_check(self) -> bool:
        """Check if parser service is available."""
        try:
            response = requests.get(self.parser_url, timeout=2)
            return response.status_code == 200
        except:
            return False
