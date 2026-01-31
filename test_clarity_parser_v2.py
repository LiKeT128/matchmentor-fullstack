import asyncio
import os
import sys
import logging
from pathlib import Path

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.services.clarity_parser import ClarityParser
from app.services.match_analyzer import MatchAnalyzer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_parsing():
    demo_path = r"c:\mm-test\8642447925.dem"
    
    print(f"--- TESTING CLARITY PARSER V2 ---")
    print(f"File: {demo_path}")
    
    try:
        # Use our new robust parser
        parsed_data = ClarityParser.parse_demo_file(demo_path)
        
        print("\n--- PARSE SUCCESS ---")
        print(f"Match ID: {parsed_data.get('match_id')}")
        print(f"Players found: {len(parsed_data.get('players', []))}")
        
        # Test analysis with MatchAnalyzer
        analyzer = MatchAnalyzer()
        hero_name = parsed_data['players'][0]['hero_name']
        print(f"Analyzing hero: {hero_name}")
        
        analysis = analyzer.analyze_match(parsed_data, hero_name=hero_name)
        
        print(f"Analysis Object type: {type(analysis)}")
        print(f"Analysis keys: {analysis.keys() if analysis else 'None'}")
        
        if not analysis:
            print("CRITICAL: MatchAnalyzer returned None!")
            return

        print("\n--- ANALYSIS SUCCESS ---")
        print(f"Overall Score: {analysis.get('overall_score')}")
        
        metrics = analysis.get('metrics')
        if metrics:
            basic = metrics.get('basic_stats', {})
            print(f"Kills: {basic.get('kills')}")
            print(f"Deaths: {basic.get('deaths')}")
            print(f"Assists: {basic.get('assists')}")
            print(f"GPM: {basic.get('gpm')}")
            
            laning = metrics.get('laning_phase', {})
            print(f"Laning LH@10: {laning.get('lh_10m')}")
            print(f"Laning Score: {laning.get('performance_score')}%")
        else:
            print("WARNING: Metrics object is None/Missing")
        
    except Exception as e:
        print(f"\n--- TEST FAILED ---")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_parsing()
