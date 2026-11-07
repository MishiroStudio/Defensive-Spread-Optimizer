"""Tests for shared usage data and its importer."""

from __future__ import annotations

from datetime import date
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from shared.repositories import UsageRepository
from tools.import_usage_stats import completed_months, parse_usage_table


SAMPLE_TABLE = """\
Total battles: 12345
Avg. weight/team: 0.125
+ ---- + ------------------ + --------- + ------ +
| Rank | Pokemon            | Usage %   | Raw    |
+ ---- + ------------------ + --------- + ------ +
| 1    | Sneasler           | 49.94690% | 1000   |
| 2    | Charizard-Mega-Y   | 32.34853% |  800   |
"""


class UsageImporterTests(unittest.TestCase):
    def test_parse_usage_table(self) -> None:
        total_battles, entries = parse_usage_table(SAMPLE_TABLE)

        self.assertEqual(total_battles, 12345)
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0].showdown_name, "Sneasler")
        self.assertAlmostEqual(entries[1].usage_percent, 32.34853)

    def test_completed_months_excludes_current_month(self) -> None:
        self.assertEqual(
            completed_months(None, 3, today=date(2026, 11, 3)),
            ("2026-10", "2026-09", "2026-08"),
        )

    def test_explicit_start_month_crosses_year_boundary(self) -> None:
        self.assertEqual(
            completed_months("2026-01", 3),
            ("2026-01", "2025-12", "2025-11"),
        )


class UsageRepositoryTests(unittest.TestCase):
    def test_repository_loads_ranked_local_ids(self) -> None:
        payload = {
            "schema_version": 1,
            "source": {"imported_at": "2026-11-03T00:00:00+00:00"},
            "current_regulation_id": "reg-test",
            "formats": {
                "reg-test": {
                    "format_id": "testformat",
                    "month": "2026-10",
                    "rating_cutoff": 1760,
                    "total_battles": 100,
                    "source_url": "https://example.test/stats.txt",
                    "entries": [
                        {
                            "rank": 1,
                            "pokemon_id": 25,
                            "api_name": "pikachu",
                            "showdown_id": "pikachu",
                            "showdown_name": "Pikachu",
                            "usage_percent": 12.5,
                        },
                        {
                            "rank": 2,
                            "pokemon_id": 6,
                            "api_name": "charizard",
                            "showdown_id": "charizard",
                            "showdown_name": "Charizard",
                            "usage_percent": 10.0,
                        },
                    ],
                }
            },
        }

        with TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "usage_stats.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            repository = UsageRepository(path)

        dataset = repository.dataset("reg-test")
        self.assertIsNotNone(dataset)
        assert dataset is not None
        self.assertEqual(dataset.month, "2026-10")
        self.assertEqual(
            repository.ranked_pokemon_ids("reg-test"),
            (25, 6),
        )
        self.assertEqual(
            repository.ranked_pokemon_ids("reg-test", limit=1),
            (25,),
        )


if __name__ == "__main__":
    unittest.main()
