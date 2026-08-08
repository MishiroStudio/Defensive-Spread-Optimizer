"""Pokémon Champions level-50 stat calculations.

This module is the single Python source of truth for the Pokédex, Defensive
Spread Optimizer, and future Damage Calculator.
"""

from __future__ import annotations

import math
from collections.abc import Mapping

PERFECT_IV = 31
MAX_STAT_POINTS = 32
NEUTRAL_NATURE = 1.0
INCREASED_NATURE = 1.1
DECREASED_NATURE = 0.9
STAT_KEYS = ("hp", "atk", "def", "spa", "spd", "spe")


def _validate_inputs(base_stat: int, stat_points: int, iv: int) -> None:
    if not isinstance(base_stat, int) or isinstance(base_stat, bool):
        raise TypeError("base_stat must be an integer")
    if base_stat < 1:
        raise ValueError("base_stat must be at least 1")
    if not isinstance(stat_points, int) or isinstance(stat_points, bool):
        raise TypeError("stat_points must be an integer")
    if not 0 <= stat_points <= MAX_STAT_POINTS:
        raise ValueError(
            f"stat_points must be between 0 and {MAX_STAT_POINTS}"
        )
    if not isinstance(iv, int) or isinstance(iv, bool):
        raise TypeError("iv must be an integer")
    if not 0 <= iv <= PERFECT_IV:
        raise ValueError(f"iv must be between 0 and {PERFECT_IV}")


def calculate_hp(
    base_hp: int,
    stat_points: int = 0,
    *,
    iv: int = PERFECT_IV,
) -> int:
    """Return a level-50 HP stat; natures never affect HP."""
    _validate_inputs(base_hp, stat_points, iv)
    level_50_hp = math.floor((2 * base_hp + iv) / 2) + 60
    return level_50_hp + stat_points


def calculate_other_stat(
    base_stat: int,
    stat_points: int = 0,
    nature: float = NEUTRAL_NATURE,
    *,
    iv: int = PERFECT_IV,
) -> int:
    """Return a level-50 non-HP stat after points and nature."""
    _validate_inputs(base_stat, stat_points, iv)
    if nature <= 0:
        raise ValueError("nature must be greater than 0")
    level_50_stat = math.floor((2 * base_stat + iv) / 2) + 5
    return math.floor((level_50_stat + stat_points) * nature)


def calculate_stat(
    stat: str,
    base_stat: int,
    stat_points: int = 0,
    nature: float = NEUTRAL_NATURE,
    *,
    iv: int = PERFECT_IV,
) -> int:
    """Calculate one named stat, ignoring the nature argument for HP."""
    if stat not in STAT_KEYS:
        raise ValueError(f"unknown stat: {stat}")
    if stat == "hp":
        return calculate_hp(base_stat, stat_points, iv=iv)
    return calculate_other_stat(base_stat, stat_points, nature, iv=iv)


def calculate_all_stats(
    base_stats: Mapping[str, int],
    stat_points: Mapping[str, int] | None = None,
    nature_modifiers: Mapping[str, float] | None = None,
    *,
    ivs: Mapping[str, int] | None = None,
) -> dict[str, int]:
    """Calculate all six stats from per-stat points, natures, and IVs."""
    points = stat_points or {}
    natures = nature_modifiers or {}
    resolved_ivs = ivs or {}
    return {
        stat: calculate_stat(
            stat,
            base_stats[stat],
            points.get(stat, 0),
            natures.get(stat, NEUTRAL_NATURE),
            iv=resolved_ivs.get(stat, PERFECT_IV),
        )
        for stat in STAT_KEYS
    }


def calculate_max_stats(
    base_stats: Mapping[str, int],
    nature: float = NEUTRAL_NATURE,
) -> dict[str, int]:
    """Return each stat's theoretical maximum with 32 Stat Points."""
    return {
        stat: calculate_stat(
            stat,
            base_stats[stat],
            MAX_STAT_POINTS,
            nature,
        )
        for stat in STAT_KEYS
    }
