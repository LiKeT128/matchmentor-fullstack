"""
Inspect parsed_data structure from OpenDota to understand real format
"""
import asyncio
import json
import sys
import os

sys.path.append(os.path.join(os.getcwd(), "backend"))

import logging
logging.basicConfig(level=logging.INFO)

from app.services.opendota_client import OpenDotaClient

async def inspect_data():
    match_id = "8641028604"  # Muerta match
    client = OpenDotaClient()
    
    print(f"\n{'='*80}")
    print(f"INSPECTING PARSED_DATA STRUCTURE FOR MATCH {match_id}")
    print(f"{'='*80}\n")
    
    match_data = await client.get_match(match_id)
    
    if not match_data:
        print("❌ Failed to fetch match data")
        return
    
    print(f"✅ Match data fetched successfully\n")
    
    # Print top-level keys
    print("📋 TOP-LEVEL KEYS:")
    for key in match_data.keys():
        value = match_data[key]
        value_type = type(value).__name__
        if isinstance(value, list):
            print(f"  {key}: {value_type} (length: {len(value)})")
        elif isinstance(value, dict):
            print(f"  {key}: {value_type} (keys: {len(value)})")
        else:
            print(f"  {key}: {value_type}")
    
    # Inspect players array
    players = match_data.get("players", [])
    if not players:
        print("\n❌ No players array found")
        return
    
    print(f"\n{'='*80}")
    print(f"PLAYER[0] STRUCTURE (First player)")
    print(f"{'='*80}\n")
    
    player_0 = players[0]
    
    # Print all keys and their types
    print("📊 ALL PLAYER KEYS AND TYPES:")
    for key in sorted(player_0.keys()):
        value = player_0[key]
        value_type = type(value).__name__
        
        if isinstance(value, list):
            length = len(value)
            if length > 0:
                first_item_type = type(value[0]).__name__
                print(f"  {key}: {value_type} (length: {length}, items: {first_item_type})")
            else:
                print(f"  {key}: {value_type} (empty)")
        elif isinstance(value, dict):
            print(f"  {key}: {value_type} (keys: {list(value.keys())[:5]}...)")
        else:
            print(f"  {key}: {value_type} = {value}")
    
    # Focus on time-series data
    print(f"\n{'='*80}")
    print("⏱️  TIME-SERIES DATA INSPECTION")
    print(f"{'='*80}\n")
    
    # Check gold_t
    if "gold_t" in player_0:
        gold_t = player_0["gold_t"]
        print(f"gold_t type: {type(gold_t).__name__}")
        if isinstance(gold_t, list):
            print(f"  Length: {len(gold_t)}")
            print(f"  First 15 values: {gold_t[:15]}")
            print(f"  Value at index 10: {gold_t[10] if len(gold_t) > 10 else 'N/A'}")
        elif isinstance(gold_t, dict):
            print(f"  Keys (first 15): {list(gold_t.keys())[:15]}")
            print(f"  Value at key '10': {gold_t.get('10', 'N/A')}")
        else:
            print(f"  Value: {gold_t}")
    else:
        print("❌ gold_t not found")
    
    # Check xp_t
    if "xp_t" in player_0:
        xp_t = player_0["xp_t"]
        print(f"\nxp_t type: {type(xp_t).__name__}")
        if isinstance(xp_t, list):
            print(f"  Length: {len(xp_t)}")
            print(f"  First 15 values: {xp_t[:15]}")
            print(f"  Value at index 10: {xp_t[10] if len(xp_t) > 10 else 'N/A'}")
        elif isinstance(xp_t, dict):
            print(f"  Keys (first 15): {list(xp_t.keys())[:15]}")
            print(f"  Value at key '10': {xp_t.get('10', 'N/A')}")
    else:
        print("❌ xp_t not found")
    
    # Check lh_t
    if "lh_t" in player_0:
        lh_t = player_0["lh_t"]
        print(f"\nlh_t type: {type(lh_t).__name__}")
        if isinstance(lh_t, list):
            print(f"  Length: {len(lh_t)}")
            print(f"  First 15 values: {lh_t[:15]}")
            print(f"  Value at index 10: {lh_t[10] if len(lh_t) > 10 else 'N/A'}")
        elif isinstance(lh_t, dict):
            print(f"  Keys (first 15): {list(lh_t.keys())[:15]}")
            print(f"  Value at key '10': {lh_t.get('10', 'N/A')}")
    else:
        print("❌ lh_t not found")
    
    # Check benchmarks
    if "benchmarks" in player_0:
        benchmarks = player_0["benchmarks"]
        print(f"\nbenchmarks type: {type(benchmarks).__name__}")
        if isinstance(benchmarks, dict):
            print(f"  Keys: {list(benchmarks.keys())}")
            if "lhten" in benchmarks:
                lhten = benchmarks["lhten"]
                print(f"  lhten: {lhten}")
    else:
        print("❌ benchmarks not found")
    
    # Print full JSON for first player (pretty printed)
    print(f"\n{'='*80}")
    print("📄 FULL PLAYER[0] JSON (for reference)")
    print(f"{'='*80}\n")
    
    print(json.dumps(player_0, indent=2, default=str)[:3000] + "\n... (truncated)")
    
    print(f"\n{'='*80}")
    print("✅ INSPECTION COMPLETE")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    asyncio.run(inspect_data())
