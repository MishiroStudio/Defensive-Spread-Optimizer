"""Import shared Pokémon Showdown usage rankings — version 1.

The importer downloads the newest completed monthly 1760-rating usage table
available for every regulation in ``data/regulations.json``. It maps Showdown
form names to the local PokéAPI-backed form IDs and writes one offline snapshot
to ``data/usage_stats.json``. Desktop and web applications can then consume the
same rankings without making network requests at application startup.

Run from the project root with:

    python3 tools/import_usage_stats.py

Use ``--cutoff`` to select another published ladder rating and ``--start-month``
to reproduce an older snapshot.
"""

from __future__ import annotations

import argparse
import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable

try:
    from tools.import_regulations import (
        flatten_forms,
        form_showdown_candidates,
        load_json,
        to_showdown_id,
        write_json_atomically,
    )
except ModuleNotFoundError:  # Direct execution from the tools directory.
    from import_regulations import (  # type: ignore[no-redef]
        flatten_forms,
        form_showdown_candidates,
        load_json,
        to_showdown_id,
        write_json_atomically,
    )


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_NAME = "usage_stats.json"
SMOGON_STATS_ROOT = "https://www.smogon.com/stats"
USER_AGENT = "CordysLab-Usage-Importer/1.0"
MONTH_RE = re.compile(r"^\d{4}-(?:0[1-9]|1[0-2])$")
TOTAL_BATTLES_RE = re.compile(r"^Total battles:\s*(\d+)\s*$")
USAGE_ROW_RE = re.compile(
    r"^\|\s*(?P<rank>\d+)\s*"
    r"\|\s*(?P<name>.+?)\s*"
    r"\|\s*(?P<usage>\d+(?:\.\d+)?)%\s*\|"
)


@dataclass(frozen=True, slots=True)
class ParsedUsage:
    rank: int
    showdown_name: str
    usage_percent: float


def parse_usage_table(text: str) -> tuple[int, tuple[ParsedUsage, ...]]:
    """Parse Smogon's compact monthly usage text format."""
    total_battles: int | None = None
    entries: list[ParsedUsage] = []
    for line in text.splitlines():
        total_match = TOTAL_BATTLES_RE.match(line)
        if total_match is not None:
            total_battles = int(total_match.group(1))
            continue
        row_match = USAGE_ROW_RE.match(line)
        if row_match is None:
            continue
        entries.append(
            ParsedUsage(
                rank=int(row_match.group("rank")),
                showdown_name=row_match.group("name").strip(),
                usage_percent=float(row_match.group("usage")),
            )
        )

    if total_battles is None or not entries:
        raise ValueError("Smogon usage table has an invalid structure")
    entries.sort(key=lambda entry: entry.rank)
    return total_battles, tuple(entries)


def previous_month(value: date) -> date:
    if value.month == 1:
        return date(value.year - 1, 12, 1)
    return date(value.year, value.month - 1, 1)


def completed_months(
    start_month: str | None,
    count: int,
    *,
    today: date | None = None,
) -> tuple[str, ...]:
    """Return newest-to-oldest month labels, excluding the current month."""
    if count < 1:
        raise ValueError("months-back must be at least 1")
    if start_month is not None:
        if MONTH_RE.fullmatch(start_month) is None:
            raise ValueError("start-month must use YYYY-MM")
        current = datetime.strptime(start_month, "%Y-%m").date()
    else:
        current = previous_month((today or date.today()).replace(day=1))

    result: list[str] = []
    for _ in range(count):
        result.append(current.strftime("%Y-%m"))
        current = previous_month(current)
    return tuple(result)


def stats_url(month: str, format_id: str, cutoff: int) -> str:
    return f"{SMOGON_STATS_ROOT}/{month}/{format_id}-{cutoff}.txt"


