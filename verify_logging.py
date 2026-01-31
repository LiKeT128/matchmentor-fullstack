import sys
import os
import json

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.services.match_analyzer import MatchAnalyzer
from app.services.analysis_logger import AnalysisLogger

def test_diagnostic():
    print("Starting Diagnostic Test...")
    
    # Load sample data
    with open("backend/8648645713_opendota.json", "r") as f:
        parsed_data = json.load(f)
    
    # Run analysis for Luna
    analyzer = MatchAnalyzer()
    print("Running analyze_match for Luna...")
    result = analyzer.analyze_match(parsed_data, hero_name="npc_dota_hero_luna")
    
    # Check for analysis_logs
    if "analysis_logs" in result:
        logs = result["analysis_logs"]
        print("\n=== ANALYSIS LOGS SUMMARY ===")
        print(f"Match ID: {logs['match_id']}")
        print(f"Hero Name: {logs['hero_name']}")
        print(f"Total Duration: {logs['total_duration']:.4f}s")
        print("\n--- Data Sources ---")
        for comp, src in logs['data_sources'].items():
            print(f"{comp}: {src}")
            
        print("\n--- Full Analysis Trace ---")
        for i, entry in enumerate(logs['trace']):
            time_str = f"[{entry['timestamp']:.3f}s]"
            step_str = f"{entry['step']}".ljust(12)
            level_str = f"({entry['level']})".ljust(9)
            print(f"{time_str} {step_str} {level_str}: {entry['message']}")
            if entry.get('data'):
                # print data indented
                data_str = json.dumps(entry['data'], indent=4).replace('\n', '\n    ')
                print(f"    Data: {data_str}")
            
        print("\nDIAGNOSTIC SUCCESS: Logs correctly generated and integrated.")
    else:
        print("\nDIAGNOSTIC FAILURE: No analysis_logs found in result.")
        sys.exit(1)

if __name__ == "__main__":
    test_diagnostic()
