"""Tests for the bilingual Gen VIII/IX and Champions item catalog."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from tools.import_items import (
    apply_pokeapi_data,
    clean_api_text,
    load_regulation_sources,
    to_showdown_id,
    validate_items,
)
from tools.item_mechanics import validate_item_mechanics


PROJECT_ROOT = Path(__file__).resolve().parent.parent


class ItemCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.records = json.loads(
            (PROJECT_ROOT / "data" / "items.json").read_text(
                encoding="utf-8"
            )
        )
        cls.records_by_api_name = {
            record["api_name"]: record for record in cls.records
        }
        cls.regulation_sources = load_regulation_sources(
            PROJECT_ROOT / "data" / "regulations.json"
        )
        cls.regulation_ids = {
            source["key"] for source in cls.regulation_sources
        }

    def test_generated_catalog_is_complete_unique_and_valid(self) -> None:
        self.assertGreaterEqual(len(self.records), 400)
        self.assertEqual(
            len(self.records),
            len(self.records_by_api_name),
        )
        validate_items(self.records, self.regulation_ids)

    def test_catalog_contains_gen_eight_and_nine_items(self) -> None:
        sitrus_berry = self.records_by_api_name["sitrus-berry"]

        self.assertEqual(
            sitrus_berry["legal_in_games"],
            ["sword-shield", "scarlet-violet"],
        )
        self.assertIn("reg-m-b", sitrus_berry["legal_in_regulations"])

    def test_non_champions_item_remains_in_catalog(self) -> None:
        assault_vest = self.records_by_api_name["assault-vest"]

        self.assertIn("sword-shield", assault_vest["legal_in_games"])
        self.assertIn("scarlet-violet", assault_vest["legal_in_games"])
        self.assertEqual(assault_vest["legal_in_regulations"], [])

    def test_champions_exclusive_item_has_regulation_legality(self) -> None:
        chandelurite = self.records_by_api_name["chandelurite"]

        self.assertEqual(chandelurite["legal_in_games"], [])
        self.assertTrue(chandelurite["legal_in_regulations"])
        self.assertTrue(chandelurite["name_de_is_fallback"])

    def test_pokeapi_id_and_official_german_name_are_retained(self) -> None:
        sitrus_berry = self.records_by_api_name["sitrus-berry"]

        self.assertEqual(sitrus_berry["item_id"], 135)
        self.assertEqual(sitrus_berry["showdown_id"], "sitrusberry")
        self.assertEqual(sitrus_berry["name_de"], "Tsitrubeere")
        self.assertFalse(sitrus_berry["name_de_is_fallback"])

    def test_every_regulation_reference_exists(self) -> None:
        referenced_ids = {
            regulation_id
            for item in self.records
            for regulation_id in item["legal_in_regulations"]
        }

        self.assertTrue(referenced_ids)
        self.assertTrue(referenced_ids.issubset(self.regulation_ids))

    def test_current_regulation_has_fully_structured_mechanics(self) -> None:
        current_items = [
            item
            for item in self.records
            if "reg-m-b" in item["legal_in_regulations"]
        ]

        self.assertEqual(len(current_items), 148)
        self.assertTrue(
            all(
                item["mechanics"]["status"] == "structured"
                for item in current_items
            )
        )

    def test_life_orb_has_damage_and_hp_loss_rules(self) -> None:
        mechanics = self.records_by_api_name["life-orb"]["mechanics"]
        rules_by_type = {
            rule["type"]: rule for rule in mechanics["rules"]
        }

        self.assertEqual(mechanics["status"], "structured")
        self.assertEqual(
            rules_by_type["damage-multiplier"]["multiplier"],
            {"numerator": 5324, "denominator": 4096},
        )
        self.assertEqual(
            rules_by_type["hp-loss"]["amount"],
            {
                "kind": "fraction",
                "value": {"numerator": 1, "denominator": 10},
                "basis": "holder-base-max-hp",
            },
        )

    def test_sitrus_berry_has_trigger_and_healing_fraction(self) -> None:
        mechanics = self.records_by_api_name["sitrus-berry"]["mechanics"]
        rule = mechanics["rules"][0]

        self.assertEqual(rule["type"], "heal")
        self.assertEqual(
            rule["hp_threshold"]["value"],
            {"numerator": 1, "denominator": 2},
        )
        self.assertEqual(
            rule["amount"]["value"],
            {"numerator": 1, "denominator": 4},
        )
        self.assertTrue(rule["consume_item"])

    def test_all_mechanics_objects_are_schema_valid(self) -> None:
        for item in self.records:
            validate_item_mechanics(item["mechanics"], item["api_name"])

    def test_showdown_id_normalizes_pokeapi_slug(self) -> None:
        self.assertEqual(to_showdown_id("choice-scarf"), "choicescarf")
        self.assertEqual(to_showdown_id("King's Rock"), "kingsrock")

    def test_api_text_cleanup_removes_formatting_whitespace(self) -> None:
        self.assertEqual(
            clean_api_text("Restores HP.\nWorks once.\f"),
            "Restores HP. Works once.",
        )

    def test_apply_pokeapi_data_keeps_legality_lists(self) -> None:
        record = apply_pokeapi_data(
            {
                "showdown_id": "testitem",
                "showdown_num": 100,
                "showdown_name": "Test Item",
                "showdown_description_en": "Test effect.",
                "mechanics_source_key": "reg-m-b",
                "mechanics_source_mod": "champions",
                "showdown_fling_power": 30,
                "item_class": "held-item",
                "restricted_to": [],
                "mega_stone": {},
                "is_choice_item": False,
                "has_custom_logic": False,
                "callback_fields": [],
                "legal_in_games": ["scarlet-violet"],
                "legal_in_regulations": ["reg-m-b"],
            },
            {
                "id": 9999,
                "name": "test-item",
                "names": [
                    {
                        "name": "Test Item",
                        "language": {"name": "en"},
                    },
                    {
                        "name": "Testitem",
                        "language": {"name": "de"},
                    },
                ],
                "effect_entries": [
                    {
                        "short_effect": "Test effect.",
                        "language": {"name": "en"},
                    }
                ],
                "flavor_text_entries": [],
                "category": {"name": "held-items"},
                "attributes": [],
                "fling_power": 30,
                "fling_effect": None,
            },
        )

        self.assertEqual(record["item_id"], 9999)
        self.assertEqual(record["name_de"], "Testitem")
        self.assertEqual(record["legal_in_games"], ["scarlet-violet"])
        self.assertEqual(record["legal_in_regulations"], ["reg-m-b"])


if __name__ == "__main__":
    unittest.main()
