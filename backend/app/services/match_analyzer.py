"""Match analyzer service for calculating 60+ performance metrics."""

from typing import Dict, Any, List, Optional
import logging

from app.services.benchmark_service import benchmark_service
from app.services.stage_extractors import LaningStageExtractor
from app.services.stage_constants import get_position

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
            
        # CRITICAL FIX: Merge rich data from 'players' array if available
        # The 'heroes' list often contains simplified data. We need 'gold_t', 'lh_t' etc from 'players'.
        players_list = parsed_data.get("players", [])
        if players_list and "player_id" in player_data:
            try:
                p_idx = int(player_data["player_id"])
                if 0 <= p_idx < len(players_list):
                    rich_data = players_list[p_idx]
                    # Merge rich data INTO player_data, prioritizing existing specific fields but adding missing ones
                    # We want to keep identified hero_name from player_data but get time-series from rich_data
                    for k, v in rich_data.items():
                        if k not in player_data:
                            player_data[k] = v
                    
                    # Also ensure 'full_data' is populated if missing (needed for some calculators)
                    if "full_data" not in player_data:
                        player_data["full_data"] = rich_data
                        
                    logger.info(f"[analyze_match] Merged rich data for player {p_idx}")
            except Exception as e:
                logger.warning(f"Failed to merge rich player data: {e}")

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
        
        # === NEW: LANING STAGE ANALYSIS using LaningStageExtractor ===
        laning_result = None
        
        logger.info(f"[ANALYZE_MATCH_START] hero_name={hero_name}, hero_index={hero_index}")
        logger.debug(f"[PARSED_DATA_STRUCTURE] keys={list(parsed_data.keys())}")
        
        try:
            if hero_index is not None:
                # Get player data for extraction
                players = parsed_data.get('players', [])
                logger.debug(f"[PLAYERS_ARRAY] Found {len(players)} players in parsed_data")
                
                if hero_index < len(players):
                    player_data_for_extraction = players[hero_index]
                    player_slot = player_data_for_extraction.get('player_slot', hero_index)
                    position = get_position(player_slot)
                    
                    logger.info(
                        f"[PLAYER_DATA_EXTRACTED] player_slot={player_slot}, position={position}, "
                        f"hero={player_data_for_extraction.get('hero', 'unknown')}"
                    )
                    logger.debug(
                        f"[PLAYER_DATA_FIELDS] keys={list(player_data_for_extraction.keys())[:20]}..."
                    )
                    
                    # Extract laning stage using new extractor
                    laning_extractor = LaningStageExtractor(player_data_for_extraction, position)
                    laning_result = laning_extractor.extract()
                    
                    logger.info(
                        f"[analyze_match] Laning extraction complete: "
                        f"score={laning_result.performance_score:.1f}%, "
                        f"advice_count={len(laning_result.advice)}, "
                        f"data_source={laning_result.data_source}"
                    )
        except Exception as e:
            logger.error(f"[analyze_match] Laning stage extraction failed: {str(e)}", exc_info=True)
            laning_result = None
        
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
        if laning_result and laning_result.advice:
            # Convert extractor advice format to old format if needed
            for adv in laning_result.advice:
                if isinstance(adv, dict):
                    advice.append(adv.get('message', adv.get('title', str(adv))))
                else:
                    advice.append(str(adv))
        
        # Calculate overall score
        overall_score = self._calculate_overall_score(flat_metrics, benchmark_comparison)
        
        # If laning analysis exists, factor it into overall score
        if laning_result and laning_result.performance_score > 0:
            # Weight: 60% existing score + 40% laning score
            overall_score = int(overall_score * 0.6 + laning_result.performance_score * 0.4)
            logger.info(f"[analyze_match] Overall score updated with laning: {overall_score}")
        
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
        # Now using LaningStageExtractor data when available
        lh_benchmark = 55  # Default
        if laning_result and laning_result.metrics:
            lh_benchmark = laning_result.metrics.get('lh_benchmark', 55)
        
        flat_metrics.update({
            "pro_avg_gpm": pro_gpm,
            "pro_avg_xpm": pro_xpm,
            "pro_avg_lh": pro_lh,
            "pro_avg_lh_10": lh_benchmark,
            "pro_avg_vision": 15.5
        })
        
        # Build game_stages structure using LaningStageExtractor result
        game_stages = {}
        
        if laning_result:
            game_stages["laning"] = {
                "duration_min": 10,
                "data": laning_result.snapshots[0] if laning_result.snapshots else {},
                "metrics": laning_result.metrics,
                "score": laning_result.performance_score,
                "advice": laning_result.advice,
                "data_source": laning_result.data_source,
                "events": laning_result.events[:10] if laning_result.events else []  # First 10 events
            }
        else:
            # Fallback if extraction failed
            game_stages["laning"] = {
                "duration_min": 10,
                "status": "extraction_failed",
                "score": 0,
                "advice": ["Laning analysis not available for this match"]
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
        
        Uses multiple data sources to provide meaningful positioning metrics.
        """
        full_data = data.get("full_data", {})
        positions = full_data.get("positions", [])
        
        # If we actually HAVE coordinate data, use the advanced logic
        if positions and len(positions) > 0:
            danger_ticks = 0
            total_dist = 0
            team_proximity_sum = 0
            valid_positions = 0
            
            for pos in positions[:1000]:  # Sample first 1000 positions for performance
                try:
                    x, y = pos.get("x", 0), pos.get("y", 0)
                    dist_from_origin = (x**2 + y**2)**0.5
                    total_dist += dist_from_origin
                    
                    # Danger zone: far from origin (likely deep in enemy territory)
                    if dist_from_origin > 3000:
                        danger_ticks += 1
                    
                    valid_positions += 1
                except (TypeError, ValueError):
                    continue
            
            if valid_positions > 0:
                danger_zone_pct = round((danger_ticks / valid_positions) * 100, 1)
                avg_dist = round(total_dist / valid_positions, 0)
                
                # Estimate team proximity based on hero role and deaths
                deaths = data.get("deaths", 0)
                position_safety_score = max(0, min(100, 100 - danger_zone_pct - (deaths * 2)))
                
                # Farming time estimate based on LH and net worth
                last_hits = data.get("last_hits", 0)
                net_worth = data.get("net_worth", last_hits * 40)
                farming_time_pct = min(100, (last_hits * 100) / max(net_worth / 40, 1))
                
                return {
                    "avg_distance_from_team": avg_dist / 10,  # Scale down for readability
                    "danger_zone_pct": danger_zone_pct,
                    "position_safety_score": position_safety_score,
                    "farming_time_pct": farming_time_pct
                }

        # FALLBACK: Heuristic based on position string and performance metrics
        position = data.get("position", "unknown")
        deaths = data.get("deaths", 0)
        kills = data.get("kills", 0)
        assists = data.get("assists", 0)
        gpm = data.get("gpm", 0)
        
        # Infer position safety from string and performance
        safety_map = {
            "Hard Support": 75,    # Stays close to base/allies
            "Soft Support": 70,
            "Safe Lane": 65,       # Should be protected but targets
            "Mid Lane": 45,        # Centrally exposed
            "Off Lane": 40,        # Typically dangerous lane
            "Jungle": 60,
            "Roaming": 30,         # Always in depth
            "unknown": 50
        }
        
        base_safety = safety_map.get(position, 50)
        
        # Adjust based on KDA performance (better KDA = better positioning)
        kda = (kills + assists) / max(deaths, 1)
        kda_bonus = min(20, kda * 2)  # Max 20 points bonus
        
        # Adjust based on GPM (higher GPM = better farming positioning)
        gpm_bonus = min(10, gpm / 50)  # Max 10 points bonus
        
        # Penalize deaths heavily
        death_penalty = deaths * 3
        
        # Calculate final safety score
        safety_adjusted = base_safety + kda_bonus + gpm_bonus - death_penalty
        safety_score = max(0, min(100, safety_adjusted))
        
        # Danger zone is inverse of safety
        danger_zone_pct = 100 - safety_score
        
        # Estimate farming time based on GPM vs expected
        expected_gpm_by_position = {
            "Safe Lane": 500, "Mid Lane": 600, "Off Lane": 450,
            "Jungle": 400, "Hard Support": 250, "Soft Support": 300
        }
        expected_gpm = expected_gpm_by_position.get(position, 400)
        farming_efficiency = min(100, (gpm / max(expected_gpm, 1)) * 100)
        
        return {
            "avg_distance_from_team": 0,  # Cannot calculate without coordinates
            "danger_zone_pct": danger_zone_pct,
            "position_safety_score": safety_score,
            "farming_time_pct": farming_efficiency
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
        
        # Get team scores for participation calculation
        # Try multiple possible field names for team scores
        radiant_score = (data.get("radiant_score") or 
                        full_data.get("radiant_score") or 0)
        
        dire_score = (data.get("dire_score") or 
                     full_data.get("dire_score") or 0)
        
        # Determine player's team and get their team's score
        is_radiant = data.get("team") == "radiant" or data.get("isRadiant") == True
        team_score = radiant_score if is_radiant else dire_score
        
        # Calculate Participation - FIXED: Cap at 100% max
        if team_score > 0:
            tf_participation = min(round(((kills + assists) / team_score) * 100, 1), 100.0)
        else:
            # Fallback: estimate from match duration and kills
            duration = data.get("duration_minutes", 30)
            expected_team_kills = max(10, duration // 3)  # Rough estimate
            tf_participation = min(round(((kills + assists) / expected_team_kills) * 100, 1), 100.0)
        
        logger.debug(
            f"[TEAMFIGHT_CALC] kills={kills}, assists={assists}, team_score={team_score}, "
            f"participation={tf_participation}% (capped at 100%)"
        )
        
        # Extract combat metrics
        hero_damage = data.get("hero_damage") or full_data.get("hero_damage", 0)
        tower_damage = data.get("tower_damage") or full_data.get("tower_damage", 0)
        hero_healing = data.get("hero_healing") or full_data.get("hero_healing", 0)
        
        # Estimate fight damage (assume 70% in fights, 30% poking)
        fight_damage = int(hero_damage * 0.7) if hero_damage else 0
        
        # Stun/disable metrics - try multiple sources
        stuns = (data.get("stuns") or 
                combat.get("stuns") or 
                full_data.get("stuns") or 
                self._estimate_stuns_from_items(data))
        
        stun_duration = round(float(stuns), 1) if stuns else 0.0
        
        # Calculate derived metrics
        fight_kills_ratio = round(kills / max(kills + assists, 1), 2)
        fight_deaths_ratio = round(deaths / max(kills + deaths, 1), 2)
        
        # Estimate disable rate based on hero type and items
        disable_rate = self._calculate_disable_rate(data)
        
        # Support-specific metrics
        last_hit_steal_pct = self._calculate_last_hit_steal(data)
        save_success_rate = self._calculate_save_success(data)
        
        # Objective participation
        roshan_participation = self._calculate_roshan_participation(data)
        gank_response_time = self._estimate_gank_response(data)
        
        logger.debug(
            f"[TEAMFIGHT_METRICS] hero_damage={hero_damage}, fight_damage={fight_damage}, "
            f"stun_duration={stun_duration}"
        )
        
        return {
            "teamfight_participation": tf_participation,
            "fight_kills_ratio": fight_kills_ratio,
            "fight_deaths_ratio": fight_deaths_ratio,
            "fight_damage": fight_damage,
            "stun_duration_total": stun_duration,
            "disable_rate": disable_rate,
            "last_hit_steal_pct": last_hit_steal_pct,
            "save_success_rate": save_success_rate,
            "roshan_participation": roshan_participation,
            "gank_response_time": gank_response_time
        }
    
    def _estimate_stuns_from_items(self, data: Dict[str, Any]) -> float:
        """Estimate stun duration based on items and hero."""
        items = data.get("items", [])
        stun_items = ["item_sheepstick", "item_orchid", "item_bloodthorn", "item_abyssal_blade"]
        stun_duration = 0.0
        
        for item in items:
            if any(stun_item in item for stun_item in stun_items):
                stun_duration += 1.5  # Rough estimate per stun item
        
        # Some heroes have built-in stuns
        hero_name = data.get("hero_name", "").lower()
        stun_heroes = ["axe", "sven", "dragon_knight", "slardar", "tiny"]
        if any(hero in hero_name for hero in stun_heroes):
            stun_duration += 2.0
        
        return stun_duration
    
    def _calculate_disable_rate(self, data: Dict[str, Any]) -> float:
        """Calculate disable rate based on items and performance."""
        items = data.get("items", [])
        disable_items = ["item_sheepstick", "item_orchid", "item_bloodthorn", "item_abyssal_blade", 
                        "item_heavens_halberd", "item_silver_edge", "item_force_staff"]
        
        disable_count = sum(1 for item in items if any(dis_item in item for dis_item in disable_items))
        
        # Base rate + item bonus
        base_rate = 0.1  # 10% base
        item_bonus = disable_count * 0.15  # 15% per disable item
        
        return min(1.0, base_rate + item_bonus)
    
    def _calculate_last_hit_steal(self, data: Dict[str, Any]) -> float:
        """Calculate last hit steal rate (for supports)."""
        position = data.get("position", "").lower()
        if "support" not in position:
            return 0.0
        
        # Estimate based on assists vs kills
        kills = data.get("kills", 0)
        assists = data.get("assists", 0)
        
        if assists > kills * 3:
            return min(0.3, (assists - kills * 3) / assists)  # Max 30%
        return 0.0
    
    def _calculate_save_success(self, data: Dict[str, Any]) -> float:
        """Calculate save success rate."""
        # Estimate based on healing and assists
        hero_healing = data.get("hero_healing", 0)
        assists = data.get("assists", 0)
        
        if hero_healing > 1000 and assists > 5:
            return min(0.8, 0.3 + (hero_healing / 10000) + (assists / 20))
        return 0.0
    
    def _calculate_roshan_participation(self, data: Dict[str, Any]) -> float:
        """Calculate Roshan participation."""
        # Check if player has items that indicate Roshan participation
        items = data.get("items", [])
        roshan_items = ["item_abyssal_blade", "item_refresher", "item_black_king_bar"]
        
        if any(item in items for item in roshan_items):
            return 1.0
        
        # Estimate from match duration and kills
        duration = data.get("duration_minutes", 0)
        kills = data.get("kills", 0)
        
        if duration > 25 and kills > 8:  # Late game with good performance
            return 0.7
        elif duration > 20 and kills > 5:
            return 0.4
        
        return 0.0
    
    def _estimate_gank_response(self, data: Dict[str, Any]) -> float:
        """Estimate gank response time in seconds."""
        # Estimate based on position and mobility items
        position = data.get("position", "").lower()
        items = data.get("items", [])
        
        mobility_items = ["item_blink", "item_force_staff", "item_phase_boots", "item_travel_boots"]
        has_mobility = any(item in items for item in mobility_items)
        
        if "mid" in position and has_mobility:
            return 3.0  # Fast response
        elif "support" in position:
            return 8.0  # Slower response
        elif has_mobility:
            return 5.0
        else:
            return 10.0  # Slow response
    
    # =========================================================================
    # TIMING METRICS (12)
    # =========================================================================
    def calculate_item_efficiency(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate item timing metrics (12 total)."""
        item_timings = data.get("item_timings", {}) # {item_name: seconds}
        items = data.get("items", [])  # Final items list
        
        # Extract key item timings
        blink_time = item_timings.get("item_blink", 0)
        bkb_time = item_timings.get("item_black_king_bar", 0)
        boots_time = 0
        first_item_time = 0
        
        # Find boots timing
        for k, v in item_timings.items():
            if "boots" in k.lower() and v > 0:
                boots_time = v
                break
        
        # Find first significant item timing
        significant_items = [k for k, v in item_timings.items() 
                           if v > 0 and not any(x in k.lower() for x in ["tango", "clarity", "branches", "ward"])]
        if significant_items:
            first_item_time = min(item_timings[k] for k in significant_items)
        
        # Pro comparison for Blink
        pro_blink = benchmark_service.get_pro_item_timing("blink") or 780
        blink_diff = (blink_time - pro_blink) if blink_time > 0 else 0
        
        # Calculate item completion rate
        # Count significant items vs expected for match duration
        duration = data.get("duration_minutes", 30)
        expected_items = max(3, duration // 10)  # Rough expectation
        significant_item_count = len([i for i in items if not any(x in i.lower() for x in ["tango", "clarity", "branches", "ward"])])
        item_completion_rate = min(1.0, significant_item_count / max(expected_items, 1))
        
        # GPM/XPM by game phases (estimated from overall stats)
        gpm = data.get("gpm", 0)
        xpm = data.get("xpm", 0)
        
        # Phase breakdown estimates
        gpm_by_window = {
            "0-10": min(gpm, 300),  # Early game lower GPM
            "10-25": gpm,          # Mid game peak
            "25+": max(gpm * 0.8, 200)  # Late game may drop
        }
        
        xpm_by_window = {
            "0-10": min(xpm, 350),
            "10-25": xpm,
            "25+": max(xpm * 0.8, 250)
        }
        
        # Level timing (estimated from XP)
        total_xp = data.get("xp_per_min", 0) * duration
        level_timing = self._estimate_level_timing(total_xp, duration)
        
        return {
            "first_item_timing": first_item_time,
            "core_item_1_timing": blink_time,
            "core_item_2_timing": bkb_time,
            "core_item_3_timing": 0,  # Could be hero-specific
            "boots_timing": boots_time,
            "blink_timing": blink_time,
            "upgrade_items_timing": 0,  # Placeholder for Aghanim's, etc.
            "pro_timing_diff": blink_diff,
            "item_completion_rate": item_completion_rate,
            "gpm_by_window": gpm_by_window,
            "xpm_by_window": xpm_by_window,
            "level_timing": level_timing
        }
    
    def _estimate_level_timing(self, total_xp: int, duration: int) -> Dict[str, int]:
        """Estimate timing for key levels based on total XP."""
        # XP thresholds for key levels
        level_xp = {
            6: 2300,   # Level 6 (ultimate)
            12: 6720,  # Level 12 (mid-game power)
            18: 16000, # Level 18 (late game)
            25: 25000  # Level 25 (max)
        }
        
        timing = {}
        if total_xp > 0:
            # Estimate linear progression (simplified)
            xp_rate = total_xp / max(duration, 1)
            for level, xp_needed in level_xp.items():
                if total_xp >= xp_needed:
                    # Estimate when this level was reached
                    estimated_time = (xp_needed / xp_rate) if xp_rate > 0 else duration
                    timing[f"level_{level}"] = min(int(estimated_time), duration)
        
        return timing
    
    # =========================================================================
    # WARDING METRICS (6)
    # =========================================================================
    def calculate_warding_value(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate warding metrics (6 total).
        
        Provides meaningful warding metrics even with limited data.
        """
        full_data = data.get("full_data", {})
        map_data = full_data.get("map", {})
        warding = full_data.get("warding", {})
        
        # Extract ward data from multiple possible sources
        wards_placed = (map_data.get("wards_placed") or 
                       warding.get("wards_placed") or 
                       data.get("wards_placed") or 0)
        
        obs_placed = (map_data.get("obs_placed") or 
                     warding.get("obs_placed") or 
                     data.get("obs_placed") or 0)
        
        sen_placed = (map_data.get("sen_placed") or 
                     warding.get("sen_placed") or 
                     data.get("sen_placed") or 0)
        
        # Calculate vision score (observer wards worth more)
        vision_score = (obs_placed * 2.0) + (sen_placed * 1.0)
        
        # Estimate ward value based on position and game duration
        position = data.get("position", "").lower()
        duration = data.get("duration_minutes", 30)
        
        # Expected wards by position and duration
        if "support" in position:
            expected_wards = max(2, duration // 7)  # Supports should ward more
        elif "jungle" in position:
            expected_wards = max(1, duration // 10)
        else:
            expected_wards = max(1, duration // 15)  # Cores ward less
        
        # Ward efficiency based on expectations
        ward_efficiency = min(1.0, wards_placed / max(expected_wards, 1))
        
        # Vision uptime estimation
        # Each obs ward lasts ~7 minutes, sentry ~3 minutes
        obs_uptime = obs_placed * 7
        sen_uptime = sen_placed * 3
        total_vision_time = obs_uptime + sen_uptime
        vision_uptime_pct = min(100, (total_vision_time / max(duration, 1)) * 100)
        
        # Deward count (estimate from items and performance)
        deward_items = ["item_sentry", "item_dust", "item_gem"]
        deward_count = sum(1 for item in data.get("items", []) 
                          if any(ward_item in item for ward_item in deward_items))
        
        # Counter-ward success (estimate)
        counter_ward_success = min(1.0, deward_count / max(obs_placed, 1)) if obs_placed > 0 else 0.0
        
        # Ward locations (placeholder - would need coordinate data)
        ward_locations = warding.get("ward_locations", [])
        
        # Average ward value (based on efficiency and vision uptime)
        avg_ward_value = ward_efficiency * (vision_uptime_pct / 100) * 20  # Scale to 0-20
        
        return {
            "wards_placed": wards_placed,
            "obs_placed": obs_placed,
            "sen_placed": sen_placed,
            "vision_score": vision_score,
            "avg_ward_value": avg_ward_value,
            "ward_locations": ward_locations,
            "vision_uptime_pct": vision_uptime_pct,
            "deward_count": deward_count,
            "counter_ward_success": counter_ward_success
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
        xp_t = full_data.get("xp_t") or data.get("xp_t")
        duration = data.get("duration_minutes", 30)
        
        if lh_t and len(lh_t) > 10:
            logger.debug("[LANE_METRICS] Found real time-series data")
            idx = 10 if len(lh_t) < 120 else 600  # 10 min mark (10 seconds per tick)
            
            # Get values at 10 minutes
            lh_at_10 = lh_t[idx] if len(lh_t) > idx else lh_t[-1]
            gold_at_10 = gold_t[idx] if gold_t and len(gold_t) > idx else (data.get("gold_per_min", 0) * 10)
            xp_at_10 = xp_t[idx] if xp_t and len(xp_t) > idx else (data.get("xp_per_min", 0) * 10)
            
            # Estimate deaths in lane from total deaths (assume 25% in lane)
            total_deaths = data.get("deaths", 0)
            deaths_in_lane = max(0, total_deaths // 4)
            
            # Calculate lane control based on LH vs expected
            expected_lh = 50  # Baseline expectation
            lane_control_pct = min(100, max(0, (lh_at_10 / expected_lh) * 100))
            
            return {
                "lh_at_10": lh_at_10,
                "gold_at_10": gold_at_10,
                "xp_at_10": xp_at_10,
                "deaths_in_lane": deaths_in_lane,
                "lane_control_pct": lane_control_pct
            }

        # 2. Check for OpenDota benchmarks
        benchmarks = data.get("benchmarks", {})
        if "lhten" in benchmarks:
            logger.debug("[LANE_METRICS] Found OpenDota benchmarks")
            lh_at_10 = benchmarks["lhten"].get("raw", 0)
            gold_at_10 = int(data.get("gold_per_min", 0) * 10)
            xp_at_10 = int(data.get("xp_per_min", 0) * 10)
            
            return {
                "lh_at_10": lh_at_10,
                "gold_at_10": gold_at_10,
                "xp_at_10": xp_at_10,
                "deaths_in_lane": 0,
                "lane_control_pct": min(100, (lh_at_10 / 50) * 100)
            }

        # 3. FALLBACK: Estimate from basic stats
        logger.warning("[LANE_METRICS] No real laning data found. Using estimates from basic stats.")
        
        gpm = data.get("gpm", 0)
        xpm = data.get("xpm", 0)
        total_lh = data.get("last_hits", 0)
        total_deaths = data.get("deaths", 0)
        
        # Estimate 10-minute values from overall stats
        # Assume linear progression - rough but better than 0
        estimated_lh_10 = min(total_lh, max(0, gpm // 10))  # Rough estimate: 1 LH per 10 gold
        estimated_gold_10 = min(gpm * 10, total_lh * 40)  # Gold from LH + some estimate
        estimated_xp_10 = xpm * 10
        estimated_deaths_lane = max(0, min(total_deaths, 2))  # Assume max 2 deaths in lane
        
        # Basic lane control based on LH
        lane_control_pct = min(100, max(0, (estimated_lh_10 / 50) * 100))
        
        return {
            "lh_at_10": estimated_lh_10,
            "gold_at_10": estimated_gold_10,
            "xp_at_10": estimated_xp_10,
            "deaths_in_lane": estimated_deaths_lane,
            "lane_control_pct": lane_control_pct
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
        
        Estimates mid-game performance from available data.
        """
        full_data = data.get("full_data", {})
        midgame = full_data.get("midgame", {})
        
        # Extract basic stats
        gpm = data.get("gpm", 0)
        xpm = data.get("xpm", 0)
        kills = data.get("kills", 0)
        assists = data.get("assists", 0)
        deaths = data.get("deaths", 0)
        duration = data.get("duration_minutes", 30)
        
        # Estimate mid-game GPM (usually higher than overall)
        midgame_gpm = min(gpm * 1.2, 800) if gpm > 0 else 0
        
        # Estimate mid-game deaths (assume 40% of deaths in mid-game)
        midgame_deaths = max(0, deaths // 3) if duration > 15 else deaths // 2
        
        # Fight participation in mid-game
        # Mid-game is when most fights happen, so participation should be high
        total_kills_assists = kills + assists
        expected_midgame_kills = max(5, duration // 5)
        midgame_fight_participation = min(1.0, total_kills_assists / max(expected_midgame_kills, 1))
        
        # Objectives taken (estimate from hero type and items)
        items = data.get("items", [])
        position = data.get("position", "").lower()
        
        objectives_taken = 0
        if "support" in position and any("item_smoke" in item for item in items):
            objectives_taken = 2  # Supports smoke for objectives
        elif any(item in items for item in ["item_blink", "item_black_king_bar"]):
            objectives_taken = 3  # Core heroes with fight items
        elif kills > 5:
            objectives_taken = 1  # Some contribution
        
        # Farm pattern efficiency (based on GPM consistency)
        # High GPM with low deaths = efficient farming
        farm_efficiency = min(1.0, (midgame_gpm / max(400, 1)) * (1 - (midgame_deaths / max(duration, 1))))
        
        return {
            "midgame_gpm": midgame_gpm,
            "midgame_deaths": midgame_deaths,
            "midgame_fight_participation": midgame_fight_participation,
            "objectives_taken": objectives_taken,
            "farm_pattern_efficiency": max(0, farm_efficiency)
        }
    
    def calculate_lategame_metrics(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate late game metrics 25+ min (4 total).
        
        Estimates late-game performance from available data.
        """
        full_data = data.get("full_data", {})
        lategame = full_data.get("lategame", {})
        
        # Extract basic stats
        gpm = data.get("gpm", 0)
        net_worth = data.get("net_worth", gpm * data.get("duration_minutes", 30))
        kills = data.get("kills", 0)
        deaths = data.get("deaths", 0)
        duration = data.get("duration_minutes", 30)
        
        # Late game gold efficiency (net worth vs potential)
        # In late game, net worth should be high
        expected_net_worth = max(15000, duration * 500)  # Rough expectation
        gold_efficiency = min(1.0, net_worth / max(expected_net_worth, 1))
        
        # Fight positioning score (based on KDA in late game)
        # Late game deaths are more costly
        kda = (kills + data.get("assists", 0)) / max(deaths, 1)
        fight_positioning_score = min(1.0, kda / 5.0)  # Scale KDA to 0-1
        
        # High ground control (estimate from items and performance)
        items = data.get("items", [])
        high_ground_items = ["item_black_king_bar", "item_blink", "item_refresher", "item_abyssal_blade"]
        has_high_ground_items = any(item in items for item in high_ground_items)
        
        if duration > 35 and kills > 8 and has_high_ground_items:
            high_ground_control = 0.8
        elif duration > 30 and kills > 5:
            high_ground_control = 0.5
        else:
            high_ground_control = 0.2
        
        # Buyback utilization (estimate from deaths and net worth)
        # Buyback is expensive, so high net worth with few deaths = good buyback usage
        if net_worth > 20000 and deaths < 3:
            buyback_utilization = 0.9  # Good buyback management
        elif net_worth > 15000 and deaths < 5:
            buyback_utilization = 0.6
        elif net_worth > 10000:
            buyback_utilization = 0.3
        else:
            buyback_utilization = 0.0
        
        return {
            "lategame_gold_efficiency": gold_efficiency,
            "fight_positioning_score": fight_positioning_score,
            "high_ground_control": high_ground_control,
            "buyback_utilization": buyback_utilization
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
        Determine player position (pos1-pos5) based on parsed data (PREFERRED) or index.
        """
        try:
            # 1. Try to get from specific player data first
            players = parsed_data.get("players", [])
            if hero_index < len(players):
                p = players[hero_index]
                
                # Check for explicit 'position' field (Clarity/OpenDota sometimes has it)
                if "position" in p:
                    pos_val = p["position"]
                    logger.debug(f"[POS_EXTRACT] Found explicit 'position' field: {pos_val}")
                    # Handle "pos1", 1, "SAFE LANE", etc.
                    if str(pos_val).lower().startswith("pos"):
                        return str(pos_val).lower()
                    if str(pos_val).isdigit() and 1 <= int(pos_val) <= 5:
                        return f"pos{pos_val}"
                
                # Check for 'lane' and 'lane_role' (OpenDota standard)
                # lane: 1=Safe, 2=Mid, 3=Off
                # lane_role: 1=Core, 2=Support (Approximate)
                if "lane" in p:
                    lane = p.get("lane")
                    role = p.get("lane_role") 
                    
                    logger.debug(f"[POS_EXTRACT] Found 'lane': {lane}, 'lane_role': {role}")
                    
                    # Mid lane is easiest
                    if lane == 2:
                        return "pos2"
                    
                    # Safe lane (1)
                    if lane == 1:
                        # If meaningful role/gold distinction exists, use it. 
                        # Else assume Core (1) if GPM is high? No, avoid pure GPM guessing if possible.
                        # Check benchmarks/lh
                        return "pos1" if p.get("last_hits", 0) > 50 else "pos5" # Heuristic refinement only if needed
                    
                    # Off lane (3)
                    if lane == 3:
                        return "pos3" if p.get("last_hits", 0) > 50 else "pos4"

            # 2. Try hero role mapping if available (Fallback)
            heroes_list = parsed_data.get("heroes", [])
            if hero_index < len(heroes_list):
                position_str = heroes_list[hero_index].get("position", "")
                if position_str:
                    logger.debug(f"[POS_EXTRACT] Using hero list position: {position_str}")
                    if "safe" in str(position_str).lower(): return "pos1"
                    if "mid" in str(position_str).lower(): return "pos2"
                    if "off" in str(position_str).lower(): return "pos3"
                    if "soft" in str(position_str).lower(): return "pos4"
                    if "hard" in str(position_str).lower(): return "pos5"

            # 3. Fallback: Index-based heuristic (Last Resort)
            local_idx = hero_index % 5
            logger.warning(f"[POS_EXTRACT] Using index heuristic for hero_index {hero_index} -> {local_idx}")
            
            mapping = {0: "pos1", 1: "pos2", 2: "pos3", 3: "pos4", 4: "pos5"}
            return mapping.get(local_idx, "pos1")

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
