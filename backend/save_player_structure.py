"""
Save parsed_data structure to JSON file for inspection
"""
import asyncio
import json
import sys
import os

sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.services.opendota_client import OpenDotaClient

async def save_structure():
    match_id = "8641028604"
    client = OpenDotaClient()
    
    print(f"Fetching match {match_id}...")
    match_data = await client.get_match(match_id)
    
    if not match_data:
        print("Failed to fetch")
        return
    
    # Get first player
    player_0 = match_data.get("players", [])[0] if match_data.get("players") else {}
    
    # Save to file
    with open("player_0_structure.json", "w", encoding="utf-8") as f:
        json.dump(player_0, f, indent=2, default=str)
    
    print("✅ Saved to player_0_structure.json")
    
    # Print key info
    print(f"\n📊 Data Types:")
    print(f"  gold_t: {type(player_0.get('gold_t')).__name__}")
    print(f"  xp_t: {type(player_0.get('xp_t')).__name__}")
    print(f"  lh_t: {type(player_0.get('lh_t', 'NOT_FOUND'))}")
    
    if "benchmarks" in player_0:
        print(f"  benchmarks: {type(player_0['benchmarks']).__name__}")
        print(f"    keys: {list(player_0['benchmarks'].keys())}")

if __name__ == "__main__":
    asyncio.run(save_structure())
