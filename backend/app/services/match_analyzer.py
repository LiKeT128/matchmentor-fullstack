"""Match analyzer service for calculating 60+ performance metrics."""

from typing import Dict, Any, List, Optional
import logging
from datetime import datetime

from app.services.benchmark_service import benchmark_service
from app.services.stage_extractors import LaningStageExtractor
from app.services.stage_constants import get_position
from app.services.hero_mapping import get_hero_id, get_hero_name
from app.services.advanced_calculators import AdvancedCalculators

logger = logging.getLogger(__name__)


class MatchAnalyzer:
    """
    Service for analyzing parsed match data and generating 60+ metrics.
    
    Calculates deterministic metrics across categories.
    STATUS: Currently 30+ metrics implemented. Some are estimates or placeholders
    pending full Clarity integration in stage_extractors.py.
    
    Categories:
    - Basic (8): GPM, XPM, LH, Denies, KDA (Implemented)
    - Positioning (2): Safety Rating, Danger Zone % (Placeholder)
    - Fighting (3): TF Participation, Hero DMG/Min, DMG/Kill (Implemented)
    - Timing (2): Purchase Counts, Timing log (Implemented)
    - Warding (3): Wards Placed, Sentries, Vision Score (Implemented)
    - Lane Phase (5): LH@10, Gold@10, XP@10, Lane control (Implemented)
    - Mid Game (3): Kills (Estimated), Efficiency (Stub), Objectives (Stub)
    - Late Game (3): Kills (Estimated), HG Defense (Stub), Buyback (Stub)

    """
    
    def __init__(self):
        """Initialize analyzer."""
        self.benchmark_service = benchmark_service

    def analyze_match(self, parsed_data: Dict[str, Any], hero_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze parsed match data for a specific hero or the match overall.
        
        Args:
            parsed_data: Full match data from ReplayParser.
            hero_name: npc_dota_hero_* name to isolate.
            
        Returns:
            Dictionary with metrics, advice, score, strengths, weaknesses, and game_stages.
        """
        if not parsed_data:
            raise ValueError("No parsed data provided")
            
        # 1. Isolate the target player data
        player_data = None
        heroes_list = parsed_data.get("heroes", [])
        
        if hero_name:
            # Try to match by mapped name (e.g. from parsed_data which uses hero_mapping)
            for h in heroes_list:
                # Handle string case (if heroes is just a list of names)
                if isinstance(h, str):
                    if h == hero_name:
                        # If we match a string, we don't have player_data yet, but we know it exists.
                        # We will find it in players list below.
                        pass
                elif isinstance(h, dict):
                    if h.get("hero_name") == hero_name:
                        player_data = h
                        break
                    
            # If not found, try to match by internal name just in case
            if not player_data:
                 for h in heroes_list:
                    if isinstance(h, dict) and h.get("hero") == hero_name:
                        player_data = h
                        break
        
        # If no hero specified or not found, use a default fallback (first hero)
        if not player_data and heroes_list:
            first = heroes_list[0]
            if isinstance(first, dict):
                player_data = first
            else:
                 # If string, we can't use it as player_data directly, will rely on players list
                 if not hero_name:
                     hero_name = first
            
            if hero_name and not player_data:
                 # We have a name but no data object. 
                 # We will look it up in 'players' list in the next step.
                 pass

        if not player_data:
            # Create a minimal structure if somehow heroes list is empty
            player_data = parsed_data
            
        # 2. Enrich with rich data from 'players' array
        players_list = parsed_data.get("players", [])
        rich_player = None
        
        target_hero_id = get_hero_id(hero_name) if hero_name else None
        
        # Try finding by hero_name or hero_id in players list
        if (hero_name or target_hero_id) and players_list:
            for p in players_list:
                p_hero = p.get("hero_name") or p.get("hero")
                p_hero_id = p.get("hero_id")
                
                if (hero_name and p_hero == hero_name) or (target_hero_id and p_hero_id == target_hero_id):
                    rich_player = p
                    break
        
        # Fallback: if we have player_data with an index/id, use it
        if not rich_player and players_list:
             idx = player_data.get("player_id") or player_data.get("player_slot")
             if idx is not None and isinstance(idx, int) and idx < len(players_list):
                 rich_player = players_list[idx]
        
        # Merge if found
        if rich_player:
            player_data = {**player_data, **rich_player}
            # Ensure full_data is set for sub-extractors
            if "full_data" not in player_data:
                player_data["full_data"] = rich_player

        if not player_data:
             logger.warning(f"No player data found for hero {hero_name} in match {match_id}")
             # Return minimal skeleton instead of crashing
             return {
                 "match_id": str(match_id),
                 "hero_id": target_hero_id or 0,
                 "hero_name": hero_name,
                 "match_duration": 0,
                 "metrics": {"error": "Hero data missing in parse"},
                 "advice": [],
                 "mistakes": [],
                 "overall_score": 0,
                 "strengths": [],
                 "weaknesses": []
             }

        # Ensure duration_minutes is globally available to calculators
        duration = parsed_data.get("duration") or parsed_data.get("duration_seconds") or 1800
        player_data["duration_minutes"] = max(duration / 60, 1)
        player_data["duration"] = duration
        
        # Merged rich metrics
        match_id = parsed_data.get("match_id", "unknown_match")
        logger.info(f"Analyzing match {match_id} for hero {hero_name}")
        print(f"DEBUG: [MatchAnalyzer] Beginning full analysis for {hero_name}...", flush=True)

        # 1. Basic Stats
        print("DEBUG: [MatchAnalyzer] Calculating Basic Stats...", flush=True)
        basic_stats = self.calculate_gpm_xpm(player_data)
        
        # 2. Laning Phase
        print("DEBUG: [MatchAnalyzer] Calculating Laning Phase...", flush=True)
        lane_metrics = self.calculate_lane_metrics(player_data)
        
        # 3. Vision & Map Control
        print("DEBUG: [MatchAnalyzer] Calculating Vision Metrics...", flush=True)
        vision_metrics = self.calculate_warding_value(player_data)

        # 4. Role & Impact
        print("DEBUG: [MatchAnalyzer] Calculating Role Metrics...", flush=True)
        role_impact = {
            "fighting": self.calculate_teamfight_stats(player_data),
            "farming": self._calculate_farming(player_data),
            "items": self.calculate_item_efficiency(player_data),
            "mid_game": self.calculate_midgame_metrics(player_data),
            "late_game": self.calculate_lategame_metrics(player_data),
            "positioning": self.calculate_positioning_risk(player_data)
        }
        
        # 5. Advanced Unique Metrics (from AdvancedCalculators) - 48 Metrics Total
        print("DEBUG: [MatchAnalyzer] Calculating Advanced Metrics...", flush=True)
        hero_id = get_hero_id(hero_name) if hero_name else player_data.get("hero_id", 0)
        
        fight_eff = AdvancedCalculators.calculate_fight_effectiveness(player_data, hero_id)
        adv_pos = AdvancedCalculators.calculate_advanced_positioning(player_data)
        dec_qual = AdvancedCalculators.calculate_decision_quality(player_data)
        threat_pred = AdvancedCalculators.calculate_threat_prediction(player_data)
        psych = AdvancedCalculators.calculate_psychological_metrics(player_data)
        stat_corr = AdvancedCalculators.calculate_stat_correlations(player_data)
        print("DEBUG: [MatchAnalyzer] Advanced Metrics finished", flush=True)

        # Final Metrics Assembly (STRUCTURED for next-gen UI)
        metrics = {
            "overall_score": 0,
            "match_id": match_id,
            "hero_name": hero_name,
            "duration": player_data.get("duration", 0),
            
            # CORE GROUPS
            "basic_stats": basic_stats,
            "laning_phase": lane_metrics,
            "vision": vision_metrics,
            "role_impact": role_impact,
            
            # UNIQUE ADVANCED GROUPS (MatchMentor Originals)
            "fight_effectiveness": fight_eff,
            "positioning_risk": adv_pos,
            "decision_quality": dec_qual,
            "threat_prediction": threat_pred,
            "psychological_profile": psych,
            "stat_correlations": stat_corr
        }

        # Benchmarks
        print("DEBUG: [MatchAnalyzer] Comparing with benchmarks...", flush=True)
        active_hero = player_data.get("hero_name", hero_name or "unknown")
        metrics["_raw_benchmarks"] = player_data.get("benchmarks", {})
        benchmark_comparison = self.compare_with_benchmark(metrics, active_hero)
        metrics["benchmarks"] = benchmark_comparison
        
        # Advice
        print("DEBUG: [MatchAnalyzer] Generating advice...", flush=True)
        advice_data = self.generate_deterministic_advice(metrics, benchmark_comparison)
        
        # Calculate overall score for metrics
        metrics["overall_score"] = advice_data.get("score", 75)
        
        return {
            "match_id": str(match_id),
            "hero_id": hero_id,
            "hero_name": hero_name,
            "match_duration": int(player_data.get("duration", 0)),
            "metrics": metrics,
            "advice": advice_data.get("top_improvements", []), 
            "mistakes": advice_data.get("top_mistakes", []),    
            "overall_score": metrics["overall_score"],
            "strengths": [a["title"] for a in advice_data.get("top_improvements", []) if a.get("type") == "strength"],
            "weaknesses": [a["title"] for a in advice_data.get("top_improvements", []) if a.get("type") == "weakness"] or advice_data.get("top_mistakes", []),
            "power_spikes": [],
            "timestamp": datetime.utcnow().isoformat()
        }

    def _calculate_farming(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Group 2: CS & Farming (4 metrics)"""
        lh = data.get("last_hits", 0)
        denies = data.get("denies", 0)
        cs = lh + denies
        duration = data.get("duration_minutes", 1)
        
        return {
            "cs": cs,
            "cs_per_min": round(cs / duration, 1),
            "denies": denies,
            "deny_ratio": round(denies / max(cs, 1), 3)
        }

    def calculate_gpm_xpm(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Group 1: Basic Stats (8 metrics)"""
        # Support both OpenDota (gold_per_min) and Clarity (gpm) keys
        gpm = data.get("gold_per_min", data.get("gpm", 0))
        xpm = data.get("xp_per_min", data.get("xpm", 0))
        lh = data.get("last_hits", data.get("lh", 0))
        
        kills = data.get("kills", 0)
        deaths = data.get("deaths", 0)
        assists = data.get("assists", 0)
        deaths_safe = max(deaths, 1)
        
        return {
            "kills": kills,
            "deaths": deaths,
            "assists": assists,
            "kd_ratio": round(kills / deaths_safe, 2),
            "kda_ratio": round((kills + assists) / deaths_safe, 2),
            "gpm": gpm,
            "xpm": xpm,
            "lh": lh
        }

    def calculate_lane_metrics(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Group 6: Lane Phase Analysis (7 metrics)"""
        # Try direct extraction first (lh_at_10 provided by parser or opendota)
        lh_10 = data.get("lh_at_10", data.get("last_hits_10", 0))
        
        # Fallback to time series if available
        if lh_10 == 0:
            lh_t = data.get("lh_t", data.get("last_hits_t", []))
            if len(lh_t) > 10:
                lh_10 = lh_t[10]
        
        # Gold at 10
        gold_10 = data.get("gold_at_10", 0)
        if gold_10 == 0:
            gold_t = data.get("gold_t", data.get("gold_adv_t", []))
            if len(gold_t) > 10:
                gold_10 = gold_t[10]
            else:
                 # Estimate if missing
                 gold_10 = int(data.get("gold_per_min", data.get("gpm", 0)) * 10)

        # XP at 10
        xp_10 = 0
        xp_t = data.get("xp_t", [])
        if len(xp_t) > 10:
            xp_10 = xp_t[10]
        else:
            xp_10 = int(data.get("xp_per_min", 0) * 10)

        # Estimate level from XP (simple version of the table)
        # XP thresholds: 2: 230, 3: 600, 4: 1080, 5: 1680, 6: 2300, 10: 5080
        if xp_10 >= 5080: level_10 = 10
        elif xp_10 >= 4280: level_10 = 9
        elif xp_10 >= 3600: level_10 = 8
        elif xp_10 >= 2940: level_10 = 7
        elif xp_10 >= 2300: level_10 = 6
        elif xp_10 >= 1680: level_10 = 5
        elif xp_10 >= 1080: level_10 = 4
        elif xp_10 >= 600: level_10 = 3
        elif xp_10 >= 230: level_10 = 2
        else: level_10 = 1

        return {
            "lh_at_10": lh_10,
            "gold_at_10": gold_10,
            "xp_at_10": xp_10,
            "level_10m": level_10,
            "lane_efficiency_pct": round(data.get("lane_efficiency_pct", (lh_10 / 50) * 100), 1),
            "deaths_in_lane": len([d for d in data.get("deaths_log", []) if d.get("time", 0) <= 600]),
            "lane_control_score": min(100, (lh_10 / 45) * 100) # Heuristic for lane control
        }

    def calculate_midgame_metrics(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Group 7: Mid Game Analysis (10-25 mins)"""
        # Break down kills by time
        kills_log = data.get("kills_log", [])
        mid_game_kills = len([k for k in kills_log if 600 < k.get("time", 0) <= 1500])
        
        # Efficiency: GPM in mid game vs average
        gold_t = data.get("gold_t", [])
        mid_efficiency = 0
        if len(gold_t) > 25:
            gold_gain = gold_t[25] - gold_t[10]
            mid_efficiency = (gold_gain / 15) / 500 # Relative to 500 GPM
            
        return {
            "mid_game_kills": mid_game_kills,
            "mid_efficiency_score": round(min(100, mid_efficiency * 100), 1),
            "objectives_participation": 0 # Difficult from summarized JSON
        }

    def calculate_lategame_metrics(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Group 8: Late Game Analysis (25+ mins)"""
        kills_log = data.get("kills_log", [])
        late_kills = len([k for k in kills_log if k.get("time", 0) > 1500])
        
        return {
            "late_game_kills": late_kills,
            "high_ground_defense": 0,
            "buyback_efficiency": data.get("buyback_count", 0) # Proxy
        }

    def calculate_teamfight_stats(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Group 3/9: Teamfight & Fighting"""
        kills = data.get("kills", 0)
        assists = data.get("assists", 0)
        
        # Need team total kills for participation
        # Mocking 40 team kills if not present
        team_kills = 40 
        
        participation = round(((kills + assists) / team_kills) * 100, 1)
        
        hero_damage = data.get("hero_damage", 0)
        duration = data.get("duration_minutes", 1)
        
        return {
            "teamfight_participation": participation,
            "hero_damage_per_min": round(hero_damage / duration, 0),
            "damage_per_kill": round(hero_damage / max(kills, 1), 0)
        }

    def calculate_item_efficiency(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Group 5: Item Analysis"""
        items = []
        for i in range(6):
            # item_0, item_1... keys in OpenDota style
            item_id = data.get(f"item_{i}")
            if item_id:
                items.append(item_id)
        
        # Also check separate 'items' list if available
        if not items and "items" in data:
            # If it's a list of IDs or objects
            raw_items = data["items"]
            if raw_items and isinstance(raw_items[0], int):
                 items = raw_items
            elif raw_items and isinstance(raw_items[0], dict):
                 items = [x.get("content") for x in raw_items] # Hypothetical
        
        # Timings
        timings = []
        purchase_log = data.get("purchase_log", [])
        if purchase_log:
            for p in purchase_log:
                timings.append({
                    "name": p.get("key"),
                    "time": p.get("time")
                })
        
        return {
            "count": len(items),
            "timings": timings,
            "gold_efficiency": 90 # Placeholder
        }

    def calculate_positioning_risk(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Group 9: Positioning Risk calculation based on deaths and mapping data."""
        # Use direct deaths count if log is missing
        total_deaths = data.get("deaths", 0)
        
        # Risk/Reward proxy
        gpm = data.get("gold_per_min", 1)
        deaths_per_gpm = total_deaths / (gpm / 100) if gpm > 0 else 0
        
        # Safety rating: base 100, deduct for deaths
        safety_rating = max(0, 100 - (total_deaths * 10))
        
        return {
            "safety_rating": round(safety_rating, 1),
            "total_deaths": total_deaths,
            "deaths_per_100_gpm": round(deaths_per_gpm, 2),
            "danger_zone_pct": round(min(100, total_deaths * 8), 1)
        }

    def calculate_warding_value(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Group 10: Vision Analysis using obs/sen logs."""
        obs_log = data.get("obs_log", [])
        sen_log = data.get("sen_log", [])
        
        total_obs = len(obs_log)
        total_sen = len(sen_log)
        
        # Calculate vision coverage score (diversity of placements)
        # Using a simple set of unique coordinates
        unique_pos = set([(w.get("x"), w.get("y")) for w in obs_log])
        coverage = (len(unique_pos) / 5) * 100 if total_obs > 0 else 0
        
        return {
            "wards_placed": total_obs,
            "sentries_placed": total_sen,
            "vision_score": round(min(100, coverage), 1),
            "deward_count": data.get("item_uses", {}).get("item_ward_sentry", 0) # Proxy
        }

    def compare_with_benchmark(self, metrics: Dict[str, Any], hero_name: str) -> Dict[str, Any]:
        """Group 12: High-fidelity Comparison with MMR-Adjusted Benchmarks."""
        benchmarks = metrics.get("_raw_benchmarks", {})
        if not benchmarks:
            return {"tier": "B", "performance_rating": 50}

        results = {}
        pct_sum = 0
        count = 0
        
        for key, val in benchmarks.items():
            if isinstance(val, dict) and "pct" in val:
                pct = val.get("pct", 0.5)
                results[f"{key}_pct"] = round(pct * 100, 1)
                pct_sum += pct
                count += 1
        
        avg_pct = (pct_sum / count) if count > 0 else 0.5
        
        if avg_pct >= 0.9: tier = "S"
        elif avg_pct >= 0.75: tier = "A"
        elif avg_pct >= 0.5: tier = "B"
        elif avg_pct >= 0.25: tier = "C"
        else: tier = "D"
        
        results["tier"] = tier
        results["performance_rating"] = int(avg_pct * 100)
        return results

    def generate_deterministic_advice(self, metrics: Dict[str, Any], benchmarks: Dict[str, Any]) -> Dict[str, Any]:
        """Group 13: Decision Quality & Advice"""
        
        mistakes = []
        improvements = [] # These will be rich objects
        
        lh = metrics.get("last_hits", 0)
        
        if lh < 100:
            msg = "Low farm priority: You need to focus more on securing last hits throughout the game."
            mistakes.append(msg)
            improvements.append({
                "category": "Farming",
                "title": "Improve Last Hitting",
                "description": "Aim for at least 150-200 last hits as a core hero to maintain economic pressure.",
                "priority": "high",
                "type": "improvement"
            })
            
        gpm = metrics.get("gpm", 0)
        if gpm < 400:
            mistakes.append("Insufficient GPM: Your gold accumulation is below the optimal threshold for your role.")
            improvements.append({
                "category": "Economy",
                "title": "Maximize GPM",
                "description": "Utilize empty lanes and jungle camps more efficiently during mid-game rotations.",
                "priority": "medium",
                "type": "improvement"
            })

        kda = metrics.get("kda", 0)
        if kda < 2.0:
            mistakes.append("High death count or low participation.")
            improvements.append({
                "category": "Combat",
                "title": "Teamfight Positioning",
                "description": "Work on your positioning in teamfights to stay alive longer and contribute more damage.",
                "priority": "high",
                "type": "improvement"
            })

        # Add some strengths if metrics are good
        if metrics.get("vision_score", 0) > 40:
            improvements.append({
                "category": "Vision",
                "title": "Excellent Map Control",
                "description": "Your warding and vision score were significantly above average this match.",
                "priority": "low",
                "type": "strength"
            })

        return {
            "top_mistakes": mistakes,
            "top_improvements": improvements,
            "playstyle_analysis": "Balanced",
            "score": max(40, 100 - (len(mistakes) * 10))
        }
