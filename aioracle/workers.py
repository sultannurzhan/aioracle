from __future__ import annotations

import random
import time

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
        steps = [
            (10, "Connecting to arXiv API..."),
            (30, "Scraping GitHub repos for 'Transformer' activity..."),
            (50, "Analyzing global compute funding trends..."),
            (70, "Running Monte Carlo simulations..."),
            (90, "Finalizing probability weights..."),
            (100, "Done."),
        ]

        for progress, msg in steps:
            time.sleep(random.uniform(0.3, 0.8))
            self.progress_update.emit(progress, msg)

        prediction: Prediction = self._engine.generate_prediction()
        self.result_ready.emit(prediction)
