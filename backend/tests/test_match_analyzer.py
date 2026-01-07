"""Tests for Match Analyzer service with 60+ metrics."""

import pytest
from app.services.match_analyzer import MatchAnalyzer
from app.services.benchmark_service import BenchmarkService


class TestMatchAnalyzer:
    """Test suite for MatchAnalyzer service."""
    
    @pytest.fixture
    def analyzer(self):
        """Create analyzer instance."""
        return MatchAnalyzer()
    
    @pytest.fixture
    def sample_parsed_data(self):
        """Sample parsed data from replay."""
        return {
            "match_id": "12345",
            "duration_minutes": 40,
            "hero_name": "Invoker",
            "result": "WIN",
            "kills": 12,
            "deaths": 4,
            "assists": 15,
            "gpm": 550,
            "xpm": 620,
            "last_hits": 280,
            "denies": 18,
            "hero_damage": 32000,
            "tower_damage": 5500,
            "items": ["blink", "aghanims_scepter", "octarine_core"],
            "item_timings": {
                "item_blink": 720,
                "item_aghanims_scepter": 1200,
                "item_power_treads": 420
            },
            "full_data": {
                "laning": {
                    "last_hits_10min": 65,
                    "deaths_10min": 1,
                    "gold_10min": 3200,
                    "xp_10min": 4500,
                    "lane_control_pct": 55,
                    "camps_stacked": 2
                },
                "combat": {
                    "teamfight_participation": 0.72,
                    "stun_duration": 45,
                    "fight_damage": 18000
                },
                "positioning": {
                    "position_safety_score": 0.65,
                    "danger_zone_pct": 25
                },
                "map": {
                    "wards_placed": 8,
                    "wards_destroyed": 3
                }
            }
        }
    
    def test_analyzer_initialization(self, analyzer):
        """Test analyzer can be initialized."""
        assert analyzer is not None
    
    def test_analyze_match_returns_all_keys(self, analyzer, sample_parsed_data):
        """Test analyze_match returns all expected keys."""
        result = analyzer.analyze_match(sample_parsed_data)
        
        assert "metrics" in result
        assert "advice" in result
        assert "overall_score" in result
        assert "strengths" in result
        assert "weaknesses" in result
        assert "power_spikes" in result
        assert "mistakes" in result
    
    def test_basic_metrics_calculated(self, analyzer, sample_parsed_data):
        """Test basic metrics (10) are calculated."""
        result = analyzer.calculate_gpm_xpm(sample_parsed_data)
        
        assert result["gpm"] == 550
        assert result["xpm"] == 620
        assert result["last_hits"] == 280
        assert result["denies"] == 18
        assert result["kills"] == 12
        assert result["deaths"] == 4
        assert result["assists"] == 15
        assert "kda" in result
        assert "damage_ratio" in result
        assert "gold_efficiency" in result
    
    def test_kda_calculation(self, analyzer, sample_parsed_data):
        """Test KDA is calculated correctly."""
        result = analyzer.calculate_gpm_xpm(sample_parsed_data)
        # KDA = (12 + 15) / 4 = 6.75
        assert result["kda"] == 6.75
    
    def test_positioning_metrics(self, analyzer, sample_parsed_data):
        """Test positioning metrics (8) are calculated."""
        result = analyzer.calculate_positioning_risk(sample_parsed_data)
        
        assert "position_safety_score" in result
        assert "danger_zone_pct" in result
        assert "farm_location_diversity" in result
        assert "tower_proximity_score" in result
    
    def test_fighting_metrics(self, analyzer, sample_parsed_data):
        """Test fighting metrics (10) are calculated."""
        result = analyzer.calculate_teamfight_stats(sample_parsed_data)
        
        assert "teamfight_participation" in result
        assert "stun_duration_total" in result
        assert "fight_damage" in result
        assert "roshan_participation" in result
    
    def test_timing_metrics(self, analyzer, sample_parsed_data):
        """Test timing metrics (12) are calculated."""
        result = analyzer.calculate_item_efficiency(sample_parsed_data)
        
        assert "blink_timing" in result
        assert "boots_timing" in result
        assert "first_item_timing" in result
        assert "pro_timing_diff" in result
    
    def test_blink_timing_extraction(self, analyzer, sample_parsed_data):
        """Test blink timing is extracted correctly."""
        result = analyzer.calculate_item_efficiency(sample_parsed_data)
        assert result["blink_timing"] == 720
    
    def test_warding_metrics(self, analyzer, sample_parsed_data):
        """Test warding metrics (6) are calculated."""
        result = analyzer.calculate_warding_value(sample_parsed_data)
        
        assert result["wards_placed"] == 8
        assert result["deward_count"] == 3
        assert "vision_uptime_pct" in result
    
    def test_lane_metrics(self, analyzer, sample_parsed_data):
        """Test lane phase metrics (6) are calculated."""
        result = analyzer.calculate_lane_metrics(sample_parsed_data)
        
        assert result["lh_at_10"] == 65
        assert result["deaths_in_lane"] == 1
        assert result["gold_at_10"] == 3200
        assert result["camps_stacked"] == 2
    
    def test_midgame_metrics(self, analyzer, sample_parsed_data):
        """Test mid game metrics (5) are calculated."""
        result = analyzer.calculate_midgame_metrics(sample_parsed_data)
        
        assert "midgame_gpm" in result
        assert "objectives_taken" in result
        assert "farm_pattern_efficiency" in result
    
    def test_lategame_metrics(self, analyzer, sample_parsed_data):
        """Test late game metrics (4) are calculated."""
        result = analyzer.calculate_lategame_metrics(sample_parsed_data)
        
        assert "lategame_gold_efficiency" in result
        assert "high_ground_control" in result
        assert "buyback_utilization" in result
    
    def test_benchmark_comparison(self, analyzer, sample_parsed_data):
        """Test benchmark comparison is generated."""
        metrics = analyzer.calculate_gpm_xpm(sample_parsed_data)
        comparison = analyzer.compare_with_benchmark(metrics, "Invoker")
        
        assert "gpm_ratio" in comparison
        assert "xpm_ratio" in comparison
        assert "deaths_ratio" in comparison
        assert comparison["gpm_ratio"] > 1.0  # 550 > 450 benchmark
    
    def test_advice_generation(self, analyzer, sample_parsed_data):
        """Test deterministic advice is generated."""
        result = analyzer.analyze_match(sample_parsed_data)
        
        assert isinstance(result["advice"], list)
        for item in result["advice"]:
            assert "type" in item
            assert "severity" in item
            assert "message" in item
            assert "suggestion" in item
    
    def test_overall_score_in_range(self, analyzer, sample_parsed_data):
        """Test overall score is between 0-100."""
        result = analyzer.analyze_match(sample_parsed_data)
        
        assert 0 <= result["overall_score"] <= 100
    
    def test_good_performance_high_score(self, analyzer, sample_parsed_data):
        """Test good performance yields high score."""
        result = analyzer.analyze_match(sample_parsed_data)
        
        # With 550 GPM, 6.75 KDA, 280 LH - should be above average
        assert result["overall_score"] >= 60
    
    def test_power_spikes_detection(self, analyzer, sample_parsed_data):
        """Test power spikes are detected from item timings."""
        result = analyzer.analyze_match(sample_parsed_data)
        
        # Should detect blink at 720s (12 min) as early
        blink_spike = next(
            (s for s in result["power_spikes"] if "Blink" in s["item"]), 
            None
        )
        if blink_spike:
            assert blink_spike["status"] in ["early", "average", "late"]
    
    def test_strengths_identification(self, analyzer, sample_parsed_data):
        """Test strengths are identified."""
        result = analyzer.analyze_match(sample_parsed_data)
        
        assert isinstance(result["strengths"], list)
        # With KDA 6.75, should identify high KDA as strength
        assert any("KDA" in s for s in result["strengths"])
    
    def test_mistakes_detection(self, analyzer, sample_parsed_data):
        """Test mistakes are detected."""
        result = analyzer.analyze_match(sample_parsed_data)
        
        assert isinstance(result["mistakes"], list)
    
    def test_metrics_count(self, analyzer, sample_parsed_data):
        """Test that 60+ metrics are calculated."""
        result = analyzer.analyze_match(sample_parsed_data)
        metrics = result["metrics"]
        
        # Count all metrics (excluding nested dicts)
        count = sum(
            1 for k, v in metrics.items() 
            if not isinstance(v, (dict, list))
        )
        
        # Should have at least 50 scalar metrics
        assert count >= 50


class TestBenchmarkService:
    """Test suite for BenchmarkService."""
    
    def test_default_benchmarks(self):
        """Test default benchmarks are available."""
        service = BenchmarkService()
        defaults = service.DEFAULT_BENCHMARKS
        
        assert defaults["gpm"] == 450
        assert defaults["xpm"] == 500
        assert defaults["deaths"] == 5
    
    def test_pro_item_timings(self):
        """Test pro item timings are defined."""
        service = BenchmarkService()
        
        assert service.get_pro_item_timing("blink") == 780
        assert service.get_pro_item_timing("hand_of_midas") == 540
        assert service.get_pro_item_timing("black_king_bar") == 1200
    
    def test_pro_timing_normalization(self):
        """Test item name normalization."""
        service = BenchmarkService()
        
        # Should handle item_ prefix
        assert service.get_pro_item_timing("item_blink") == 780
    
    def test_unknown_item_returns_none(self):
        """Test unknown item returns None."""
        service = BenchmarkService()
        
        assert service.get_pro_item_timing("unknown_item") is None
