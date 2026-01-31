import sys
import os
import json
import subprocess
import time
import asyncio

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.services.clarity_parser import ClarityParser
from app.services.match_analyzer import MatchAnalyzer

async def run_real_analysis(demo_name, hero_name=None):
    print(f"--- STARTING REAL CLARITY PARSING TEST: {demo_name} ---")
    
    # Use the absolute path to the demo in the backend folder
    demo_path = os.path.abspath(os.path.join("backend", demo_name))
    
    print(f"Using demo at: {demo_path}")
    
    start_parse = time.time()
    try:
        # Use our robust official service which handles the space-in-path workaround correctly!
        parsed_data = ClarityParser.parse_demo_file(demo_path)
        print(f"✓ Clarity parsing finished in {time.time() - start_parse:.2f}s")
        
    except Exception as e:
        print(f"ERROR: Parsing failed: {e}")
        return

    # 3. Detect heroes in the match
    players = parsed_data.get("players", [])
    if not players:
        print("ERROR: No players found in parsed data!")
        return
        
    print(f"\nFound {len(players)} players in match:")
    for p in players:
        p_hero = p.get("hero_name") or p.get("unit", "Unknown")
        print(f" - {p_hero}")

    # 4. Analyze first hero if none specified
    if not hero_name and players:
        hero_player = players[0]
        hero_name = hero_player.get("hero_name")
        print(f"\nNo hero specified, picking {hero_name} for analysis...")

    # 5. Run MatchAnalyzer
    print(f"\n--- ANALYZING HERO: {hero_name} ---")
    analyzer = MatchAnalyzer()
    
    analysis_result = analyzer.analyze_match(parsed_data, hero_name=hero_name)

    # 6. Show Results
    if analysis_result:
        print(f"\n=== ANALYSIS SUCCESS FOR {hero_name} ===")
        print(f"Overall Score: {analysis_result.get('overall_score')}")
        
        metrics = analysis_result.get('metrics', {})
        if metrics:
            basic = metrics.get('basic_stats', {})
            print(f"Kills/Deaths/Assists: {basic.get('kills')}/{basic.get('deaths')}/{basic.get('assists')}")
            print(f"GPM: {basic.get('gpm')}, XPM: {basic.get('xpm')}")
            
        print("\n✓ SUCCESS: Match data extracted and analyzed!")
    else:
        print("\nERROR: Analysis failed or returned empty.")


if __name__ == "__main__":
    demo_to_test = "8642447925.dem"
    # Set event loop for the async caller if needed, 
    # but the logic above is sync except for the wrapper call
    asyncio.run(run_real_analysis(demo_to_test))
