"""Tests for the shared Pokémon Champions stat calculations."""

from __future__ import annotations

import unittest

from shared.calculations.stats import (
    DECREASED_NATURE,
    INCREASED_NATURE,
    MAX_STAT_POINTS,
    calculate_all_stats,
    calculate_hp,
    calculate_max_stats,
    calculate_other_stat,
    calculate_stat,
)


class StatCalculationTests(unittest.TestCase):
    def test_hp_at_level_50(self) -> None:
        self.assertEqual(calculate_hp(80), 155)
        self.assertEqual(calculate_hp(80, MAX_STAT_POINTS), 187)

    def test_non_hp_natures_round_down(self) -> None:
        self.assertEqual(calculate_other_stat(80), 100)
        self.assertEqual(calculate_other_stat(80, MAX_STAT_POINTS), 132)
        self.assertEqual(
            calculate_other_stat(80, MAX_STAT_POINTS, INCREASED_NATURE),
            145,
        )
        self.assertEqual(
            calculate_other_stat(80, MAX_STAT_POINTS, DECREASED_NATURE),
            118,
        )

    def test_hp_ignores_nature(self) -> None:
        self.assertEqual(
            calculate_stat("hp", 80, MAX_STAT_POINTS, INCREASED_NATURE),
            187,
        )

    def test_all_stats_accepts_per_stat_configuration(self) -> None:
        base = {
            "hp": 80,
            "atk": 90,
            "def": 100,
            "spa": 110,
            "spd": 120,
            "spe": 130,
        }
        result = calculate_all_stats(
            base,
            stat_points={"hp": 32, "atk": 10},
            nature_modifiers={"atk": INCREASED_NATURE},
        )
        self.assertEqual(result["hp"], 187)
        self.assertEqual(result["atk"], 132)
        self.assertEqual(result["def"], 120)

    def test_max_stats_treats_each_non_hp_stat_as_nature_increased(self) -> None:
        base = {stat: 80 for stat in ("hp", "atk", "def", "spa", "spd", "spe")}
        result = calculate_max_stats(base, INCREASED_NATURE)
        self.assertEqual(result["hp"], 187)
        self.assertEqual(result["atk"], 145)

    def test_stat_points_are_limited_to_champions_range(self) -> None:
        with self.assertRaises(ValueError):
            calculate_hp(80, MAX_STAT_POINTS + 1)


if __name__ == "__main__":
    unittest.main()
