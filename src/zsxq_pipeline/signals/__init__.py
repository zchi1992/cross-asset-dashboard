"""Derived metric calculation modules."""

from .processed_series import build_processed_series_with_trend_scores
from .trend_score import calculate_trend_score_rows

__all__ = [
    "build_processed_series_with_trend_scores",
    "calculate_trend_score_rows",
]
