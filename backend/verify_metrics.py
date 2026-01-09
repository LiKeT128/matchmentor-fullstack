import asyncio
import json
import os
import sys

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.services.opendota_client import OpenDotaClient
from app.services.match_analyzer import MatchAnalyzer

async def verify_metrics():
    match_id = "8641658282"
    client = OpenDotaClient()
    analyzer = MatchAnalyzer()
    
    print(f"Fetching match {match_id} from OpenDota...")
    match_data = await client.get_match(match_id)
    
    if not match_data:
        print("Failed to fetch match data.")
        return

    print("Analyzing match...")
    print(f"Match keys: {list(match_data.keys())}")
    
    # Let's find DK in the heroes list
    dk_player = None
    heroes = match_data.get("heroes", [])
    print(f"Found {len(heroes)} heroes.")
    
    for hero in heroes:
        name = str(hero.get("hero_name") or "").lower()
        if "dragon_knight" in name:
            dk_player = hero
            break
    
    if not dk_player and heroes:
        print("DK not found by name, picking first player.")
        dk_player = heroes[0]

    player_idx = dk_player["player_id"]
    print(f"Selected hero: {dk_player['hero_name']} at index {player_idx}")

    # Build analysis input
    analysis_input = {
        "match_id": match_id,
        "duration_minutes": match_data.get("duration_minutes", 30),
        "hero_name": dk_player["hero_name"],
        "result": match_data.get("result", "WIN"),
        "kills": dk_player.get("kills", 0),
        "deaths": dk_player.get("deaths", 0),
        "assists": dk_player.get("assists", 0),
        "gpm": dk_player.get("gpm", 0),
        "xpm": dk_player.get("xpm", 0),
        "last_hits": dk_player.get("last_hits", 0),
        "denies": dk_player.get("denies", 0),
        "full_data": dk_player
    }
    
    analysis = analyzer.analyze_match(analysis_input)
    metrics = analysis["metrics"]
    
    print("\n--- METRICS VERIFICATION ---")
    print(f"Total Metrics Count: {len(metrics)}")
    
    important_keys = [
        "lh_at_10", "danger_zone_pct", "stun_duration_total", 
        "pro_avg_gpm", "pro_avg_lh_10", "vision_score",
        "gold_efficiency", "teamfight_participation"
    ]
    
    all_present = True
    missing_keys = []
    found_keys = list(metrics.keys())
    
    for key in important_keys:
        val = metrics.get(key)
        status = "✅" if val is not None else "❌"
        if val is None: 
            all_present = False
            missing_keys.append(key)
        print(f"{status} {key}: {val}")
    
    if missing_keys:
        print(f"\nMissing Keys: {missing_keys}")
        print(f"Available keys (sample): {found_keys[:10]}")

    if len(metrics) >= 60:
        print("\n✅ COMPLIANCE: 60+ metrics found.")
    else:
        print(f"\n⚠️ WARNING: Only {len(metrics)} metrics found.")

    if all_present:
        print("✅ VERIFICATION SUCCESSFUL: All critical metrics present.")
    else:
        print("❌ VERIFICATION FAILED: Some metrics missing.")

if __name__ == "__main__":
    asyncio.run(verify_metrics())
