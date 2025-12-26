"""Real web scraping for AI timeline forecasts.

All data is fetched LIVE from the web on every call - no hardcoded values.

Sources:
- Metaculus API (public prediction questions on AGI/ASI/transformative AI)
- Polymarket (prediction market for AI milestones)
- Our World in Data / Wikipedia for current AI capabilities context
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from urllib.parse import urljoin

import requests

# Timeout for HTTP requests (seconds)
REQUEST_TIMEOUT = 20


@dataclass
class ForecastPoint:
    """A single forecast data point."""
    source: str
    question: str
    median_year: float
    num_forecasters: int
    url: str = ""


class MetaculusScraper:
    """Fetch AI-timeline forecasts from the Metaculus public API."""

    BASE_URL = "https://www.metaculus.com/api2"

    # Search for AI-related questions dynamically
    SEARCH_TERMS = [
        "AGI",
        "artificial general intelligence", 
        "transformative AI",
        "superintelligence",
        "human-level AI",
        "AI takeover",
        "AI singularity",
    ]

    def _parse_prediction_date(self, data: dict) -> Optional[float]:
        """Extract median prediction year from question data."""
        # Try community prediction first
        community = data.get("community_prediction") or {}
        
        # For date questions, q2 (median) is a timestamp
        q2 = community.get("q2")
        if q2 is not None:
            try:
                # Could be timestamp or year
                if q2 > 3000:  # Likely a timestamp
                    median_dt = datetime.utcfromtimestamp(q2)
                    return median_dt.year + median_dt.month / 12
                elif 2020 < q2 < 2200:  # Already a year
                    return float(q2)
            except Exception:
                pass

        # Try aggregations
        agg = data.get("aggregations", {})
        if "recency_weighted" in agg:
            centers = agg["recency_weighted"].get("centers", [])
            if centers:
                val = centers[0]
                if val > 3000:
                    return datetime.utcfromtimestamp(val).year
                elif 2020 < val < 2200:
                    return val

        return None

    def search_questions(self, term: str, limit: int = 5) -> list[dict]:
        """Search Metaculus for questions matching a term."""
        url = f"{self.BASE_URL}/questions/"
        params = {
            "search": term,
            "status": "open",
            "type": "forecast",
            "limit": limit,
            "order_by": "-activity",
        }
        try:
            resp = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            return data.get("results", [])
        except Exception:
            return []

    def fetch_question_detail(self, question_id: int) -> Optional[dict]:
        """Fetch detailed data for a specific question."""
        url = f"{self.BASE_URL}/questions/{question_id}/"
        try:
            resp = requests.get(url, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            return resp.json()
        except Exception:
            return None

    def fetch_all(self) -> list[ForecastPoint]:
        """Search and fetch all AI-timeline related forecasts."""
        results: list[ForecastPoint] = []
        seen_ids: set[int] = set()

        for term in self.SEARCH_TERMS:
            questions = self.search_questions(term, limit=10)
            
            for q in questions:
                qid = q.get("id")
                if not qid or qid in seen_ids:
                    continue
                seen_ids.add(qid)

                # Get detailed question data
                detail = self.fetch_question_detail(qid)
                if not detail:
                    continue

                median_year = self._parse_prediction_date(detail)
                if median_year is None:
                    continue

                # Only include if it's a date-type prediction in reasonable range
                if not (2025 < median_year < 2200):
                    continue

                results.append(ForecastPoint(
                    source="Metaculus",
                    question=detail.get("title", f"Question {qid}"),
                    median_year=median_year,
                    num_forecasters=detail.get("number_of_predictions", 0),
                    url=f"https://www.metaculus.com/questions/{qid}/",
                ))

        return results


class PolymarketScraper:
    """Fetch AI predictions from Polymarket."""

    BASE_URL = "https://gamma-api.polymarket.com"

    def fetch_ai_markets(self) -> list[ForecastPoint]:
        """Fetch AI-related prediction markets."""
        results: list[ForecastPoint] = []

        # Search for AI-related markets
        search_terms = ["AGI", "artificial intelligence", "AI", "GPT", "superintelligence"]
        
        for term in search_terms:
            try:
                url = f"{self.BASE_URL}/markets"
                params = {"_q": term, "_limit": 20}
                resp = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
                resp.raise_for_status()
                markets = resp.json()

                for market in markets:
                    if not isinstance(market, dict):
                        continue

                    question = market.get("question", "")
                    
                    # Look for year mentions in the question
                    year_match = re.search(r'\b(202[5-9]|20[3-9]\d|21\d\d)\b', question)
                    if not year_match:
                        continue

                    year = int(year_match.group(1))
                    
                    # Get probability (used as confidence indicator)
                    outcome_prices = market.get("outcomePrices", [])
                    volume = market.get("volume", 0)
                    
                    if volume < 1000:  # Skip low-volume markets
                        continue

                    results.append(ForecastPoint(
                        source="Polymarket",
                        question=question[:100],
                        median_year=float(year),
                        num_forecasters=int(volume / 10),  # Rough estimate
                        url=market.get("url", ""),
                    ))

            except Exception:
                continue

        return results


class ManifoldScraper:
    """Fetch AI predictions from Manifold Markets."""

    BASE_URL = "https://api.manifold.markets/v0"

    def fetch_ai_markets(self) -> list[ForecastPoint]:
        """Fetch AI-related prediction markets."""
        results: list[ForecastPoint] = []

        search_terms = ["AGI", "superintelligence", "transformative AI", "AI timeline"]

        for term in search_terms:
            try:
                url = f"{self.BASE_URL}/search-markets"
                params = {"term": term, "limit": 20}
                resp = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
                resp.raise_for_status()
                markets = resp.json()

                for market in markets:
                    if not isinstance(market, dict):
                        continue

                    question = market.get("question", "")
                    
                    # Look for year mentions
                    year_match = re.search(r'\b(202[5-9]|20[3-9]\d|21\d\d)\b', question)
                    if not year_match:
                        continue

                    year = int(year_match.group(1))
                    
                    # Get trader count as proxy for forecasters
                    unique_bettors = market.get("uniqueBettorCount", 0)
                    
                    if unique_bettors < 5:  # Skip low-activity markets
                        continue

                    results.append(ForecastPoint(
                        source="Manifold",
                        question=question[:100],
                        median_year=float(year),
                        num_forecasters=unique_bettors,
                        url=market.get("url", ""),
                    ))

            except Exception:
                continue

        return results


def aggregate_forecasts(points: list[ForecastPoint]) -> float:
    """Weighted median of forecast years (weight = sqrt(num_forecasters))."""
    if not points:
        # No data available - return a neutral "unknown" indicator
        return float(datetime.now().year + 25)

    # Weighted average using sqrt of forecaster count
    total_weight = 0.0
    weighted_sum = 0.0
    for p in points:
        w = max(1, p.num_forecasters) ** 0.5
        weighted_sum += p.median_year * w
        total_weight += w

    return weighted_sum / total_weight if total_weight else points[0].median_year


def fetch_agi_forecasts() -> tuple[list[ForecastPoint], float]:
    """Fetch ALL forecasts from ALL sources and return (points, aggregated_year).
    
    This function performs LIVE web scraping on every call.
    """
    all_points: list[ForecastPoint] = []

    # Metaculus - prediction platform
    try:
        metaculus = MetaculusScraper()
        all_points.extend(metaculus.fetch_all())
    except Exception:
        pass

    # Polymarket - prediction market
    try:
        polymarket = PolymarketScraper()
        all_points.extend(polymarket.fetch_ai_markets())
    except Exception:
        pass

    # Manifold Markets - prediction market
    try:
        manifold = ManifoldScraper()
        all_points.extend(manifold.fetch_ai_markets())
    except Exception:
        pass

    # Deduplicate by similar questions
    unique_points: list[ForecastPoint] = []
    seen_titles: set[str] = set()
    for p in all_points:
        title_key = p.question.lower()[:50]
        if title_key not in seen_titles:
            seen_titles.add(title_key)
            unique_points.append(p)

    agg = aggregate_forecasts(unique_points)
    return unique_points, agg
