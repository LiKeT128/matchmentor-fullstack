
import sys
import os
import logging
import unittest
from datetime import datetime

# Add project root to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

# Mock dependencies
from unittest.mock import MagicMock
sys.modules["app.services.benchmark_service"] = MagicMock()

# Import after mocks
from app.services.match_analyzer import MatchAnalyzer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestMatchMetrics(unittest.TestCase):
    def setUp(self):
        self.analyzer = MatchAnalyzer()
        
        # Mock parsed data reflecting the structure from OpenDotaParserClient
        self.mock_data = {
            "match_id": "1234567890",
            "duration": 1800, # 30 minutes
            "players": [
                {
                    "player_slot": 0,
                    "hero_id": 1,
                    "hero_name": "npc_dota_hero_antimage",
                    "kills": 10,
                    "deaths": 2,
                    "assists": 5,
                    "gold_per_min": 600,
                    "xp_per_min": 700,
                    "last_hits": 250,
                    "denies": 15,
                    "hero_damage": 15000,
                    "tower_damage": 2000,
                    "hero_healing": 0,
                    "level": 20,
                    "gold": 1500,
                    "gold_spent": 16500,
                    # Items
                    "item_0": 63, # Power Treads
                    "item_1": 145, # Battle Fury
                    "item_2": 147, # Manta Style
                    "item_3": 116, # BKB
                    "item_4": 0,
                    "item_5": 0,
                    "backpack_0": 0,
                    "backpack_1": 0,
                    "backpack_2": 0,
                    # Detailed purchase log (for timings)
                    "purchase_log": [
                        {"key": "item_boots", "time": 120},
                        {"key": "item_bfury", "time": 780}, # 13 mins
                        {"key": "item_manta", "time": 1200}, # 20 mins
                    ],
                    # Lane stats
                    "lh_t": [0, 4, 8, 15, 30, 45, 60, 70, 80, 90, 100], # ~50 at 5 min, ~90 at 10 min? No, these are minutely usually or interval
                    # Correction: lh_t is typically every minute. len=30 for 30 mins
                    # Let's mock lh_at_10 directly if the parser provides it, or a list
                    "lh_at_10": 65,
                }
            ],
            "heroes": [
                {"hero_name": "npc_dota_hero_antimage", "player_slot": 0}
            ]
        }
        
    def test_group_1_basic_stats(self):
        """Test Group 1: Basic Stats"""
        hero_name = "npc_dota_hero_antimage"
        # We need to simulate the analyzer extracting this specific hero
        # Ideally calculate_basic_stats is a method we can test, or we run main analyze_match
        
        # For now, let's assume we are testing the new internal method we will write
        # or the public analyze_match interface
        
        # Note: MatchAnalyzer.analyze_match signature: (parsed_data, hero_name)
        result = self.analyzer.analyze_match(self.mock_data, hero_name=hero_name)
        metrics = result.get("metrics", {}).get("basic_stats", {})
        
        self.assertEqual(metrics.get("kills"), 10)
        self.assertEqual(metrics.get("deaths"), 2)
        self.assertEqual(metrics.get("assists"), 5)
        self.assertEqual(metrics.get("gpm"), 600)
        self.assertEqual(metrics.get("xpm"), 700)
        self.assertEqual(metrics.get("lh"), 250)
        
        # KDA Ratio: (K+A)/D = (10+5)/2 = 7.5
        self.assertAlmostEqual(metrics.get("kda_ratio"), 7.5)
        
    def test_group_2_farming(self):
        """Test Group 2: CS & Farming"""
        hero_name = "npc_dota_hero_antimage"
        result = self.analyzer.analyze_match(self.mock_data, hero_name=hero_name)
        metrics = result.get("metrics", {}).get("cs", {})
        
        self.assertEqual(metrics.get("cs"), 265) # 250 + 15
        self.assertEqual(metrics.get("denies"), 15)
        # CS/min = 265 / 30 = 8.83
        self.assertAlmostEqual(metrics.get("cs_per_min"), 8.83, delta=0.1)
        
    def test_group_5_items(self):
        """Test Group 5: Item Analysis"""
        hero_name = "npc_dota_hero_antimage"
        result = self.analyzer.analyze_match(self.mock_data, hero_name=hero_name)
        metrics = result.get("metrics", {}).get("items", {})
        
        # Check timings
        # bfury at 780s = 13:00
        timings = metrics.get("timings", [])
        bfury = next((i for i in timings if "bfury" in i["key"] or "Battle Fury" in i["name"]), None)
        self.assertIsNotNone(bfury)
        self.assertEqual(bfury["time"], 780)

if __name__ == "__main__":
    unittest.main()
