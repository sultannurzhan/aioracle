"""Backend engine for AI timeline predictions.

This module provides the core prediction engine that aggregates forecasts
from multiple sources and generates unified predictions with confidence metrics.
"""

from __future__ import annotations

import logging
import statistics
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from threading import Lock
from typing import Callable, Optional

from .models import Prediction
from .scraper import ForecastPoint, fetch_agi_forecasts, aggregate_forecasts

# Configure module logger
logger = logging.getLogger(__name__)


class PredictionError(Exception):
    """Base exception for prediction-related errors."""
    pass


class DataFetchError(PredictionError):
    """Raised when unable to fetch forecast data."""
    pass


class DataValidationError(PredictionError):
    """Raised when fetched data fails validation."""
    pass


class TakeoffScenario(Enum):
    """AI takeoff scenario classifications."""
    RAPID = "Rapid Takeoff Scenario"
    MODERATE = "Moderate Transition"
    SLOW = "Slow Takeoff Scenario"
    
    @classmethod
    def from_year_gap(cls, gap: float) -> "TakeoffScenario":
        """Determine takeoff scenario from AGI-to-ASI year gap."""
        if gap < 5:
            return cls.RAPID
        elif gap < 15:
            return cls.MODERATE
        return cls.SLOW


class ConsensusType(Enum):
    """Types of prediction consensus."""
    CROWD_EXPERT = "Crowd + Expert Consensus"
    PREDICTION_MARKET = "Prediction Market Consensus"
    EXPERT_SURVEY = "Expert Survey"
    SINGLE_SOURCE = "Single Source Estimate"


@dataclass
class CacheEntry:
    """Cache entry with timestamp for TTL-based invalidation."""
    data: list[ForecastPoint]
    timestamp: datetime
    
    def is_expired(self, ttl_seconds: int) -> bool:
        """Check if cache entry has expired."""
        age = (datetime.now() - self.timestamp).total_seconds()
        return age > ttl_seconds


@dataclass
class ConfidenceMetrics:
    """Statistical confidence metrics for predictions."""
    mean_year: float
    median_year: float
    std_deviation: float
    sample_size: int
    source_diversity: int
    confidence_score: float = field(init=False)
    
    def __post_init__(self) -> None:
        """Calculate overall confidence score."""
        # Higher sample size and lower std_dev = higher confidence
        size_factor = min(1.0, self.sample_size / 50)
        diversity_factor = min(1.0, self.source_diversity / 3)
        spread_factor = max(0.3, 1 - (self.std_deviation / 30))
        
        self.confidence_score = (size_factor * 0.3 + diversity_factor * 0.3 + spread_factor * 0.4) * 100


class ForecastClassifier:
    """Classifies forecast points into AGI, ASI, and Singularity categories."""
    
    # Keywords for classification
    AGI_KEYWORDS = frozenset([
        "agi", "artificial general intelligence", "human-level", 
        "human level", "hlai", "general ai"
    ])
    ASI_KEYWORDS = frozenset([
        "asi", "superintelligence", "superintelligent", 
        "transformative ai", "transformative artificial"
    ])
    SINGULARITY_KEYWORDS = frozenset([
        "singularity", "full automation", "technological singularity",
        "intelligence explosion", "recursive self-improvement"
    ])
    
    @classmethod
    def classify(cls, points: list[ForecastPoint]) -> dict[str, list[ForecastPoint]]:
        """Classify forecast points into categories.
        
        Args:
            points: List of forecast points to classify.
            
        Returns:
            Dictionary with 'agi', 'asi', and 'singularity' keys.
        """
        classified = {
            "agi": [],
            "asi": [],
            "singularity": []
        }
        
        for point in points:
            question_lower = point.question.lower()
            
            # Check for singularity first (most specific)
            if any(kw in question_lower for kw in cls.SINGULARITY_KEYWORDS):
                classified["singularity"].append(point)
            elif any(kw in question_lower for kw in cls.ASI_KEYWORDS):
                classified["asi"].append(point)
            else:
                # Default to AGI category
                classified["agi"].append(point)
        
        return classified


