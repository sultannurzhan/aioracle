from __future__ import annotations

import random
from datetime import datetime, timedelta

from .models import Prediction


class PredictionEngine:
    """Simulates a complex prediction algorithm using 'internet data'."""

    def __init__(self):
        self.base_agi_date = datetime(2027, 10, 1)
        self.base_asi_date = datetime(2032, 5, 15)
        self.base_singularity = datetime(2045, 1, 1)

    def generate_prediction(self) -> Prediction:
        agi_shift = random.randint(-400, 600)  # days
        asi_shift = random.randint(-600, 900)
        sing_shift = random.randint(-1000, 1000)

        p_agi = self.base_agi_date + timedelta(days=agi_shift)
        p_asi = self.base_asi_date + timedelta(days=asi_shift)
        p_sing = self.base_singularity + timedelta(days=sing_shift)

        if p_asi < p_agi:
            p_asi = p_agi + timedelta(days=random.randint(365, 1000))

        return Prediction(
            timestamp=datetime.now().isoformat(timespec="seconds"),
            agi_date=p_agi.strftime("%Y-%m-%d"),
            agi_type=random.choice(["Public Release", "Private/Military", "Research Lab Demo"]),
            agi_prob=round(random.uniform(65.0, 95.0), 1),
            asi_date=p_asi.strftime("%Y-%m-%d"),
            asi_context=random.choice(["Open Source", "Corporate Monopoly", "Government Restricted"]),
            singularity_date=p_sing.strftime("%Y-%m-%d"),
            singularity_prob=round(random.uniform(40.0, 85.0), 1),
        )
