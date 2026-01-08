
import sys
import os
import logging
from unittest.mock import MagicMock

# Mock missing dependencies
sys.modules["httpx"] = MagicMock()
sys.modules["app.services.benchmark_service"] = MagicMock()
sys.modules["sendgrid"] = MagicMock()
sys.modules["sendgrid.helpers.mail"] = MagicMock()
sys.modules["email_validator"] = MagicMock()

# Add project root to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.api.matches import _extract_heroes_from_match

# Mock logger
logging.basicConfig(level=logging.INFO)

def test_extraction():
    # Test case 1: Missing hero_name but has hero_id (e.g. from OpenDota sometimes)
    parsed_data_1 = {
        "heroes": [
            {
                "hero_id": 1, # Anti-Mage
                "hero_name": "unknown", 
                "lane": 1, # Bot
                "team": "radiant" 
            },
            {
                "hero_id": 2, # Axe
                "hero_name": None,
                "lane": 3, # Top
                "team": "dire"
            }
        ]
    }
    
    # Expected: "npc_dota_hero_antimage" -> "antimage" -> "Antimage" (mapped)
    # Expected: "npc_dota_hero_axe" -> "axe" -> "Axe"
    
    print("Testing extraction with missing names...")
    heroes = _extract_heroes_from_match(parsed_data_1)
    
    for h in heroes:
        print(f"ID: {h['player_id']}, Name: {h['hero_name']}, Display: {h['hero_display_name']}, Position: {h['position']}, Team: {h['team']}")
        
    # Assertions
    h0 = heroes[0]
    assert "antimage" in h0['hero_name'], f"Expected antimage, got {h0['hero_name']}"
    assert h0['position'] == "Safe Lane", f"Expected Safe Lane for Radiant Bot, got {h0['position']}"
    
    h1 = heroes[1]
    assert "axe" in h1['hero_name'], f"Expected axe, got {h1['hero_name']}"
    assert h1['position'] == "Safe Lane", f"Expected Safe Lane for Dire Top, got {h1['position']}" 
    # Wait, Dire Top is OFF LANE for Dire? No, Map is mirrored?
    # Radiant: Bot=Safe, Top=Off, Mid=Mid
    # Dire: Bot=Off, Top=Safe, Mid=Mid
    # Let's check my logic in matches.py:
    # elif lane_val == 1: # Bot
    #     position = "Safe Lane" if is_radiant else "Off Lane"  <-- Correct
    # elif lane_val == 3: # Top
    #     position = "Off Lane" if is_radiant else "Safe Lane"  <-- Correct
    
    print("\nSUCCESS: Hero extraction logic verified!")

if __name__ == "__main__":
    test_extraction()