class PredictionEngine:
    """Generates AI timeline predictions from real web data.
    
    Features:
    - Optional TTL-based caching to reduce API load
    - Statistical confidence metrics
    - Proper error handling and logging
    - Thread-safe cache access
    - Configurable data validation
    
    Example:
        >>> engine = PredictionEngine(cache_ttl_seconds=300)
        >>> prediction = engine.generate_prediction()
        >>> print(f"AGI predicted: {prediction.agi_date}")
    """
    
    # Validation constants
    MIN_VALID_YEAR = 2025
    MAX_VALID_YEAR = 2200
    MIN_FORECASTERS = 0
    
    def __init__(
        self, 
        cache_ttl_seconds: int = 0,
        min_data_points: int = 1,
        fetch_func: Optional[Callable[[], list[ForecastPoint]]] = None
    ):
        """Initialize the prediction engine.
        
        Args:
            cache_ttl_seconds: Cache TTL in seconds. 0 disables caching.
            min_data_points: Minimum required data points for prediction.
            fetch_func: Optional custom fetch function for testing.
        """
        self._cache: Optional[CacheEntry] = None
        self._cache_lock = Lock()
        self._cache_ttl = cache_ttl_seconds
        self._min_data_points = min_data_points
        self._fetch_func = fetch_func or self._default_fetch
        
        logger.debug(
            f"PredictionEngine initialized with cache_ttl={cache_ttl_seconds}s, "
            f"min_data_points={min_data_points}"
        )
    
    def _default_fetch(self) -> list[ForecastPoint]:
        """Default fetch function using the scraper module."""
        points, _ = fetch_agi_forecasts()
        return points
    
    def _validate_point(self, point: ForecastPoint) -> bool:
        """Validate a single forecast point.
        
        Args:
            point: Forecast point to validate.
            
        Returns:
            True if point is valid, False otherwise.
        """
        if not self.MIN_VALID_YEAR <= point.median_year <= self.MAX_VALID_YEAR:
            logger.debug(f"Invalid year {point.median_year} for '{point.question[:50]}...'")
            return False
        
        if point.num_forecasters < self.MIN_FORECASTERS:
            logger.debug(f"Invalid forecaster count {point.num_forecasters}")
            return False
        
        return True
    
    def _validate_data(self, points: list[ForecastPoint]) -> list[ForecastPoint]:
        """Validate and filter forecast data.
        
        Args:
            points: Raw forecast points.
            
        Returns:
            List of validated forecast points.
            
        Raises:
            DataValidationError: If insufficient valid data points.
        """
        valid_points = [p for p in points if self._validate_point(p)]
        
        logger.info(f"Validated {len(valid_points)}/{len(points)} data points")
        
        if len(valid_points) < self._min_data_points:
            raise DataValidationError(
                f"Insufficient valid data: got {len(valid_points)}, "
                f"need {self._min_data_points}"
            )
        
        return valid_points

    def fetch_data(self, force_refresh: bool = False) -> list[ForecastPoint]:
        """Fetch forecast data, optionally from cache.
        
        Args:
            force_refresh: If True, bypass cache and fetch fresh data.
            
        Returns:
            List of ForecastPoints.
            
        Raises:
            DataFetchError: If unable to fetch any data.
        """
        with self._cache_lock:
            # Check cache if enabled and not forcing refresh
            if (
                not force_refresh 
                and self._cache_ttl > 0 
                and self._cache is not None 
                and not self._cache.is_expired(self._cache_ttl)
            ):
                logger.debug("Returning cached forecast data")
                return self._cache.data
            
            # Fetch fresh data
            logger.info("Fetching fresh forecast data from sources")
            try:
                points = self._fetch_func()
            except Exception as e:
                logger.error(f"Failed to fetch forecast data: {e}")
                raise DataFetchError(f"Failed to fetch data: {e}") from e
            
            if not points:
                raise DataFetchError(
                    "No forecast data retrieved. Check your internet connection."
                )
            
            # Update cache
            if self._cache_ttl > 0:
                self._cache = CacheEntry(data=points, timestamp=datetime.now())
                logger.debug(f"Cached {len(points)} forecast points")
            
            return points
    
    def calculate_confidence_metrics(
        self, 
        points: list[ForecastPoint]
    ) -> ConfidenceMetrics:
        """Calculate statistical confidence metrics for a set of forecasts.
        
        Args:
            points: List of forecast points.
            
        Returns:
            ConfidenceMetrics with statistical analysis.
        """
        if not points:
            return ConfidenceMetrics(
                mean_year=0, median_year=0, std_deviation=0,
                sample_size=0, source_diversity=0
            )
        
        years = [p.median_year for p in points]
        sources = {p.source for p in points}
        
        mean_year = statistics.mean(years)
        median_year = statistics.median(years)
        std_dev = statistics.stdev(years) if len(years) > 1 else 0.0
        
        return ConfidenceMetrics(
            mean_year=mean_year,
            median_year=median_year,
            std_deviation=std_dev,
            sample_size=len(points),
            source_diversity=len(sources)
        )
    
    def _determine_consensus_type(self, points: list[ForecastPoint]) -> ConsensusType:
        """Determine the type of consensus based on data sources.
        
        Args:
            points: List of forecast points.
            
        Returns:
            ConsensusType enum value.
        """
        sources = {p.source for p in points}
        
        if len(sources) == 0:
            return ConsensusType.SINGLE_SOURCE
        elif len(sources) == 1:
            if "Metaculus" in sources:
                return ConsensusType.PREDICTION_MARKET
            return ConsensusType.EXPERT_SURVEY
        elif "Metaculus" in sources:
            return ConsensusType.CROWD_EXPERT
        return ConsensusType.EXPERT_SURVEY
    
    def _calculate_probability(self, metrics: ConfidenceMetrics) -> float:
        """Calculate probability based on confidence metrics.
        
        Args:
            metrics: Statistical confidence metrics.
            
        Returns:
            Probability value (0-100).
        """
        if metrics.sample_size < 2:
            return 60.0
        
        # Use confidence score as base, adjusted for spread
        base_prob = metrics.confidence_score
        
        # Clamp to reasonable range
        return max(40.0, min(95.0, base_prob))
    
    @staticmethod
    def _year_to_date_string(year: float) -> str:
        """Convert a floating-point year to a date string.
        
        Args:
            year: Year as float (e.g., 2030.5 = mid-2030).
            
        Returns:
            ISO date string (YYYY-MM-01).
        """
        yr = int(year)
        month = int((year - yr) * 12) + 1
        month = max(1, min(12, month))
        return f"{yr}-{month:02d}-01"
    
    def generate_prediction(self, force_refresh: bool = False) -> Prediction:
        """Generate a comprehensive prediction from forecast data.
        
        Args:
            force_refresh: If True, bypass cache and fetch fresh data.
            
        Returns:
            Prediction object with all timeline estimates.
            
        Raises:
            DataFetchError: If unable to fetch data.
            DataValidationError: If data validation fails.
        """
        logger.info("Generating new prediction")
        
        # Fetch and validate data
        raw_points = self.fetch_data(force_refresh=force_refresh)
        points = self._validate_data(raw_points)
        
        # Classify points by category
        classified = ForecastClassifier.classify(points)
        agi_points = classified["agi"]
        asi_points = classified["asi"]
        sing_points = classified["singularity"]
        
        # Apply fallbacks for empty categories
        if not agi_points:
            agi_points = points
            logger.debug("Using all points as AGI fallback")
        if not asi_points:
            asi_points = agi_points
            logger.debug("Using AGI points as ASI fallback")
        if not sing_points:
            sing_points = agi_points
            logger.debug("Using AGI points as singularity fallback")
        
        # Calculate aggregated years
        agi_year = aggregate_forecasts(agi_points)
        asi_year = aggregate_forecasts(asi_points)
        sing_year = aggregate_forecasts(sing_points)
        
        # Ensure logical ordering: AGI <= ASI <= Singularity
        if asi_year <= agi_year:
            asi_year = agi_year + 5
            logger.debug(f"Adjusted ASI year to {asi_year} (AGI + 5)")
        if sing_year <= asi_year:
            sing_year = asi_year + 15
            logger.debug(f"Adjusted singularity year to {sing_year} (ASI + 15)")
        
        # Calculate metrics and probabilities
        agi_metrics = self.calculate_confidence_metrics(agi_points)
        sing_metrics = self.calculate_confidence_metrics(sing_points)
        
        agi_prob = self._calculate_probability(agi_metrics)
        sing_prob = self._calculate_probability(sing_metrics)
        
        # Determine consensus type and takeoff scenario
        consensus_type = self._determine_consensus_type(agi_points)
        takeoff_scenario = TakeoffScenario.from_year_gap(asi_year - agi_year)
        
        prediction = Prediction(
            timestamp=datetime.now().isoformat(timespec="seconds"),
            agi_date=self._year_to_date_string(agi_year),
            agi_type=consensus_type.value,
            agi_prob=round(agi_prob, 1),
            asi_date=self._year_to_date_string(asi_year),
            asi_context=takeoff_scenario.value,
            singularity_date=self._year_to_date_string(sing_year),
            singularity_prob=round(sing_prob, 1),
        )
        
        logger.info(
            f"Prediction generated: AGI={prediction.agi_date} ({agi_prob:.1f}%), "
            f"ASI={prediction.asi_date}, Singularity={prediction.singularity_date}"
        )
        
        return prediction
    
    def get_detailed_analysis(self, force_refresh: bool = False) -> dict:
        """Get detailed analysis including raw data and metrics.
        
        Args:
            force_refresh: If True, bypass cache and fetch fresh data.
            
        Returns:
            Dictionary with prediction, metrics, and source breakdown.
        """
        raw_points = self.fetch_data(force_refresh=force_refresh)
        points = self._validate_data(raw_points)
        classified = ForecastClassifier.classify(points)
        
        return {
            "prediction": self.generate_prediction(force_refresh=False),
            "total_data_points": len(points),
            "sources": list({p.source for p in points}),
            "agi_metrics": self.calculate_confidence_metrics(classified["agi"]),
            "asi_metrics": self.calculate_confidence_metrics(classified["asi"]),
            "singularity_metrics": self.calculate_confidence_metrics(classified["singularity"]),
            "raw_forecasts": points,
        }
    
    def clear_cache(self) -> None:
        """Clear the forecast data cache."""
        with self._cache_lock:
            self._cache = None
            logger.debug("Cache cleared")

