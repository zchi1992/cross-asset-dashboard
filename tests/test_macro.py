from __future__ import annotations

import csv
from pathlib import Path

import pytest

from dashboard.macro_loader import build_macro_history, build_macro_overview, load_macro_dataset
from src.macro_pipeline.calculations import calculate_curve_factors, calculate_hy_ig_spread, observation_changes
from src.macro_pipeline.pipeline import CREDIT_FIELDS, _upsert_csv


FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "dashboard"
MACRO_CONFIG = {
    "processed_path": "processed/macro",
    "source_state_path": "state/macro_sources.json",
    "thresholds": {
        "curve_change_bp": 10,
        "credit_spread_change_bp": 10,
        "stress_index_change": 0.25,
        "sloos_change_pp": 5,
    },
}


def test_curve_factor_formulas_and_changes() -> None:
    factors = calculate_curve_factors({2.0: 4.0, 5.0: 4.1, 10.0: 4.4})
    assert factors == pytest.approx({
        "level_10y": 4.4,
        "slope_2s10s": 40.0,
        "curvature_2s5s10s": -20.0,
    })
    assert calculate_curve_factors({2.0: -0.2, 10.0: 0.1}) is None
    assert observation_changes([1, 2, 4], windows=(1, 2)) == {"change_1": 2.0, "change_2": 3.0}
    assert calculate_hy_ig_spread(2.8, 0.75) == 204.99999999999997


def test_fixture_macro_overview_and_history() -> None:
    dataset = load_macro_dataset(FIXTURE_ROOT, MACRO_CONFIG)
    overview = build_macro_overview(dataset, MACRO_CONFIG)

    assert [item["region"] for item in overview["curves"]] == ["CN", "EU", "GB", "JP", "US"]
    us_curve = next(item for item in overview["curves"] if item["region"] == "US")
    assert us_curve["observed_at"] == "2026-06-28"
    assert next(item for item in us_curve["factors"] if item["series_id"].endswith("slope_2s10s"))["value"] == pytest.approx(60.0)

    hy_ig = next(item for item in overview["credit"] if item["series_id"] == "HY_IG")
    assert round(hy_ig["value"]) == 205
    assert round(hy_ig["changes"]["change_1"]) == -10

    history = build_macro_history(dataset, "CURVE.US.level_10y", start="2026-06-25")
    assert history is not None
    assert history["points"] == [{"date": "2026-06-28", "value": 4.5}]
    assert build_macro_history(dataset, "UNKNOWN") is None


def test_upsert_overwrites_same_business_key(tmp_path) -> None:
    path = tmp_path / "credit.csv"
    base = {
        "date": "2026-06-28",
        "series_id": "NFCI",
        "label": "NFCI",
        "value": "-0.5",
        "unit": "index",
        "frequency": "weekly",
        "source_id": "fred",
        "source_name": "FRED",
        "source_url": "https://fred.stlouisfed.org/",
    }
    _upsert_csv(path, [base], CREDIT_FIELDS, ("date", "series_id"))
    _upsert_csv(path, [{**base, "value": "-0.4"}], CREDIT_FIELDS, ("date", "series_id"))

    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 1
    assert rows[0]["value"] == "-0.4"
