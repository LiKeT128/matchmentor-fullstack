#!/usr/bin/env python3
"""
Test script to validate the MatchAnalyzer fixes.
"""

import sys
import os
sys.path.append('.')

from app.services.match_analyzer import MatchAnalyzer
from app.services.benchmark_service import benchmark_service

def create_test_data():
    """Create realistic test data for a Dota 2 match."""
    return {
        "duration_minutes": 35,
        "gpm": 520,
        "xpm": 580,
        "last_hits": 320,
        "denies": 25,
        "kills": 12,
        "deaths": 4,
        "assists": 8,
        "hero_damage": 35000,
        "tower_damage": 8500,
        "hero_healing": 2500,
        "net_worth": 18500,
        "position": "Safe Lane",
        "team": "radiant",
        "items": [
            "item_power_treads",
            "item_blink",
            "item_black_king_bar",
            "item_manta_style",
            "item_butterfly",
            "item_travel_boots"
        ],
        "item_timings": {
            "item_power_treads": 420,
            "item_blink": 780,
            "item_black_king_bar": 1320
        },
        "full_data": {
            "positions": [{"x": 1000, "y": 1000}] * 100,  # Sample positions
            "gold_t": [0] * 600 + [100] * 600 + [300] * 900,  # Sample gold timeline
            "last_hits_t": [0] * 600 + [50] * 600 + [200] * 900,  # Sample LH timeline
            "xp_t": [0] * 600 + [80] * 600 + [400] * 900,  # Sample XP timeline
        },
        "radiant_score": 28,
        "dire_score": 15,
        "hero_name": "npc_dota_hero_phantom_assassin"
    }

def test_metrics_calculation():
    """Test all metric categories with realistic data."""
    print("🧪 Testing MatchAnalyzer with realistic data...")
    
    analyzer = MatchAnalyzer()
    test_data = create_test_data()
    
    print(f"📊 Test Data: {test_data['hero_name']} - {test_data['position']}")
    print(f"   Duration: {test_data['duration_minutes']}min")
    print(f"   K/D/A: {test_data['kills']}/{test_data['deaths']}/{test_data['assists']}")
    print(f"   GPM/XPM: {test_data['gpm']}/{test_data['xpm']}")
    print()
    
    # Test each metric category
    categories = {
        "Basic": analyzer.calculate_gpm_xpm(test_data),
        "Positioning": analyzer.calculate_positioning_risk(test_data),
        "Fighting": analyzer.calculate_teamfight_stats(test_data),
        "Timing": analyzer.calculate_item_efficiency(test_data),
        "Warding": analyzer.calculate_warding_value(test_data),
        "Lane": analyzer.calculate_lane_metrics(test_data),
        "Mid Game": analyzer.calculate_midgame_metrics(test_data),
        "Late Game": analyzer.calculate_lategame_metrics(test_data)
    }
    
    total_metrics = 0
    non_zero_metrics = 0
    
    for category, metrics in categories.items():
        print(f"📈 {category} Metrics:")
        for key, value in metrics.items():
            total_metrics += 1
            if value != 0 and value is not None:
                non_zero_metrics += 1
            print(f"   {key}: {value}")
        print()
    
    print(f"📊 Summary:")
    print(f"   Total metrics calculated: {total_metrics}")
    print(f"   Non-zero metrics: {non_zero_metrics}")
    print(f"   Coverage: {non_zero_metrics/total_metrics*100:.1f}%")
    
    # Test full analysis
    print("\n🔬 Testing Full Analysis...")
    try:
        analysis = analyzer.analyze_match(test_data, hero_name="npc_dota_hero_phantom_assassin")
        
        print(f"✅ Overall Score: {analysis.get('overall_score', 'N/A')}")
        print(f"✅ Strengths: {len(analysis.get('strengths', []))}")
        print(f"✅ Weaknesses: {len(analysis.get('weaknesses', []))}")
        print(f"✅ Advice: {len(analysis.get('advice', []))}")
        print(f"✅ Power Spikes: {len(analysis.get('power_spikes', []))}")
        print(f"✅ Mistakes: {len(analysis.get('mistakes', []))}")
        
        if 'game_stages' in analysis:
            print(f"✅ Game Stages: {list(analysis['game_stages'].keys())}")
        
        print("\n🎉 Full analysis completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Full analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_benchmark_service():
    """Test benchmark service."""
    print("\n🧪 Testing Benchmark Service...")
    
    try:
        # Test with hero ID 1 (Anti-Mage)
        benchmarks = benchmark_service.get_hero_benchmarks_sync(1)
        print(f"✅ Benchmarks loaded: {type(benchmarks)}")
        
        # Test specific metric extraction
        gpm_75 = benchmark_service.get_benchmark_for_metric(benchmarks, 'gold_per_min', '75')
        print(f"✅ GPM 75th percentile: {gpm_75}")
        
        # Test pro item timing
        blink_timing = benchmark_service.get_pro_item_timing('blink')
        print(f"✅ Pro blink timing: {blink_timing}s")
        
        return True
        
    except Exception as e:
        print(f"❌ Benchmark service test failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting MatchMentor Metrics Validation\n")
    
    # Test benchmark service first
    benchmark_ok = test_benchmark_service()
    
    # Test metrics calculation
    metrics_ok = test_metrics_calculation()
    
    print("\n" + "="*50)
    print("🏁 FINAL RESULTS:")
    print(f"   Benchmark Service: {'✅ PASS' if benchmark_ok else '❌ FAIL'}")
    print(f"   Metrics Calculation: {'✅ PASS' if metrics_ok else '❌ FAIL'}")
    
    if benchmark_ok and metrics_ok:
        print("\n🎉 All tests passed! The MatchAnalyzer fixes are working.")
        sys.exit(0)
    else:
        print("\n⚠️  Some tests failed. Check the output above.")
        sys.exit(1)
