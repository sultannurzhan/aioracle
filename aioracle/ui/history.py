from __future__ import annotations

from datetime import datetime

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QPushButton, QHeaderView

from ..db import DatabaseManager
from ..style import AppStyle

from ..mpl import get_mpl


class HistoryTab(QWidget):
    def __init__(self, db_manager: DatabaseManager):
        super().__init__()
        self.db = db_manager

        FigureCanvas, Figure, mdates = get_mpl()
        self._FigureCanvas = FigureCanvas
        self._Figure = Figure
        self._mdates = mdates

        self._init_ui()
        self.load_history()

    def _init_ui(self) -> None:
        layout = QVBoxLayout()
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        self.figure = self._Figure()
        self.canvas = self._FigureCanvas(self.figure)
        layout.addWidget(self.canvas)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Timestamp", "AGI Date", "ASI Date", "Singularity"])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setStyleSheet(
            f"QTableWidget {{ background: {AppStyle.BG_CARD}; color: {AppStyle.TEXT_PRIMARY}; border: 1px solid {AppStyle.BORDER}; border-radius: 12px; gridline-color: {AppStyle.BORDER}; }}"
            f" QTableWidget::item {{ padding: 8px; }}"
            f" QTableWidget::item:selected {{ background: {AppStyle.BG_INPUT}; }}"
            f" QHeaderView::section {{ background: {AppStyle.BG_INPUT}; color: {AppStyle.TEXT_PRIMARY}; padding: 10px; border: none; font-weight: 700; }}"
        )
        layout.addWidget(self.table)

        btn_refresh = QPushButton("Refresh History / Compare")
        btn_refresh.clicked.connect(self.load_history)
        btn_refresh.setMinimumHeight(40)
        btn_refresh.setStyleSheet(
            f"QPushButton {{ background: {AppStyle.GRADIENT_BTN}; color: {AppStyle.TEXT_PRIMARY}; font-weight: 700; border-radius: 12px; padding: 10px 14px; }}"
            f" QPushButton:hover {{ background: {AppStyle.ACCENT_HOVER}; }}"
            f" QPushButton:pressed {{ background: {AppStyle.ACCENT_PRESSED}; }}"
        )
        layout.addWidget(btn_refresh)

        self.setLayout(layout)

    def load_history(self) -> None:
        data = self.db.get_history()
        self.table.setRowCount(0)

        series_agi: list[tuple[datetime, datetime]] = []
        series_asi: list[tuple[datetime, datetime]] = []
        series_sing: list[tuple[datetime, datetime]] = []

        for row in data:
            row_idx = self.table.rowCount()
            self.table.insertRow(row_idx)

            self.table.setItem(row_idx, 0, QTableWidgetItem(row[1][:16]))
            self.table.setItem(row_idx, 1, QTableWidgetItem(row[2]))
            self.table.setItem(row_idx, 2, QTableWidgetItem(row[5]))
            self.table.setItem(row_idx, 3, QTableWidgetItem(row[7]))

            try:
                ts = datetime.fromisoformat(row[1])
            except Exception:
                continue

            try:
                agi = datetime.strptime(row[2], "%Y-%m-%d")
                series_agi.append((ts, agi))
            except Exception:
                pass

            try:
                asi = datetime.strptime(row[5], "%Y-%m-%d")
                series_asi.append((ts, asi))
            except Exception:
                pass

            try:
                sing = datetime.strptime(row[7], "%Y-%m-%d")
                series_sing.append((ts, sing))
            except Exception:
                pass

        self._plot_chart(series_agi=series_agi, series_asi=series_asi, series_sing=series_sing)

    def _plot_chart(
        self,
        *,
        series_agi: list[tuple[datetime, datetime]],
        series_asi: list[tuple[datetime, datetime]],
        series_sing: list[tuple[datetime, datetime]],
    ) -> None:
        self.figure.clear()
        ax = self.figure.add_subplot(111)

        # Dark theme chart styling
        self.figure.set_facecolor(AppStyle.BG_CARD)
        ax.set_facecolor(AppStyle.BG_CARD)

        if series_agi or series_asi or series_sing:
            def _plot(series: list[tuple[datetime, datetime]], *, label: str, linestyle: str, marker: str) -> None:
                if not series:
                    return
                series_sorted = sorted(series, key=lambda t: t[0])
                x = [t[0] for t in series_sorted]
                y = [t[1] for t in series_sorted]
                ax.plot(
                    x,
                    y,
                    marker=marker,
                    linestyle=linestyle,
                    color=AppStyle.ACCENT,
                    label=label,
                    linewidth=2,
                    markersize=4,
                )

            _plot(series_agi, label="AGI", linestyle="-", marker="o")
            _plot(series_asi, label="ASI", linestyle="--", marker="s")
            _plot(series_sing, label="Singularity", linestyle=":", marker="^")

            ax.xaxis.set_major_formatter(self._mdates.DateFormatter("%m-%d %H:%M"))
            ax.yaxis.set_major_formatter(self._mdates.DateFormatter("%Y"))

            ax.set_title("History of Timeline Predictions", color=AppStyle.TEXT_PRIMARY)
            ax.set_ylabel("Predicted Year", color=AppStyle.TEXT_SECONDARY)
            ax.set_xlabel("Prediction Timestamp", color=AppStyle.TEXT_SECONDARY)
            ax.tick_params(colors=AppStyle.TEXT_SECONDARY)
            ax.grid(True, linestyle="--", alpha=0.25, color=AppStyle.BORDER)
            legend = ax.legend(frameon=True)
            legend.get_frame().set_facecolor(AppStyle.BG_CARD)
            legend.get_frame().set_edgecolor(AppStyle.BORDER)
        else:
            ax.set_title("No prediction history yet", color=AppStyle.TEXT_SECONDARY)
            ax.axis("off")

        self.canvas.draw()
