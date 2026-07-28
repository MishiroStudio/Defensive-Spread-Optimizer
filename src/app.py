import sys

from PySide6.QtWidgets import QApplication

from window import MainWindow


app = QApplication(sys.argv)

window = MainWindow()
window.show()

screen_geometry = app.primaryScreen().availableGeometry()
window_geometry = window.frameGeometry()

window_geometry.moveCenter(screen_geometry.center())
window.move(window_geometry.topLeft())

sys.exit(app.exec())