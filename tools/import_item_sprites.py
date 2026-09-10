"""Download PokéAPI item sprites for Cordy's Lab — version 1.

The item catalog stores predictable local paths such as
``assets/items/sitrus-berry.png``. This tool resolves the canonical sprite URL
through PokéAPI and downloads the PNG files without changing ``items.json``.

Run from the project root with:

    python tools/import_item_sprites.py

Useful test options:

    python tools/import_item_sprites.py --limit 10
    python tools/import_item_sprites.py --overwrite
"""

from __future__ import annotations

import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


IMPORTER_VERSION = "v1"
POKEAPI_BASE_URL = "https://pokeapi.co/api/v2"
REQUEST_TIMEOUT_SECONDS = 60
MAX_REQUEST_ATTEMPTS = 6
RETRYABLE_HTTP_STATUS_CODES = {429, 500, 502, 503, 504}
USER_AGENT = "Cordys-Lab-Item-Sprites/1.0"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ITEMS_FILE = PROJECT_ROOT / "data" / "items.json"
SPRITES_DIRECTORY = PROJECT_ROOT / "assets" / "items"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def load_items(path: Path = ITEMS_FILE) -> list[dict[str, Any]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise RuntimeError(f"Item catalog not found: {path}") from error
    except json.JSONDecodeError as error:
        raise RuntimeError(f"Invalid JSON in {path}: {error}") from error
    if not isinstance(data, list):
        raise RuntimeError(f"Expected a JSON list in {path}")
    return data


def destination_for_item(item: dict[str, Any]) -> Path:
    api_name = item.get("api_name")
    if not isinstance(api_name, str) or not api_name:
        raise ValueError("Every item needs a non-empty api_name.")
    relative_path = item.get("sprite") or f"assets/items/{api_name}.png"
    if not isinstance(relative_path, str):
        raise ValueError(f"Invalid sprite path for {api_name}")

    destination = (PROJECT_ROOT / relative_path).resolve()
    sprites_root = SPRITES_DIRECTORY.resolve()
    if not destination.is_relative_to(sprites_root):
        raise ValueError(f"Sprite path escapes assets/items: {relative_path}")
    if destination.suffix.casefold() != ".png":
        raise ValueError(f"Sprite path is not a PNG: {relative_path}")
    return destination


def request_bytes(url: str) -> bytes:
    last_error: Exception | None = None
    for attempt in range(1, MAX_REQUEST_ATTEMPTS + 1):
        request = Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urlopen(  # noqa: S310 - URLs originate from PokéAPI.
                request,
                timeout=REQUEST_TIMEOUT_SECONDS,
            ) as response:
                return response.read()
        except HTTPError as error:
            last_error = error
            if error.code not in RETRYABLE_HTTP_STATUS_CODES:
                raise
        except (TimeoutError, URLError) as error:
            last_error = error

        if attempt < MAX_REQUEST_ATTEMPTS:
            time.sleep(min(2 ** (attempt - 1), 12))

    raise RuntimeError(f"Request failed after retries: {url}") from last_error


def request_json(url: str) -> dict[str, Any]:
    try:
        data = json.loads(request_bytes(url).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RuntimeError(f"PokéAPI returned invalid JSON: {url}") from error
    if not isinstance(data, dict):
        raise RuntimeError(f"PokéAPI returned a non-object response: {url}")
    return data


def download_item_sprite(
    item: dict[str, Any],
    *,
    overwrite: bool,
) -> tuple[str, str, Path | None]:
    api_name = str(item["api_name"])
    destination = destination_for_item(item)
    if destination.is_file() and destination.stat().st_size > 0 and not overwrite:
        return api_name, "skipped", destination

    item_id = item.get("item_id")
    resource = item_id if isinstance(item_id, int) else api_name
    api_item = request_json(f"{POKEAPI_BASE_URL}/item/{resource}/")
    sprites = api_item.get("sprites")
    sprite_url = sprites.get("default") if isinstance(sprites, dict) else None
    if not isinstance(sprite_url, str) or not sprite_url:
        return api_name, "missing", None

    image = request_bytes(sprite_url)
    if not image.startswith(PNG_SIGNATURE):
        raise RuntimeError(f"Sprite for {api_name} is not a valid PNG.")

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(".tmp.png")
    temporary.write_bytes(image)
    temporary.replace(destination)
    return api_name, "downloaded", destination


def import_item_sprites(
    *,
    workers: int,
    limit: int | None,
    overwrite: bool,
) -> dict[str, int]:
    if workers < 1:
        raise ValueError("--workers must be at least 1.")
    if limit is not None and limit < 1:
        raise ValueError("--limit must be at least 1.")

    items = sorted(load_items(), key=lambda item: int(item["item_id"]))
    if limit is not None:
        items = items[:limit]
    SPRITES_DIRECTORY.mkdir(parents=True, exist_ok=True)

    counts = {"downloaded": 0, "skipped": 0, "missing": 0, "failed": 0}
    failures: list[str] = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(
                download_item_sprite,
                item,
                overwrite=overwrite,
            ): str(item["api_name"])
            for item in items
        }
        total = len(futures)
        for position, future in enumerate(as_completed(futures), start=1):
            api_name = futures[future]
            try:
                _name, status, _path = future.result()
            except Exception as error:  # Report every failed item together.
                status = "failed"
                failures.append(f"{api_name}: {error}")
            counts[status] += 1
            print(f"[{position:>3}/{total}] {status:<10} {api_name}")

    if failures:
        details = "\n".join(f"  - {failure}" for failure in failures)
        raise RuntimeError(f"{len(failures)} sprite downloads failed:\n{details}")
    return counts


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download local PokéAPI item sprites."
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=12,
        help="parallel downloads (default: 12)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="only process the first N items",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="download existing sprites again",
    )
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    counts = import_item_sprites(
        workers=arguments.workers,
        limit=arguments.limit,
        overwrite=arguments.overwrite,
    )
    print("\nDone!")
    print(f"Downloaded: {counts['downloaded']}")
    print(f"Already present: {counts['skipped']}")
    print(f"No PokéAPI sprite: {counts['missing']}")
    print(f"Saved in: {SPRITES_DIRECTORY}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
