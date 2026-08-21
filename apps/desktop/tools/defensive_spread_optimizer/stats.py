"""Stat helpers for the Defensive Spread Optimizer.

The actual calculations live centrally in shared.calculations.stats.
"""

from shared.calculations.stats import calculate_hp, calculate_other_stat


def calculate_attack(base_atk, stat_points, nature=1.0):
    return calculate_other_stat(base_atk, stat_points, nature)


def calculate_defense(base_def, stat_points, nature=1.0):
    return calculate_other_stat(base_def, stat_points, nature)


def calculate_special_attack(base_spa, stat_points, nature=1.0):
    return calculate_other_stat(base_spa, stat_points, nature)


def calculate_special_defense(base_spd, stat_points, nature=1.0):
    return calculate_other_stat(base_spd, stat_points, nature)


def calculate_speed(base_spe, stat_points, nature=1.0):
    return calculate_other_stat(base_spe, stat_points, nature)