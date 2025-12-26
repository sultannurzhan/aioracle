# AIORACLE

Small PyQt6 desktop app that generates simulated AGI/ASI timeline predictions, stores them in SQLite, and shows a history chart.

Code is split into reusable modules under `aioracle/` (backend, db, workers, ui).

## Setup

```zsh
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Run

```zsh
python main.py
```

## Notes

- The database file `ai_predictions.db` is created in the project folder.
- `sqlite3` is built into Python (it is not installed via `pip`).
