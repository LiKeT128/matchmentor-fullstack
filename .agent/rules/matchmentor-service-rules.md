---
trigger: always_on
---

# 🎯 MatchMentor: CRITICAL RULES FOR ANTIGRAVITY

**Version:** 2.0 MVP-Ready  
**Date:** January 17, 2026  
**Purpose:** These 15 CRITICAL Rules ensure Antigravity makes ZERO mistakes when parsing Dota 2 replays

---

## ⚠️ THESE RULES ARE MANDATORY FOR ALL TASKS

Antigravity MUST follow these rules for EVERY match analysis, EVERY metric calculation, EVERY API call.

---

## RULE #1: DATA SOURCES (CRITICAL)

**Where to get EVERY piece of data:**

### Heroes (all heroes in game)
- **Source:** OpenDota API
- **Endpoint:** `https://api.opendota.com/api/heroes`
- **Rate Limit:** 60 requests/minute
- **Format:** JSON with `id`, `name`, `localized_name`, `roles`
- **How to use:** Build hero_id → hero_name mapping at startup
- **Never:** Hardcode hero names, use cached data, guess IDs

### Items (all items in game)
- **Source:** OpenDota API
- **Endpoint:** `https://api.opendota.com/api/constants/items`
- **Rate Limit:** 60 requests/minute
- **Format:** JSON with `id`, `name`, `cost`, `type`
- **How to use:** Build item_id → item_name mapping at startup
- **Never:** Hardcode item names, use old data

### Hero Icons (for UI)
- **Source:** jsDelivr CDN (always up-to-date)
- **URL Pattern:** `https://cdn.jsdelivr.net/gh/dotabuff/d2vpk@master/resources/images/heroes/{hero_name}_vert.jpg`
- **Fallback:** If 404, use `https://via.placeholder.com/256x144?text={hero_name}`
- **Never:** Use hardcoded URLs, old CDNs, or guess paths

### Item Icons (for UI)
- **Source:** jsDelivr CDN
- **URL Pattern:** `https://cdn.jsdelivr.net/gh/dotabuff/d2vpk@master/resources/images/items/{item_name}.png`
- **Fallback:** If 404, use `https://via.placeholder.com/64x64?text={item_name}`
- **Never:** Use hardcoded URLs, old CDNs, guess paths

### Match Data
- **Source:** Clarity Parser (Java subprocess)
- **File:** `clarity-3.2.0.jar`
- **How to run:** `java -jar clarity-3.2.0.jar replay.dem` (timeout: 300 seconds)
- **Output:** JSON with all events, player stats, item purchases, ability casts
- **Never:** Hardcode match data, cache results without validation

### Benchmarks & Stats
- **Source:** OpenDota API
- **Endpoint:** `https://api.opendota.com/api/explorer?query=SELECT * FROM matches WHERE hero_id = {hero_id} LIMIT 100`
- **What:** Average GPM/XPM/K/D/A for hero by MMR bracket
- **Never:** Use outdated benchmarks, hardcode stats

---

## RULE #2: ACCURACY & PRECISION (CRITICAL)

**All calculations must be EXACT. No approximations. No rounding errors.**

### For all metrics:
- ✅ Use precise formulas (no guessing)
- ✅ Validate all calculations
- ✅ Compare with expected ranges
- ✅ Log all calculations
- ❌ Never approximate
- ❌ Never round until final display

### Example - GPM (Gold Per Minute):
```python
# ✅ CORRECT:
gold_earned = sum(player.gold_gained_events)
match_duration_minutes = match.duration / 60
gpm = gold_earned / match_duration_minutes

# ❌ WRONG:
gpm = random_guess()  # NO!
gpm = hero_benchmark  # NO! (use for comparison, not calculation)
```

### Validation:
- All metrics must be >= 0
- K/D/A must be integers
- GPM/XPM typically: 200-800
- If outside range: investigate, don't ignore

---

## RULE #3: ERROR HANDLING (CRITICAL)

**Every operation must have error handling. No silent failures.**

### For match parsing:
```python
try:
    clarity_output = run_clarity_parser(replay_path)
    if not clarity_output:
        raise ValueError("Clarity parser returned empty output")
    
    # Parse each hero
    for hero_id in match.hero_ids:
        try:
            metrics = calculate_hero_metrics(clarity_output, hero_id)
        except Exception as e:
            logger.error(f"Failed to calculate metrics for hero {hero_id}: {e}")
            metrics = None  # or return partial metrics
    
except TimeoutError:
    return {"error": "Parser timeout (>300s)", "status": "timeout"}
except Exception as e:
    logger.error(f"Critical error: {e}")
    return {"error": str(e), "status": "error"}
```

