import sys
import os
import json
import subprocess
import time
import asyncio

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.services.match_analyzer import MatchAnalyzer

async def run_real_analysis(demo_name, hero_name=None):
    print(f"--- STARTING REAL CLARITY PARSING TEST: {demo_name} ---")
    
    # Workaround for space in path "My Projects" on Windows
    # Clarity/Snappy fails if the path contains spaces
    temp_work_dir = "C:\\mm-test"
    if not os.path.exists(temp_work_dir):
        os.makedirs(temp_work_dir)
        
    jar_source = "backend/clarity.jar"
    demo_source = os.path.join("backend", demo_name)
    
    jar_dest = os.path.join(temp_work_dir, "clarity.jar")
    demo_dest = os.path.join(temp_work_dir, demo_name)
    json_dest = demo_dest + ".json"
    
    print(f"Copying files to {temp_work_dir} (workspace workaround)...")
    import shutil
    shutil.copy2(jar_source, jar_dest)
    shutil.copy2(demo_source, demo_dest)
    
    if os.path.exists(json_dest):
        os.remove(json_dest)

    # 1. Run Clarity JAR
    print(f"Executing Clarity JAR on {demo_name}...")
    start_parse = time.time()
    try:
        # Run from temp dir
        result = subprocess.run(
            ["java", "-Xmx2G", "-jar", "clarity.jar", demo_name, "--json"],
            cwd=temp_work_dir,
            capture_output=True,
            text=True,
            timeout=300 
        )
        
        if result.returncode != 0:
            print(f"ERROR: Clarity failed with return code {result.returncode}")
            # print first 500 chars of stderr
            print(f"Stderr: {result.stderr[:500]}")
            return
            
        print(f"✓ Clarity parsing finished in {time.time() - start_parse:.2f}s")
        
    except subprocess.TimeoutExpired:
        print("ERROR: Clarity timed out after 300s")
        return
    except Exception as e:
        print(f"ERROR: Unexpected error: {e}")
        return

    # 2. Load the JSON
    if not os.path.exists(json_dest):
        print(f"ERROR: Output JSON {json_dest} not found!")
        return
        
    print(f"Loading {json_dest}...")
    with open(json_dest, 'r', encoding='utf-8') as f:
        parsed_data = json.load(f)

    # 3. Detect heroes in the match
    players = parsed_data.get("players", [])
    print(f"\nFound {len(players)} players in match:")
    for p in players:
        p_hero = p.get("hero") or p.get("hero_name") or p.get("unit", "Unknown")
        print(f" - {p_hero}")

    # 4. Analyze first hero if none specified
    if not hero_name and players:
        hero_player = players[0]
        hero_name = hero_player.get("hero") or hero_player.get("hero_name") or hero_player.get("unit")
        print(f"\nNo hero specified, picking {hero_name} for analysis...")

    # 5. Run MatchAnalyzer
    print(f"\n--- ANALYZING HERO: {hero_name} ---")
    analyzer = MatchAnalyzer()
    # Mock some basic match info since Clarity JSON might be missing epilogue
    if "match_id" not in parsed_data or not parsed_data["match_id"]:
        parsed_data["match_id"] = demo_name.split(".")[0]
        
    analysis_result = analyzer.analyze_match(parsed_data, hero_name=hero_name)

    # 6. Show the Trace
    if "analysis_logs" in analysis_result:
        logs = analysis_result["analysis_logs"]
        print(f"\n=== ANALYSIS TRACE FOR {hero_name} ===")
        print(f"Match ID: {logs['match_id']}")
        print(f"Total Duration: {logs['total_duration']:.4f}s")
        
        print("\n--- Technical Log (Step by Step) ---")
        for entry in logs['trace']:
            time_mark = f"[{entry['timestamp']:.3f}s]"
            step = f"{entry['step']}".ljust(12)
            msg = entry['message']
            print(f"{time_mark} {step}: {msg}")
            if entry.get("data"):
                # Simplified data print: only first 3 keys to avoid bloat
                data_keys = list(entry["data"].keys())
                keys_str = ", ".join(data_keys[:5])
                if len(data_keys) > 5: keys_str += "..."
                print(f"    Data: {keys_str} -> {entry['data'][data_keys[0]]}")
        
        print("\n--- Data Source Summary ---")
        for comp, src in logs['data_sources'].items():
            print(f" - {comp}: {src}")
            
        print("\n✓ SUCCESS: Real Clarity data extracted and analyzed!")
    else:
        print("\nERROR: No analysis_logs found in result.")

if __name__ == "__main__":
    demo_to_test = "8642447925.dem"
    # Set event loop for the async caller if needed, 
    # but the logic above is sync except for the wrapper call
    asyncio.run(run_real_analysis(demo_to_test))
