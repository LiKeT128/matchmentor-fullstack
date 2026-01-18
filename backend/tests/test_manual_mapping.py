import sys
import os
import re

# Simulate the logic in ODotaParserClient._convert_events_to_match
# We copy it here for rapid iteration without needing to import everything

def resolve_hero_name(unit_name):
    if not unit_name or not unit_name.startswith('CDOTA_Unit_Hero_'):
        return None
        
    short_name = unit_name[len('CDOTA_Unit_Hero_'):]
    
    # Custom mapping for known inconsistencies
    CUSTOM_MAPPINGS = {
        "AntiMage": "antimage",
        "OgreMagi": "ogre_magi",
        "Windrunner": "windrunner", 
        "Necrolyte": "necrolyte",
        "QueenOfPain": "queenofpain",
        "ShadowFiend": "shadow_fiend",
        "VengefulSpirit": "vengefulspirit",
        "DoomBringer": "doom_bringer",
        "SkeletonKing": "wraith_king",
        "Zuus": "zuus",
        "Nevermore": "shadow_fiend",
        "ObsidianDestroyer": "obsidian_destroyer",
        "LifeStealer": "life_stealer",
        "Magnataur": "magnataur", # Frontend expects magnataur? Wait, opendota_client says "magnataur": "magnus"??
        # Let's check reliability
        "WinterWyvern": "winter_wyvern",
        "Furion": "furion", # Nature's Prophet
    }
    
    if short_name in CUSTOM_MAPPINGS:
        return f"npc_dota_hero_{CUSTOM_MAPPINGS[short_name]}"
    
    # Default snake_case conversion
    # e.g. WinterWyvern -> winter_wyvern
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', short_name)
    snake_case = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
    return f"npc_dota_hero_{snake_case}"

# Test Cases based on user report
test_cases = [
    ("CDOTA_Unit_Hero_OgreMagi", "npc_dota_hero_ogre_magi"),
    ("CDOTA_Unit_Hero_WinterWyvern", "npc_dota_hero_winter_wyvern"),
    ("CDOTA_Unit_Hero_Magnataur", "npc_dota_hero_magnataur"), # Or magnus? 
    ("CDOTA_Unit_Hero_Nevermore", "npc_dota_hero_shadow_fiend"),
    ("CDOTA_Unit_Hero_AntiMage", "npc_dota_hero_antimage"),
]

print("Running local mapping tests...")
for unit, expected in test_cases:
    result = resolve_hero_name(unit)
    status = "PASS" if result == expected else "FAIL"
    print(f"[{status}] {unit} -> {result} (Expected: {expected})")

# Also check what opendota_client.py expects for Magnus
# opendota_client.py line 248: "magnataur": "magnus"
# So if we generate "npc_dota_hero_magnataur", opendota_client will remap it to "magnus" for the image?
# Line 230: hero_name_raw = self.get_hero_name(hero_id)
# Line 234: short_name = hero_name_raw.replace("npc_dota_hero_", "")
# Line 260: image_name = image_mapping.get(short_name, short_name)

# If parser gives "npc_dota_hero_magnataur", short_name is "magnataur".
# image_mapping["magnataur"] = "magnus".
# So "npc_dota_hero_magnataur" IS safe because opendota_client handles the image mapping.
# BUT, is "npc_dota_hero_magnataur" the valid OpenDota name? 
# ID 97 in hero_mapping.py is "npc_dota_hero_magnataur".
# So yes, it is valid.

print("\nDone.")