### User-facing errors:
- Clear message in English
- Suggest action (retry, contact support)
- Never show stack traces
- Log full error server-side

---

## RULE #4: TECHNOLOGY STACK (CRITICAL)

**Use ONLY these exact versions (as of 2026):**

### Backend:
- Python: 3.11+ (latest stable)
- FastAPI: 0.104+
- SQLAlchemy: 2.0+
- PostgreSQL: 15+
- Pydantic: 2.0+
- pytest: 7.4+

### Frontend:
- Node: 18+ (latest stable)
- React: 18+
- TypeScript: 5.2+
- Vite: 5.0+
- Tailwind CSS: 3.3+
- axios: 1.6+

### Deployment:
- Python: 3.11.6+ (Railway)
- Node: 18.18+ (Vercel)
- PostgreSQL: 15+ (Railway)

### Parser:
- Java: 11+ (Clarity)
- Clarity: 3.2.0 (exact version)

### External APIs:
- OpenDota: Latest (no version pinning)
- Stripe: 2024+ API version
- SendGrid: v3 API

---

## RULE #5: HERO PARSING (CRITICAL)

**Parse EACH hero's actions separately and COMPLETELY:**

### For each hero in match:
```python
def parse_hero_complete(replay_path, hero_id):
    """Extract ALL data for ONE hero from replay"""
    
    # 1. Basic stats
    kills = sum(1 for event in events if event['type'] == 'kills' and event['player_id'] == hero_id)
    deaths = sum(1 for event in events if event['type'] == 'deaths' and event['player_id'] == hero_id)
    assists = sum(1 for event in events if event['type'] == 'assists' and event['player_id'] == hero_id)
    
    # 2. Items (with TIMING)
    items = [
        {
            'item_id': event['item_id'],
            'item_name': item_name(event['item_id']),
            'time_purchased': event['timestamp'],
            'gold_spent': item_cost(event['item_id']),
        }
        for event in events if event['type'] == 'item_purchase' and event['player_id'] == hero_id
    ]
    
    # 3. Lane phase (0-10 min)
    lane_events = [e for e in events if e['timestamp'] <= 600 and e['player_id'] == hero_id]
    lane_lh = sum(1 for e in lane_events if e['type'] == 'last_hit')
    lane_denies = sum(1 for e in lane_events if e['type'] == 'deny')
    
    # 4. Mid game (10-25 min)
    mid_events = [e for e in events if 600 < e['timestamp'] <= 1500 and e['player_id'] == hero_id]
    mid_kills = sum(1 for e in mid_events if e['type'] == 'kills')
    
    # 5. Late game (25+ min)
    late_events = [e for e in events if e['timestamp'] > 1500 and e['player_id'] == hero_id]
    late_positioning = analyze_positioning(late_events)
    
    return {
        'hero_id': hero_id,
        'basic': {'k': kills, 'd': deaths, 'a': assists},
        'items': items,
        'lane_phase': {'lh': lane_lh, 'denies': lane_denies},
        'mid_game': {'kills': mid_kills},
        'late_game': {'positioning': late_positioning},
    }
```

### Never:
- ❌ Approximate hero data
- ❌ Skip heroes (parse ALL)
- ❌ Reuse data from other heroes
- ❌ Cache without validation

---

## RULE #6: 60+ METRICS (CRITICAL)

**Calculate ALL 60+ metrics for EACH hero. No skipping.**

### Group 1: Basic Stats (8 metrics)
1. Kills
2. Deaths
3. Assists
4. K/D/A Ratio
5. GPM (Gold Per Minute)
6. XPM (Experience Per Minute)
7. Last Hits (LH)
8. Denies

### Group 2: Damage & Healing (6 metrics)
9. Total Damage to Heroes
10. Damage Per Minute
11. Total Healing to Allies
12. Healing Per Minute
13. Damage Taken
14. Damage Reduction %

### Group 3: Item Analysis (8 metrics)
15. Item Efficiency (Gold Value / Items Sold)
16. First Major Item Timing (seconds)
17. Second Major Item Timing
18. Luxury Item Count
19. Core Item Count
20. Wasted Item Slots %
21. Item Build Accuracy (vs benchmark)
22. Item Timings vs Optimal

### Group 4: Lane Phase (7 metrics, 0-10 min)
23. Last Hits
24. Denies
25. CS Per Minute (Lane Phase)
26. Kill Participation %
27. Lane Pressure (pushing vs defensive)
28. Deaths in Lane
29. Solo Kill Potential

