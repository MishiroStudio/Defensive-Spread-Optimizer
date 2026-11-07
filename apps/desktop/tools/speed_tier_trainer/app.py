"""Cordy's Lab Speed Tier Trainer — app.py, version 7.

Run from the project root with:

    python apps/desktop/tools/speed_tier_trainer/app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMessageBox


if __package__ in (None, ""):
    for candidate in Path(__file__).resolve().parents:
        if (
            (candidate / "apps").is_dir()
            and (candidate / "shared").is_dir()
            and (candidate / "data").is_dir()
        ):
            sys.path.insert(0, str(candidate))
            break

    from apps.desktop.tools.speed_tier_trainer.trainer import TrainerCatalog
    from apps.desktop.tools.speed_tier_trainer.window import (
        SpeedTierTrainerWindow,
    )
else:
    from .trainer import TrainerCatalog
    from .window import SpeedTierTrainerWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Cordy's Lab Speed Tier Trainer")
    app.setApplicationVersion("7")

    try:
        catalog = TrainerCatalog()
    except (FileNotFoundError, ValueError) as error:
        QMessageBox.critical(
            None,
            "MISHIRO – Speed Tier Trainer",
            f"Die Trainer-Daten konnten nicht geladen werden:\n\n{error}",
        )
        return 1

    window = SpeedTierTrainerWindow(catalog)
    window.show()

    screen = app.primaryScreen()
    if screen is not None:
        geometry = window.frameGeometry()
        geometry.moveCenter(screen.availableGeometry().center())
        window.move(geometry.topLeft())

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

