"""Tests for the Defensive Spread Optimizer Pokémon data adapter."""

from __future__ import annotations

import unittest

from apps.desktop.tools.defensive_spread_optimizer.database import (
    get_pokemon,
    load_pokemon,
)
from shared.repositories import PokemonRepository


class OptimizerDatabaseTests(unittest.TestCase):
    def test_adapter_contains_every_pokedex_form(self) -> None:
        repository = PokemonRepository()

        self.assertEqual(
            len(load_pokemon()),
            len(repository.all_forms()),
        )

    def test_adapter_maps_base_stats_and_sprites(self) -> None:
        bulbasaur = get_pokemon("Bisasam")

        self.assertIsNotNone(bulbasaur)
        assert bulbasaur is not None

        self.assertEqual(bulbasaur["dex"], 1)
        self.assertEqual(bulbasaur["api_name"], "bulbasaur")
        self.assertEqual(bulbasaur["name_en"], "Bulbasaur")
        self.assertEqual(bulbasaur["name_de"], "Bisasam")
        self.assertEqual(bulbasaur["base_hp"], 45)
        self.assertEqual(bulbasaur["base_atk"], 49)
        self.assertEqual(bulbasaur["base_def"], 49)
        self.assertEqual(bulbasaur["base_spa"], 65)
        self.assertEqual(bulbasaur["base_spd"], 65)
        self.assertEqual(bulbasaur["base_spe"], 45)
        self.assertEqual(
            bulbasaur["sprite_home"],
            "assets/sprites/home/normal/bulbasaur.png",
        )

    def test_adapter_accepts_english_and_api_names(self) -> None:
        self.assertEqual(
            get_pokemon("Bulbasaur"),
            get_pokemon("bulbasaur"),
        )

    def test_unknown_pokemon_returns_none(self) -> None:
        self.assertIsNone(get_pokemon("Definitely not a Pokémon"))


if __name__ == "__main__":
    unittest.main()