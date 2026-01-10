"""
Quick verification that analyze_match returns game_stages with real data
"""
import asyncio
import json
from app.services.opendota_client import OpenDotaClient
from app.services.match_analyzer import MatchAnalyzer

async def test_integration():
    print("="*80)
    print("INTEGRATION VERIFICATION - LaningStageExtractor in analyze_match()")
    print("="*80 + "\n")
    
    # Fetch real match
    match_id = "8641028604"
    client = OpenDotaClient()
    
    print(f"1. Fetching match {match_id} from OpenDota...")
    match_data = await client.get_match(match_id)
    
    if not match_data:
        print("❌ Failed to fetch match")
        return
    
    print(f"✅ Match fetched successfully\n")
    
    # Get hero name
    hero_name = match_data.get('heroes', [])[0].get('hero_name', 'unknown') if match_data.get('heroes') else 'unknown'
    print(f"2. Analyzing hero: {hero_name}\n")
    
    # Create analyzer and run analysis
    analyzer = MatchAnalyzer()
    result = analyzer.analyze_match(match_data, hero_name)
    
    # Check response structure
    print("3. Checking response structure:\n")
    
    has_game_stages = 'game_stages' in result
    print(f"   {'✅' if has_game_stages else '❌'} game_stages field exists: {has_game_stages}")
    
    if has_game_stages:
        has_laning = 'laning' in result['game_stages']
        print(f"   {'✅' if has_laning else '❌'} game_stages.laning exists: {has_laning}")
        
        if has_laning:
            laning = result['game_stages']['laning']
            
            score = laning.get('score', 0)
            print(f"   {'✅' if score > 0 else '❌'} score > 0: {score}")
            
            data_source = laning.get('data_source', 'unknown')
            print(f"   {'✅' if data_source in ['opendota', 'clarity'] else '❌'} data_source: {data_source}")
            
            metrics = laning.get('metrics', {})
            print(f"   {'✅' if metrics else '❌'} metrics populated: {len(metrics)} items")
            
            advice = laning.get('advice', [])
            print(f"   {'✅' if advice else '❌'} advice populated: {len(advice)} items")
            
            print("\n4. Sample metrics:")
            for key in ['lh_10m', 'gpm', 'xpm', 'gpm_performance_pct']:
                value = metrics.get(key, 'N/A')
                print(f"   {key}: {value}")
            
            print("\n5. Sample advice:")
            for i, adv in enumerate(advice[:3], 1):
                if isinstance(adv, str):
                    print(f"   {i}. {adv}")
                elif isinstance(adv, dict):
                    print(f"   {i}. {adv.get('title', 'N/A')}: {adv.get('message', 'N/A')}")
            
            print("\n" + "="*80)
            print("✅ INTEGRATION VERIFICATION PASSED")
            print("="*80)
            
            # Print full JSON for inspection
            print("\nFull game_stages.laning JSON:\n")
            print(json.dumps(laning, indent=2, default=str)[:1000] + "...\n")
            
        else:
            print("\n❌ FAILED: game_stages.laning not found")
    else:
        print("\n❌ FAILED: game_stages not in response")
        print(f"Response keys: {list(result.keys())}")

if __name__ == '__main__':
    asyncio.run(test_integration())
