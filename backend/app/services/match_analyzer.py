"""Match analyzer service for calculating 60+ performance metrics."""

from typing import Dict, Any, List, Optional
import logging

from app.services.benchmark_service import benchmark_service

logger = logging.getLogger(__name__)


class MatchAnalyzer:
    """
    Service for analyzing parsed match data and generating 60+ metrics.
    
    Calculates deterministic metrics across categories:
    - Basic (10): GPM, XPM, LH, Denies, KDA, etc.
    - Positioning (8): Distance, Danger Zone, Safety Score, etc.
    - Fighting (10): Teamfight participation, Stun duration, etc.
    - Timing (12): Item timings, Level progression, etc.
    - Warding (6): Wards placed, Vision uptime, etc.
    - Lane Phase (6): LH@10, Gold@10, Lane control, etc.
    - Mid Game (5): GPM 10-25, Objectives, etc.
    - Late Game (4): Gold efficiency, HG control, etc.
    """
    
    def analyze_match(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze parsed match data and generate all metrics/advice.
        
        Args:
            parsed_data: Normalized data from ReplayParser.
            
        Returns:
            Dictionary with metrics, advice, score, strengths, weaknesses.
        """
        metrics = {}
        
        # Calculate all 60+ metrics by category
        metrics["basic"] = self.calculate_gpm_xpm(parsed_data)
        metrics["positioning"] = self.calculate_positioning_risk(parsed_data)
        metrics["fighting"] = self.calculate_teamfight_stats(parsed_data)
        metrics["timing"] = self.calculate_item_efficiency(parsed_data)
        metrics["warding"] = self.calculate_warding_value(parsed_data)
        metrics["lane_phase"] = self.calculate_lane_metrics(parsed_data)
        metrics["mid_game"] = self.calculate_midgame_metrics(parsed_data)
        metrics["late_game"] = self.calculate_lategame_metrics(parsed_data)
        
        # Flatten metrics for storage
        flat_metrics = self._flatten_metrics(metrics)
        
        # Compare with benchmarks
        hero_name = parsed_data.get("hero_name", "")
        benchmark_comparison = self.compare_with_benchmark(flat_metrics, hero_name)
        flat_metrics["benchmark_comparison"] = benchmark_comparison
        
        # Generate advice
        advice = self.generate_deterministic_advice(flat_metrics, benchmark_comparison)
        
        # Calculate overall score
        overall_score = self._calculate_overall_score(flat_metrics, benchmark_comparison)
        
        # Identify strengths and weaknesses
        strengths = self._identify_strengths(flat_metrics, benchmark_comparison)
        weaknesses = self._identify_weaknesses(flat_metrics, benchmark_comparison)
        
        # Power spikes and mistakes
        power_spikes = self._analyze_power_spikes(flat_metrics, parsed_data)
        mistakes = self._detect_mistakes(flat_metrics, parsed_data)
        
        return {
            "metrics": flat_metrics,
            "advice": advice,
            "overall_score": overall_score,
            "strengths": strengths,
            "weaknesses": weaknesses,
            "power_spikes": power_spikes,
            "mistakes": mistakes
        }
    
    # =========================================================================
    # BASIC METRICS (10)
    # =========================================================================
    def calculate_gpm_xpm(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate basic performance metrics (10 total).
        
        Metrics:
        1. GPM (gold per minute)
        2. XPM (experience per minute)
        3. Last hits
        4. Denies
        5. Kill/Death/Assist ratio
        6. Damage ratio (hero damage / team total)
        7. Gold spent efficiency
        8. Items purchased count
        9. Respawn timer sum
        10. Time dead percentage
        """
        duration = max(data.get("duration_minutes", 1), 1)
        kills = data.get("kills", 0)
        deaths = max(data.get("deaths", 1), 1)
        assists = data.get("assists", 0)
        
        full_data = data.get("full_data", {})
        
        gpm = data.get("gpm", 0)
        xpm = data.get("xpm", 0)
        last_hits = data.get("last_hits", 0)
        denies = data.get("denies", 0)
        hero_damage = data.get("hero_damage", 0)
        
        # Calculate KDA
        kda = round((kills + assists) / deaths, 2)
        
        # Damage ratio (estimate team damage as 5x player damage for solo context)
        team_damage = full_data.get("team_damage", hero_damage * 5)
        damage_ratio = round(hero_damage / max(team_damage, 1), 3)
        
        # Gold spent efficiency
        gold_earned = gpm * duration
        gold_spent = full_data.get("gold_spent", gold_earned * 0.85)
        gold_efficiency = round(gold_spent / max(gold_earned, 1), 2)
        
        # Items purchased
        items = data.get("items", [])
        items_count = len(items) if isinstance(items, list) else 0
        
        # Respawn timer sum and time dead
        respawn_sum = full_data.get("respawn_timer_sum", deaths * 30)
        duration_seconds = duration * 60
        time_dead_pct = round((respawn_sum / max(duration_seconds, 1)) * 100, 1)
        
        return {
            "gpm": gpm,
            "xpm": xpm,
            "last_hits": last_hits,
            "denies": denies,
            "kda": kda,
            "kills": kills,
            "deaths": deaths,
            "assists": assists,
            "damage_ratio": damage_ratio,
            "gold_efficiency": gold_efficiency,
            "items_count": items_count,
            "respawn_sum": respawn_sum,
            "time_dead_pct": time_dead_pct
        }
    
    # =========================================================================
    # POSITIONING METRICS (8)
    # =========================================================================
    def calculate_positioning_risk(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate positioning metrics (8 total).
        
        Metrics:
        1. Avg distance from team center
        2. % time in danger zone
        3. % time farming
        4. Movement speed avg
        5. Position safety score
        6. Farm location diversity
        7. Proximity to objectives
        8. Tower proximity analysis
        """
        full_data = data.get("full_data", {})
        positioning = full_data.get("positioning", {})
        
        return {
            "avg_distance_from_team": positioning.get("avg_distance_from_team", 0),
            "danger_zone_pct": positioning.get("danger_zone_pct", 0),
            "farming_time_pct": positioning.get("farming_time_pct", 0),
            "movement_speed_avg": positioning.get("movement_speed_avg", 0),
            "position_safety_score": positioning.get("position_safety_score", 0.5),
            "farm_location_diversity": positioning.get("farm_location_diversity", 0),
            "objective_proximity": positioning.get("objective_proximity", 0),
            "tower_proximity_score": positioning.get("tower_proximity_score", 0)
        }
    
    # =========================================================================
    # FIGHTING METRICS (10)
    # =========================================================================
    def calculate_teamfight_stats(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate fighting metrics (10 total).
        
        Metrics:
        1. Teamfight participation %
        2. Kills in fights / total
        3. Deaths in fights / total
        4. Damage in fights
        5. Stun duration total
        6. Disable application rate
        7. Last hit steal % (if pos 4-5)
        8. Save success rate
        9. Roshan kill participation
        10. Gank response time
        """
        full_data = data.get("full_data", {})
        combat = full_data.get("combat", {})
        
        kills = data.get("kills", 0)
        deaths = data.get("deaths", 1)
        
        teamfight_kills = combat.get("teamfight_kills", kills * 0.7)
        teamfight_deaths = combat.get("teamfight_deaths", deaths * 0.6)
        
        return {
            "teamfight_participation": combat.get("teamfight_participation", 0),
            "fight_kills_ratio": round(teamfight_kills / max(kills, 1), 2),
            "fight_deaths_ratio": round(teamfight_deaths / max(deaths, 1), 2),
            "fight_damage": combat.get("fight_damage", 0),
            "stun_duration_total": combat.get("stun_duration", 0),
            "disable_rate": combat.get("disable_rate", 0),
            "last_hit_steal_pct": combat.get("last_hit_steal_pct", 0),
            "save_success_rate": combat.get("save_success_rate", 0),
            "roshan_participation": combat.get("roshan_participation", 0),
            "gank_response_time": combat.get("gank_response_time", 0)
        }
    
    # =========================================================================
    # TIMING METRICS (12)
    # =========================================================================
    def calculate_item_efficiency(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate item timing metrics (12 total).
        
        Metrics:
        1. First item timing
        2-4. Core items timing (3 items)
        5. Boots timing
        6. Blink dagger timing
        7. Upgrade items timing
        8. Comparison with pro average
        9. Item completion rate
        10. GPM by timing windows
        11. XPM by timing windows
        12. Level progression timing
        """
        full_data = data.get("full_data", {})
        item_timings = data.get("item_timings", {})
        timing_data = full_data.get("timing", {})
        
        # Extract specific timings
        first_item = min(item_timings.values()) if item_timings else 0
        boots_timing = self._find_item_timing(item_timings, ["boots", "power_treads", "phase_boots", "arcane_boots"])
        blink_timing = item_timings.get("item_blink", item_timings.get("blink", 0))
        
        # Core items (top 3 by cost)
        core_items = sorted(item_timings.items(), key=lambda x: x[1])[:3]
        core_timings = [t[1] for t in core_items] if core_items else [0, 0, 0]
        
        # Pro comparison
        blink_pro = benchmark_service.get_pro_item_timing("blink") or 780
        blink_diff = (blink_timing - blink_pro) if blink_timing > 0 else 0
        
        return {
            "first_item_timing": first_item,
            "core_item_1_timing": core_timings[0] if len(core_timings) > 0 else 0,
            "core_item_2_timing": core_timings[1] if len(core_timings) > 1 else 0,
            "core_item_3_timing": core_timings[2] if len(core_timings) > 2 else 0,
            "boots_timing": boots_timing,
            "blink_timing": blink_timing,
            "upgrade_items_timing": timing_data.get("upgrade_items_timing", 0),
            "pro_timing_diff": blink_diff,
            "item_completion_rate": timing_data.get("item_completion_rate", 0),
            "gpm_by_window": timing_data.get("gpm_by_window", {}),
            "xpm_by_window": timing_data.get("xpm_by_window", {}),
            "level_timing": timing_data.get("level_timing", {})
        }
    
    # =========================================================================
    # WARDING METRICS (6)
    # =========================================================================
    def calculate_warding_value(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate warding metrics (6 total).
        
        Metrics:
        1. Wards placed count
        2. Average ward value
        3. Ward placement locations
        4. Vision uptime %
        5. Deward count
        6. Counter-ward success
        """
        full_data = data.get("full_data", {})
        map_data = full_data.get("map", {})
        warding = full_data.get("warding", {})
        
        wards_placed = map_data.get("wards_placed", 0)
        
        return {
            "wards_placed": wards_placed,
            "avg_ward_value": warding.get("avg_ward_value", 0),
            "ward_locations": warding.get("ward_locations", []),
            "vision_uptime_pct": warding.get("vision_uptime_pct", 0),
            "deward_count": map_data.get("wards_destroyed", 0),
            "counter_ward_success": warding.get("counter_ward_success", 0)
        }
    
    # =========================================================================
    # LANE PHASE METRICS (0-10 min) (6)
    # =========================================================================
    def calculate_lane_metrics(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate lane phase metrics 0-10 min (6 total).
        
        Metrics:
        1. Last hits at 10
        2. Deaths in lane
        3. Gold at 10 min
        4. XP at 10 min
        5. Lane control %
        6. Jungle camps stacked
        """
        full_data = data.get("full_data", {})
        laning = full_data.get("laning", {})
        
        return {
            "lh_at_10": laning.get("last_hits_10min", 0),
            "deaths_in_lane": laning.get("deaths_10min", 0),
            "gold_at_10": laning.get("gold_10min", 0),
            "xp_at_10": laning.get("xp_10min", 0),
            "lane_control_pct": laning.get("lane_control_pct", 0),
            "camps_stacked": laning.get("camps_stacked", 0)
        }
    
    # =========================================================================
    # MID GAME METRICS (10-25 min) (5)
    # =========================================================================
    def calculate_midgame_metrics(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate mid game metrics 10-25 min (5 total).
        
        Metrics:
        1. GPM during period
        2. Deaths during period
        3. Fight participation
        4. Objective taken count
        5. Farm pattern efficiency
        """
        full_data = data.get("full_data", {})
        midgame = full_data.get("midgame", {})
        
        return {
            "midgame_gpm": midgame.get("gpm", 0),
            "midgame_deaths": midgame.get("deaths", 0),
            "midgame_fight_participation": midgame.get("fight_participation", 0),
            "objectives_taken": midgame.get("objectives_taken", 0),
            "farm_pattern_efficiency": midgame.get("farm_pattern_efficiency", 0)
        }
    
    # =========================================================================
    # LATE GAME METRICS (25+ min) (4)
    # =========================================================================
    def calculate_lategame_metrics(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate late game metrics 25+ min (4 total).
        
        Metrics:
        1. Gold efficiency
        2. Positioning in fights
        3. High ground control
        4. Buyback utilization
        """
        full_data = data.get("full_data", {})
        lategame = full_data.get("lategame", {})
        
        return {
            "lategame_gold_efficiency": lategame.get("gold_efficiency", 0),
            "fight_positioning_score": lategame.get("fight_positioning_score", 0),
            "high_ground_control": lategame.get("high_ground_control", 0),
            "buyback_utilization": lategame.get("buyback_utilization", 0)
        }
    
    # =========================================================================
    # BENCHMARK COMPARISON
    # =========================================================================
    def compare_with_benchmark(
        self, 
        metrics: Dict[str, Any], 
        hero_name: str
    ) -> Dict[str, Any]:
        """
        Compare player metrics with benchmarks.
        
        Args:
            metrics: Flat dictionary of calculated metrics.
            hero_name: Hero name for hero-specific benchmarks.
            
        Returns:
            Dictionary with comparison ratios for key metrics.
        """
        benchmarks = benchmark_service.DEFAULT_BENCHMARKS
        
        comparisons = {}
        
        # GPM comparison
        benchmark_gpm = benchmarks.get("gpm", 450)
        player_gpm = metrics.get("gpm", 0)
        comparisons["gpm_ratio"] = round(player_gpm / max(benchmark_gpm, 1), 2)
        comparisons["gpm_benchmark"] = benchmark_gpm
        
        # XPM comparison
        benchmark_xpm = benchmarks.get("xpm", 500)
        player_xpm = metrics.get("xpm", 0)
        comparisons["xpm_ratio"] = round(player_xpm / max(benchmark_xpm, 1), 2)
        comparisons["xpm_benchmark"] = benchmark_xpm
        
        # Deaths comparison
        benchmark_deaths = benchmarks.get("deaths", 5)
        player_deaths = metrics.get("deaths", 0)
        comparisons["deaths_ratio"] = round(player_deaths / max(benchmark_deaths, 1), 2)
        comparisons["deaths_benchmark"] = benchmark_deaths
        
        # Last hits comparison
        benchmark_lh = benchmarks.get("last_hits", 200)
        player_lh = metrics.get("last_hits", 0)
        comparisons["last_hits_ratio"] = round(player_lh / max(benchmark_lh, 1), 2)
        comparisons["last_hits_benchmark"] = benchmark_lh
        
        return comparisons
    
    # =========================================================================
    # DETERMINISTIC ADVICE GENERATION
    # =========================================================================
    def generate_deterministic_advice(
        self, 
        metrics: Dict[str, Any],
        benchmarks: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Generate coaching advice based on deterministic rules.
        
        Args:
            metrics: Calculated performance metrics.
            benchmarks: Benchmark comparison data.
            
        Returns:
            List of advice items with type, severity, message, suggestion.
        """
        advice = []
        
        # ===== FARMING ADVICE =====
        gpm_ratio = benchmarks.get("gpm_ratio", 1.0)
        if gpm_ratio < 0.8:
            advice.append({
                "type": "farming",
                "severity": "warning",
                "message": f"Your GPM {metrics.get('gpm', 0)} is {int((1 - gpm_ratio) * 100)}% below average",
                "suggestion": "Focus on efficient farming. Reduce time traveling, more time hitting creeps."
            })
        
        # ===== DEATHS ADVICE =====
        deaths_ratio = benchmarks.get("deaths_ratio", 1.0)
        if deaths_ratio > 1.5:
            advice.append({
                "type": "positioning",
                "severity": "critical",
                "message": f"You die {metrics.get('deaths', 0)} times vs average {benchmarks.get('deaths_benchmark', 5)}",
                "suggestion": "Work on positioning. Stay further back in fights. Watch pro replays."
            })
        
        # ===== POSITIONING ADVICE =====
        position_risk = metrics.get("position_safety_score", 0.5)
        if position_risk < 0.3:
            advice.append({
                "type": "positioning",
                "severity": "warning",
                "message": "You spend too much time in dangerous positions",
                "suggestion": "Position safer. Use fog of war. Play further from enemies."
            })
        
        # ===== ITEM TIMING ADVICE =====
        blink_timing = metrics.get("blink_timing", 0)
        pro_blink = benchmark_service.get_pro_item_timing("blink") or 780
        if blink_timing > 0 and blink_timing > pro_blink + 300:
            advice.append({
                "type": "itemization",
                "severity": "warning",
                "message": f"Blink timing {blink_timing // 60}:{blink_timing % 60:02d} vs pro avg {pro_blink // 60}:{pro_blink % 60:02d}",
                "suggestion": "Speed up farming. Practice item builds in practice lobby."
            })
        
        # ===== WARDING ADVICE =====
        wards_placed = metrics.get("wards_placed", 0)
        if wards_placed < 5:
            advice.append({
                "type": "warding",
                "severity": "info",
                "message": f"You placed only {wards_placed} wards this game",
                "suggestion": "Even as a core, consider carrying a ward. Vision wins games."
            })
        
        # ===== LANE PHASE ADVICE =====
        lh_at_10 = metrics.get("lh_at_10", 0)
        if lh_at_10 < 50:
            advice.append({
                "type": "laning",
                "severity": "warning",
                "message": f"Only {lh_at_10} last hits at 10 min is below average",
                "suggestion": "Practice last hitting. Aim for 60+ at 10 minutes for cores."
            })
        
        # ===== KDA ADVICE =====
        kda = metrics.get("kda", 0)
        if kda < 2.0:
            advice.append({
                "type": "combat",
                "severity": "warning",
                "message": f"KDA of {kda} indicates too many deaths relative to kills",
                "suggestion": "Focus on surviving fights. Get assists if you can't get kills safely."
            })
        
        # ===== TEAMFIGHT ADVICE =====
        tf_participation = metrics.get("teamfight_participation", 0)
        if tf_participation < 0.4:
            advice.append({
                "type": "teamplay",
                "severity": "info",
                "message": f"Only {int(tf_participation * 100)}% teamfight participation",
                "suggestion": "Join more fights with your team. Map awareness is key."
            })
        
        # Sort by severity
        severity_order = {"critical": 0, "warning": 1, "info": 2}
        advice.sort(key=lambda x: severity_order.get(x.get("severity", "info"), 2))
        
        return advice
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    def _flatten_metrics(self, categorized: Dict[str, Dict]) -> Dict[str, Any]:
        """Flatten categorized metrics into single dictionary."""
        flat = {}
        for category, metrics in categorized.items():
            if isinstance(metrics, dict):
                flat.update(metrics)
        return flat
    
    def _find_item_timing(
        self, 
        timings: Dict[str, int], 
        item_names: List[str]
    ) -> int:
        """Find timing for any of the given item names."""
        for name in item_names:
            for key, value in timings.items():
                if name in key.lower():
                    return value
        return 0
    
    def _calculate_overall_score(
        self, 
        metrics: Dict[str, Any],
        benchmarks: Dict[str, Any]
    ) -> int:
        """Calculate overall performance score (0-100)."""
        score = 50  # Base score
        
        # GPM contribution (max +15)
        gpm_ratio = benchmarks.get("gpm_ratio", 1.0)
        score += min(int((gpm_ratio - 1) * 30), 15)
        
        # XPM contribution (max +10)
        xpm_ratio = benchmarks.get("xpm_ratio", 1.0)
        score += min(int((xpm_ratio - 1) * 20), 10)
        
        # KDA contribution (max +15)
        kda = metrics.get("kda", 2)
        score += min(int((kda - 2) * 5), 15)
        
        # Deaths penalty (max -20)
        deaths_ratio = benchmarks.get("deaths_ratio", 1.0)
        if deaths_ratio > 1.0:
            score -= min(int((deaths_ratio - 1) * 20), 20)
        
        # Last hits contribution (max +10)
        lh_ratio = benchmarks.get("last_hits_ratio", 1.0)
        score += min(int((lh_ratio - 1) * 20), 10)
        
        return max(0, min(100, score))
    
    def _identify_strengths(
        self, 
        metrics: Dict[str, Any],
        benchmarks: Dict[str, Any]
    ) -> List[str]:
        """Identify player's strengths based on metrics."""
        strengths = []
        
        if benchmarks.get("gpm_ratio", 0) >= 1.2:
            strengths.append("Excellent gold farming")
        if benchmarks.get("xpm_ratio", 0) >= 1.2:
            strengths.append("Strong XP gain")
        if metrics.get("kda", 0) >= 4.0:
            strengths.append("High KDA ratio")
        if metrics.get("deaths", 10) <= 3:
            strengths.append("Low death count")
        if metrics.get("teamfight_participation", 0) >= 0.7:
            strengths.append("Active in teamfights")
        if metrics.get("wards_placed", 0) >= 15:
            strengths.append("Vision contribution")
        
        return strengths[:5]
    
    def _identify_weaknesses(
        self, 
        metrics: Dict[str, Any],
        benchmarks: Dict[str, Any]
    ) -> List[str]:
        """Identify player's weaknesses based on metrics."""
        weaknesses = []
        
        if benchmarks.get("gpm_ratio", 1) < 0.8:
            weaknesses.append("Low GPM compared to average")
        if benchmarks.get("deaths_ratio", 0) > 1.5:
            weaknesses.append("Too many deaths")
        if metrics.get("kda", 10) < 2.0:
            weaknesses.append("Low KDA ratio")
        if metrics.get("lh_at_10", 100) < 40:
            weaknesses.append("Weak laning phase")
        if metrics.get("position_safety_score", 1) < 0.3:
            weaknesses.append("Risky positioning")
        
        return weaknesses[:5]
    
    def _analyze_power_spikes(
        self, 
        metrics: Dict[str, Any], 
        data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Identify power spikes based on item timings."""
        spikes = []
        
        major_items = {
            "blink": {"early": 600, "late": 900, "name": "Blink Dagger"},
            "black_king_bar": {"early": 1080, "late": 1500, "name": "BKB"},
            "battle_fury": {"early": 720, "late": 1020, "name": "Battle Fury"},
            "hand_of_midas": {"early": 420, "late": 660, "name": "Hand of Midas"},
            "radiance": {"early": 900, "late": 1200, "name": "Radiance"}
        }
        
        item_timings = data.get("item_timings", {})
        
        for item_key, config in major_items.items():
            for timing_key, timing_val in item_timings.items():
                if item_key in timing_key.lower():
                    status = "early" if timing_val <= config["early"] else \
                             "late" if timing_val >= config["late"] else "average"
                    spikes.append({
                        "item": config["name"],
                        "time": timing_val,
                        "timing_minutes": round(timing_val / 60, 1),
                        "status": status
                    })
                    break
        
        return spikes
    
    def _detect_mistakes(
        self, 
        metrics: Dict[str, Any], 
        data: Dict[str, Any]
    ) -> List[str]:
        """Identify specific gameplay mistakes."""
        mistakes = []
        
        # Laning mistakes
        if metrics.get("lh_at_10", 100) < 40:
            mistakes.append("Poor last hitting in lane phase")
        
        if metrics.get("deaths_in_lane", 0) > 2:
            mistakes.append("Too many deaths in laning phase")
        
        # Farming mistakes
        if metrics.get("time_dead_pct", 0) > 15:
            mistakes.append("Too much time spent dead")
        
        # Positioning mistakes
        if metrics.get("position_safety_score", 1) < 0.3:
            mistakes.append("Frequently caught in dangerous positions")
        
        # Warding mistakes (for supports)
        if metrics.get("wards_placed", 100) < 5:
            mistakes.append("Limited vision contribution")
        
        return mistakes
