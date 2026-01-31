"""
Stage extractors for game analysis - extracts metrics for each game stage.
Supports both OpenDota API format and Clarity parser format.
"""

import logging
from typing import Dict, List, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .analysis_logger import AnalysisLogger
from dataclasses import dataclass, field
from datetime import datetime

from .stage_constants import (
    GAME_STAGES,
    TimeSnapshot,
    get_position,
    convert_timestamp_to_minute,
    get_pro_benchmark,
    calculate_performance_percentage,
    ITEM_BUILD_TIMINGS
)

logger = logging.getLogger(__name__)

# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class LaningStageData:
    """Laning stage (0-10min) analysis result."""
    stage: str = 'laning'
    snapshots: List[Dict] = field(default_factory=list)
    events: List[Dict] = field(default_factory=list)
    metrics: Dict = field(default_factory=dict)
    advice: List[str] = field(default_factory=list)
    performance_score: float = 0.0
    data_source: str = 'unknown'  # 'opendota' or 'clarity'
    
    def to_dict(self):
        return {
            'stage': self.stage,
            'snapshots': self.snapshots,
            'events': self.events,
            'metrics': self.metrics,
            'advice': self.advice,
            'performance_score': self.performance_score,
            'data_source': self.data_source
        }


# ============================================================================
# LANING STAGE EXTRACTOR (0-10 minutes)
# ============================================================================

