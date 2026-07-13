from __future__ import annotations

from collections.abc import Iterable


REQUIRED_CURVE_TENORS = (2.0, 5.0, 10.0)


def calculate_curve_factors(points: dict[float, float]) -> dict[str, float] | None:
    """Return transparent fixed-tenor factors for one curve observation."""
    if not all(tenor in points for tenor in REQUIRED_CURVE_TENORS):
        return None
    two_year = float(points[2.0])
    five_year = float(points[5.0])
    ten_year = float(points[10.0])
    return {
        "level_10y": ten_year,
        "slope_2s10s": (ten_year - two_year) * 100.0,
        "curvature_2s5s10s": (2.0 * five_year - two_year - ten_year) * 100.0,
    }


def observation_changes(values: Iterable[float], windows: tuple[int, ...] = (1, 5, 20)) -> dict[str, float | None]:
    ordered = [float(value) for value in values]
    if not ordered:
        return {f"change_{window}": None for window in windows}
    latest = ordered[-1]
    return {
        f"change_{window}": latest - ordered[-1 - window] if len(ordered) > window else None
        for window in windows
    }


def calculate_hy_ig_spread(hy_percent: float, ig_percent: float) -> float:
    return (float(hy_percent) - float(ig_percent)) * 100.0
