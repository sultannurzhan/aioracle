import sys

from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication

from aioracle.ui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setFont(QFont("Helvetica Neue", 12))

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())