class LaningStageExtractor:
    """
    Extract and analyze laning stage (0-10 minutes).
    
    Supports two data formats:
    1. OpenDota API - benchmarks-based, estimates from rates
    2. Clarity Parser - full time-series arrays
    """
    
    def __init__(self, player_data: Dict[str, Any], position: int, analysis_logger: Optional[Any] = None):
        """
        Initialize extractor.
        
        Args:
            player_data: Single player's data from parsed_data['players'][i]
            position: Hero position (1-5)
            analysis_logger: Optional logger for step-by-step trace
        """
        self.player_data = player_data
        self.position = position
        self.analysis_logger = analysis_logger
        self.hero = player_data.get('hero') or player_data.get('hero_name', 'Unknown')
        
        # Stage boundaries
        self.stage_start = GAME_STAGES['laning']['start']
        self.stage_end = GAME_STAGES['laning']['end']
        
        # Auto-detect data source
        self.data_source = self._detect_data_source()
        
        logger.info(
            f"LaningStageExtractor initialized: hero={self.hero}, "
            f"position={position}, data_source={self.data_source}"
        )
    
    def _detect_data_source(self) -> str:
        """
        Auto-detect whether data is from OpenDota or Clarity parser.
        
        Returns:
            'opendota' or 'clarity'
        """
        # Clarity has time-series arrays
        gold_t = self.player_data.get('gold_t')
        if gold_t and (isinstance(gold_t, list) or isinstance(gold_t, dict)):
            if self.analysis_logger:
                self.analysis_logger.log("LANING", "Detected 'gold_t' time-series - Using Clarity extraction.")
            return 'clarity'
        
        # OpenDota has benchmarks dictionary
        if 'benchmarks' in self.player_data:
            if self.analysis_logger:
                self.analysis_logger.log("LANING", "No time-series found, but 'benchmarks' present - Using OpenDota estimates.")
            return 'opendota'
        
        # Default to opendota if unclear
        if self.analysis_logger:
            self.analysis_logger.log("LANING", "No time-series or benchmarks found - Defaulting to legacy estimates.", level="WARNING")
        logger.warning(f"Could not detect data source, defaulting to opendota")
        return 'opendota'
    
    def extract(self) -> LaningStageData:
        """
        Main extraction method - orchestrates extraction based on data source.
        
        Returns:
            LaningStageData with all metrics and analysis
        """
        try:
            logger.info(f"Starting laning stage extraction (source: {self.data_source})")
            
            if self.data_source == 'clarity':
                return self._extract_from_clarity()
            else:
                return self._extract_from_opendota()
                
        except Exception as e:
            logger.error(f"Error during laning stage extraction: {str(e)}", exc_info=True)
            return LaningStageData(
                stage='laning',
                performance_score=0.0,
                data_source=self.data_source
            )
    
    # ========================================================================
    # OPENDOTA MODE (benchmarks-based, estimates)
    # ========================================================================
    
    def _extract_from_opendota(self) -> LaningStageData:
        """
        Extract laning data from OpenDota API format.
        
        Uses:
        - benchmarks.lhten.raw for LH at 10min
        - gold_per_min × 10 for gold estimate
        - xp_per_min × 10 for XP estimate
        - purchase_log for item events
        """
        logger.info("Extracting from OpenDota format")
        
        # Extract metrics
        metrics = self._calculate_metrics_opendota()
        
        # Compare with benchmarks
        comparison = self._compare_with_benchmarks(metrics)
        metrics.update(comparison)
        
        # Calculate performance score
        performance_score = self._calculate_performance_score(metrics)
        
        # Generate advice
        advice = self._generate_advice(metrics)
        
        # Create snapshots (estimate for 10min only)
        snapshots = [self._create_snapshot_opendota(10)]
        
        # Extract events from purchase_log
        events = self._extract_events_opendota()
        
        result = LaningStageData(
            stage='laning',
            snapshots=snapshots,
            events=events,
            metrics=metrics,
            advice=advice,
            performance_score=performance_score,
            data_source='opendota'
        )
        
        if self.analysis_logger:
            self.analysis_logger.set_data_source("laning_phase", "opendota_estimates")
            self.analysis_logger.log("LANING", f"OpenDota-based laning extraction complete. Score: {performance_score:.1f}%")

        return result
    
    def _calculate_metrics_opendota(self) -> Dict[str, Any]:
        """Calculate laning metrics from OpenDota data."""
        metrics = {}
        
        try:
            # Get from benchmarks
            benchmarks = self.player_data.get('benchmarks', {})
            lhten = benchmarks.get('lhten', {})
            lh_10 = lhten.get('raw', 0) if isinstance(lhten, dict) else 0
            
            # Get rates
            gpm = self.player_data.get('gold_per_min', 0)
            xpm = self.player_data.get('xp_per_min', 0)
            
            # Estimate 10-minute values
            gold_10 = int(gpm * 10)
            xp_10 = int(xpm * 10)
            
            # Estimate level from XP
            level_10 = self._xp_to_level(xp_10)
            
            metrics['lh_10m'] = lh_10
            metrics['gpm'] = round(gpm, 1)
            metrics['xpm'] = round(xpm, 1)
            metrics['gold_at_10'] = gold_10
            metrics['xp_at_10'] = xp_10
            metrics['level_10m'] = level_10
            
            # Get total stats for context
            metrics['kills'] = self.player_data.get('kills', 0)
            metrics['deaths'] = self.player_data.get('deaths', 0)
            metrics['assists'] = self.player_data.get('assists', 0)
            
            # Estimate laning deaths (assume 20-30% of deaths in first 10min)
            total_deaths = metrics['deaths']
            metrics['deaths_laning'] = max(1, int(total_deaths * 0.25)) if total_deaths > 0 else 0
            
            metrics['kda'] = f"{metrics['kills']}/{metrics['deaths']}/{metrics['assists']}"
            
            if self.analysis_logger:
                self.analysis_logger.log(
                    "LANING", 
                    f"OpenDota Estimates: LH@10={lh_10}, Gold@10={gold_10}, XP@10={xp_10}, GPM={gpm}",
                    data={"lh_10": lh_10, "gold_10": gold_10, "xp_10": xp_10, "gpm": gpm}
                )
            
            logger.info(f"Metrics calculated: GPM={gpm}, LH@10={lh_10}, Level@10={level_10}")
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating OpenDota metrics: {str(e)}")
            return metrics
    
    def _create_snapshot_opendota(self, minute: int) -> Dict:
        """Create estimated snapshot at given minute from OpenDota data."""
        gpm = self.player_data.get('gold_per_min', 0)
        xpm = self.player_data.get('xp_per_min', 0)
        
        benchmarks = self.player_data.get('benchmarks', {})
        lh_10 = benchmarks.get('lhten', {}).get('raw', 0) if minute == 10 else 0
        
        gold = int(gpm * minute)
        xp = int(xpm * minute)
        level = self._xp_to_level(xp)
        
        return {
            'minute': minute,
            'timestamp': minute * 60,
            'gold': gold,
            'xp': xp,
            'level': level,
            'last_hits': lh_10 if minute == 10 else int(lh_10 * (minute / 10)),
            'position': {'x': 0, 'y': 0},  # Not available in OpenDota
            'hero': self.hero
        }
    
    def _extract_events_opendota(self) -> List[Dict]:
        """Extract events from OpenDota purchase_log."""
        events = []
        
        try:
            purchase_log = self.player_data.get('purchase_log', [])
            
            for item in purchase_log:
                timestamp = item.get('time', 0)
                minute = convert_timestamp_to_minute(timestamp)
                
                if self.stage_start <= minute <= self.stage_end:
                    events.append({
                        'type': 'item',
                        'minute': round(minute, 2),
                        'timestamp': timestamp,
                        'item': item.get('key', 'Unknown'),
                        'timing_status': self._check_item_timing(item.get('key', ''), timestamp)
                    })
            
            events.sort(key=lambda x: x['timestamp'])
            logger.info(f"Extracted {len(events)} item events from purchase_log")
            
            return events
            
        except Exception as e:
            logger.error(f"Error extracting OpenDota events: {str(e)}")
            return []
    
    # ========================================================================
    # CLARITY MODE (time-series, full data)
    # ========================================================================
    
    def _extract_from_clarity(self) -> LaningStageData:
        """
        Extract laning data from Clarity parser format using time-series arrays.
        """
        logger.info("Extracting from Clarity format (Time-Series)")
        if self.analysis_logger:
            self.analysis_logger.set_data_source("laning_phase", "clarity_time_series")
        
        # 1. Calculate metrics from time series
        metrics = self._calculate_metrics_clarity()
        
        # 2. Compare with benchmarks
        comparison = self._compare_with_benchmarks(metrics)
        metrics.update(comparison)
        
        # 3. Calculate performance score
        performance_score = self._calculate_performance_score(metrics)
        
        # 4. Generate advice
        advice = self._generate_advice(metrics)
        
        # 5. Create snapshots for each minute in the laning phase
        snapshots = self._create_snapshots_clarity()
        
        # 6. Extract events (item purchases)
        events = self._extract_events_clarity()
        
        result = LaningStageData(
            stage='laning',
            snapshots=snapshots,
            events=events,
            metrics=metrics,
            advice=advice,
            performance_score=performance_score,
            data_source='clarity'
        )
        
        logger.info(f"Clarity extraction complete: score={performance_score:.1f}%")
        return result

    def _calculate_metrics_clarity(self) -> Dict[str, Any]:
        """Calculate metrics directly from Clarity time-series arrays."""
        metrics = {}
        data = self.player_data
        
        # Get time-series arrays
        lh_t = data.get('lh_t', [])
        gold_t = data.get('gold_t', [])
        xp_t = data.get('xp_t', [])
        
        # Extract values at 10 minutes (or end of array)
        idx_10 = min(10, len(lh_t) - 1) if lh_t else 0
        
        lh_10 = lh_t[idx_10] if idx_10 < len(lh_t) else 0
        gold_10 = gold_t[idx_10] if idx_10 < len(gold_t) else 0
        xp_10 = xp_t[idx_10] if idx_10 < len(xp_t) else 0
        
        # Calculate rates
        duration_min = max(data.get('duration_minutes', 0), 10)
        total_gold = gold_t[-1] if gold_t else data.get('gold', 0)
        total_xp = xp_t[-1] if xp_t else data.get('xp', 0)
        
        gpm = total_gold / duration_min
        xpm = total_xp / duration_min
        
        metrics['lh_10m'] = lh_10
        metrics['gpm'] = round(gpm, 1)
        metrics['xpm'] = round(xpm, 1)
        metrics['gold_at_10'] = gold_10
        metrics['xp_at_10'] = xp_10
        metrics['level_10m'] = self._xp_to_level(xp_10)
        
        # Exact laning deaths from deaths_log
        deaths_log = data.get('deaths_log', [])
        laning_deaths = len([d for d in deaths_log if d.get('time', 0) <= 600])
        metrics['deaths_laning'] = laning_deaths
        
        metrics['kills'] = data.get('kills', 0)
        metrics['deaths'] = data.get('deaths', 0)
        metrics['assists'] = data.get('assists', 0)
        metrics['kda'] = f"{metrics['kills']}/{metrics['deaths']}/{metrics['assists']}"
        
        if self.analysis_logger:
            self.analysis_logger.log("LANING", f"Extracted metrics at 10m: LH={lh_10}, Gold={gold_10}, XP={xp_10}", data={
                "lh_10": lh_10, "gold_10": gold_10, "xp_10": xp_10
            })
            
        return metrics

    def _create_snapshots_clarity(self) -> List[Dict]:
        """Create snapshots from time-series for laning graph."""
        snapshots = []
        lh_t = self.player_data.get('lh_t', [])
        gold_t = self.player_data.get('gold_t', [])
        xp_t = self.player_data.get('xp_t', [])
        
        # Create one snapshot per minute for first 10 mins
        for m in range(min(11, len(gold_t))):
            snapshots.append({
                'minute': m,
                'timestamp': m * 60,
                'gold': gold_t[m] if m < len(gold_t) else 0,
                'xp': xp_t[m] if m < len(xp_t) else 0,
                'level': self._xp_to_level(xp_t[m]) if m < len(xp_t) else 1,
                'last_hits': lh_t[m] if m < len(lh_t) else 0,
                'hero': self.hero
            })
        return snapshots

    def _extract_events_clarity(self) -> List[Dict]:
        """Extract events from Clarity item timings."""
        events = []
        item_timings = self.player_data.get('item_timings', {})
        
        for item_key, timestamp in item_timings.items():
            minute = timestamp / 60
            if minute <= 10:
                events.append({
                    'type': 'item',
                    'minute': round(minute, 2),
                    'timestamp': timestamp,
                    'item': item_key,
                    'timing_status': self._check_item_timing(item_key, timestamp)
                })
        
        events.sort(key=lambda x: x['timestamp'])
        return events
    
    # ========================================================================
    # SHARED METHODS (used by both modes)
    # ========================================================================
    
    def _compare_with_benchmarks(self, metrics: Dict) -> Dict[str, Any]:
        """Compare actual metrics with pro benchmarks."""
        comparison = {}
        
        try:
            # GPM comparison
            benchmark_gpm = get_pro_benchmark(self.position, 'laning', 'gpm')
            if metrics.get('gpm'):
                gpm_perf = calculate_performance_percentage(metrics['gpm'], benchmark_gpm)
                comparison['gpm_benchmark'] = benchmark_gpm
                comparison['gpm_performance_pct'] = round(gpm_perf, 1)
            
            # XPM comparison
            benchmark_xpm = get_pro_benchmark(self.position, 'laning', 'xpm')
            if metrics.get('xpm'):
                xpm_perf = calculate_performance_percentage(metrics['xpm'], benchmark_xpm)
                comparison['xpm_benchmark'] = benchmark_xpm
                comparison['xpm_performance_pct'] = round(xpm_perf, 1)
            
            # LH @ 10min comparison
            benchmark_lh = get_pro_benchmark(self.position, 'laning', 'lh_10m')
            if metrics.get('lh_10m') is not None:
                lh_perf = calculate_performance_percentage(metrics['lh_10m'], benchmark_lh)
                comparison['lh_benchmark'] = benchmark_lh
                comparison['lh_performance_pct'] = round(lh_perf, 1)
            
            logger.info(
                f"Benchmark comparison: GPM {comparison.get('gpm_performance_pct', 0)}%, "
                f"LH {comparison.get('lh_performance_pct', 0)}%"
            )
            
            return comparison
            
        except Exception as e:
            logger.error(f"Error comparing with benchmarks: {str(e)}")
            return {}
    
    def _calculate_performance_score(self, metrics: Dict) -> float:
        """
        Calculate overall performance score (0-100%).
        
        Weighted average of:
        - GPM performance (40%)
        - LH @ 10m performance (30%)
        - Survival (20%)
        - Participation (10%)
        """
        scores = []
        
        try:
            # GPM score (weight 0.4)
            if 'gpm_performance_pct' in metrics:
                gpm_score = min(metrics['gpm_performance_pct'], 150)  # cap at 150%
                scores.append((gpm_score, 0.4))
            
            # LH score (weight 0.3)
            if 'lh_performance_pct' in metrics:
                lh_score = min(metrics['lh_performance_pct'], 150)
                scores.append((lh_score, 0.3))
            
            # Survival score (weight 0.2)
            deaths = metrics.get('deaths_laning', 0)
            max_deaths = get_pro_benchmark(self.position, 'laning', 'deaths_max')
            if deaths == 0:
                survival_score = 100
            elif deaths <= max_deaths:
                survival_score = 80
            else:
                survival_score = max(0, 80 - ((deaths - max_deaths) * 20))
            scores.append((survival_score, 0.2))
            
            # Participation score (weight 0.1)
            kills = metrics.get('kills', 0)
            assists = metrics.get('assists', 0)
            participation = min((kills + assists) * 10, 100)  # up to 100%
            scores.append((participation, 0.1))
            
            # Calculate weighted average
            if scores:
                total_score = sum(score * weight for score, weight in scores)
                total_weight = sum(weight for _, weight in scores)
                final_score = (total_score / total_weight) if total_weight > 0 else 0
            else:
                final_score = 0
            
            logger.info(f"Performance score calculated: {final_score:.1f}%")
            return round(final_score, 1)
            
        except Exception as e:
            logger.error(f"Error calculating performance score: {str(e)}")
            return 0.0
    
    def _generate_advice(self, metrics: Dict) -> List[str]:
        """Generate targeted advice based on performance."""
        advice = []
        
        try:
            # LH advice
            lh_perf = metrics.get('lh_performance_pct', 100)
            lh_actual = metrics.get('lh_10m', 0)
            lh_benchmark = metrics.get('lh_benchmark', 0)
            
            if lh_perf < 70:
                advice.append(
                    f"❌ Last Hits низкие: {lh_actual} vs {lh_benchmark} ожидается. "
                    f"Работай над паттернами ласта."
                )
            elif lh_perf >= 110:
                advice.append(
                    f"✅ Отличный ласт! {lh_actual} хитов (+{int(lh_perf-100)}% от нормы)"
                )
            
            # GPM advice
            gpm_perf = metrics.get('gpm_performance_pct', 100)
            if gpm_perf < 80:
                advice.append(
                    f"⚠️ GPM низкий ({metrics.get('gpm', 0)}/min). "
                    f"Улучши экономику фарма."
                )
            
            # Deaths advice
            deaths = metrics.get('deaths_laning', 0)
            max_deaths = get_pro_benchmark(self.position, 'laning', 'deaths_max')
            
            if deaths > max_deaths:
                advice.append(
                    f"❌ Слишком много смертей на лайнинге ({deaths}). "
                    f"Фокусируйся на позиционировании."
                )
            elif deaths == 0:
                advice.append("✅ Идеальная выживаемость на лайнинге!")
            
            # Position-specific advice
            if self.position in [1, 2] and lh_perf < 60:
                advice.append(
                    "💡 Для carry/mid позиции критично иметь высокий CS. "
                    "Приоритизируй фарм над харасом."
                )
            
            return advice
            
        except Exception as e:
            logger.error(f"Error generating advice: {str(e)}")
            return []
    
    def _check_item_timing(self, item_name: str, timestamp: int) -> str:
        """
        Check if item was bought at reasonable time.
        
        Returns:
            'early', 'on_time', 'late', or 'unknown'
        """
        try:
            # Simple check for boots
            if 'boots' in item_name.lower():
                expected = ITEM_BUILD_TIMINGS.get(self.position, {}).get('boots', 300)
                if timestamp <= expected * 0.8:
                    return 'early'
                elif timestamp <= expected * 1.2:
                    return 'on_time'
                else:
                    return 'late'
            
            return 'unknown'
            
        except Exception as e:
            logger.error(f"Error checking item timing: {str(e)}")
            return 'unknown'
    
    def _xp_to_level(self, xp: int) -> int:
        """Convert XP to hero level using Dota 2 XP table."""
        xp_table = {
            1: 0, 2: 230, 3: 600, 4: 1080, 5: 1680,
            6: 2300, 7: 2940, 8: 3600, 9: 4280, 10: 5080,
            11: 5900, 12: 6720, 13: 7560, 14: 8420, 15: 9380,
            16: 10340, 17: 11300, 18: 12260, 19: 13220, 20: 16000,
            21: 18000, 22: 20000, 23: 22000, 24: 24000, 25: 25000
        }
        
        for level in sorted(xp_table.keys(), reverse=True):
            if xp >= xp_table[level]:
                return level
        return 1
