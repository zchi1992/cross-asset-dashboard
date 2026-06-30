from __future__ import annotations

from typing import Any


def is_long_candidate(row: dict[str, Any], thresholds: dict[str, float]) -> bool:
    return (
        float(row["trend_score"]) >= float(thresholds["long_trend_threshold"])
        and float(row["rs_score"]) >= float(thresholds["long_rs_threshold"])
        and float(row["leverage_velocity_score"]) >= float(thresholds["long_flow_threshold"])
    )


def is_short_candidate(row: dict[str, Any], thresholds: dict[str, float]) -> bool:
    return (
        float(row["trend_score"]) <= float(thresholds["short_trend_threshold"])
        and float(row["rs_score"]) <= float(thresholds["short_rs_threshold"])
        and float(row["leverage_velocity_score"]) <= float(thresholds["short_flow_threshold"])
    )


def normalize_flow_state(value: str | None) -> str:
    text = (value or "").strip()
    if text == "long_candidate":
        return "Leveraging"
    if text == "short_candidate":
        return "Deleveraging"
    if text in {"Leveraging", "Deleveraging", "Neutral"}:
        return text
    return "Neutral"


def normalized_marker_sizes(values: list[float], *, min_size: float = 8, max_size: float = 42) -> list[float]:
    if not values:
        return []
    absolute_values = [abs(float(value)) for value in values]
    largest = max(absolute_values)
    if largest <= 0:
        return [float(min_size) for _ in absolute_values]
    spread = float(max_size) - float(min_size)
    return [float(min_size) + (value / largest) * spread for value in absolute_values]
