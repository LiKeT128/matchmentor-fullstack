import json
import logging

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Mocking hero_mapping.py ---
HERO_MAP = {
    36: "npc_dota_hero_necrolyte",
    87: "npc_dota_hero_disruptor",
    79: "npc_dota_hero_shadow_demon",
    # Add minimal required for test
}

def get_hero_name(hero_id: int) -> str:
    return HERO_MAP.get(hero_id, f"npc_dota_hero_unknown")

# --- Copy of _extract_heroes_from_match logic (simplified for test) ---
def _extract_heroes_from_match(parsed_data):
    if not parsed_data:
        print("parsed_data is None")
        return []

    heroes = []
    heroes_raw = parsed_data.get("heroes", [])
    if heroes_raw:
        print(f"Found {len(heroes_raw)} in 'heroes'")
    else:
        heroes_raw = parsed_data.get("players", [])
        print(f"Fallback to 'players', found {len(heroes_raw)}")

    for idx, entry in enumerate(heroes_raw):
        raw_hero_name = "unknown"
        hero_id = None
        
        if isinstance(entry, dict):
            raw_hero_name = entry.get("hero_name", entry.get("hero"))
            hero_id = entry.get("hero_id")
            
            print(f"Player {idx}: raw_name={raw_hero_name}, id={hero_id}")

            if (not raw_hero_name or "unknown" in str(raw_hero_name).lower()) and hero_id:
                try:
                    mapped_name = get_hero_name(int(hero_id))
                    if mapped_name and "unknown" not in mapped_name:
                         raw_hero_name = mapped_name
                         print(f"  -> Mapped to {mapped_name}")
                except Exception as e:
                    print(f"  -> Mapping failed: {e}")

        # Image mapping logic
        raw_name = str(raw_hero_name) if raw_hero_name else "unknown"
        short_name = raw_name.replace("npc_dota_hero_", "")
        
        heroes.append({
            "player_id": idx,
            "hero_name": short_name
        })
    
    return heroes

# --- Run Test ---
def run_test():
    try:
        with open("backend/match_dump.json", "r") as f:
            data = json.load(f)
            
        print("Loaded JSON.")
        extract = _extract_heroes_from_match(data)
        print("Extraction Result:")
        for h in extract[:5]:
            print(h)
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    run_test()
