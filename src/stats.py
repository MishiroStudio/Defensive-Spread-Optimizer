import math


def calculate_hp(base_hp, stat_points):
    level_50_hp = math.floor((2 * base_hp + 31) / 2) + 60
    return level_50_hp + stat_points


def calculate_other_stat(base_stat, stat_points, nature=1.0):
    level_50_stat = math.floor((2 * base_stat + 31) / 2) + 5
    stat_with_points = level_50_stat + stat_points
    return math.floor(stat_with_points * nature)


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