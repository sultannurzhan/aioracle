from __future__ import annotations

import sqlite3

from .models import Prediction


class DatabaseManager:
    def __init__(self, db_name: str = "ai_predictions.db"):
        self.conn = sqlite3.connect(db_name)
        self._create_table()

    def _create_table(self) -> None:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                agi_date TEXT,
                agi_type TEXT,
                agi_prob REAL,
                asi_date TEXT,
                asi_context TEXT,
                singularity_date TEXT,
                singularity_prob REAL
            )
            """
        )
        self.conn.commit()

    def close(self) -> None:
        try:
            self.conn.close()
        except Exception:
            pass

    def save_prediction(self, prediction: Prediction) -> None:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO predictions (
                timestamp, agi_date, agi_type, agi_prob,
                asi_date, asi_context, singularity_date, singularity_prob
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            prediction.to_db_tuple(),
        )
        self.conn.commit()

    def get_history(self) -> list[tuple]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM predictions ORDER BY timestamp DESC")
        return cursor.fetchall()
