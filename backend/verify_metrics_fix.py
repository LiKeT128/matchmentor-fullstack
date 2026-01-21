"""Quick verification script to test metrics fixes."""
import json
import sys
sys.path.insert(0, ".")

from app.services.match_analyzer import MatchAnalyzer

# Load real data
with open("8648645713_opendota.json", "r") as f:
    data = json.load(f)

print("=" * 60)
print("METRICS FIX VERIFICATION")
print("=" * 60)

analyzer = MatchAnalyzer()

# Test Luna
luna = analyzer.analyze_match(data, hero_name="npc_dota_hero_luna")
luna_metrics = luna["metrics"]

# Test Shadow Fiend
sf = analyzer.analyze_match(data, hero_name="npc_dota_hero_shadow_fiend")
sf_metrics = sf["metrics"]

print("\n--- BASIC STATS ---")
print(f"Luna GPM: {luna_metrics['basic_stats']['gpm']} (expected: 824)")
print(f"SF GPM:   {sf_metrics['basic_stats']['gpm']} (expected: 662)")
print(f"Luna LH:  {luna_metrics['basic_stats']['lh']} (expected: 414)")
print(f"SF LH:    {sf_metrics['basic_stats']['lh']} (expected: 249)")

# Check if metrics are different
gpm_diff = luna_metrics['basic_stats']['gpm'] != sf_metrics['basic_stats']['gpm']
print(f"\n✓ Different GPM: {gpm_diff}")

# Check team kills
fighting = luna_metrics.get("role_impact", {}).get("fighting", {})
team_kills = fighting.get("team_kills")
print(f"\n--- TEAMFIGHT ---")
print(f"Team kills (Dire): {team_kills} (expected: 32, was hardcoded 40)")
print(f"TF Participation: {fighting.get('teamfight_participation')}%")

# Check laning
laning = luna_metrics.get("laning_phase", {})
print(f"\n--- LANING PHASE ---")
print(f"LH at 10: {laning.get('lh_at_10')}")
print(f"Gold at 10: {laning.get('gold_at_10')}")
print(f"XP at 10: {laning.get('xp_at_10')}")

# Check advanced metrics for placeholders
print(f"\n--- ADVANCED METRICS (checking for placeholders) ---")
pos_risk = luna_metrics.get("positioning_risk", {})
rotation = pos_risk.get("rotation_timing")
print(f"rotation_timing: {rotation} (was hardcoded 75.0)")

decision = luna_metrics.get("decision_quality", {})
recovery = decision.get("recovery_prowess")
print(f"recovery_prowess: {recovery} (was hardcoded 70.0)")

psych = luna_metrics.get("psychological_profile", {})
consistency = psych.get("consistency_score")
print(f"consistency_score: {consistency} (was hardcoded 78.0)")

# Check gold efficiency
items = luna_metrics.get("role_impact", {}).get("items", {})
gold_eff = items.get("gold_efficiency")
print(f"gold_efficiency: {gold_eff} (was hardcoded 90)")

print("\n" + "=" * 60)
print("VERIFICATION COMPLETE")
print("=" * 60)

# Summary
errors = []
if luna_metrics['basic_stats']['gpm'] != 824:
    errors.append(f"Luna GPM mismatch: {luna_metrics['basic_stats']['gpm']}")
if sf_metrics['basic_stats']['gpm'] != 662:
    errors.append(f"SF GPM mismatch: {sf_metrics['basic_stats']['gpm']}")
if not gpm_diff:
    errors.append("GPM values are identical (placeholder issue)")
if team_kills == 40:
    errors.append("Team kills still hardcoded to 40")
if rotation == 75.0:
    errors.append("rotation_timing still hardcoded to 75.0")
if recovery == 70.0:
    errors.append("recovery_prowess still hardcoded to 70.0")
if consistency == 78.0:
    errors.append("consistency_score still hardcoded to 78.0")
if gold_eff == 90:
    errors.append("gold_efficiency still hardcoded to 90")

if errors:
    print("\n❌ ISSUES FOUND:")
    for e in errors:
        print(f"  - {e}")
else:
    print("\n✅ ALL CHECKS PASSED!")
