"""Read centrally imported competitive Pokémon usage rankings."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from shared.paths import USAGE_STATS_FILE


@dataclass(frozen=True, slots=True)
class UsageEntry:
    rank: int
    pokemon_id: int
    api_name: str
    showdown_id: str
    showdown_name: str
    usage_percent: float


@dataclass(frozen=True, slots=True)
class UsageDataset:
    scope_id: str
    format_id: str
    month: str
    rating_cutoff: int
    total_battles: int
    source_url: str
    entries: tuple[UsageEntry, ...]


class UsageRepository:
    """Load shared usage data once and expose regulation rankings."""

    def __init__(
        self,
        file_path: str | Path = USAGE_STATS_FILE,
    ) -> None:
        self.file_path = Path(file_path)
        self.current_regulation_id = ""
        self.imported_at = ""
        self._datasets: dict[str, UsageDataset] = {}
        self.reload()

    def reload(self) -> None:
        if not self.file_path.is_file():
            raise FileNotFoundError(
                f"Usage data not found: {self.file_path}"
            )

        try:
            raw_data = json.loads(
                self.file_path.read_text(encoding="utf-8")
            )
        except json.JSONDecodeError as error:
            raise ValueError(
                f"Invalid JSON in {self.file_path}: {error}"
            ) from error

        if not isinstance(raw_data, dict):
            raise ValueError("usage_stats.json must contain a JSON object")
        if raw_data.get("schema_version") != 1:
            raise ValueError("Unsupported usage_stats.json schema version")

        current_regulation_id = raw_data.get("current_regulation_id")
        formats = raw_data.get("formats")
        source = raw_data.get("source")
        if not isinstance(current_regulation_id, str) or not isinstance(
            formats,
            dict,
        ):
            raise ValueError("usage_stats.json contains an invalid structure")

        datasets: dict[str, UsageDataset] = {}
        for scope_id, record in formats.items():
            if not isinstance(scope_id, str) or not isinstance(record, dict):
                raise ValueError("usage_stats.json contains an invalid format")
            datasets[scope_id] = self._parse_dataset(scope_id, record)

        if current_regulation_id not in datasets:
            raise ValueError(
                "Current regulation is missing from usage_stats.json"
            )

        self.current_regulation_id = current_regulation_id
        self.imported_at = (
            str(source.get("imported_at", ""))
            if isinstance(source, dict)
            else ""
        )
        self._datasets = datasets

    @staticmethod
    def _parse_dataset(
        scope_id: str,
        record: dict[str, Any],
    ) -> UsageDataset:
        required = {
            "format_id": str,
            "month": str,
            "rating_cutoff": int,
            "total_battles": int,
            "source_url": str,
            "entries": list,
        }
        if any(
            not isinstance(record.get(key), expected_type)
            for key, expected_type in required.items()
        ):
            raise ValueError(
                f"Invalid usage dataset for scope {scope_id!r}"
            )

        entries: list[UsageEntry] = []
        seen_ranks: set[int] = set()
        seen_ids: set[int] = set()
        for item in record["entries"]:
            if not isinstance(item, dict):
                raise ValueError(
                    f"Invalid usage entry for scope {scope_id!r}"
                )
            try:
                entry = UsageEntry(
                    rank=int(item["rank"]),
                    pokemon_id=int(item["pokemon_id"]),
                    api_name=str(item["api_name"]),
                    showdown_id=str(item["showdown_id"]),
                    showdown_name=str(item["showdown_name"]),
                    usage_percent=float(item["usage_percent"]),
                )
            except (KeyError, TypeError, ValueError) as error:
                raise ValueError(
                    f"Invalid usage entry for scope {scope_id!r}"
                ) from error
            if entry.rank < 1 or entry.pokemon_id < 1:
                raise ValueError(
                    f"Invalid usage entry for scope {scope_id!r}"
                )
            if entry.rank in seen_ranks or entry.pokemon_id in seen_ids:
                raise ValueError(
                    f"Duplicate usage entry for scope {scope_id!r}"
                )
            seen_ranks.add(entry.rank)
            seen_ids.add(entry.pokemon_id)
            entries.append(entry)

        entries.sort(key=lambda item: item.rank)
        return UsageDataset(
            scope_id=scope_id,
            format_id=str(record["format_id"]),
            month=str(record["month"]),
            rating_cutoff=int(record["rating_cutoff"]),
            total_battles=int(record["total_battles"]),
            source_url=str(record["source_url"]),
            entries=tuple(entries),
        )

    def dataset(self, scope_id: str) -> UsageDataset | None:
        return self._datasets.get(scope_id)

    def ranked_pokemon_ids(
        self,
        scope_id: str,
        limit: int | None = None,
    ) -> tuple[int, ...]:
        dataset = self.dataset(scope_id)
        if dataset is None:
            return ()
        if limit is not None and limit < 1:
            raise ValueError("Usage limit must be at least 1")
        entries = dataset.entries if limit is None else dataset.entries[:limit]
        return tuple(entry.pokemon_id for entry in entries)
