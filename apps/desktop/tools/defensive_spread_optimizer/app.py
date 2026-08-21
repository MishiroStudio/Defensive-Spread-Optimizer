import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication


if __package__ in (None, ""):
    for candidate in Path(__file__).resolve().parents:
        if (
            (candidate / "apps").is_dir()
            and (candidate / "shared").is_dir()
        ):
            sys.path.insert(0, str(candidate))
            break

    from apps.desktop.tools.defensive_spread_optimizer.window import MainWindow
else:
    from .window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    screen_geometry = app.primaryScreen().availableGeometry()
    window_geometry = window.frameGeometry()

    window_geometry.moveCenter(screen_geometry.center())
    window.move(window_geometry.topLeft())

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())