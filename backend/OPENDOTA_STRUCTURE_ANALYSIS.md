# OpenDota parsed_data Structure Analysis

## Executive Summary

**CRITICAL FINDING**: OpenDota API does **NOT** provide time-series arrays like `gold_t`, `xp_t`, `lh_t`.

Instead, OpenDota provides:
- **`benchmarks` dictionary** with aggregated statistics
- **Total game stats** (final values)
- **Specific milestone data** (e.g., `lh_at_10`)

## Actual OpenDota Response Structure

### What OpenDota DOES Provide

```json
{
  "player_slot": 0,
  "hero_id": 138,
  "hero_name": "npc_dota_hero_muerta",
  
  // TOTAL STATS (end of game)
  "kills": 17,
  "deaths": 7,
  "assists": 12,
  "last_hits": 352,
  "denies": 12,
  "gold_per_min": 766,
  "xp_per_min": 748,
  "level": 25,
  "net_worth": 22500,
  "hero_damage": 25000,
  "tower_damage": 5000,
  
  // BENCHMARKS DICTIONARY
  "benchmarks": {
    "gold_per_min": {"raw": 766, "pct": 0.85},
    "xp_per_min": {"raw": 748, "pct": 0.82},
    "kills_per_min": {"raw": 0.5, "pct": 0.75},
    "last_hits_per_min": {"raw": 12.3, "pct": 0.70},
    "hero_damage_per_min": {"raw": 850, "pct": 0.80},
    "tower_damage": {"raw": 5000, "pct": 0.65},
    "lhten": {"raw": 45, "pct": 0.60}  // ← LH at 10 minutes!
  },
  
  // TIME-SERIES: NONE (all null or missing)
  "gold_t": null,
  "xp_t": null,
  "lh_t": null,
  "level_t": null,
  
  // ITEMS
  "item_0": "item_power_treads",
  "item_1": "item_black_king_bar",
  // ... etc
  
  // PURCHASE LOG
  "purchase_log": [
    {"time": 45, "key": "tango"},
    {"time": 300, "key": "boots_of_speed"},
    {"time": 750, "key": "power_treads"}
  ]
}
```

### What OpenDota DOES NOT Provide

❌ `gold_t` - Gold over time array  
❌ `xp_t` - XP over time array  
❌ `lh_t` - Last hits over time array  
❌ `deaths_t` - Deaths timestamps array  
❌ `position_t` - Position coordinates over time  

## Implications for Architecture

### Option 1: Use Only OpenDota Data (Limitations)

**Available for Laning Stage (0-10min):**
- ✅ `benchmarks.lhten.raw` - Last hits at 10 min
- ✅ Estimate `gold_at_10` from GPM: `(gold_per_min × 10)`
- ✅ Estimate `xp_at_10` from XPM: `(xp_per_min × 10)`
- ❌ Deaths at 10min - NOT AVAILABLE
- ❌ Exact snapshots at 0m, 5m, 10m - NOT AVAILABLE
- ❌ Events timeline - LIMITED (only purchase_log)

**Workarounds:**
- Use estimates instead of exact values
- Focus on end-of-stage metrics (10min, 20min, etc)
- Skip granular event analysis

### Option 2: Require Clarity Parser Upload (Full Data)

**What Clarity Parser Provides:**
- ✅ Full time-series: `gold_t`, `xp_t`, `lh_t` as **arrays**
- ✅ Death timestamps with coordinates
- ✅ Position tracking every second
- ✅ Detailed event timeline

**Format:**
```python
{
  "gold_t": [625, 750, 950, ...],  # Array indexed by time
  "xp_t": [0, 250, 450, ...],
  "lh_t": [0, 2, 5, 8, ...],
  "deaths": [
    {"timestamp": 600, "killer": "enemy", "x": 100, "y": 200}
  ]
}
```

## Recommended Hybrid Approach

### Architecture Design

```python
class LaningStageExtractor:
    def __init__(self, player_data, position, data_source="opendota"):
        self.data_source = data_source  # "opendota" or "clarity"
        
    def extract(self):
        if self.data_source == "clarity":
            return self._extract_from_clarity()  # Full time-series
        else:
            return self._extract_from_opendota()  # Estimates + benchmarks
```

### Implementation Strategy

**Week 1 Day 1-2**: Build with OpenDota support first
- Use `benchmarks.lhten.raw` for LH at 10min
- Estimate gold/xp from GPM/XPM
- Skip detailed event timeline
- **PRO**: Works immediately with match lookup
- **CON**: Limited granularity

**Week 1 Day 3-5**: Add Clarity parser support
- Full time-series extraction
- Detailed snapshots at 0m, 5m, 10m
- Complete event timeline
- **PRO**: Professional-grade analysis
- **CON**: Requires .dem file upload

## Data Format Reference

### OpenDota Format (Current)
```json
{
  "benchmarks": {
    "lhten": {"raw": 45, "pct": 0.60}
  },
  "gold_per_min": 766,
  "xp_per_min": 748,
  "purchase_log": [...]
}
```

### Clarity Parser Format (Target)
```python
{
  "gold_t": {
    "0": 625,
    "1": 750,
    "5": 1550,
    "10": 2650
  },  # OR as array: [625, 750, ...]
  "xp_t": {...},
  "lh_t": {...}
}
```

## Recommendations for You

Given that we already have OpenDota working:

**Immediate Action (Today)**:
1. Use `benchmarks.lhten.raw` for real LH at 10min
2. Estimate `gold_at_10 = gold_per_min × 10`
3. Estimate `xp_at_10 = xp_per_min × 10`
4. Skip events timeline for now
5. Focus on end-of-stage metrics

**Future Enhancement**:
- Add Clarity parser adapter when needed
- Implement full time-series extraction
- Add detailed event analysis

## Code Example for OpenDota

```python
def _extract_laning_stage_data_opendota(self, player):
    """Extract from OpenDota format (benchmarks-based)"""
    
    # Get from benchmarks
    benchmarks = player.get("benchmarks", {})
    lh_10 = benchmarks.get("lhten", {}).get("raw", 0)
    
    # Estimate from rates
    gpm = player.get("gold_per_min", 0)
    xpm = player.get("xp_per_min", 0)
    
    gold_10 = int(gpm × 10)
    xp_10 = int(xpm × 10)
    
    return {
        "gold_at_10": gold_10,
        "xp_at_10": xp_10,
        "last_hits_at_10": lh_10,
        "gpm_10m": gpm,
        "xpm_10m": xpm
    }
```

---

**Bottom Line**: OpenDota gives us enough for basic laning analysis, but not detailed time-series. We can build the architecture to support both formats.
