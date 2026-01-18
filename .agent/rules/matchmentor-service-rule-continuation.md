---
trigger: always_on
---

## RULE #9: VALIDATION CHECKLIST (CRITICAL)

**Before returning ANY analysis, validate:**

```python
def validate_analysis(analysis, hero_id):
    """Validate all 60+ metrics before returning"""
    
    checks = {
        'basic_stats': {
            'kills': lambda x: 0 <= x['kills'] <= 50,
            'deaths': lambda x: 0 <= x['deaths'] <= 50,
            'assists': lambda x: 0 <= x['assists'] <= 100,
            'gpm': lambda x: 0 <= x['gpm'] <= 2000,
            'xpm': lambda x: 0 <= x['xpm'] <= 2000,
            'lh': lambda x: 0 <= x['lh'] <= 2000,
        },
        'by_phase': {
            'early_gpm': lambda x: 0 <= x.get('gpm', 0) <= 2000,
            'mid_gpm': lambda x: 0 <= x.get('gpm', 0) <= 2000,
        }
    }
    
    for category, validators in checks.items():
        for field, validator in validators.items():
            if not validator(analysis.get(category, {})):
                logger.error(f"Validation failed: {category}.{field}")
                return False
    
    return True
```

---

## RULE #10: MATCH EDGE CASES (CRITICAL)

**Handle these cases specifically:**

### Case 1: Game ended in <3 minutes
- Return warning: "Game ended too early for meaningful analysis"
- Still return basic K/D/A but no phases
- No advice given

### Case 2: Hero didn't participate (AFK, disconnected)
- Return error: "Hero had minimal participation (check for DC/AFK)"
- Show time inactive, items not bought, no movements
- No tier/advice

### Case 3: Unusual farm efficiency
- If GPM > 1500: "Likely Roshan farming or abuse, review manually"
- If LH > 3000: "Check for possible exploits"
- Flag for review but still calculate

### Case 4: Player disconnected mid-game
- Calculate only up to disconnect time
- Mark as "Incomplete analysis (hero DC at 15:30)"
- Don't compare to full-game benchmarks

---

## RULE #11: CLARITY PARSER OUTPUT (CRITICAL)

**How to use Clarity parser output:**

```bash
# Run parser
java -jar clarity-3.2.0.jar /path/to/replay.dem > output.json

# Output includes:
# - All hero events (kills, deaths, last hits, denies, abilities, items)
# - Timestamps (in milliseconds from game start)
# - Player IDs (0-9, maps to radiant/dire teams)
# - Gold values for each event
# - Position data (x,y coordinates)
```

**Parse it:**
```python
import json

with open('output.json') as f:
    clarity_data = json.load(f)

# Events is array of all game events
events = clarity_data['events']

# Filter by hero_id (player ID)
hero_events = [e for e in events if e['player_id'] == target_hero_id]

# Calculate metrics from events
for event in hero_events:
    if event['type'] == 'kill':
        kills += 1
    elif event['type'] == 'death':
        deaths += 1
    elif event['type'] == 'last_hit':
        last_hits += 1
    # ... etc
```

---

## RULE #12: PERFORMANCE & TIMEOUT (CRITICAL)

**All operations must complete quickly:**

- ✅ Parse replay: < 30 seconds
- ✅ Calculate metrics: < 5 seconds
- ✅ Generate advice: < 2 seconds
- ✅ API response: < 500ms
- ✅ Total: < 40 seconds end-to-end

**Timeout handling:**
```python
from concurrent.futures import TimeoutError

try:
    result = run_parser_with_timeout(replay_path, timeout=30)
except TimeoutError:
    return {"error": "Parser timeout", "status": "timeout"}
```

---

## RULE #13: LOGGING & DEBUG (CRITICAL)

**Log everything for debugging:**

