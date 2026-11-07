"""Cordy's Lab Damage Calculator desktop interface.

Run from the project root with:

    python apps/desktop/tools/damage_calculator/app.py
"""

from __future__ import annotations

import sys
from pathlib import Path


def _bootstrap_project_root() -> None:
    for candidate in Path(__file__).resolve().parents:
        if (candidate / "apps").is_dir() and (candidate / "shared").is_dir() and (candidate / "data").is_dir():
            if str(candidate) not in sys.path:
                sys.path.insert(0, str(candidate))
            return
    raise RuntimeError("Could not find the Cordy's Lab project root.")


_bootstrap_project_root()

from PySide6.QtWidgets import QApplication, QMessageBox

from apps.desktop.tools.damage_calculator.data import CalculatorData
from apps.desktop.tools.damage_calculator.window import DamageCalculatorWindow


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("Cordy's Lab Damage Calculator")
    try:
        data = CalculatorData()
    except Exception as error:
        QMessageBox.critical(None, "Damage Calculator", str(error))
        return 1
    window = DamageCalculatorWindow(data)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
