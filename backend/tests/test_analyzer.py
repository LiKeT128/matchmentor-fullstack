"""Tests for match analyzer service."""

import pytest

from app.services.match_analyzer import MatchAnalyzer


class TestMatchAnalyzer:
    """Test suite for MatchAnalyzer service."""
    
    @pytest.fixture
    def analyzer(self):
        """Create analyzer instance."""
        return MatchAnalyzer()
    
    @pytest.fixture
    def sample_match_data(self):
        """Sample parsed match data for testing."""
        return {
            "match_id": "12345",
            "duration_minutes": 40,
            "hero_name": "Invoker",
            "result": "WIN",
            "kills": 10,
            "deaths": 5,
            "assists": 15,
            "gpm": 500,
            "xpm": 550,
            "last_hits": 200,
            "denies": 15,
            "hero_damage": 25000,
            "tower_damage": 5000,
            "hero_healing": 0,
            "items": ["blink", "aghanims", "octarine"],
            "item_timings": {"blink": 12, "aghanims": 22},
            "full_data": {
                "laning": {
                    "kills_10min": 2,
                    "deaths_10min": 1,
                    "lane_efficiency": 75,
                    "outcome": "won",
                    "first_blood": True
                },
                "combat": {
                    "stuns": 25,
                    "teamfight_participation": 80,
                    "solo_kills": 3,
                    "multi_kills": [2, 3],
                    "kill_streaks": 4
                },
                "farming": {
                    "neutral_kills": 45,
                    "ancient_kills": 10,
                    "gold_efficiency": 85,
                    "dead_time_seconds": 120,
                    "time_farming_percent": 45,
                    "camps_stacked": 8
                },
                "map": {
                    "wards_placed": 5,
                    "wards_destroyed": 2,
                    "sentries_placed": 3,
                    "towers_killed": 2,
                    "roshans": 1,
                    "tp_scrolls": 12,
                    "smokes_used": 4
                },
                "items": {
                    "first_major_item_time": 15,
                    "slot_efficiency": 90,
                    "backpack_usage": 8,
                    "neutral_tier": 4
                },
                "team": {
                    "damage_share": 28,
                    "gold_share": 25,
                    "kill_participation": 75,
                    "buybacks": 1,
                    "saves": 2,
                    "stacks_created": 5
                }
            }
        }
    
    def test_analyze_match_returns_metrics(self, analyzer, sample_match_data):
        """Test analyzer returns metrics dict."""
        result = analyzer.analyze_match(sample_match_data)
        
        assert "metrics" in result
        assert isinstance(result["metrics"], dict)
        assert len(result["metrics"]) > 0
    
    def test_analyze_match_returns_advice(self, analyzer, sample_match_data):
        """Test analyzer returns advice list."""
        result = analyzer.analyze_match(sample_match_data)
        
        assert "advice" in result
        assert isinstance(result["advice"], list)
    
    def test_analyze_match_returns_overall_score(self, analyzer, sample_match_data):
        """Test analyzer returns overall score."""
        result = analyzer.analyze_match(sample_match_data)
        
        assert "overall_score" in result
        assert isinstance(result["overall_score"], int)
        assert 0 <= result["overall_score"] <= 100
    
    def test_analyze_match_returns_strengths(self, analyzer, sample_match_data):
        """Test analyzer identifies strengths."""
        result = analyzer.analyze_match(sample_match_data)
        
        assert "strengths" in result
        assert isinstance(result["strengths"], list)
    
    def test_analyze_match_returns_weaknesses(self, analyzer, sample_match_data):
        """Test analyzer identifies weaknesses."""
        result = analyzer.analyze_match(sample_match_data)
        
        assert "weaknesses" in result
        assert isinstance(result["weaknesses"], list)
    
    def test_laning_metrics_calculated(self, analyzer, sample_match_data):
        """Test laning phase metrics are calculated."""
        result = analyzer.analyze_match(sample_match_data)
        metrics = result["metrics"]
        
        assert "last_hits" in metrics
        assert "lh_at_10" in metrics
        assert "denies" in metrics
    
    def test_combat_metrics_calculated(self, analyzer, sample_match_data):
        """Test combat metrics are calculated."""
        result = analyzer.analyze_match(sample_match_data)
        metrics = result["metrics"]
        
        assert "kills" in metrics
        assert "kda" in metrics
        assert "teamfight_participation" in metrics
    
    def test_farming_metrics_calculated(self, analyzer, sample_match_data):
        """Test farming metrics are calculated."""
        result = analyzer.analyze_match(sample_match_data)
        metrics = result["metrics"]
        
        assert "gpm" in metrics
        assert "xpm" in metrics
        assert "last_hits" in metrics
    
    def test_kda_calculation(self, analyzer, sample_match_data):
        """Test KDA is calculated correctly."""
        result = analyzer.analyze_match(sample_match_data)
        
        # (10 + 15) / 5 = 5.0
        assert result["metrics"]["kda"] == 5.0
    
    def test_cs_per_min_calculation(self, analyzer, sample_match_data):
        """Test CS count is tracked correctly."""
        result = analyzer.analyze_match(sample_match_data)
        
        # 200 last hits
        assert result["metrics"]["last_hits"] == 200
    
    def test_advice_generation_low_cs(self, analyzer):
        """Test advice generated for low CS."""
        low_cs_data = {
            "match_id": "123",
            "duration_minutes": 40,
            "hero_name": "Anti-Mage",
            "result": "LOSS",
            "kills": 5,
            "deaths": 8,
            "assists": 5,
            "gpm": 350,
            "xpm": 400,
            "last_hits": 120,  # Low for 40 min
            "denies": 5,
            "hero_damage": 15000,
            "tower_damage": 2000,
            "full_data": {}
        }
        
        result = analyzer.analyze_match(low_cs_data)
        
        # Should have advice about farming (new structure uses 'type' and 'message')
        advice_types = [a["type"] for a in result["advice"]]
        advice_messages = [a["message"] for a in result["advice"]]
        # Check for farming or laning related advice
        assert any(t in ["farming", "laning"] for t in advice_types) or \
               any("GPM" in m or "last hit" in m.lower() for m in advice_messages)
    
    def test_advice_generation_high_deaths(self, analyzer):
        """Test advice generated for high deaths."""
        high_death_data = {
            "match_id": "123",
            "duration_minutes": 30,
            "hero_name": "Phantom Assassin",
            "result": "LOSS",
            "kills": 5,
            "deaths": 15,  # Very high
            "assists": 5,
            "gpm": 400,
            "xpm": 450,
            "last_hits": 180,
            "denies": 10,
            "hero_damage": 20000,
            "tower_damage": 3000,
            "full_data": {}
        }
        
        result = analyzer.analyze_match(high_death_data)
        
        # Should have advice about positioning or deaths
        advice_types = [a["type"] for a in result["advice"]]
        advice_messages = [a["message"] for a in result["advice"]]
        assert any(t == "positioning" for t in advice_types) or \
               any("die" in m.lower() or "death" in m.lower() for m in advice_messages)
    
    def test_overall_score_high_performance(self, analyzer, sample_match_data):
        """Test high score for good performance."""
        result = analyzer.analyze_match(sample_match_data)
        
        # With good KDA (5.0), good GPM (500), should score above 60
        assert result["overall_score"] >= 60
    
    def test_overall_score_low_performance(self, analyzer):
        """Test low score for poor performance."""
        bad_performance = {
            "match_id": "123",
            "duration_minutes": 40,
            "hero_name": "Drow Ranger",
            "result": "LOSS",
            "kills": 1,
            "deaths": 12,
            "assists": 3,
            "gpm": 280,
            "xpm": 320,
            "last_hits": 80,
            "denies": 2,
            "hero_damage": 8000,
            "tower_damage": 500,
            "full_data": {}
        }
        
        result = analyzer.analyze_match(bad_performance)
        
        # Should score below 50
        assert result["overall_score"] <= 50
    
    def test_handles_zero_deaths(self, analyzer):
        """Test analyzer handles zero deaths correctly."""
        zero_death_data = {
            "match_id": "123",
            "duration_minutes": 30,
            "hero_name": "Slark",
            "result": "WIN",
            "kills": 15,
            "deaths": 0,  # No deaths
            "assists": 10,
            "gpm": 600,
            "xpm": 650,
            "last_hits": 250,
            "denies": 20,
            "hero_damage": 30000,
            "tower_damage": 6000,
            "full_data": {}
        }
        
        result = analyzer.analyze_match(zero_death_data)
        
        # Should handle without division by zero
        assert "kda" in result["metrics"]
        # KDA should be very high (25/1 since we use max(deaths, 1))
        assert result["metrics"]["kda"] >= 20
    
    def test_handles_zero_duration(self, analyzer):
        """Test analyzer handles abandoned/short matches."""
        short_match = {
            "match_id": "123",
            "duration_minutes": 0,  # Early abandon
            "hero_name": "Zeus",
            "result": "ABANDONED",
            "kills": 0,
            "deaths": 1,
            "assists": 0,
            "gpm": 100,
            "xpm": 100,
            "last_hits": 10,
            "denies": 0,
            "hero_damage": 500,
            "tower_damage": 0,
            "full_data": {}
        }
        
        # Should not raise exception
        result = analyzer.analyze_match(short_match)
        assert "metrics" in result