```python
import logging

logger = logging.getLogger(__name__)

logger.info(f"Starting analysis for hero {hero_id}")
logger.debug(f"Parsed {len(events)} events from replay")
logger.debug(f"Calculated K/D/A: {kills}/{deaths}/{assists}")
logger.warning(f"Unusual GPM: {gpm} (expected 200-800)")
logger.error(f"Failed to get benchmark for hero {hero_id}")

# Never expose full errors to user, but log server-side
try:
    metrics = calculate(data)
except Exception as e:
    logger.exception(f"Calculation failed: {e}")
    return {"error": "Internal error", "status": "error"}
```

---

## RULE #14: CACHING (CRITICAL)

**What to cache and what NOT to cache:**

### ✅ SAFE to cache (24 hours):
- Hero list (heroes endpoint)
- Item list (items endpoint)
- Benchmarks for hero (updates daily at 12 UTC)
- Icon URLs (change rarely)

### ❌ NEVER cache:
- Match replay data (always parse fresh)
- Calculated metrics (specific to match)
- Player stats (changes every game)
- Rankings (changes every day)

**Cache implementation:**
```python
from functools import lru_cache
from datetime import datetime, timedelta

@lru_cache(maxsize=128)
def get_hero_list(cache_key):
    """Cache expires after 24 hours"""
    return api.get('https://api.opendota.com/api/heroes')

def get_cached_heroes():
    cache_key = datetime.now().date()  # Changes daily
    return get_hero_list(cache_key)
```

---

## RULE #15: SECURITY & SECRETS (CRITICAL)

**Protect all secrets:**

```python
import os
from dotenv import load_dotenv

load_dotenv()  # Load from .env

# ✅ CORRECT:
db_password = os.getenv('DATABASE_PASSWORD')
stripe_key = os.getenv('STRIPE_SECRET_KEY')

# ❌ WRONG:
# db_password = "hardcoded_password"  # NO!
# stripe_key = "sk_live_123456"  # NO!
```

**Never in code/logs:**
- Database passwords
- API keys
- Stripe secrets
- User data
- Match IDs (can be private replays)

**In .env file:**
```env
DATABASE_PASSWORD=your_password
STRIPE_SECRET_KEY=sk_live_xxx
SENDGRID_API_KEY=SG_xxx
OPENDATA_API_KEY=xxx
```

---

## QUICK REFERENCE TABLE

| Rule | What | How | Never |
|------|------|-----|-------|
| #1 | Data Sources | Use APIs (OpenDota, CDN) | Hardcode, cache without validation |
| #2 | Accuracy | Exact formulas, validate | Approximate, round early |
| #3 | Errors | Handle all cases, log | Silent failures, expose stack traces |
| #4 | Tech Stack | Use listed versions | Use old versions, mix tech |
| #5 | Hero Parsing | Parse each hero completely | Skip heroes, approximate |
| #6 | 60+ Metrics | Calculate all, no skipping | Partial metrics, guessing |
| #7 | Phases | Always early/mid/late | Single view, no phases |
| #8 | API Format | Return exact JSON | Random format, missing fields |
| #9 | Validation | Check before returning | Return unvalidated data |
| #10 | Edge Cases | Handle AFK/DC/early games | Ignore edge cases |
| #11 | Clarity Parser | Use correctly, parse events | Misuse, ignore events |
| #12 | Performance | <40 sec total, timeout handling | Slow, no timeouts |
| #13 | Logging | Log all, protect user data | Expose errors, no logs |
| #14 | Caching | Cache safe data, never cache metrics | Cache match data |
| #15 | Security | .env for secrets, never expose | Hardcode secrets |

---

## SUMMARY

✅ **Antigravity MUST follow ALL 15 rules**  
✅ **No exceptions, no shortcuts**  
✅ **These rules guarantee ZERO parsing errors**  
✅ **100% accurate metrics for all 106 heroes**  

When given ANY MatchMentor task:
1. Read these rules
2. Apply them to the code
3. Test against the checklist
4. Validate before returning

---

**Made for fixing MatchMentor parser with 100% accuracy ❤️**
This is it for the rules, you've read everything! But take into account, if some services named here are outdated or not used as efficient as before then change them for more productive according to your perspective! Always take the most recent version of each service possible (should be the newest one as of 2026).