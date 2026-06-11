from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from dashboard.config import DEFAULT_MARKET_MAP_CONFIG
from dashboard.data_loader import (
    MARKET_MAP_COLUMNS,
    filter_market_map_rows,
    load_market_map_rows,
    matching_asset_ids,
)
from dashboard.plotting.market_map_plot import _score_axis_ranges
from dashboard.scoring_rules import normalized_marker_sizes


class MarketMapDashboardTests(unittest.TestCase):
    def test_processed_long_rows_are_mapped_to_market_map_rows(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            storage_root = Path(temp_dir)
            _write_processed_asset(
                storage_root,
                "core",
                "AAA.csv",
                [
                    ("2026-06-04", "AAA", "Asset A", "capped_final_trend_score", "75"),
                    ("2026-06-04", "AAA", "Asset A", "state_name", "主升浪"),
                    ("2026-06-04", "AAA", "Asset A", "rs_score", "82"),
                    ("2026-06-04", "AAA", "Asset A", "current_relative_state", "Lead"),
                    ("2026-06-04", "AAA", "Asset A", "funding_signal_strength", "55"),
                    ("2026-06-04", "AAA", "Asset A", "funding_signal_direction", "long_candidate"),
                ],
            )

            rows = load_market_map_rows(storage_root, DEFAULT_MARKET_MAP_CONFIG)

        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(list(row), MARKET_MAP_COLUMNS)
        self.assertEqual(row["asset_id"], "AAA")
        self.assertEqual(row["asset_class"], "core")
        self.assertEqual(row["trend_score"], 75)
        self.assertEqual(row["rs_score"], 82)
        self.assertEqual(row["flow_score"], 55)
        self.assertEqual(row["flow_state"], "Leveraging")
        self.assertTrue(row["long_candidate"])
        self.assertFalse(row["short_candidate"])

    def test_incomplete_or_invalid_assets_are_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            storage_root = Path(temp_dir)
            _write_processed_asset(
                storage_root,
                "core",
                "BAD.csv",
                [
                    ("2026-06-04", "BAD", "Bad Asset", "capped_final_trend_score", "not-a-number"),
                    ("2026-06-04", "BAD", "Bad Asset", "state_name", "静默"),
                    ("2026-06-04", "BAD", "Bad Asset", "rs_score", "10"),
                    ("2026-06-04", "BAD", "Bad Asset", "current_relative_state", "Lag"),
                    ("2026-06-04", "BAD", "Bad Asset", "funding_signal_strength", "1"),
                    ("2026-06-04", "BAD", "Bad Asset", "funding_signal_direction", "short_candidate"),
                ],
            )
            _write_processed_asset(
                storage_root,
                "core",
                "MISSING.csv",
                [
                    ("2026-06-04", "MISSING", "Missing Asset", "capped_final_trend_score", "1"),
                    ("2026-06-04", "MISSING", "Missing Asset", "state_name", "静默"),
                ],
            )

            rows = load_market_map_rows(storage_root, DEFAULT_MARKET_MAP_CONFIG)

        self.assertEqual(rows, [])

    def test_short_candidate_and_filters(self) -> None:
        rows = [
            {
                "date": "2026-06-04",
                "asset_id": "SHORT",
                "asset_name": "Short Asset",
                "asset_class": "core",
                "trend_score": -80.0,
                "rs_score": -90.0,
                "flow_score": -60.0,
                "trend_state": "主跌浪",
                "rs_state": "Lag",
                "flow_state": "Deleveraging",
                "long_candidate": False,
                "short_candidate": True,
            },
            {
                "date": "2026-06-04",
                "asset_id": "LONG",
                "asset_name": "Long Asset",
                "asset_class": "instruments",
                "trend_score": 80.0,
                "rs_score": 90.0,
                "flow_score": 60.0,
                "trend_state": "主升浪",
                "rs_state": "Lead",
                "flow_state": "Leveraging",
                "long_candidate": True,
                "short_candidate": False,
            },
        ]

        filtered = filter_market_map_rows(
            rows,
            date="2026-06-04",
            asset_classes={"core"},
            flow_states={"Deleveraging"},
            trend_range=(-100, 0),
            rs_range=(-100, 0),
            flow_range=(-100, 0),
        )

        self.assertEqual([row["asset_id"] for row in filtered], ["SHORT"])
        self.assertEqual(matching_asset_ids(rows, "long\nmissing"), {"LONG"})

    def test_marker_size_normalization_uses_absolute_positive_values(self) -> None:
        sizes = normalized_marker_sizes([-10, 0, 20], min_size=8, max_size=42)

        self.assertEqual(len(sizes), 3)
        self.assertGreater(sizes[0], 8)
        self.assertEqual(sizes[1], 8)
        self.assertEqual(sizes[2], 42)
        self.assertTrue(all(size > 0 for size in sizes))

    def test_market_map_axis_ranges_use_dataset_scale(self) -> None:
        rows = [
            _market_map_row("AAA", trend_score=80.0, rs_score=90.0, flow_score=-10.0),
            _market_map_row("BBB", trend_score=84.0, rs_score=120.0, flow_score=20.0),
        ]

        ranges = _score_axis_ranges(rows)

        self.assertLess(ranges["rs_score"][0], 90)
        self.assertGreater(ranges["rs_score"][1], 120)
        self.assertLess(ranges["flow_score"][0], -10)
        self.assertGreater(ranges["flow_score"][1], 20)
        self.assertEqual(ranges["trend_score"], [-100, 100])


def _write_processed_asset(
    storage_root: Path,
    dataset_type: str,
    filename: str,
    rows: list[tuple[str, str, str, str, str]],
) -> None:
    target_dir = storage_root / "processed" / "series" / dataset_type
    target_dir.mkdir(parents=True, exist_ok=True)
    with (target_dir / filename).open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["date", "dataset_type", "asset_code", "asset_name", "metric_name", "metric_value"],
        )
        writer.writeheader()
        for date, asset_code, asset_name, metric_name, metric_value in rows:
            writer.writerow(
                {
                    "date": date,
                    "dataset_type": dataset_type,
                    "asset_code": asset_code,
                    "asset_name": asset_name,
                    "metric_name": metric_name,
                    "metric_value": metric_value,
                }
            )


def _market_map_row(
    asset_id: str,
    *,
    trend_score: float,
    rs_score: float,
    flow_score: float = 55.0,
) -> dict:
    return {
        "date": "2026-06-04",
        "asset_id": asset_id,
        "asset_name": f"Asset {asset_id}",
        "asset_class": "core",
        "trend_score": trend_score,
        "rs_score": rs_score,
        "flow_score": flow_score,
        "trend_state": "主升浪",
        "rs_state": "Lead",
        "flow_state": "Leveraging",
        "long_candidate": True,
        "short_candidate": False,
    }


if __name__ == "__main__":
    unittest.main()
