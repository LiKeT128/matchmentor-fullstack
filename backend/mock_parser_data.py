"""
Script to mock replay parser data from a JSON file for MatchAnalyzer testing.
This avoids the need for large .dem files during backend development.
"""
import json
import os
import sys
import logging
from pathlib import Path

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.services.match_analyzer import MatchAnalyzer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_mock_analysis(json_path: str, hero_name: str = None):
    """
    Load JSON parser output and run analysis.
    
    Args:
        json_path: Path to the Clarity/OpenDota JSON output file.
        hero_name: Optional hero name to analyze.
    """
    path = Path(json_path)
    if not path.exists():
        logger.error(f"File not found: {json_path}")
        return
    
    logger.info(f"Loading mock data from {json_path}...")
    with open(path, 'r', encoding='utf-8') as f:
        try:
            parsed_data = json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            return

    # Normalize structure if it's from Clarity JAR -- it might need a wrapper
    # Our analyzer expects a dict with 'players', 'heroes', etc.
    if isinstance(parsed_data, list) and len(parsed_data) > 0:
        # If it's just a list of players (some parsers do this)
        parsed_data = {"players": parsed_data}
    
    analyzer = MatchAnalyzer()
    
    logger.info(f"Running analysis for hero: {hero_name or 'first available'}...")
    try:
        results = analyzer.analyze_match(parsed_data, hero_name=hero_name)
        
        # Save results to a debug file
        output_path = path.with_name(f"analysis_{path.stem}.json")
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"✓ Analysis complete. Results saved to {output_path}")
        logger.info(f"Overall Score: {results.get('overall_score')}")
        
        return results
    except Exception as e:
        logger.exception(f"Analysis failed: {e}")
        return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python mock_parser_data.py <path_to_json> [hero_name]")
        sys.exit(1)
    
    target_json = sys.argv[1]
    target_hero = sys.argv[2] if len(sys.argv) > 2 else None
    
    run_mock_analysis(target_json, target_hero)
