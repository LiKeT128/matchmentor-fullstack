
import sys
import os
import logging
import traceback

# Add project root to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

# Mock dependencies
from unittest.mock import MagicMock
sys.modules["app.services.benchmark_service"] = MagicMock()

# Import after mocks
from app.services.match_analyzer import MatchAnalyzer

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def run_debug():
    analyzer = MatchAnalyzer()
    
    mock_data = {
        "match_id": "1234567890",
        "duration": 1800,
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
                "gold_spent": 16500
            }
        ],
        "heroes": [
            {"hero_name": "npc_dota_hero_antimage", "player_slot": 0}
        ]
    }
    
    try:
        print("Starting analysis...")
        result = analyzer.analyze_match(mock_data, hero_name="npc_dota_hero_antimage")
        print("Analysis success!")
        print(result)
    except Exception:
        traceback.print_exc()

if __name__ == "__main__":
    run_debug()
