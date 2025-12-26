from __future__ import annotations

from PyQt6.QtCore import QThread, pyqtSignal

from .backend import PredictionEngine
from .models import Prediction


class AnalysisWorker(QThread):
    progress_update = pyqtSignal(int, str)
    result_ready = pyqtSignal(object)

    def __init__(self, engine: PredictionEngine):
        super().__init__()
        self._engine = engine

    def run(self):
        try:
            self.progress_update.emit(5, "Connecting to prediction markets...")

            # Fetch FRESH data from web on every button press
            self.progress_update.emit(15, "Scraping Metaculus API...")
            self.progress_update.emit(35, "Scraping Polymarket...")
            self.progress_update.emit(55, "Scraping Manifold Markets...")
            
            # This fetches ALL data fresh from web
            prediction: Prediction = self._engine.generate_prediction()

            self.progress_update.emit(85, "Aggregating forecasts (weighted analysis)...")
            self.progress_update.emit(100, "Done - fresh data analyzed!")
            
            self.result_ready.emit(prediction)

        except Exception as e:
            self.progress_update.emit(0, f"Error: {e}")
