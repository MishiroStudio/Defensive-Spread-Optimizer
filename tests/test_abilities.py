"""Tests for the standalone bilingual ability catalog."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from tools.import_abilities import (
    CHAMPIONS_ABILITY_OVERRIDES,
    CURRENT_GERMAN_NAME_OVERRIDES,
    build_record,
    clean_api_text,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent


class AbilityCatalogTests(unittest.TestCase):
    def test_generated_catalog_is_complete_and_unique(self) -> None:
        records = json.loads(
            (PROJECT_ROOT / "data" / "abilities.json").read_text(
                encoding="utf-8"
            )
        )
        api_names = [record["api_name"] for record in records]

        self.assertEqual(len(api_names), len(set(api_names)))
        self.assertTrue(records)
        for record in records:
            for key in (
                "name_de",
                "name_en",
                "description_de",
                "description_en",
            ):
                self.assertTrue(record[key])

    def test_pokeapi_markup_is_removed(self) -> None:
        self.assertEqual(
            clean_api_text("Can make [targets]{mechanic:target}\nflinch."),
            "Can make targets flinch.",
        )

    def test_new_ability_uses_german_fallback(self) -> None:
        record = build_record(
            {
                "id": 296,
                "name": "armor-tail",
                "is_main_series": True,
                "names": [
                    {
                        "name": "Armor Tail",
                        "language": {"name": "en"},
                    },
                    {
                        "name": "Schweifrüstung",
                        "language": {"name": "de"},
                    },
                ],
                "effect_entries": [
                    {
                        "short_effect": "Prevents priority moves.",
                        "language": {"name": "en"},
                    }
                ],
                "flavor_text_entries": [],
            }
        )

        self.assertIsNotNone(record)
        assert record is not None
        self.assertEqual(record["name_de"], "Schweifrüstung")
        self.assertIn("erhöhter Priorität", record["description_de"])

    def test_precise_german_description_precedes_vague_flavor_text(self) -> None:
        record = build_record(
            {
                "id": 102,
                "name": "leaf-guard",
                "is_main_series": True,
                "names": [
                    {
                        "name": "Leaf Guard",
                        "language": {"name": "en"},
                    },
                    {
                        "name": "Floraschild",
                        "language": {"name": "de"},
                    },
                ],
                "effect_entries": [
                    {
                        "short_effect": "Protects against status ailments.",
                        "language": {"name": "en"},
                    },
                    {
                        "short_effect": (
                            "Schützt vor Primäre Statusveränderungen."
                        ),
                        "language": {"name": "de"},
                    },
                ],
                "flavor_text_entries": [
                    {
                        "flavor_text": (
                            "Verhindert bei Sonnenschein Statusprobleme."
                        ),
                        "language": {"name": "de"},
                        "version_group": {"name": "sword-shield"},
                    }
                ],
            }
        )

        self.assertIsNotNone(record)
        assert record is not None
        self.assertEqual(
            record["description_de"],
            "Schützt das Pokémon bei Sonnenschein vor Statusproblemen.",
        )

    def test_catalog_has_correct_floraschild_description(self) -> None:
        records = json.loads(
            (PROJECT_ROOT / "data" / "abilities.json").read_text(
                encoding="utf-8"
            )
        )
        records_by_name = {record["api_name"]: record for record in records}

        self.assertEqual(
            records_by_name["leaf-guard"]["description_de"],
            "Schützt das Pokémon bei Sonnenschein vor Statusproblemen.",
        )
        self.assertFalse(
            any(
                "Primäre Statusveränderung" in record["description_de"]
                for record in records
            )
        )

    def test_catalog_uses_current_german_ability_names(self) -> None:
        records = json.loads(
            (PROJECT_ROOT / "data" / "abilities.json").read_text(
                encoding="utf-8"
            )
        )
        records_by_name = {record["api_name"]: record for record in records}

        for api_name, expected_name in CURRENT_GERMAN_NAME_OVERRIDES.items():
            self.assertEqual(records_by_name[api_name]["name_de"], expected_name)

    def test_vgc_examples_retain_exact_mechanics(self) -> None:
        records = json.loads(
            (PROJECT_ROOT / "data" / "abilities.json").read_text(
                encoding="utf-8"
            )
        )
        records_by_name = {record["api_name"]: record for record in records}
        expected_fragments = {
            "intimidate": ("1 Stufe", "angrenzenden"),
            "effect-spore": ("30 %", "Kontaktattacke"),
            "compound-eyes": ("Faktor 1,3",),
            "technician": ("höchstens 60", "Faktor 1,5"),
            "poison-heal": ("1/8", "Giftschaden"),
        }

        for api_name, fragments in expected_fragments.items():
            description = records_by_name[api_name]["description_de"]
            for fragment in fragments:
                self.assertIn(fragment, description)

    def test_catalog_has_no_known_german_localization_errors(self) -> None:
        records = json.loads(
            (PROJECT_ROOT / "data" / "abilities.json").read_text(
                encoding="utf-8"
            )
        )
        forbidden_fragments = (
            "Primäre Statusveränderung",
            " Versärkt ",
            " Schütz ",
            "erhöhrt",
            "for negativen",
            "Statuswerteänderungenen",
        )

        for record in records:
            description = record["description_de"]
            for fragment in forbidden_fragments:
                self.assertNotIn(fragment, description)
            self.assertRegex(description, r"[.!?]$")

    def test_champions_catalog_matches_curated_overrides(self) -> None:
        records = json.loads(
            (PROJECT_ROOT / "data" / "abilities.json").read_text(
                encoding="utf-8"
            )
        )
        records_by_name = {record["api_name"]: record for record in records}

        for api_name, expected in CHAMPIONS_ABILITY_OVERRIDES.items():
            self.assertIn(api_name, records_by_name)
            for key, expected_value in expected.items():
                self.assertEqual(records_by_name[api_name][key], expected_value)

    def test_champions_override_replaces_incomplete_api_localization(self) -> None:
        record = build_record(
            {
                "id": 312,
                "name": "eelevate",
                "is_main_series": True,
                "names": [
                    {
                        "name": "Eelevate",
                        "language": {"name": "en"},
                    }
                ],
                "effect_entries": [
                    {
                        "short_effect": "Incomplete API description.",
                        "language": {"name": "en"},
                    }
                ],
                "flavor_text_entries": [],
            }
        )

        self.assertIsNotNone(record)
        assert record is not None
        self.assertEqual(record["name_de"], "Emporwindung")
        self.assertIn("Klebenetz", record["description_de"])


if __name__ == "__main__":
    unittest.main()