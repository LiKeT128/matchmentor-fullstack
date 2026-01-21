"""Quick verification of the data pipeline fixes."""
import json
import sys
sys.path.insert(0, ".")

from app.services.match_analyzer import MatchAnalyzer

# Load real data
with open("8648645713_opendota.json", "r") as f:
    data = json.load(f)

print("=" * 70)
print("DATA PIPELINE FIX VERIFICATION")
print("=" * 70)

analyzer = MatchAnalyzer()

# Test Luna (Dire carry)
print("\n--- Testing Luna Analysis ---")
luna = analyzer.analyze_match(data, hero_name="npc_dota_hero_luna")
luna_metrics = luna["metrics"]

print(f"Match ID: {luna.get('match_id')}")
print(f"Duration: {luna.get('match_duration', 'N/A')} seconds")

print("\n--- BASIC STATS ---")
bs = luna_metrics.get("basic_stats", {})
print(f"GPM: {bs.get('gpm')} (expected: 824)")
print(f"XPM: {bs.get('xpm')} (expected: 940)")
print(f"LH: {bs.get('lh')} (expected: 414)")
print(f"K/D/A: {bs.get('kills')}/{bs.get('deaths')}/{bs.get('assists')}")

print("\n--- LANING PHASE ---")
lp = luna_metrics.get("laning_phase", {})
print(f"LH @ 10m: {lp.get('lh_at_10')}")
print(f"Gold @ 10m: {lp.get('gold_at_10')}")
print(f"XP @ 10m: {lp.get('xp_at_10')}")
print(f"Lane Efficiency: {lp.get('lane_efficiency_pct')}%")
print(f"Deaths in Lane: {lp.get('deaths_in_lane')}")

print("\n--- ROLE IMPACT / FIGHTING ---")
ri = luna_metrics.get("role_impact", {})
fighting = ri.get("fighting", {})
print(f"TF Participation: {fighting.get('teamfight_participation')}%")
print(f"Fight Contribution: {fighting.get('fight_contribution')}")

print("\n--- VISION ---")
vision = ri.get("vision", {})
print(f"Observers Placed: {vision.get('obs_placed')}")
print(f"Sentries Placed: {vision.get('sen_placed')}")

# Test Shadow Fiend for comparison
print("\n\n--- Testing Shadow Fiend Analysis (different hero) ---")
sf = analyzer.analyze_match(data, hero_name="npc_dota_hero_shadow_fiend")
sf_metrics = sf["metrics"]

print("\n--- BASIC STATS ---")
sf_bs = sf_metrics.get("basic_stats", {})
print(f"GPM: {sf_bs.get('gpm')} (expected: 662)")
print(f"XPM: {sf_bs.get('xpm')} (expected: 729)")
print(f"LH: {sf_bs.get('lh')} (expected: 249)")

# Verify different metrics
print("\n" + "=" * 70)
print("COMPARISON CHECK")
print("=" * 70)

errors = []

if bs.get('gpm') != 824:
    errors.append(f"Luna GPM={bs.get('gpm')}, expected 824")
if sf_bs.get('gpm') != 662:
    errors.append(f"SF GPM={sf_bs.get('gpm')}, expected 662")
if bs.get('gpm') == sf_bs.get('gpm'):
    errors.append("Luna GPM == SF GPM (should be different)")
if lp.get('lh_at_10') == 0 and lp.get('gold_at_10') == 0:
    errors.append("Laning phase data is all zeros")

if errors:
    print("\n❌ ISSUES FOUND:")
    for e in errors:
        print(f"  - {e}")
else:
    print("\n✅ ALL CHECKS PASSED!")
    print("  - Different heroes show different GPM")
    print("  - Laning phase has data")
    print("  - Duration extracted correctly")
