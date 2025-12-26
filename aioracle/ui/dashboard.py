from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QProgressBar,
    QFrame,
)

from ..backend import PredictionEngine
from ..db import DatabaseManager
from ..models import Prediction
from ..style import AppStyle
from ..workers import AnalysisWorker


class DashboardTab(QWidget):
    def __init__(self, db_manager: DatabaseManager):
        super().__init__()
        self.db = db_manager
        self.engine = PredictionEngine()
        self.worker: Optional[AnalysisWorker] = None
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout()
        layout.setSpacing(18)
        layout.setContentsMargins(28, 24, 28, 24)

        title = QLabel("AI Timeline Oracle")
        title.setFont(QFont("Helvetica Neue", 28, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(f"color: {AppStyle.TEXT_PRIMARY};")
        layout.addWidget(title)

        self.status_label = QLabel("Ready to analyze.")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet(f"color: {AppStyle.TEXT_SECONDARY};")
        layout.addWidget(self.status_label)

        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet(
            f"QProgressBar {{ height: 8px; border-radius: 4px; background: {AppStyle.BG_INPUT}; }}"
            f" QProgressBar::chunk {{ background: {AppStyle.ACCENT}; border-radius: 4px; }}"
        )
        layout.addWidget(self.progress)

        cards_layout = QHBoxLayout()

        self.card_agi = self._create_prediction_card("First AGI", "Unknown", "Waiting...")
        self.card_asi = self._create_prediction_card("First ASI", "Unknown", "Waiting...")
        self.card_sing = self._create_prediction_card("Singularity", "Unknown", "Waiting...")

        cards_layout.addWidget(self.card_agi)
        cards_layout.addWidget(self.card_asi)
        cards_layout.addWidget(self.card_sing)
        layout.addLayout(cards_layout)

        self.refresh_btn = QPushButton("Calculate New Prediction")
        self.refresh_btn.setMinimumHeight(50)
        self.refresh_btn.setStyleSheet(
            f"QPushButton {{ background: {AppStyle.GRADIENT_BTN}; color: {AppStyle.TEXT_PRIMARY}; font-size: 16px; font-weight: 700; border-radius: 12px; padding: 10px 14px; }}"
            f" QPushButton:hover {{ background: {AppStyle.ACCENT_HOVER}; }}"
            f" QPushButton:pressed {{ background: {AppStyle.ACCENT_PRESSED}; }}"
            f" QPushButton:disabled {{ background: {AppStyle.BG_INPUT}; color: {AppStyle.TEXT_SECONDARY}; }}"
        )
        self.refresh_btn.clicked.connect(self.start_analysis)
        layout.addWidget(self.refresh_btn)

        layout.addStretch()
        self.setLayout(layout)

    def _create_prediction_card(self, title: str, date_placeholder: str, detail_placeholder: str) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(
            f"QFrame {{ background-color: {AppStyle.BG_CARD}; border: 1px solid {AppStyle.BORDER}; border-radius: 16px; }}"
        )

        layout = QVBoxLayout()
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(8)

        lbl_title = QLabel(title)
        lbl_title.setFont(QFont("Helvetica", 14, QFont.Weight.Bold))
        lbl_title.setStyleSheet(f"border: none; color: {AppStyle.TEXT_PRIMARY};")

        lbl_date = QLabel(date_placeholder)
        lbl_date.setFont(QFont("Helvetica", 24, QFont.Weight.Bold))
        lbl_date.setStyleSheet(f"border: none; color: {AppStyle.ACCENT};")

        lbl_detail = QLabel(detail_placeholder)
        lbl_detail.setWordWrap(True)
        lbl_detail.setStyleSheet(f"border: none; color: {AppStyle.TEXT_SECONDARY};")

        layout.addWidget(lbl_title)
        layout.addWidget(lbl_date)
        layout.addWidget(lbl_detail)
        layout.addStretch()
        frame.setLayout(layout)

        frame.lbl_date = lbl_date
        frame.lbl_detail = lbl_detail
        return frame

    def start_analysis(self) -> None:
        self.refresh_btn.setEnabled(False)
        self.progress.setValue(0)

        self.worker = AnalysisWorker(self.engine)
        self.worker.progress_update.connect(self._update_progress)
        self.worker.result_ready.connect(self._display_results)
        self.worker.start()

    def _update_progress(self, value: int, msg: str) -> None:
        self.progress.setValue(value)
        self.status_label.setText(msg)

    def _display_results(self, prediction_obj: object) -> None:
        prediction = prediction_obj if isinstance(prediction_obj, Prediction) else Prediction.from_dict(prediction_obj)  # type: ignore[arg-type]

        self.status_label.setText("Prediction Complete (Confidence: High)")

        self.card_agi.lbl_date.setText(prediction.agi_date[:4])
        self.card_agi.lbl_detail.setText(
            f"Full Date: {prediction.agi_date}\nMode: {prediction.agi_type}\nProbability: {prediction.agi_prob}%"
        )

        self.card_asi.lbl_date.setText(prediction.asi_date[:4])
        self.card_asi.lbl_detail.setText(f"Full Date: {prediction.asi_date}\nContext: {prediction.asi_context}")

        self.card_sing.lbl_date.setText(prediction.singularity_date[:4])
        self.card_sing.lbl_detail.setText(
            f"Est. Date: {prediction.singularity_date}\nProbability: {prediction.singularity_prob}%"
        )

        self.db.save_prediction(prediction)
        self.refresh_btn.setEnabled(True)