def download_text(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8")


def find_latest_table(
    format_id: str,
    cutoff: int,
    months: Iterable[str],
) -> tuple[str, str, str]:
    """Return ``month, URL, text`` for the newest published table."""
    for month in months:
        url = stats_url(month, format_id, cutoff)
        try:
            return month, url, download_text(url)
        except urllib.error.HTTPError as error:
            if error.code == 404:
                continue
            raise RuntimeError(f"Could not download {url}: {error}") from error
        except (urllib.error.URLError, TimeoutError) as error:
            raise RuntimeError(f"Could not download {url}: {error}") from error
    raise FileNotFoundError(
        f"No published usage table found for {format_id} at cutoff {cutoff}"
    )


def candidate_map(
    forms: list[dict[str, Any]],
) -> dict[str, list[tuple[int, dict[str, Any]]]]:
    """Index local forms by their ordered Showdown naming candidates."""
    result: dict[str, list[tuple[int, dict[str, Any]]]] = {}
    for form in forms:
        for priority, candidate in enumerate(form_showdown_candidates(form)):
            result.setdefault(candidate, []).append((priority, form))
    for candidates in result.values():
        candidates.sort(
            key=lambda item: (
                item[0],
                not bool(item[1].get("is_default")),
                int(item[1]["pokemon_id"]),
            )
        )
    return result


def resolve_local_form(
    showdown_name: str,
    candidates_by_id: dict[str, list[tuple[int, dict[str, Any]]]],
    legal_ids: frozenset[int],
) -> tuple[str, dict[str, Any]] | None:
    showdown_id = to_showdown_id(showdown_name)
    candidates = candidates_by_id.get(showdown_id, ())
    legal_candidates = [
        form
        for _priority, form in candidates
        if int(form["pokemon_id"]) in legal_ids
    ]
    if not legal_candidates:
        return None
    return showdown_id, legal_candidates[0]


def regulation_format_id(record: dict[str, Any]) -> str:
    format_name = record.get("format_name")
    if not isinstance(format_name, str) or not format_name:
        raise ValueError("Regulation record has no valid format_name")
    return to_showdown_id(format_name)


def import_usage_stats(
    data_dir: Path,
    *,
    cutoff: int = 1760,
    start_month: str | None = None,
    months_back: int = 24,
) -> tuple[Path, dict[str, Any]]:
    if cutoff < 0:
        raise ValueError("cutoff must not be negative")

    regulations_data = load_json(data_dir / "regulations.json")
    pokemon_data = load_json(data_dir / "pokemon_v2.json")
    if not isinstance(regulations_data, dict) or not isinstance(
        regulations_data.get("regulations"),
        list,
    ):
        raise ValueError("regulations.json contains an invalid structure")
    current_regulation_id = regulations_data.get("current_regulation_id")
    if not isinstance(current_regulation_id, str):
        raise ValueError("regulations.json has no current regulation")

    forms = flatten_forms(pokemon_data)
    candidates_by_id = candidate_map(forms)
    months = completed_months(start_month, months_back)
    datasets: dict[str, Any] = {}

    for regulation in regulations_data["regulations"]:
        if not isinstance(regulation, dict):
            continue
        scope_id = regulation.get("id")
        pokemon_ids = regulation.get("pokemon_ids")
        if not isinstance(scope_id, str) or not isinstance(pokemon_ids, list):
            continue

        format_id = regulation_format_id(regulation)
        print(f"Finding usage data for {regulation.get('name', scope_id)} …")
        month, source_url, table_text = find_latest_table(
            format_id,
            cutoff,
            months,
        )
        total_battles, parsed_entries = parse_usage_table(table_text)
        legal_ids = frozenset(
            pokemon_id
            for pokemon_id in pokemon_ids
            if isinstance(pokemon_id, int)
        )

        entries: list[dict[str, Any]] = []
        unresolved: list[dict[str, Any]] = []
        seen_local_ids: set[int] = set()
        for usage in parsed_entries:
            resolved = resolve_local_form(
                usage.showdown_name,
                candidates_by_id,
                legal_ids,
            )
            if resolved is None:
                unresolved.append(
                    {
                        "rank": usage.rank,
                        "showdown_name": usage.showdown_name,
                        "usage_percent": usage.usage_percent,
                    }
                )
                continue
            showdown_id, form = resolved
            pokemon_id = int(form["pokemon_id"])
            if pokemon_id in seen_local_ids:
                unresolved.append(
                    {
                        "rank": usage.rank,
                        "showdown_name": usage.showdown_name,
                        "usage_percent": usage.usage_percent,
                        "reason": "maps to an already ranked local form",
                    }
                )
                continue
            seen_local_ids.add(pokemon_id)
            entries.append(
                {
                    "rank": usage.rank,
                    "pokemon_id": pokemon_id,
                    "api_name": str(form["api_name"]),
                    "showdown_id": showdown_id,
                    "showdown_name": usage.showdown_name,
                    "usage_percent": usage.usage_percent,
                }
            )

        datasets[scope_id] = {
            "format_id": format_id,
            "month": month,
            "rating_cutoff": cutoff,
            "total_battles": total_battles,
            "source_url": source_url,
            "entries": entries,
            "unresolved": unresolved,
        }
        print(
            f"  {month}: {len(entries)} mapped, "
            f"{len(unresolved)} unresolved, {total_battles} battles"
        )

    if current_regulation_id not in datasets:
        raise ValueError("No usage data was imported for the current regulation")

    output = {
        "schema_version": 1,
        "source": {
            "name": "Smogon Pokémon Showdown usage statistics",
            "stats_root": SMOGON_STATS_ROOT,
            "rating_cutoff": cutoff,
            "imported_at": datetime.now(timezone.utc).isoformat(),
        },
        "current_regulation_id": current_regulation_id,
        "formats": datasets,
    }
    output_file = data_dir / OUTPUT_NAME
    write_json_atomically(output, output_file)
    return output_file, output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help="Directory containing regulations.json and pokemon_v2.json.",
    )
    parser.add_argument(
        "--cutoff",
        type=int,
        default=1760,
        help="Smogon ladder rating cutoff (default: 1760).",
    )
    parser.add_argument(
        "--start-month",
        help="Newest month to try in YYYY-MM format (default: last month).",
    )
    parser.add_argument(
        "--months-back",
        type=int,
        default=24,
        help="Number of months searched per regulation (default: 24).",
    )
    args = parser.parse_args()

    output_file, output = import_usage_stats(
        args.data_dir,
        cutoff=args.cutoff,
        start_month=args.start_month,
        months_back=args.months_back,
    )
    print()
    print(f"Wrote {output_file}")
    print(
        json.dumps(
            {
                scope_id: {
                    "month": dataset["month"],
                    "entries": len(dataset["entries"]),
                }
                for scope_id, dataset in output["formats"].items()
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
