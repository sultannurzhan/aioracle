from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Prediction:
    timestamp: str
    agi_date: str
    agi_type: str
    agi_prob: float
    asi_date: str
    asi_context: str
    singularity_date: str
    singularity_prob: float

    @staticmethod
    def from_dict(data: dict) -> "Prediction":
        return Prediction(
            timestamp=str(data["timestamp"]),
            agi_date=str(data["agi_date"]),
            agi_type=str(data["agi_type"]),
            agi_prob=float(data["agi_prob"]),
            asi_date=str(data["asi_date"]),
            asi_context=str(data["asi_context"]),
            singularity_date=str(data["singularity_date"]),
            singularity_prob=float(data["singularity_prob"]),
        )

    def to_db_tuple(self) -> tuple:
        return (
            self.timestamp,
            self.agi_date,
            self.agi_type,
            self.agi_prob,
            self.asi_date,
            self.asi_context,
            self.singularity_date,
            self.singularity_prob,
        )
