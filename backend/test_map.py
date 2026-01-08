
import sys
import os

sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.services.hero_mapping import get_hero_name

def test_map():
    print(f"ID 1 -> {get_hero_name(1)}") # npc_dota_hero_antimage
    print(f"ID 2 -> {get_hero_name(2)}") # npc_dota_hero_axe
    
    # Assert
    assert get_hero_name(1) == "npc_dota_hero_antimage"
    assert get_hero_name(2) == "npc_dota_hero_axe"
    print("Mapping verified.")

if __name__ == "__main__":
    test_map()
