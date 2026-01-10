"""
Game stage constants and pro benchmarks for Dota 2 match analysis.
Based on professional player statistics and tournament data.
"""

from typing import Dict, Any
from dataclasses import dataclass

# ============================================================================
# GAME STAGE DEFINITIONS (in minutes)
# ============================================================================

GAME_STAGES = {
    'laning': {'start': 0, 'end': 10},
    'midgame': {'start': 10, 'end': 25},
    'late_midgame': {'start': 25, 'end': 35},
    'late_game': {'start': 35, 'end': 45},
    'ultra_late': {'start': 45, 'end': 999}
}

# ============================================================================
# PRO BENCHMARKS BY POSITION (1-5)
# Based on top 1000 MMR professional matches
# ============================================================================

PRO_BENCHMARKS = {
    1: {  # Position 1: Carry / Safe Lane
        'laning': {'gpm': 500, 'xpm': 600, 'lh_10m': 50, 'deaths_max': 1},
        'midgame': {'gpm': 650, 'xpm': 800, 'deaths_max': 2},
        'late_game': {'gpm': 750, 'xpm': 900, 'deaths_max': 3}
    },
    2: {  # Position 2: Mid Lane
        'laning': {'gpm': 550, 'xpm': 700, 'lh_10m': 40, 'deaths_max': 1},
        'midgame': {'gpm': 700, 'xpm': 900, 'deaths_max': 2},
        'late_game': {'gpm': 800, 'xpm': 1000, 'deaths_max': 3}
    },
    3: {  # Position 3: Offlane
        'laning': {'gpm': 400, 'xpm': 550, 'lh_10m': 25, 'deaths_max': 2},
        'midgame': {'gpm': 500, 'xpm': 650, 'deaths_max': 3},
        'late_game': {'gpm': 600, 'xpm': 750, 'deaths_max': 4}
    },
    4: {  # Position 4: Soft Support
        'laning': {'gpm': 250, 'xpm': 400, 'lh_10m': 10, 'deaths_max': 2},
        'midgame': {'gpm': 300, 'xpm': 450, 'deaths_max': 4},
        'late_game': {'gpm': 350, 'xpm': 500, 'deaths_max': 5}
    },
    5: {  # Position 5: Hard Support
        'laning': {'gpm': 200, 'xpm': 350, 'lh_10m': 5, 'deaths_max': 2},
        'midgame': {'gpm': 250, 'xpm': 400, 'deaths_max': 4},
        'late_game': {'gpm': 300, 'xpm': 450, 'deaths_max': 6}
    }
}

# ============================================================================
# EXPECTED ITEM TIMINGS BY POSITION (in seconds)
# ============================================================================

ITEM_BUILD_TIMINGS = {
    1: {  # Carry
        'boots': 300,  # 5 min
        'first_item': 900,  # 15 min (BF, Midas, etc)
        'second_item': 1500,  # 25 min
        'third_item': 2100  # 35 min
    },
    2: {  # Mid
        'boots': 300,
        'first_item': 750,  # 12-13 min
        'second_item': 1350,  # 22-23 min
        'third_item': 1950  # 32-33 min
    },
    3: {  # Offlane
        'boots': 360,
        'first_item': 1200,
        'second_item': 1800,
        'third_item': 2400
    },
    4: {  # Support
        'boots': 480,
        'first_item': 1200,
        'second_item': 2100,
        'third_item': 3000
    },
    5: {  # Hard Support
        'boots': 600,
        'first_item': 1500,
        'second_item': 2400,
        'third_item': 3300
    }
}

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_game_stage(minute: float) -> str:
    """
    Determine which game stage we're in based on game minute.
    
    Args:
        minute: Game time in minutes
        
    Returns:
        Stage name: 'laning', 'midgame', etc.
    """
    for stage, bounds in GAME_STAGES.items():
        if bounds['start'] <= minute < bounds['end']:
            return stage
    return 'ultra_late'


def get_position(player_slot: int) -> int:
    """
    Convert player_slot to position (1-5).
    
    Radiant: slots 0-4 = positions 1-5
    Dire: slots 128-132 = positions 1-5
    
    Args:
        player_slot: OpenDota player slot value
        
    Returns:
        Position number (1-5) or None if invalid
    """
    if 0 <= player_slot <= 4:
        return player_slot + 1
    elif 128 <= player_slot <= 132:
        return player_slot - 127
    return None


def convert_timestamp_to_minute(timestamp: int) -> float:
    """Convert game timestamp (seconds) to game minute."""
    return timestamp / 60.0


def get_pro_benchmark(position: int, stage: str, metric: str) -> float:
    """
    Get pro benchmark for specific position, stage, and metric.
    
    Args:
        position: Player position (1-5)
        stage: Game stage ('laning', 'midgame', etc)
        metric: Metric name ('gpm', 'xpm', 'lh_10m', etc)
        
    Returns:
        Benchmark value or 0 if not found
    """
    try:
        return PRO_BENCHMARKS[position][stage].get(metric, 0)
    except (KeyError, TypeError):
        return 0


def calculate_performance_percentage(actual: float, benchmark: float) -> float:
    """
    Calculate performance as percentage of benchmark.
    
    100% = at benchmark
    150% = 50% above benchmark  
    50% = 50% below benchmark
    
    Args:
        actual: Actual player value
        benchmark: Pro benchmark value
        
    Returns:
        Performance percentage
    """
    if benchmark <= 0:
        return 0
    return (actual / benchmark) * 100


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class TimeSnapshot:
    """Single point in time snapshot of player stats."""
    minute: float
    timestamp: int
    gold: int
    xp: int
    level: int
    last_hits: int
    position: Dict[str, Any]  # {x, y}
    
    def to_dict(self):
        return {
            'minute': self.minute,
            'timestamp': self.timestamp,
            'gold': self.gold,
            'xp': self.xp,
            'level': self.level,
            'last_hits': self.last_hits,
            'position': self.position
        }
