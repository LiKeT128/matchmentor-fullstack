import asyncio
import json
import os
import sys

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

import logging
logging.basicConfig(level=logging.INFO)

from app.services.opendota_client import OpenDotaClient
from app.services.match_analyzer import MatchAnalyzer

async def verify_metrics():
    match_id = "8641028604" # Muerta Match
    client = OpenDotaClient()
    analyzer = MatchAnalyzer()
    
    print(f"Fetching match {match_id} from OpenDota...")
    match_data = await client.get_match(match_id)
    
    if not match_data:
        print("Failed to fetch match data.")
        return

    # Muerta is hero_id 138
    muerta_hero_name = "npc_dota_hero_muerta"
    
    print(f"Heroes in match: {[h.get('hero_name') for h in match_data.get('heroes', [])]}")
    
    print(f"Analyzing match for {muerta_hero_name}...")
    
    analysis = analyzer.analyze_match(match_data, hero_name=muerta_hero_name)
    metrics = analysis["metrics"]
    
    print("\n--- METRICS VERIFICATION (MUERTA) ---")
    print(f"Total Metrics Count: {len(metrics)}")
    
    important_keys = ["lh_at_10", "gold_at_10", "vision_score", "position_safety_score", "gpm"]
    print("---RESULTS_START---")
    for key in important_keys:
        print(f"{key}: {metrics.get(key)}")
    print("---RESULTS_END---")

if __name__ == "__main__":
    asyncio.run(verify_metrics())
