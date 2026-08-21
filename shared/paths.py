"""Stable paths shared by the Cordy's Lab applications."""

from __future__ import annotations

import sys
from pathlib import Path


def _find_project_root() -> Path:
    """Return the source root or PyInstaller bundle root."""
    if getattr(sys, "frozen", False):
        bundle_root = getattr(sys, "_MEIPASS", None)
        if bundle_root:
            return Path(bundle_root)

        return Path(sys.executable).resolve().parent

    current_file = Path(__file__).resolve()

    for candidate in current_file.parents:
        if (
            (candidate / "data").is_dir()
            and (candidate / "assets").is_dir()
        ):
            return candidate

    raise RuntimeError(
        "Could not locate the Cordy's Lab project root. "
        "Expected directories named 'data' and 'assets'."
    )


PROJECT_ROOT = _find_project_root()
DATA_DIR = PROJECT_ROOT / "data"
ASSETS_DIR = PROJECT_ROOT / "assets"

POKEMON_V2_FILE = DATA_DIR / "pokemon_v2.json"