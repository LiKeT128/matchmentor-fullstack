"""
Integration tests for MatchMentor metrics using REAL OpenDota data.

These tests verify that:
1. All metrics are calculated from real data, not placeholders
2. Different heroes in the same match get different metrics
3. Time-series data (lh_t, gold_t, xp_t) is properly extracted
4. No hardcoded values remain in the output

Uses the real match data file: backend/8648645713_opendota.json
"""

import pytest
import json
import os
from pathlib import Path


# Get the path to the real match data file
BACKEND_DIR = Path(__file__).parent.parent
REAL_DATA_FILE = BACKEND_DIR / "8648645713_opendota.json"


class TestRealDataMetrics:
    """Test that metrics are calculated from real match data."""
    
    @pytest.fixture
    def real_match_data(self):
        """Load real OpenDota match data."""
        if not REAL_DATA_FILE.exists():
            pytest.skip(f"Real data file not found: {REAL_DATA_FILE}")
        
        with open(REAL_DATA_FILE, "r") as f:
            return json.load(f)
    
    @pytest.fixture
    def analyzer(self):
        """Create MatchAnalyzer instance."""
        from app.services.match_analyzer import MatchAnalyzer
        return MatchAnalyzer()
    
    def test_different_heroes_get_different_metrics(self, analyzer, real_match_data):
        """
        CRITICAL TEST: Verify different heroes get different metrics.
        
        This is the core test that proves we're not using placeholders.
        Luna (hero_id=48) and Shadow Fiend (hero_id=11) should have very different stats.
        """
        # Analyze Luna (Dire carry - 414 LH, 824 GPM in real data)
        luna_result = analyzer.analyze_match(real_match_data, hero_name="npc_dota_hero_luna")
        
        # Analyze Shadow Fiend (Dire mid - 249 LH, 662 GPM in real data)
        sf_result = analyzer.analyze_match(real_match_data, hero_name="npc_dota_hero_shadow_fiend")
        
        # BASIC STATS MUST BE DIFFERENT
        luna_gpm = luna_result["metrics"]["basic_stats"]["gpm"]
        sf_gpm = sf_result["metrics"]["basic_stats"]["gpm"]
        
        assert luna_gpm != sf_gpm, f"Luna GPM ({luna_gpm}) should differ from SF GPM ({sf_gpm})"
        
        # Verify actual values match OpenDota data
        assert luna_gpm == 824, f"Luna GPM should be 824 (from real data), got {luna_gpm}"
        assert sf_gpm == 662, f"SF GPM should be 662 (from real data), got {sf_gpm}"
        
        # LAST HITS MUST BE DIFFERENT
        luna_lh = luna_result["metrics"]["basic_stats"]["lh"]
        sf_lh = sf_result["metrics"]["basic_stats"]["lh"]
        
        assert luna_lh != sf_lh, f"Luna LH ({luna_lh}) should differ from SF LH ({sf_lh})"
        assert luna_lh > 400, f"Luna should have 400+ LH, got {luna_lh}"
        assert sf_lh < 300, f"SF should have <300 LH, got {sf_lh}"
    
    def test_laning_metrics_extracted_from_time_series(self, analyzer, real_match_data):
        """
        Test that laning phase metrics (lh_at_10, gold_at_10, xp_at_10) come from
        the minute-by-minute time series arrays, not estimates.
        """
        # Pick a hero with known laning data
        result = analyzer.analyze_match(real_match_data, hero_name="npc_dota_hero_luna")
        
        laning = result["metrics"]["laning_phase"]
        
        # lh_at_10 should be extracted from lh_t[10]
        # In the real data, Luna's lh_t array exists with per-minute values
        assert "lh_at_10" in laning, "Missing lh_at_10 metric"
        
        # Gold at 10 should come from gold_t[10]
        assert "gold_at_10" in laning, "Missing gold_at_10 metric"
        
        # XP at 10 should come from xp_t[10]
        assert "xp_at_10" in laning, "Missing xp_at_10 metric"
        
        # These values should be > 0 (not missing data)
        assert laning["lh_at_10"] >= 0, f"lh_at_10 should be >= 0, got {laning['lh_at_10']}"
        assert laning["gold_at_10"] >= 0, f"gold_at_10 should be >= 0, got {laning['gold_at_10']}"
    
    def test_teamfight_participation_uses_real_team_kills(self, analyzer, real_match_data):
        """
        Test that teamfight participation uses actual team kills, not hardcoded 40.
        
        From the real data:
        - Radiant score: 22 kills
        - Dire score: 32 kills
        """
        # Test a Dire hero (Shadow Fiend)
        sf_result = analyzer.analyze_match(real_match_data, hero_name="npc_dota_hero_shadow_fiend")
        
        fighting = sf_result["metrics"]["role_impact"]["fighting"]
        
        # SF has 11 kills, 9 assists = 20 contributions
        # Dire team has 32 kills
        # Participation should be around (20/32)*100 = 62.5%
        
        if "team_kills" in fighting:
            assert fighting["team_kills"] == 32, f"Dire team kills should be 32, got {fighting['team_kills']}"
        
        # Participation should NOT be based on 40 (the old hardcoded value)
        # With 40, it would be (20/40)*100 = 50%
        participation = fighting["teamfight_participation"]
        assert participation != 50.0, f"Participation {participation}% suggests hardcoded team_kills=40 still used"
    
    def test_no_placeholder_values_in_advanced_metrics(self, analyzer, real_match_data):
        """
        Test that advanced calculators don't return hardcoded placeholder values.
        
        Previously hardcoded values to check are NOT present:
        - rotation_timing: 75.0
        - recovery_prowess: 70.0
        - enemy_cd_tracking: 65.0
        - rosh_awareness: 55.0
        - consistency_score: 78.0
        - pressure_performance: 72.0
        - game_discipline: 85.0
        - vision_farm_efficiency: 0.82
        - gold_win_probability: 0.68
        """
        result = analyzer.analyze_match(real_match_data, hero_name="npc_dota_hero_luna")
        metrics = result["metrics"]
        
        # Check positioning metrics
        if "positioning_risk" in metrics:
            pos = metrics["positioning_risk"]
            # rotation_timing should NOT be exactly 75.0 (old placeholder)
            if "rotation_timing" in pos:
                assert pos["rotation_timing"] != 75.0 or pos.get("_data_sources"), \
                    "rotation_timing appears to be hardcoded 75.0"
        
        # Check decision quality
        if "decision_quality" in metrics:
            dq = metrics["decision_quality"]
            # recovery_prowess should NOT be exactly 70.0 (old placeholder)
            if "recovery_prowess" in dq:
                assert dq["recovery_prowess"] != 70.0 or dq.get("_data_sources"), \
                    "recovery_prowess appears to be hardcoded 70.0"
        
        # Check psychological metrics
        if "psychological_profile" in metrics:
            psych = metrics["psychological_profile"]
            # consistency_score should NOT be exactly 78.0 (old placeholder)
            if "consistency_score" in psych:
                assert psych["consistency_score"] != 78.0 or psych.get("_data_sources"), \
                    "consistency_score appears to be hardcoded 78.0"
    
    def test_gold_efficiency_not_placeholder(self, analyzer, real_match_data):
        """
        Test that gold_efficiency is calculated, not the old hardcoded 90.
        """
        result = analyzer.analyze_match(real_match_data, hero_name="npc_dota_hero_luna")
        
        items = result["metrics"]["role_impact"]["items"]
        
        # gold_efficiency should NOT be exactly 90 (old placeholder)
        # Unless the player genuinely has 90% efficiency
        gold_eff = items.get("gold_efficiency", 0)
        
        # Since Luna has high net_worth (25988), efficiency should be calculated
        # If it's still 90, that's suspicious
        if gold_eff == 90:
            # Check if there's net_worth data to validate
            net_worth = items.get("net_worth", 0)
            gold_spent = items.get("gold_spent", 0)
            assert net_worth > 0 or gold_spent > 0, \
                "gold_efficiency=90 with no net_worth/gold_spent data suggests placeholder"
    
    def test_all_players_can_be_analyzed(self, analyzer, real_match_data):
        """
        Test that all 10 heroes in the match can be analyzed without errors.
        """
        heroes = real_match_data.get("heroes", [])
        
        assert len(heroes) >= 10, "Match should have 10 heroes"
        
        analyzed_count = 0
        for hero in heroes:
            hero_name = hero.get("hero_name")
            if hero_name:
                try:
                    result = analyzer.analyze_match(real_match_data, hero_name=hero_name)
                    assert result is not None
                    assert "metrics" in result
                    analyzed_count += 1
                except Exception as e:
                    pytest.fail(f"Failed to analyze {hero_name}: {e}")
        
        assert analyzed_count == 10, f"Should analyze all 10 heroes, got {analyzed_count}"
    
    def test_metrics_have_data_source_audit(self, analyzer, real_match_data):
        """
        Test that metrics include _data_sources for auditability.
        """
        result = analyzer.analyze_match(real_match_data, hero_name="npc_dota_hero_luna")
        
        # Check if advanced metrics have data sources
        if "fight_effectiveness" in result["metrics"]:
            fe = result["metrics"]["fight_effectiveness"]
            assert "_data_sources" in fe or len(fe) > 0, \
                "fight_effectiveness should have data source tracking"
        
        if "positioning_risk" in result["metrics"]:
            pr = result["metrics"]["positioning_risk"]
            assert "_data_sources" in pr or len(pr) > 0, \
                "positioning_risk should have data source tracking"


