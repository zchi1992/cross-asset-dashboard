from __future__ import annotations

from typing import Any


def score_bounds(rows: list[dict[str, Any]], field: str, default: tuple[float, float]) -> tuple[float, float]:
    values = [float(row[field]) for row in rows if row.get(field) is not None]
    if not values:
        return default
    low = min(values)
    high = max(values)
    if low == high:
        return (low - 1, high + 1)
    return (float(low), float(high))

