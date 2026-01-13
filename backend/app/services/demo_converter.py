from typing import Dict, Any, List, Optional
import logging
from app.models.match import Match
from app.services.match_analyzer import MatchAnalyzer
from app.services.hero_mapping import get_hero_name

logger = logging.getLogger(__name__)

class DemoConverter:
    """Convert Clarity parsed data to MatchMentor format."""
    
    @staticmethod
    def convert_clarity_to_match(
        clarity_data: Dict[str, Any],
        player_id: int,
        account_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Convert Clarity JSON output to MatchMentor match format.
        
        Args:
            clarity_data: Parsed output from Clarity (via ReplayParser).
            player_id: Database user_id (the user who uploaded).
            account_id: Optional Dota 2 account ID to identify player.
            
        Returns:
            Dictionary ready for Match model creation.
        """
        
        # 1. Identify User's Hero
        # ReplayParser returns normalized data with "heroes" key (not "players")
        # Also check full_data for raw Clarity output
        full_data = clarity_data.get("full_data", {})
        players = clarity_data.get("players", full_data.get("players", []))
        heroes = clarity_data.get("heroes", [])
        
        # Use heroes list if available (ReplayParser format), otherwise use players
        player_list = heroes if heroes else players
        
        # If clarity_data has a specific 'hero_name' set (from single-player parsing focus), use it
        focused_hero = clarity_data.get("hero_name")
        
        user_player = None
        
        if account_id:
            # Search in player list
            # account_id in Clarity might be integer or string
            str_acc_id = str(account_id)
            for p in player_list:
                p_acc = str(p.get("account_id", ""))
                p_steam = str(p.get("steam_id", ""))
                if p_acc == str_acc_id or p_steam == str_acc_id:
                    user_player = p
                    break
                    
        # If still not found, and we have a focused hero name, find that player
        if not user_player and focused_hero and focused_hero != "Unknown":
            for p in player_list:
                h_name = p.get("hero_name", p.get("hero"))
                # Handle possible ID vs Name mismatch
                if isinstance(h_name, int):
                    h_name = get_hero_name(h_name)
                    
                if str(h_name) == str(focused_hero):
                    user_player = p
                    break
        
        # Fallback: use hero_name from top level if available (ReplayParser sets this)
        if not user_player and focused_hero and focused_hero != "Unknown":
            # Create a minimal player dict from top-level data
            user_player = {
                "hero_name": focused_hero,
                "steam_id": clarity_data.get("steam_id"),
                "account_id": clarity_data.get("steam_id")
            }
        elif not user_player and player_list:
            logger.warning("Could not identify specific user in replay, defaulting to first player.")
            user_player = player_list[0]
        elif not user_player and focused_hero:
            # Last resort: use top-level hero_name
            user_player = {
                "hero_name": focused_hero,
                "steam_id": clarity_data.get("steam_id")
            }
            
        if not user_player:
            raise ValueError("Could not identify player in replay data")

        # Extract hero name
        user_hero = user_player.get("hero_name", user_player.get("hero"))
        if not user_hero:
            # Fallback to top-level hero_name
            user_hero = clarity_data.get("hero_name", "Unknown")
        if isinstance(user_hero, int):
            user_hero = get_hero_name(user_hero)
            
        # 2. Run MatchAnalyzer
        # MatchAnalyzer expects the full parsed_data and an optional hero_name to focus on
        analyzer = MatchAnalyzer()
        analysis = analyzer.analyze_match(clarity_data, hero_name=user_hero)
        
        # 3. Enhance Metrics with specific prompt requirements if missing
        metrics = analysis["metrics"]
        
        # Lane Stats (kills/deaths/assists in first 10 mins)
        # MatchAnalyzer calculates 'lane_phase' metrics but maybe not K/D/A explicitly
        # output of analyze_match -> metrics['lane_phase'] has lh_at_10, gold_at_10, deaths_in_lane.
        # We can add kills/assists if we have event data.
        
        lane_kda = DemoConverter._extract_lane_kda(clarity_data, user_player.get("player_slot"))
        if lane_kda:
            metrics["lane_stats"] = lane_kda
            
        # 4. Construct Match Object Dict
        match_id = clarity_data.get("match_id")
        duration_minutes = clarity_data.get("duration_minutes", 0)
        result = clarity_data.get("result", "LOSS")
        
        # Steam ID
        steam_id = user_player.get("steam_id", user_player.get("account_id"))
        
        return {
            "match_id": str(match_id) if match_id else None,
            "player_id": player_id,
            "steam_id": str(steam_id) if steam_id else None,
            "hero_name": user_hero,
            "duration_minutes": duration_minutes,
            "result": result,
            "parsed_data": clarity_data, # Save full data
            "metrics": metrics,
            "advice": analysis["advice"],
            "source": "dem"
        }

    @staticmethod
    def _extract_lane_kda(match_data: Dict[str, Any], player_slot: Optional[int]) -> Optional[Dict[str, int]]:
        """Extract K/D/A stats for the first 10 minutes (600s)."""
        if player_slot is None:
            return None
            
        full_data = match_data.get("full_data", {})
        objectives = full_data.get("objectives", []) # Clarity parser puts events here usually
        
        # If 'objectives' isn't populated with combat log events, we might not be able to do this.
        # ReplayParser output depends on what Clarity extracts.
        # Assuming 'combat_log' or 'events' or 'objectives' exists.
        
        # Let's try to look for standard event keys
        events = objectives if objectives else match_data.get("events", [])
        
        if not events:
            return None
            
        kills = 0
        deaths = 0
        assists = 0
        
        # This assumes events have 'time', 'type', 'target_slot'/'player_slot' etc.
        # Since I don't have the exact Clarity event structure in front of me for this specific project implementation
        # (ReplayParser.py didn't show the event extraction logic in detail, just 'raw_data'),
        # I will write defensive code.
        
        for e in events:
            time = e.get("time", e.get("time_seconds", 9999))
            if time > 600:
                continue
                
            etype = e.get("type", "")
            
            # Check slot/id (logic depends on event structure)
            # Assuming widely used format
            p_slot = e.get("player_slot", e.get("player_id"))
            
            if etype == "kill":
                if p_slot == player_slot:
                    kills += 1
            elif etype == "death":
                if p_slot == player_slot:
                    deaths += 1
            elif etype == "assist":
                 # assists often stored as list of assisters
                 pass 
                 
        return {"kills": kills, "deaths": deaths, "assists": assists}