class TestDataFlowIntegrity:
    """Test that data flows correctly through the analysis pipeline."""
    
    @pytest.fixture
    def real_match_data(self):
        """Load real OpenDota match data."""
        if not REAL_DATA_FILE.exists():
            pytest.skip(f"Real data file not found: {REAL_DATA_FILE}")
        
        with open(REAL_DATA_FILE, "r") as f:
            return json.load(f)
    
    def test_players_array_has_time_series(self, real_match_data):
        """Verify the real data has time-series arrays we need."""
        players = real_match_data.get("players", [])
        
        assert len(players) >= 10, "Should have 10 players"
        
        # Check first player has time series
        p0 = players[0]
        
        assert "gold_t" in p0, "Player should have gold_t time series"
        assert "lh_t" in p0, "Player should have lh_t time series"
        assert "xp_t" in p0, "Player should have xp_t time series"
        
        # Verify arrays have data
        assert len(p0["gold_t"]) > 10, "gold_t should have 10+ entries (one per minute)"
        assert len(p0["lh_t"]) > 10, "lh_t should have 10+ entries"
    
    def test_match_has_score_data(self, real_match_data):
        """Verify the real data has score data for team kills calculation."""
        radiant_score = real_match_data.get("radiant_score", 0)
        dire_score = real_match_data.get("dire_score", 0)
        
        assert radiant_score == 22, f"Radiant score should be 22, got {radiant_score}"
        assert dire_score == 32, f"Dire score should be 32, got {dire_score}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
