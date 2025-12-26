from __future__ import annotations

from PyQt6.QtWidgets import QMainWindow, QTabWidget

from ..db import DatabaseManager
from ..style import AppStyle
from .dashboard import DashboardTab
from .history import HistoryTab


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MacOS AI Oracle")
        self.resize(900, 700)

        self.db = DatabaseManager()

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.dashboard = DashboardTab(self.db)
        self.history = HistoryTab(self.db)

        self.tabs.addTab(self.dashboard, "Dashboard")
        self.tabs.addTab(self.history, "History")

        self.setStyleSheet(
            f"""
            QMainWindow {{ background-color: {AppStyle.BG_MAIN}; }}
            
            /* Tabs */
            QTabWidget::pane {{ border: none; }}
            QTabBar::tab {{
                background: {AppStyle.BG_CARD};
                color: {AppStyle.TEXT_SECONDARY};
                padding: 12px 24px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                margin-right: 4px;
                font-weight: 600;
            }}
            QTabBar::tab:selected {{
                background: {AppStyle.ACCENT};
                color: {AppStyle.TEXT_PRIMARY};
            }}
            QTabBar::tab:hover:!selected {{
                background: {AppStyle.BG_INPUT};
                color: {AppStyle.TEXT_PRIMARY};
            }}

            /* Scrollbars */
            QScrollBar:vertical {{
                border: none;
                background: {AppStyle.BG_MAIN};
                width: 10px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {AppStyle.BG_INPUT};
                min-height: 20px;
                border-radius: 5px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            """
        )

    def closeEvent(self, event):
        try:
            self.db.close()
        finally:
            super().closeEvent(event)
