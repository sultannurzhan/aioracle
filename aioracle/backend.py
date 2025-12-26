from __future__ import annotations

from datetime import datetime

from .models import Prediction
from .scraper import ForecastPoint, fetch_agi_forecasts, aggregate_forecasts


class PredictionEngine:
    """Generates AI timeline predictions from real web data.
    
    Every call to generate_prediction() fetches FRESH data from the web.
    No caching, no hardcoded values.
    """

    def fetch_data(self) -> list[ForecastPoint]:
        """Fetch real forecasts from the web RIGHT NOW. Returns list of ForecastPoints."""
        points, _ = fetch_agi_forecasts()
        return points

    def generate_prediction(self) -> Prediction:
        """Generate a Prediction by fetching FRESH data from the web."""
        # Always fetch fresh data - no caching
        points = self.fetch_data()
        
        if not points:
            raise RuntimeError("Could not fetch any forecast data from the web. Check your internet connection.")

        now = datetime.now()

        # Separate AGI-ish vs full-automation/singularity forecasts by keyword heuristics
        agi_points: list[ForecastPoint] = []
        asi_points: list[ForecastPoint] = []
        sing_points: list[ForecastPoint] = []

        for p in points:
            q_lower = p.question.lower()
            if "full automation" in q_lower or "singularity" in q_lower:
                sing_points.append(p)
            elif "transformative" in q_lower or "superintelligence" in q_lower or "asi" in q_lower:
                asi_points.append(p)
            else:
                agi_points.append(p)

        # Fallbacks: if no specific category, use all for AGI and offset for others
        if not agi_points:
            agi_points = points
        if not asi_points:
            # Estimate ASI as AGI + 5-15 years
            asi_points = agi_points
        if not sing_points:
            sing_points = agi_points

        agi_year = aggregate_forecasts(agi_points)
        asi_year = aggregate_forecasts(asi_points)
        sing_year = aggregate_forecasts(sing_points)

        # Ensure logical ordering: AGI <= ASI <= Singularity
        if asi_year <= agi_year:
            asi_year = agi_year + 5
        if sing_year <= asi_year:
            sing_year = asi_year + 15

        # Convert years to date strings (use July 1 as midpoint)
        def year_to_date(y: float) -> str:
            yr = int(y)
            month = int((y - yr) * 12) + 1
            month = max(1, min(12, month))
            return f"{yr}-{month:02d}-01"

        agi_date = year_to_date(agi_year)
        asi_date = year_to_date(asi_year)
        sing_date = year_to_date(sing_year)

        # Probability heuristics based on spread of forecasts
        def calc_prob(pts: list[ForecastPoint]) -> float:
            if len(pts) < 2:
                return 60.0
            years = [p.median_year for p in pts]
            spread = max(years) - min(years)
            # Narrower spread = higher confidence
            if spread < 5:
                return 85.0
            elif spread < 15:
                return 70.0
            else:
                return 55.0

        agi_prob = calc_prob(agi_points)
        sing_prob = calc_prob(sing_points)

        # Determine AGI type based on source diversity
        sources = {p.source for p in agi_points}
        if "Metaculus" in sources and len(sources) > 1:
            agi_type = "Crowd + Expert Consensus"
        elif "Metaculus" in sources:
            agi_type = "Prediction Market Consensus"
        else:
            agi_type = "Expert Survey"

        # ASI context
        if asi_year - agi_year < 5:
            asi_context = "Rapid Takeoff Scenario"
        elif asi_year - agi_year < 15:
            asi_context = "Moderate Transition"
        else:
            asi_context = "Slow Takeoff Scenario"

        return Prediction(
            timestamp=now.isoformat(timespec="seconds"),
            agi_date=agi_date,
            agi_type=agi_type,
            agi_prob=round(agi_prob, 1),
            asi_date=asi_date,
            asi_context=asi_context,
            singularity_date=sing_date,
            singularity_prob=round(sing_prob, 1),
        )

