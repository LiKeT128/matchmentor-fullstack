"""
Verification test for JSON mock data workflow.
"""
import unittest
import json
import os
import sys
from pathlib import Path

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from mock_parser_data import run_mock_analysis

class TestParserMock(unittest.TestCase):
    def setUp(self):
        self.test_json = "backend/test_fixture.json"
        # Create a small fixture
        self.fixture_data = {
            "match_id": "999999",
            "duration": 600,
            "players": [
                {
                    "player_slot": 0,
                    "hero_name": "npc_dota_hero_pudge",
                    "kills": 5,
                    "deaths": 1,
                    "assists": 2,
                    "gold_per_min": 400,
                    "xp_per_min": 500,
                    "last_hits": 40,
                    "denies": 5,
                    "observer_wards_placed": 2,
                    "obs_log": [{"time": 100, "x": 100, "y": 100}, {"time": 200, "x": 120, "y": 120}],
                    "sen_log": [{"time": 150, "x": 110, "y": 110}],
                    "gold_t": [0, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000],
                    "kills_log": [{"time": 300, "type": "kill"}]
                }
            ],
            "heroes": [
                {"hero_name": "npc_dota_hero_pudge", "player_slot": 0}
            ]
        }
        with open(self.test_json, 'w') as f:
            json.dump(self.fixture_data, f)

    def tearDown(self):
        if os.path.exists(self.test_json):
            os.remove(self.test_json)
        analysis_file = Path("backend/analysis_test_fixture.json")
        if analysis_file.exists():
            analysis_file.unlink()

    def test_mock_analysis_flow(self):
        """Test that run_mock_analysis executes and returns valid metrics."""
        results = run_mock_analysis(self.test_json, "npc_dota_hero_pudge")
        
        self.assertIsNotNone(results)
        self.assertEqual(results["hero_name"], "npc_dota_hero_pudge")
        
        metrics = results.get("metrics", {})
        basic = metrics.get("basic_stats", {})
        self.assertEqual(basic.get("kills"), 5)
        self.assertEqual(basic.get("gpm"), 400)
        
        vision = metrics.get("vision", {})
        self.assertEqual(vision.get("wards_placed"), 2)
        
        # Unique Advanced Groups
        self.assertIn("fight_effectiveness", metrics)
        self.assertIn("advanced_positioning", metrics)
        self.assertIn("decision_quality", metrics)
        self.assertIn("threat_prediction", metrics)
        self.assertIn("psychological", metrics)
        self.assertIn("stat_correlations", metrics)
        
        # Specific nested values check
        self.assertEqual(metrics["psychological"].get("risk_score_aggression"), 7.0) # (5+2)/1

if __name__ == "__main__":
    unittest.main()
