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
    
    def analyze_match(self, parsed_data: Dict[str, Any], hero_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze parsed match data for a specific hero or the match overall.
        
        Args:
            parsed_data: Full match data from ReplayParser.
            hero_name: npc_dota_hero_* name to isolate.
            
        Returns:
            Dictionary with metrics, advice, score, strengths, weaknesses, and game_stages.
        """
        # 1. Isolate the target player data
        player_data = None
        heroes_list = parsed_data.get("heroes", [])
        
        if hero_name:
            for h in heroes_list:
                if h.get("hero_name") == hero_name:
                    player_data = h
                    break
        
        # If no hero specified or not found, use a default fallback (first hero)
        # but warn that match-level analysis is limited
        if not player_data and heroes_list:
            player_data = heroes_list[0]
            logger.warning(f"Analysis for {hero_name} requested but not found. Falling back to {player_data.get('hero_name')}")
        elif not player_data:
            # Create a minimal structure if somehow heroes list is empty
            player_data = parsed_data
            
        # Ensure duration_minutes is globally available to calculators
        duration = parsed_data.get("duration_minutes", 30)
        player_data["duration_minutes"] = duration
        
        # Get hero index and position for laning analysis
        hero_index = None
        player_position = "pos1"
        
        if hero_name:
            hero_index = self._get_hero_index(parsed_data, hero_name)
            if hero_index is not None:
                player_position = self._get_player_position(parsed_data, hero_index)
                logger.info(f"[analyze_match] Analyzing {hero_name} (position: {player_position}, index: {hero_index})")
        
        metrics = {}
        
        # Calculate all 60+ metrics by category using the isolated player_data
        metrics["basic"] = self.calculate_gpm_xpm(player_data)
        metrics["positioning"] = self.calculate_positioning_risk(player_data)
        metrics["fighting"] = self.calculate_teamfight_stats(player_data)
        metrics["timing"] = self.calculate_item_efficiency(player_data)
        metrics["warding"] = self.calculate_warding_value(player_data)
        metrics["lane_phase"] = self.calculate_lane_metrics(player_data)
        metrics["mid_game"] = self.calculate_midgame_metrics(player_data)
        metrics["late_game"] = self.calculate_lategame_metrics(player_data)
        
        # === NEW: LANING STAGE ANALYSIS (0-10 min) ===
        laning_data = {}
        laning_analysis = {}
        
        if hero_name:
            laning_data = self._extract_laning_stage_data(parsed_data, hero_name)
            if laning_data:
                laning_analysis = self._analyze_laning_performance(laning_data, player_position)
                logger.info(f"[analyze_match] Laning stage analysis: score={laning_analysis.get('laning_score', 0)}")
        
        # Flatten metrics for storage
        flat_metrics = self._flatten_metrics(metrics)
        flat_metrics["position"] = player_data.get("position")
        
        # Compare with benchmarks
        active_hero = player_data.get("hero_name", hero_name or "")
        benchmark_comparison = self.compare_with_benchmark(flat_metrics, active_hero)
        flat_metrics["benchmark_comparison"] = benchmark_comparison
        
        # Generate advice
        advice = self.generate_deterministic_advice(flat_metrics, benchmark_comparison)
        
        # Merge laning advice with general advice
        if laning_analysis.get("advice"):
            advice.extend(laning_analysis["advice"])
        
        # Calculate overall score
        overall_score = self._calculate_overall_score(flat_metrics, benchmark_comparison)
        
        # If laning analysis exists, factor it into overall score
        if laning_analysis.get("laning_score"):
            # Weight: 60% existing score + 40% laning score
            overall_score = int(overall_score * 0.6 + laning_analysis["laning_score"] * 0.4)
        
        # Identify strengths and weaknesses
        strengths = self._identify_strengths(flat_metrics, benchmark_comparison)
        weaknesses = self._identify_weaknesses(flat_metrics, benchmark_comparison)
        
        # Power spikes and mistakes
        power_spikes = self._analyze_power_spikes(flat_metrics, player_data)
        mistakes = self._detect_mistakes(flat_metrics, player_data)
        
        # Pro Benchmarks (keep for backward compatibility)
        hero_id = player_data.get("hero_id")
        benchmarks = benchmark_service.get_hero_benchmarks_sync(hero_id)
        pro_gpm = benchmark_service.get_benchmark_for_metric(benchmarks, "gold_per_min", "75")
        pro_xpm = benchmark_service.get_benchmark_for_metric(benchmarks, "xp_per_min", "75")
        pro_lh = benchmark_service.get_benchmark_for_metric(benchmarks, "last_hits_per_min", "75") * duration
        
        # Update flat_metrics with pro benchmarks (keeping for backward compatibility)
        # But now these are NOT hardcoded - they come from benchmark_service or laning_analysis
        flat_metrics.update({
            "pro_avg_gpm": pro_gpm,
            "pro_avg_xpm": pro_xpm,
            "pro_avg_lh": pro_lh,
            # Use actual laning analysis data instead of hardcoded values
            "pro_avg_lh_10": laning_analysis.get("comparison", {}).get("expected_lh", 55),
            "pro_avg_vision": 15.5  # Keep this for now as we don't have vision standards yet
        })
        
        # Build game_stages structure
        game_stages = {}
        
        if laning_data and laning_analysis:
            game_stages["laning"] = {
                "duration_min": 10,
                "data": laning_data,
                "metrics": laning_analysis.get("metrics", {}),
                "score": laning_analysis.get("laning_score", 0),
                "comparison": laning_analysis.get("comparison", {}),
                "advice": laning_analysis.get("advice", [])
            }
        
        # Prepare response
        response = {
            "metrics": flat_metrics,
            "advice": advice,
            "overall_score": overall_score,
            "strengths": strengths,
            "weaknesses": weaknesses,
            "power_spikes": power_spikes,
            "mistakes": mistakes
        }
        
        # Add game_stages if available
        if game_stages:
            response["game_stages"] = game_stages
        
        return response

    
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
        
        gpm = data.get("gpm") or data.get("gold_per_min", 0)
        xpm = data.get("xpm") or data.get("xp_per_min", 0)
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
        """
        Calculate positioning from available hero data.
        
        Available: data["position"] = "Safe Lane" (string)
        NOT available: coordinate time-series (usually)
        
        Workaround: Use position string + deaths to infer safety
        """
        full_data = data.get("full_data", {})
        positions = full_data.get("positions", [])
        
        # If we actually HAVE coordinate data, use the advanced logic
        if positions:
            danger_ticks = 0
            total_dist = 0
            for pos in positions:
                x, y = pos.get("x", 0), pos.get("y", 0)
                dist_from_origin = (x**2 + y**2)**0.5
                total_dist += dist_from_origin
                if dist_from_origin > 3000:
                    danger_ticks += 1
            danger_zone_pct = round((danger_ticks / len(positions)) * 100, 1)
            avg_dist = round(total_dist / len(positions), 0)
            return {
                "avg_distance_from_team": avg_dist / 10,
                "danger_zone_pct": danger_zone_pct,
                "position_safety_score": max(0, 100 - danger_zone_pct),
                "farming_time_pct": (data.get("last_hits", 0) * 100) / max(data.get("net_worth", 1), 1)
            }

        # FALLBACK: Heuristic based on position string and deaths
        position = data.get("position", "unknown")
        deaths = data.get("deaths", 0)
        
        # Infer position safety from string
        safety_map = {
            "Hard Support": 80,    # Stays close to base/allies
            "Soft Support": 70,
            "Safe Lane": 65,       # Should be protected but targets
            "Mid Lane": 40,        # Centrally exposed
            "Off Lane": 35,        # Typically dangerous lane
            "Jungle": 55,
            "Roaming": 25          # Always in depth
        }
        
        base_safety = safety_map.get(position, 50)
        # Penalize deaths heavily for positioning score
        safety_adjusted = base_safety - (deaths * 4)
        danger_zone_pct = 100 - max(0, min(100, safety_adjusted))
        
        return {
            "avg_distance_from_team": 0,
            "danger_zone_pct": danger_zone_pct,
            "position_safety_score": max(0, min(100, safety_adjusted)),
            "farming_time_pct": (data.get("last_hits", 0) * 1.5) # Rough estimate
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
        """
        Calculate lane phase metrics (0-10 min) from available hero data.
        """
        full_data = data.get("full_data", {})
        
        # 1. Check for real time-series data first
        lh_t = full_data.get("last_hits_t") or data.get("last_hits_t")
        gold_t = full_data.get("gold_t") or data.get("gold_t")
        duration = data.get("duration_minutes", 30)
        
        if lh_t and len(lh_t) > 10:
            idx = 10 if len(lh_t) < 120 else 600
            return {
                "lh_at_10": lh_t[idx] if len(lh_t) > idx else lh_t[-1],
                "gold_at_10": gold_t[idx] if gold_t and len(gold_t) > idx else 0,
                "xp_at_10": 0,  # XP usually missing from simple arrays
                "deaths_in_lane": full_data.get("deaths_10min", 0),
                "lane_control_pct": 0
            }

        # 2. FALLBACK: Estimation heuristics
        # Actual hero stats
        total_lh = data.get("last_hits", 0)
        total_gold = data.get("net_worth") or (data.get("gold_per_min", 300) * duration)
        
        # Estimation Logic:
        # Core heroes get ~30% of their total LH by 10 min in long games, more in short games.
        # Support heroes get much less.
        position = str(data.get("position") or "").lower()
        is_core = any(r in position for r in ["safe", "mid", "off", "core", "carry", "1", "2", "3"])
        
        lh_multiplier = 0.25 if is_core else 0.1
        gold_multiplier = 0.2 if is_core else 0.15
        
        # Scale by duration - if game is 20 min, 10 min is half the game.
        # If game is 60 min, 10 min is 1/6th.
        time_factor = min(1.0, 10 / max(duration, 10))
        
        est_lh_10 = total_lh * lh_multiplier / time_factor
        # Cap at reasonable pro levels
        est_lh_10 = min(est_lh_10, 85 if is_core else 30)
        
        est_gold_10 = total_gold * gold_multiplier / time_factor
        est_gold_10 = min(est_gold_10, 5000 if is_core else 2500)
        
        return {
            "lh_at_10": int(est_lh_10),
            "gold_at_10": int(est_gold_10),
            "xp_at_10": int(est_gold_10 * 1.1), # Rough XP/Gold correlation in lane
            "deaths_in_lane": data.get("deaths", 0) // 4, # Rough estimate for lane phase
            "lane_control_pct": 50
        }

    def _xp_to_level(self, xp: int) -> int:
        """Convert XP to hero level using standard Dota 2 XP table."""
        xp_table = {
            1: 0, 2: 230, 3: 600, 4: 1080, 5: 1680, 6: 2300, 7: 2940, 
            8: 3600, 9: 4280, 10: 5080, 12: 6720, 15: 9380, 20: 16000, 
            25: 25000, 30: 35000
        }
        for level in sorted(xp_table.keys(), reverse=True):
            if xp >= xp_table[level]:
                return level
        return 1
    
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
    
    # =========================================================================
    # LANING STAGE ANALYSIS - NEW METHODS
    # =========================================================================
    def _get_hero_index(self, parsed_data: Dict[str, Any], hero_name: str) -> Optional[int]:
        """
        Find hero's index in parsed_data["heroes"] by matching hero_name.
        
        Args:
            parsed_data: Full match data from parser
            hero_name: npc_dota_hero_* name to find
            
        Returns:
            Player index (0-9) or None if not found
        """
        heroes_list = parsed_data.get("heroes", [])
        for idx, hero in enumerate(heroes_list):
            if hero.get("hero_name") == hero_name:
                return idx
        return None
    
    def _get_player_position(self, parsed_data: Dict[str, Any], hero_index: int) -> str:
        """
        Determine player position (pos1-pos5) based on index or parsed data.
        
        Args:
            parsed_data: Full match data
            hero_index: Player index (0-9)
            
        Returns:
            Position string: pos1, pos2, pos3, pos4, or pos5
        """
        try:
            # Try to get position from heroes list first
            heroes_list = parsed_data.get("heroes", [])
            if hero_index < len(heroes_list):
                position_str = heroes_list[hero_index].get("position", "")
                
                # Map position strings to pos1-pos5
                if "safe" in str(position_str).lower() or "carry" in str(position_str).lower():
                    return "pos1"
                elif "mid" in str(position_str).lower():
                    return "pos2"
                elif "off" in str(position_str).lower():
                    return "pos3"
                elif "soft support" in str(position_str).lower():
                    return "pos4"
                elif "hard support" in str(position_str).lower() or "support" in str(position_str).lower():
                    return "pos5"
            
            # Fallback: Use index-based heuristic
            # Radiant: 0-4, Dire: 5-9
            # Typical pub order: pos1/2/3 then support
            local_idx = hero_index % 5
            
            if local_idx == 0:
                return "pos1"  # Safe lane carry
            elif local_idx == 1:
                return "pos2"  # Mid
            elif local_idx == 2:
                return "pos3"  # Offlane
            elif local_idx == 3:
                return "pos4"  # Soft support
            else:
                return "pos5"  # Hard support
        except Exception as e:
            logger.error(f"Error determining position: {e}")
            return "pos1"
    
    def _calculate_items_value(self, items: List[str]) -> int:
        """
        Calculate total gold value of items.
        
        Args:
            items: List of item names
            
        Returns:
            Total gold value
        """
        # Simplified item values (common items)
        item_costs = {
            "item_tango": 90,
            "item_clarity": 50,
            "item_branches": 50,
            "item_circlet": 155,
            "item_gauntlets": 150,
            "item_slippers": 150,
            "item_mantle": 150,
            "item_boots": 500,
            "item_magic_wand": 450,
            "item_wraith_band": 505,
            "item_bracer": 505,
            "item_null_talisman": 505,
            "item_soul_ring": 770,
            "item_phase_boots": 1500,
            "item_power_treads": 1400,
            "item_arcane_boots": 1400,
            "item_hand_of_midas": 2200,
        }
        
        total = 0
        for item in items:
            total += item_costs.get(item, 0)
        
        return total
    
    def _extract_laning_stage_data(self, parsed_data: Dict[str, Any], hero_name: str) -> Dict[str, Any]:
        """
        Extract REAL laning stage (0-10min) metrics from parsed match data.
        
        This function extracts actual values from the parser instead of using constants.
        Handles both OpenDota API format and Clarity parser format.
        
        Args:
            parsed_data: Full match data from parser or OpenDota
            hero_name: npc_dota_hero_* name
            
        Returns:
            Dictionary with real laning metrics
        """
        try:
            # Find hero index
            hero_index = self._get_hero_index(parsed_data, hero_name)
            if hero_index is None:
                logger.warning(f"[_extract_laning_stage_data] Hero {hero_name} not found in heroes list")
                return {}
            
            logger.info(f"[_extract_laning_stage_data] Found hero at index {hero_index}")
            
            # Try to get data from multiple sources
            # 1. Check raw players array (OpenDota format)
            players = parsed_data.get("players", [])
            
            if not players or hero_index >= len(players):
                logger.warning(f"[_extract_laning_stage_data] No players data or invalid index {hero_index}")
                return {}
            
            player = players[hero_index]
            
            # CRITICAL: Extract REAL values from different data structures
            # OpenDota stores lh_at_10 in benchmarks.lhten.raw
            gold_10 = 0
            xp_10 = 0
            lh_10 = 0
            
            # Method 1: OpenDota benchmarks format
            benchmarks = player.get("benchmarks", {})
            if benchmarks:
                lhten_data = benchmarks.get("lhten", {})
                if lhten_data:
                    lh_10 = lhten_data.get("raw", 0)
                    logger.info(f"[_extract_laning_stage_data] Found lh_10 from OpenDota benchmarks: {lh_10}")
                
                # OpenDota also has gold_t and xp_t arrays
                gold_t = player.get("gold_t", [])
                xp_t = player.get("xp_t", [])
                
                # Gold and XP at 10 minutes (index 10 for minute 10)
                if gold_t and len(gold_t) > 10:
                    gold_10 = gold_t[10]
                    logger.info(f"[_extract_laning_stage_data] Found gold_10 from gold_t array: {gold_10}")
                
                if xp_t and len(xp_t) > 10:
                    xp_10 = xp_t[10]
                    logger.info(f"[_extract_laning_stage_data] Found xp_10 from xp_t array: {xp_10}")
            
            # Method 2: Direct fields (Clarity parser format)
            if not lh_10:
                lh_10 = player.get("lh_10") or player.get("last_hits_10") or player.get("lh_at_10") or 0
            if not gold_10:
                gold_10 = player.get("gold_at_10") or player.get("gold_10") or 0
            if not xp_10:
                xp_10 = player.get("xp_at_10") or player.get("xp_10") or 0
            
            # Method 3: Estimate from total stats if no 10-minute data available
            if lh_10 == 0 and gold_10 == 0:
                logger.warning(f"[_extract_laning_stage_data] No 10-minute data found, estimating from total stats")
                total_lh = player.get("last_hits", 0)
                total_gpm = player.get("gold_per_min", 0)
                total_xpm = player.get("xp_per_min", 0)
                
                # Estimate based on position
                heroes_list = parsed_data.get("heroes", [])
                position = heroes_list[hero_index].get("position", "") if hero_index < len(heroes_list) else ""
                
                is_core = any(x in str(position).lower() for x in ["safe", "mid", "off", "carry"])
                
                # Cores typically get 25-30% of their total LH in first 10min
                # Supports get 10-15%
                lh_multiplier = 0.28 if is_core else 0.12
                lh_10 = int(total_lh * lh_multiplier)
                
                # Estimate gold and XP from GPM/XPM
                gold_10 = int(total_gpm * 10)
                xp_10 = int(total_xpm * 10)
                
                logger.info(f"[_extract_laning_stage_data] Estimated: lh_10={lh_10}, gold_10={gold_10}, xp_10={xp_10}")
           
            logger.info(f"[_extract_laning_stage_data] Hero: {hero_name}, gold_10={gold_10}, xp_10={xp_10}, lh_10={lh_10}")
            
            # Calculate rates
            gpm_10m = (gold_10 / 10.0) if gold_10 > 0 else 0
            xpm_10m = (xp_10 / 10.0) if xp_10 > 0 else 0
            cspm_10m = (lh_10 / 10.0) if lh_10 > 0 else 0
            
            # Count deaths in laning phase (0-600 seconds)
            deaths_laning = 0
            
            # Check for deaths_t array (time-series deaths)
            deaths_t = player.get("deaths_t", [])
            if deaths_t:
                for death_time in deaths_t:
                    if death_time <= 600:  # 10 minutes in seconds
                        deaths_laning += 1
            else:
                # Fallback: estimate from total deaths
                total_deaths = player.get("deaths", 0)
                deaths_laning = total_deaths // 4  # Rough estimate
            
            # Get level at 10 minutes
            level_at_10m = 0
            
            # Check for level_t array
            level_t = player.get("level_t", [])
            if level_t and len(level_t) > 10:
                level_at_10m = level_t[10]
            elif xp_10 > 0:
                level_at_10m = self._xp_to_level(xp_10)
            
            # Get items at 10 minutes
            items_at_10m = player.get("items_at_10m", []) or []
            
            # Calculate networth (gold + items value)
            networth_10m = gold_10 + self._calculate_items_value(items_at_10m)
            
            result = {
                "gold_at_10": gold_10,
                "xp_at_10": xp_10,
                "last_hits_at_10": lh_10,
                "gpm_10m": round(gpm_10m, 2),
                "xpm_10m": round(xpm_10m, 2),
                "cspm_10m": round(cspm_10m, 2),
                "deaths_laning": deaths_laning,
                "hero_level_at_10m": level_at_10m,
                "items_at_10m": items_at_10m,
                "networth_at_10m": networth_10m
            }
            
            logger.info(f"[_extract_laning_stage_data] EXTRACTED: {result}")
            return result
        
        except Exception as e:
            logger.error(f"[_extract_laning_stage_data] ERROR: {str(e)}", exc_info=True)
            return {}

    
    def _analyze_laning_performance(self, laning_data: Dict[str, Any], player_position: str) -> Dict[str, Any]:
        """
        Compare laning stage performance against professional standards.
        
        Args:
            laning_data: Extracted laning metrics
            player_position: pos1, pos2, pos3, pos4, or pos5
            
        Returns:
            Dictionary with scores, comparison, and advice
        """
        # PRO STANDARDS by position
        PRO_STANDARDS = {
            "pos1": {"lh_10": 55, "gpm_10m": 450, "xpm_10m": 650},
            "pos2": {"lh_10": 45, "gpm_10m": 400, "xpm_10m": 620},
            "pos3": {"lh_10": 30, "gpm_10m": 350, "xpm_10m": 600},
            "pos4": {"lh_10": 15, "gpm_10m": 200, "xpm_10m": 550},
            "pos5": {"lh_10": 10, "gpm_10m": 150, "xpm_10m": 500},
        }
        
        standards = PRO_STANDARDS.get(player_position, PRO_STANDARDS["pos1"])
        
        actual_lh = laning_data.get("last_hits_at_10", 0)
        actual_gpm = laning_data.get("gpm_10m", 0)
        actual_deaths = laning_data.get("deaths_laning", 0)
        
        expected_lh = standards["lh_10"]
        expected_gpm = standards["gpm_10m"]
        
        # Calculate scores
        cs_ratio = actual_lh / expected_lh if expected_lh > 0 else 0
        gpm_ratio = actual_gpm / expected_gpm if expected_gpm > 0 else 0
        
        cs_score = min(100, int(cs_ratio * 100))
        gpm_score = min(100, int(gpm_ratio * 100))
        survival_score = 100 if actual_deaths == 0 else max(0, 100 - (actual_deaths * 25))
        
        laning_score = (cs_score + gpm_score + survival_score) / 3
        
        advice = []
        
        # Advice on CS
        if actual_lh < expected_lh * 0.7:
            advice.append({
                "category": "cs",
                "priority": "HIGH",
                "title": "Last Hits Too Low",
                "message": f"Last hits за 10м: {actual_lh} vs ожидается {expected_lh}. Работай над паттернами ласта."
            })
        
        # Advice on survival
        if actual_deaths > 1:
            advice.append({
                "category": "survival",
                "priority": "HIGH",
                "title": "Too Many Deaths",
                "message": f"Умер {actual_deaths} раз на лайнинге. Фокусируйся на позиционировании."
            })
        elif actual_deaths == 1:
            advice.append({
                "category": "survival",
                "priority": "MEDIUM",
                "title": "Avoid Deaths",
                "message": "1 смерть на лайнинге. Будь осторожнее с позицией."
            })
        
        # Advice on economy
        if actual_gpm < expected_gpm * 0.8:
            advice.append({
                "category": "farm",
                "priority": "MEDIUM",
                "title": "Farm Efficiency",
                "message": f"GPM: {actual_gpm:.0f}/min vs {expected_gpm}. Улучши экономику фарма."
            })
        
        # Positive feedback
        if actual_lh >= expected_lh * 1.1:
            advice.append({
                "category": "cs",
                "priority": "POSITIVE",
                "title": "Great CS!",
                "message": f"Отличный ласт: {actual_lh} хитов за 10м (+{int((cs_ratio-1)*100)}% от нормы)!"
            })
        
        return {
            "metrics": {
                "cs_score": cs_score,
                "gpm_score": gpm_score,
                "survival_score": survival_score
            },
            "advice": advice,
            "laning_score": round(laning_score, 1),
            "comparison": {
                "actual_lh": actual_lh,
                "expected_lh": expected_lh,
                "actual_gpm": round(actual_gpm, 1),
                "expected_gpm": expected_gpm,
                "deaths": actual_deaths
            }
        }
