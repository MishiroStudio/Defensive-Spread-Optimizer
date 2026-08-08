"""Create compact Pokémon sprites for Pokédex result lists.

Run from the project root with:

    python3 tools/create_list_sprites.py

The script reads the existing high-resolution HOME sprites from:

    assets/sprites/home/normal/

and writes compact PNG thumbnails to:

    assets/sprites/list/normal/

The default maximum size is 64x64 px, which is large enough for the current
25 px result icon even on a Retina/HiDPI display, while being much cheaper to
load and decode than the original HOME sprites.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QImage


PROJECT_DIRECTORY = Path(__file__).resolve().parent.parent
SOURCE_DIRECTORY = (
    PROJECT_DIRECTORY / "assets" / "sprites" / "home" / "normal"
)
OUTPUT_DIRECTORY = (
    PROJECT_DIRECTORY / "assets" / "sprites" / "list" / "normal"
)

DEFAULT_SIZE = 64


def create_thumbnail(
    source: Path,
    destination: Path,
    *,
    size: int,
    force: bool,
) -> str:
    """Create one compact transparent PNG and return its status."""
    if (
        not force
        and destination.exists()
        and destination.stat().st_mtime >= source.stat().st_mtime
    ):
        return "skipped"

    image = QImage(str(source))
    if image.isNull():
        raise ValueError(f"Could not read image: {source}")

    scaled = image.scaled(
        QSize(size, size),
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )

    destination.parent.mkdir(parents=True, exist_ok=True)
    if not scaled.save(str(destination), "PNG"):
        raise OSError(f"Could not save thumbnail: {destination}")

    return "created"


def create_list_sprites(
    *,
    source_directory: Path = SOURCE_DIRECTORY,
    output_directory: Path = OUTPUT_DIRECTORY,
    size: int = DEFAULT_SIZE,
    force: bool = False,
) -> tuple[int, int]:
    """Create compact copies of every normal HOME sprite."""
    if size < 1:
        raise ValueError("Thumbnail size must be at least 1 px.")
    if not source_directory.is_dir():
        raise FileNotFoundError(
            f"Missing HOME sprite directory: {source_directory}"
        )

    sources = sorted(source_directory.glob("*.png"))
    if not sources:
        raise FileNotFoundError(
            f"No PNG sprites found in: {source_directory}"
        )

    created = 0
    skipped = 0

    for source in sources:
        destination = output_directory / source.name
        status = create_thumbnail(
            source,
            destination,
            size=size,
            force=force,
        )
        if status == "created":
            created += 1
        else:
            skipped += 1

    return created, skipped


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create compact Pokémon sprites for Pokédex result lists."
    )
    parser.add_argument(
        "--size",
        type=int,
        default=DEFAULT_SIZE,
        help=f"Maximum width/height in pixels (default: {DEFAULT_SIZE}).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Recreate thumbnails even when the existing copy is up to date.",
    )
    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()
    created, skipped = create_list_sprites(
        size=arguments.size,
        force=arguments.force,
    )

    print()
    print("Done!")
    print(f"Created: {created}")
    print(f"Already up to date: {skipped}")
    print(f"Saved to: {OUTPUT_DIRECTORY}")


if __name__ == "__main__":
    main()