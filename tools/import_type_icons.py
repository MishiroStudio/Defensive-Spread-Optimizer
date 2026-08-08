"""Download the 18 regular Generation IX type symbols from PokéAPI.

The icons are stored locally for offline use in the Pokédex move table:

    assets/types/fire.png
    assets/types/water.png
    ...

Run this file once from anywhere with:

    python3 tools/import_type_icons.py

Existing valid PNG files are kept. Use ``--force`` to download them again.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


POKEAPI_BASE_URL = "https://pokeapi.co/api/v2"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIRECTORY = PROJECT_ROOT / "assets" / "types"

TYPE_NAMES = (
    "normal",
    "fire",
    "water",
    "electric",
    "grass",
    "ice",
    "fighting",
    "poison",
    "ground",
    "flying",
    "psychic",
    "bug",
    "rock",
    "ghost",
    "dragon",
    "dark",
    "steel",
    "fairy",
)

REQUEST_TIMEOUT_SECONDS = 30
MAX_REQUEST_ATTEMPTS = 5
RETRYABLE_HTTP_STATUS_CODES = {429, 500, 502, 503, 504}
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
USER_AGENT = "Cordys-Lab-Pokedex/0.1"


def request_bytes(url: str) -> bytes:
    """Return a URL response body, retrying temporary network failures."""

    for attempt in range(1, MAX_REQUEST_ATTEMPTS + 1):
        try:
            request = Request(
                url,
                headers={
                    "Accept": "application/json,image/png,*/*",
                    "User-Agent": USER_AGENT,
                },
            )
            with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
                return response.read()
        except HTTPError as error:
            retryable = error.code in RETRYABLE_HTTP_STATUS_CODES
            if not retryable or attempt == MAX_REQUEST_ATTEMPTS:
                raise RuntimeError(
                    f"HTTP {error.code} while downloading {url}"
                ) from error
        except (TimeoutError, URLError) as error:
            if attempt == MAX_REQUEST_ATTEMPTS:
                raise RuntimeError(f"Could not download {url}: {error}") from error

        time.sleep(min(2 ** (attempt - 1), 8))

    raise RuntimeError(f"Could not download {url}")


def request_json(url: str) -> dict[str, Any]:
    """Download a JSON object and validate its top-level type."""

    try:
        data = json.loads(request_bytes(url))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RuntimeError(f"Invalid JSON returned by {url}") from error

    if not isinstance(data, dict):
        raise RuntimeError(f"Expected a JSON object from {url}")
    return data


def generation_ix_symbol_url(type_data: dict[str, Any]) -> str:
    """Extract the Scarlet/Violet symbol URL from a PokéAPI type record."""

    try:
        url = type_data["sprites"]["generation-ix"]["scarlet-violet"][
            "symbol_icon"
        ]
    except (KeyError, TypeError) as error:
        type_name = type_data.get("name", "unknown")
        raise RuntimeError(
            f"PokéAPI has no Generation IX symbol for type '{type_name}'"
        ) from error

    if not isinstance(url, str) or not url.startswith("https://"):
        type_name = type_data.get("name", "unknown")
        raise RuntimeError(
            f"PokéAPI returned no valid symbol URL for type '{type_name}'"
        )
    return url


def is_valid_png(data: bytes) -> bool:
    """Return whether bytes start with the PNG file signature."""

    return data.startswith(PNG_SIGNATURE)


def write_png_atomic(path: Path, data: bytes) -> None:
    """Write a PNG without leaving a half-written destination file."""

    if not is_valid_png(data):
        raise RuntimeError(f"Downloaded data for {path.name} is not a PNG")

    temporary_path = path.with_suffix(path.suffix + ".tmp")
    temporary_path.write_bytes(data)
    temporary_path.replace(path)


def import_type_icon(
    type_name: str,
    output_directory: Path,
    *,
    force: bool,
) -> str:
    """Import one icon and return ``downloaded`` or ``kept``."""

    output_path = output_directory / f"{type_name}.png"
    if output_path.exists() and not force:
        try:
            if is_valid_png(output_path.read_bytes()):
                return "kept"
        except OSError:
            pass

    type_data = request_json(f"{POKEAPI_BASE_URL}/type/{type_name}")
    returned_name = type_data.get("name")
    if returned_name != type_name:
        raise RuntimeError(
            f"Requested type '{type_name}', but PokéAPI returned "
            f"'{returned_name}'"
        )

    icon_data = request_bytes(generation_ix_symbol_url(type_data))
    write_png_atomic(output_path, icon_data)
    return "downloaded"


def import_type_icons(output_directory: Path, *, force: bool = False) -> None:
    """Download all 18 regular type icons to ``output_directory``."""

    output_directory.mkdir(parents=True, exist_ok=True)
    downloaded = 0
    kept = 0

    for type_name in TYPE_NAMES:
        status = import_type_icon(
            type_name,
            output_directory,
            force=force,
        )
        if status == "downloaded":
            downloaded += 1
            print(f"Downloaded {type_name}.png")
        else:
            kept += 1
            print(f"Kept       {type_name}.png")

    print()
    print(f"Type icons ready: {len(TYPE_NAMES)}")
    print(f"Downloaded: {downloaded}, already present: {kept}")
    print(f"Saved to: {output_directory}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download Generation IX type symbols from PokéAPI."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_DIRECTORY,
        help="Target directory (default: assets/types)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Download icons again even when valid PNG files already exist.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    import_type_icons(args.output.resolve(), force=args.force)


if __name__ == "__main__":
    main()