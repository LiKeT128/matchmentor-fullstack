"""
Test laning stage extraction with both OpenDota and Clarity formats.
Run: python test_laning_extraction.py
"""

import asyncio
import logging
import json
import sys
import os

sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.services.stage_extractors import LaningStageExtractor
from app.services.stage_constants import get_position
from app.services.opendota_client import OpenDotaClient

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def test_opendota_mode():
    """Test extraction with real OpenDota data."""
    print("\n" + "="*80)
    print("TEST 1: OPENDOTA MODE (Real Match Data)")
    print("="*80 + "\n")
    
    # Fetch real match
    match_id = "8641028604"  # Muerta match
    client = OpenDotaClient()
    
    print(f"Fetching match {match_id} from OpenDota...")
    match_data = await client.get_match(match_id)
    
    if not match_data:
        print("❌ Failed to fetch match")
        return
    
    # Get first player (Muerta)
    players = match_data.get('players', [])
    if not players:
        print("❌ No players found")
        return
    
    player_0 = players[0]
    hero_name = player_0.get('hero_name', 'Unknown')
    player_slot = player_0.get('player_slot', 0)
    position = get_position(player_slot)
    
    print(f"Analyzing: {hero_name} (Position {position})")
    print(f"Player slot: {player_slot}\n")
    
    # Extract laning stage
    extractor = LaningStageExtractor(player_0, position)
    result = extractor.extract()
    
    # Print results
    print("\n📊 SNAPSHOTS:")
    for snap in result.snapshots:
        print(f"  {snap['minute']}m: Gold={snap['gold']}, LH={snap['last_hits']}, Level={snap['level']}")
    
    print("\n📋 EVENTS:")
    for event in result.events[:10]:  # First 10 events
        print(f"  {event['minute']:.1f}m: {event['type'].upper()} - {event.get('item', 'N/A')}")
    print(f"  ... (total {len(result.events)} events)")
    
    print("\n📈 METRICS:")
    for key, value in sorted(result.metrics.items()):
        print(f"  {key}: {value}")
    
    print(f"\n⭐ PERFORMANCE SCORE: {result.performance_score}%")
    print(f"🔧 DATA SOURCE: {result.data_source}")
    
    print("\n💡 ADVICE:")
    for adv in result.advice:
        print(f"  - {adv}")
    
    print("\n" + "="*80)
    print("✅ OPENDOTA TEST COMPLETED")
    print("="*80)
    
    return result


def test_clarity_mode():
    """Test extraction with sample Clarity-style data."""
    print("\n" + "="*80)
    print("TEST 2: CLARITY MODE (Sample Time-Series Data)")
    print("="*80 + "\n")
    
    # Sample Clarity-style data
    sample_player_data = {
        'hero': 'Anti-Mage',
        'player_slot': 0,
        'team': 'radiant',
        'gold_t': {
            '0': 625,
            '1': 750,
            '5': 1550,
            '10': 2650
        },
        'xp_t': {
            '0': 0,
            '1': 250,
            '5': 1250,
            '10': 3200
        },
        'lh_t': {
            '0': 0,
            '1': 2,
            '5': 15,
            '10': 45
        },
        'kills': [],
        'deaths': [],
        'assists': []
    }
    
    position = 1  # Carry
    print(f"Analyzing: Anti-Mage (Position {position})")
    print("Using sample Clarity time-series data\n")
    
    # Extract laning stage
    extractor = LaningStageExtractor(sample_player_data, position)
    result = extractor.extract()
    
    # Print results
    print(f"\n🔧 DATA SOURCE: {result.data_source}")
    print(f"📝 NOTE: {result.metrics.get('note', 'N/A')}")
    
    print("\n💡 ADVICE:")
    for adv in result.advice:
        print(f"  - {adv}")
    
    print("\n" + "="*80)
    print("✅ CLARITY TEST COMPLETED (Stub)")
    print("="*80)
    
    return result


async def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("LANING STAGE EXTRACTOR - HYBRID MODE TESTS")
    print("="*80)
    
    # Test 1: OpenDota mode
    opendota_result = await test_opendota_mode()
    
    # Test 2: Clarity mode (stub)
    clarity_result = test_clarity_mode()
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"\n✅ OpenDota Mode: {opendota_result.performance_score}% score")
    print(f"   - Data source: {opendota_result.data_source}")
    print(f"   - Metrics count: {len(opendota_result.metrics)}")
    print(f"   - Events count: {len(opendota_result.events)}")
    print(f"   - Advice count: {len(opendota_result.advice)}")
    
    print(f"\n⚠️  Clarity Mode: {clarity_result.performance_score}% score (stub)")
    print(f"   - Data source: {clarity_result.data_source}")
    print(f"   - Status: Not yet implemented")
    
    print("\n" + "="*80)
    print("ALL TESTS COMPLETED")
    print("="*80 + "\n")


if __name__ == '__main__':
    asyncio.run(main())
