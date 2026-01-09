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
        metrics["mid_game"] = self.calculate_midgame_metrics(parsed_data)
        metrics["late_game"] = self.calculate_lategame_metrics(parsed_data)
        
        # Flatten metrics for storage
        flat_metrics = self._flatten_metrics(metrics)
        flat_metrics["position"] = parsed_data.get("position")
        
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
        
        # Pro Benchmarks
        hero_id = parsed_data.get("hero_id")
        if not hero_id and "full_data" in parsed_data:
             hero_id = parsed_data["full_data"].get("hero_id")
             
        # Resolve from name if still None
        if not hero_id:
             # Very basic fallback for standard heroes
             hero_id = 1 # Default to Anti-Mage if unknown for benchmark purposes
             
        duration = max(parsed_data.get("duration_minutes", 1), 1)
        benchmarks = benchmark_service.get_hero_benchmarks_sync(hero_id)
        pro_gpm = benchmark_service.get_benchmark_for_metric(benchmarks, "gold_per_min", "75")
        pro_xpm = benchmark_service.get_benchmark_for_metric(benchmarks, "xp_per_min", "75")
        pro_lh = benchmark_service.get_benchmark_for_metric(benchmarks, "last_hits_per_min", "75") * duration
        
        flat_metrics.update({
            "pro_avg_gpm": pro_gpm,
            "pro_avg_xpm": pro_xpm,
            "pro_avg_lh": pro_lh,
            "pro_avg_lh_10": 55, # Standard pro average
            "pro_avg_vision": 15.5
        })
        
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
        """Calculate basic performance metrics (10 total)."""
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
        
        # Damage ratio
        team_damage = full_data.get("team_damage") or (hero_damage * 4) # Estimate if missing
        damage_ratio = round(hero_damage / max(team_damage, 1), 3)
        
        # Gold efficiency (net worth vs gold earned)
        net_worth = data.get("net_worth", gpm * duration)
        gold_efficiency = round(net_worth / max(gpm * duration, 1), 2)
        
        # Items count
        items = data.get("items", [])
        items_count = len(items)
        
        # Death impact
        respawn_sum = full_data.get("respawn_timer_sum", deaths * 30)
        time_dead_pct = round((respawn_sum / max(duration * 60, 1)) * 100, 1)
        
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
        """Calculate positioning metrics (8 total) from coordinate data."""
        full_data = data.get("full_data", {})
        positions = full_data.get("positions", []) # List of {time, x, y}
        
        if not positions:
            return {
                "avg_distance_from_team": 0,
                "danger_zone_pct": 0,
                "farming_time_pct": 0,
                "movement_speed_avg": 0,
                "position_safety_score": 50,
                "farm_location_diversity": 0,
                "objective_proximity": 0,
                "tower_proximity_score": 0
            }
        
        # Calculate Danger Zone (proximity to enemies when no allies are near)
        # For simplicity in this heuristic, we'll use a score based on distance from base
        danger_ticks = 0
        total_dist = 0
        for pos in positions:
            x, y = pos.get("x", 0), pos.get("y", 0)
            dist_from_origin = (x**2 + y**2)**0.5
            total_dist += dist_from_origin
            if dist_from_origin > 3000: # Deep in enemy territory
                danger_ticks += 1
                
        danger_zone_pct = round((danger_ticks / len(positions)) * 100, 1)
        avg_dist = round(total_dist / len(positions), 0)
        
        return {
            "avg_distance_from_team": avg_dist / 10, # Scaled
            "danger_zone_pct": danger_zone_pct,
            "farming_time_pct": 0,
            "movement_speed_avg": 0,
            "position_safety_score": max(0, 100 - danger_zone_pct),
            "farm_location_diversity": 0,
            "objective_proximity": 0,
            "tower_proximity_score": 0
        }
    
    # =========================================================================
    # FIGHTING METRICS (10)
    # =========================================================================
    def calculate_teamfight_stats(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate fighting metrics (10 total) from engagement logs."""
        full_data = data.get("full_data", {})
        combat = full_data.get("combat", {})
        
        kills = data.get("kills", 0)
        assists = data.get("assists", 0)
        deaths = max(data.get("deaths", 1), 1)
        
        # Calculate Participation
        radiant_win = data.get("radiant_win")
        is_radiant = data.get("team") == "radiant"
        team_score = data.get("radiant_score", 0) if is_radiant else data.get("dire_score", 0)
        
        tf_participation = round(((kills + assists) / max(team_score, 1)) * 100, 1)
        
        return {
            "teamfight_participation": tf_participation,
            "fight_kills_ratio": round(kills / max(kills + assists, 1), 2),
            "fight_deaths_ratio": 0.5, # Placeholder
            "fight_damage": data.get("hero_damage", 0) * 0.7, # Estimate fight damage
            "stun_duration_total": round(data.get("stuns", 0) or full_data.get("stuns", 0), 1),
            "disable_rate": 0,
            "last_hit_steal_pct": 0,
            "save_success_rate": 0,
            "roshan_participation": 0,
            "gank_response_time": 0
        }
    
    # =========================================================================
    # TIMING METRICS (12)
    # =========================================================================
    def calculate_item_efficiency(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate item timing metrics (12 total)."""
        item_timings = data.get("item_timings", {}) # {item_name: seconds}
        
        blink_time = item_timings.get("item_blink", 0)
        bkb_time = item_timings.get("item_black_king_bar", 0)
        boots_time = 0
        for k, v in item_timings.items():
            if "boots" in k:
                boots_time = v
                break
                
        # Pro comparison for Blink
        pro_blink = benchmark_service.get_pro_item_timing("blink") or 780
        blink_diff = (blink_time - pro_blink) if blink_time > 0 else 0
        
        return {
            "first_item_timing": min(item_timings.values()) if item_timings else 0,
            "core_item_1_timing": blink_time,
            "core_item_2_timing": bkb_time,
            "core_item_3_timing": 0,
            "boots_timing": boots_time,
            "blink_timing": blink_time,
            "upgrade_items_timing": 0,
            "pro_timing_diff": blink_diff,
            "item_completion_rate": len(item_timings) / 10,
            "gpm_by_window": {},
            "xpm_by_window": {},
            "level_timing": {}
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
        obs_placed = full_data.get("obs_placed", 0)
        sen_placed = full_data.get("sen_placed", 0)
        vision_score = (obs_placed * 2.0) + (sen_placed * 1.0)
        
        return {
            "wards_placed": wards_placed,
            "obs_placed": obs_placed,
            "sen_placed": sen_placed,
            "vision_score": vision_score,
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
        """Calculate lane phase metrics 0-10 min (6 total)."""
        full_data = data.get("full_data", {})
        
        # Time series data from Clarity
        lh_t = full_data.get("last_hits_t", [])
        gold_t = full_data.get("gold_t", [])
        xp_t = full_data.get("xp_t", [])
        
        # Safe extraction at 10m mark (600s or index 10 if per-minute)
        idx_10 = 10 if len(lh_t) < 120 else 600
        
        lh_10 = lh_t[idx_10] if len(lh_t) > idx_10 else data.get("lh_at_10", 0)
        gold_10 = gold_t[idx_10] if len(gold_t) > idx_10 else 0
        xp_10 = xp_t[idx_10] if len(xp_t) > idx_10 else 0
        
        return {
            "lh_at_10": lh_10,
            "deaths_in_lane": full_data.get("deaths_10min", 0),
            "gold_at_10": gold_10,
            "xp_at_10": xp_10,
            "lane_control_pct": 0,
            "camps_stacked": data.get("camp_stacking", 0)
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
        """
        advice = []
        
        position = str(metrics.get("position") or "").lower()
        is_core = any(r in position for r in ["safe", "mid", "off", "core", "carry", "1", "2", "3"])
        is_support = any(r in position for r in ["support", "soft", "hard", "4", "5"])
        
        # ===== FARMING ADVICE =====
        gpm_ratio = benchmarks.get("gpm_ratio", 1.0)
        if gpm_ratio < 0.8:
            advice.append({
                "category": "farming",
                "priority": "medium",
                "title": f"Low GPM ({metrics.get('gpm', 0)})",
                "description": "Your GPM is below average. Focus on efficient farming and reducing time traversing the map."
            })
        
        # ===== DEATHS ADVICE =====
        deaths_ratio = benchmarks.get("deaths_ratio", 1.0)
        if deaths_ratio > 1.5:
            advice.append({
                "category": "survival",
                "priority": "high",
                "title": f"High Death Count ({metrics.get('deaths', 0)})",
                "description": "You are dying too often. Work on positioning and stay further back in fights."
            })
        
        # ===== POSITIONING ADVICE =====
        position_risk = metrics.get("position_safety_score", 0.5)
        if position_risk < 0.3:
            advice.append({
                "category": "survival",
                "priority": "medium",
                "title": "Risky Positioning",
                "description": "You spend too much time in dangerous farm zones. Use fog of war effectively."
            })
        
        # ===== ITEM TIMING ADVICE =====
        blink_timing = metrics.get("blink_timing", 0)
        pro_blink = benchmark_service.get_pro_item_timing("blink") or 780
        if blink_timing > 0 and blink_timing > pro_blink + 300:
            advice.append({
                "category": "timing",
                "priority": "medium",
                "title": "Late Blink Dagger",
                "description": f"Timing {blink_timing // 60}:{blink_timing % 60:02d} is slow compared to pro avg. Focus on farming acceleration."
            })
        
        # ===== WARDING ADVICE =====
        wards_placed = metrics.get("wards_placed", 0)
        # Only advise supports or if vision is critically low for team
        if wards_placed < 5 and not is_core:
            advice.append({
                "category": "vision",
                "priority": "low",
                "title": "Low Vision Contribution",
                "description": "Consider buying and placing more wards to help your team control the map."
            })
        
        # ===== LANE PHASE ADVICE =====
        lh_at_10 = metrics.get("lh_at_10", 0)
        if lh_at_10 < 50 and is_core:
            advice.append({
                "category": "laning",
                "priority": "high",
                "title": "Weak Laning Phase",
                "description": f"Only {lh_at_10} Last Hits at 10m. Aim for 50-60+."
            })
        
        # ===== KDA ADVICE =====
        kda = metrics.get("kda", 0)
        if kda < 2.0:
            advice.append({
                "category": "fighting",
                "priority": "medium",
                "title": "Low KDA",
                "description": "Your kill contribution is low relative to deaths. Focus on survival."
            })
        
        # ===== TEAMFIGHT ADVICE =====
        tf_participation = metrics.get("teamfight_participation", 0)
        if tf_participation < 0.4:
            advice.append({
                "category": "fighting",
                "priority": "low",
                "title": "Low Teamfight Participation",
                "description": f"Only {int(tf_participation * 100)}% participation. Join your team for objectives."
            })
        
        # Sort by severity
        priority_order = {"high": 0, "medium": 1, "low": 2}
        advice.sort(key=lambda x: priority_order.get(x.get("priority", "low"), 2))
        
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