### Group 5: Mid Game (8 metrics, 10-25 min)
30. Team Fight Participation %
31. Mid Game Kills
32. Mid Game Deaths
33. Farming Efficiency
34. Map Presence Score
35. Objective Contribution %
36. Risk Taking Score
37. Positioning Quality Score

### Group 6: Late Game (7 metrics, 25+ min)
38. Late Game K/D/A
39. High Ground Defense Performance
40. Buyback Usage Efficiency
41. Position in Team Fights
42. Carry Reliability %
43. Mega Creep Defense
44. Game Closing Efficiency

### Group 7: Positioning & Movement (6 metrics)
45. Distance from Team Average
46. Position in Fights (Front/Mid/Back %)
47. Farming Location Safety Score
48. Gank Vulnerability Score
49. Map Awareness Score
50. Warding Coverage %

### Group 8: Warding & Vision (5 metrics)
51. Wards Placed
52. Wards Destroyed
53. Deward Count
54. Vision Score
55. Observer/Sentry Ratio

### Group 9: Comparison vs Benchmarks (9 metrics)
56. GPM vs Hero Average
57. XPM vs Hero Average
58. K/D/A vs Hero Average
59. LH vs Hero Average
60. Win Rate Contribution
61. Performance Rating (1-100)
62. Tier Rating (S/A/B/C/D)
63. Strengths List
64. Weaknesses List

### Group 10: Advice & Tips (5+ metrics)
65. Top 3 Mistakes
66. Top 3 Improvements
67. Item Build Feedback
68. Positioning Recommendations
69. Playstyle Analysis

---

## RULE #7: EARLY/MID/LATE BREAKDOWN (CRITICAL)

**ALWAYS break down metrics by game phase:**

```python
def analyze_by_phase(match_duration):
    """Define phases based on actual match duration"""
    
    if match_duration < 600:  # Game ended before 10 min
        phases = {
            'early': (0, match_duration),
        }
    elif match_duration < 1500:  # Game ended before 25 min
        phases = {
            'early': (0, 600),
            'mid': (600, match_duration),
        }
    else:  # Normal game
        phases = {
            'early': (0, 600),       # 0-10 min
            'mid': (600, 1500),      # 10-25 min
            'late': (1500, float('inf')),  # 25+ min
        }
    
    return phases
```

### For EACH phase, calculate:
- K/D/A
- GPM/XPM
- LH/Denies
- Item purchases
- Position changes
- Deaths
- Mistakes

---

## RULE #8: API RESPONSE FORMAT (CRITICAL)

**All analysis results MUST return this exact JSON structure:**

```json
{
  "status": "success",
  "match_id": 123456,
  "hero_id": 42,
  "hero_name": "Anti-Mage",
  "analysis": {
    "basic_stats": {
      "kills": 15,
      "deaths": 3,
      "assists": 8,
      "kda_ratio": 7.67,
      "gpm": 456,
      "xpm": 523,
      "lh": 342,
      "denies": 12
    },
    "by_phase": {
      "early": {
        "kills": 2,
        "deaths": 1,
        "lh": 52,
        "gpm": 420,
        "mistakes": ["Bad positioning in lane", "Missed deny opportunity"]
      },
      "mid": {
        "kills": 8,
        "deaths": 2,
        "farming_efficiency": 0.87,
        "mistakes": ["One early death", "Item timing could be better"]
      },
      "late": {
        "kills": 5,
        "deaths": 0,
        "high_ground_defense": 0.95,
        "mistakes": ["Risky positioning in one fight"]
      }
    },
    "items": [
      {
        "name": "Power Treads",
        "time_purchased": 145,
        "is_optimal": true,
        "timing_vs_benchmark": -5  // 5 seconds faster than average
      }
    ],
    "comparison": {
      "gpm_vs_avg": 456,
      "gpm_benchmark": 420,
      "gpm_percentile": 0.75,  // Top 25%
      "performance_rating": 78  // 0-100
    },
    "advice": {
      "top_mistakes": [
        "Risky farming without team",
        "One fight positioning mistake",
        "Could have had Blink Dagger 2 min earlier"
      ],
      "top_improvements": [
        "Better map awareness (only 2 ganks vs 5 average)",
        "Earlier item timings (power treads too late)",
        "More aggressive mid-game plays"
      ],
      "playstyle": "Farming-focused, risk-averse playstyle. Works well but could be more aggressive.",
      "tier": "A",  // S/A/B/C/D
      "estimated_mmr_impact": "+50 MMR this game"
    }
  },
  "timestamp": "2026-01-17T14:30:00Z"
}
```

---

After you've read everything here go to the next file rule - matchmentor-service-rule-continuation