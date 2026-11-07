"""Tests for the Speed Tier Trainer model."""

from __future__ import annotations

import random
import unittest

from apps.desktop.tools.speed_tier_trainer.trainer import (
    QuizPokemon,
    QuizSession,
    TrainerCatalog,
    calculate_speed_values,
)


def quiz_pokemon(pokemon_id: int, speed: int) -> QuizPokemon:
    return QuizPokemon(
        pokemon_id=pokemon_id,
        national_dex=pokemon_id,
        api_name=f"pokemon-{pokemon_id}",
        name_de=f"Pokémon {pokemon_id}",
        name_en=f"Pokemon {pokemon_id}",
        base_speed=speed,
        sprite_path=None,
    )


class TrainerCatalogTests(unittest.TestCase):
    def test_shared_data_builds_all_quiz_scopes(self) -> None:
        catalog = TrainerCatalog()

        self.assertEqual(
            [scope.key for scope in catalog.scopes],
            ["reg-m-c", "all", "reg-m-b", "reg-m-a"],
        )
        self.assertEqual(
            [scope.label_de for scope in catalog.scopes],
            [
                "Regulation M-C",
                "Nationaler Dex",
                "Regulation M-B",
                "Regulation M-A",
            ],
        )
        current = catalog.entries_for_scope("reg-m-c")
        national_dex = catalog.entries_for_scope("all")
        self.assertGreater(len(current), 0)
        self.assertLessEqual(len(current), len(national_dex))
        self.assertTrue(all(1 <= pokemon.base_speed <= 255 for pokemon in current))

    def test_speed_values_use_champions_minimum_and_maximum_rules(self) -> None:
        values = calculate_speed_values(80)

        self.assertEqual(values.minimum_neutral, 100)
        self.assertEqual(values.minimum_decreased, 90)
        self.assertEqual(values.maximum_neutral, 132)
        self.assertEqual(values.maximum_increased, 145)

    def test_floette_eternal_offers_its_legal_mega_form(self) -> None:
        catalog = TrainerCatalog()
        current = catalog.entries_for_scope("reg-m-c")
        floette = next(
            pokemon
            for pokemon in current
            if pokemon.api_name == "floette-eternal"
        )

        variants = catalog.mega_variants(floette, "reg-m-c")

        self.assertEqual(
            [pokemon.api_name for pokemon in variants],
            ["floette-eternal", "floette-mega"],
        )

    def test_usage_filter_returns_exact_ranked_pool_sizes(self) -> None:
        catalog = TrainerCatalog()

        for scope_key in ("reg-m-c", "all", "reg-m-b", "reg-m-a"):
            with self.subTest(scope=scope_key):
                self.assertEqual(
                    len(
                        catalog.entries_for_scope(
                            scope_key,
                            usage_limit=10,
                        )
                    ),
                    10,
                )
                self.assertEqual(
                    len(
                        catalog.entries_for_scope(
                            scope_key,
                            usage_limit=50,
                        )
                    ),
                    50,
                )
                self.assertEqual(
                    len(
                        catalog.entries_for_scope(
                            scope_key,
                            usage_limit=100,
                        )
                    ),
                    100,
                )

    def test_current_usage_order_is_kept_before_session_shuffle(self) -> None:
        catalog = TrainerCatalog()
        dataset = catalog.usage_dataset_for_scope("reg-m-c")
        self.assertIsNotNone(dataset)
        assert dataset is not None

        top_ten = catalog.entries_for_scope(
            "reg-m-c",
            usage_limit=10,
        )

        self.assertEqual(
            [pokemon.pokemon_id for pokemon in top_ten],
            [entry.pokemon_id for entry in dataset.entries[:10]],
        )

    def test_national_dex_uses_current_regulation_usage(self) -> None:
        catalog = TrainerCatalog()

        current = catalog.entries_for_scope("reg-m-c", usage_limit=10)
        national = catalog.entries_for_scope("all", usage_limit=10)

        self.assertEqual(
            [pokemon.pokemon_id for pokemon in national],
            [pokemon.pokemon_id for pokemon in current],
        )


class QuizSessionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.pool = (
            quiz_pokemon(1, 45),
            quiz_pokemon(2, 80),
            quiz_pokemon(3, 100),
        )

    def test_exact_and_inexact_answers_update_score(self) -> None:
        session = QuizSession(self.pool, rng=random.Random(7))
        exact_result = session.submit(session.current.base_speed)
        self.assertTrue(exact_result.is_exact)
        self.assertEqual(session.exact, 1)
        self.assertEqual(session.current_streak, 1)
        self.assertTrue(session.advance())

        high_result = session.submit(session.current.base_speed + 5)
        self.assertEqual(high_result.direction, "high")
        self.assertEqual(session.exact, 1)
        self.assertEqual(session.total_absolute_error, 5)
        self.assertEqual(session.mean_absolute_error, 2.5)
        self.assertEqual(session.current_streak, 0)
        self.assertTrue(session.advance())

    def test_reveal_counts_as_incorrect_but_not_as_a_guess(self) -> None:
        session = QuizSession(self.pool, rng=random.Random(1))
        result = session.submit(None)

        self.assertEqual(result.direction, "revealed")
        self.assertEqual(session.answered, 1)
        self.assertEqual(session.guessed, 0)
        self.assertEqual(session.mean_absolute_error, 0.0)

    def test_selected_mega_form_is_used_for_the_answer(self) -> None:
        base_form = quiz_pokemon(10, 50)
        mega_form = quiz_pokemon(11, 90)
        session = QuizSession((base_form,), rng=random.Random(2))

        result = session.submit(90, pokemon=mega_form)

        self.assertTrue(result.is_exact)
        self.assertEqual(result.pokemon, mega_form)

    def test_endless_game_has_no_repeat_before_pool_is_exhausted(self) -> None:
        session = QuizSession(self.pool, rng=random.Random(4))
        seen: list[int] = []
        for _ in self.pool:
            seen.append(session.current.pokemon_id)
            session.submit(session.current.base_speed)
            self.assertTrue(session.advance())

        self.assertEqual(len(set(seen)), len(self.pool))


if __name__ == "__main__":
    unittest.main()

