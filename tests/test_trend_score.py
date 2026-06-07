from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from src.zsxq_pipeline.signals.processed_series import build_processed_series_with_trend_scores
from src.zsxq_pipeline.signals.relative_strength import calculate_rs_score_rows
from src.zsxq_pipeline.signals.trend_score import calculate_trend_score_rows
from src.zsxq_pipeline.config import load_config
from src.zsxq_pipeline.pipeline import IngestionPipeline, bootstrap_directories


ROOT = Path(__file__).resolve().parents[1]


class TrendScoreTests(unittest.TestCase):
    def test_weekly_confirmation_enters_main_uptrend(self) -> None:
        rows = _trend_rows(
            [
                ("2026-06-03", "up", "neutral", "up", 4, 0, 4),
                ("2026-06-04", "up", "up", "up", 4, 1, 5),
            ]
        )

        output = _rows_by_date_and_metric(calculate_trend_score_rows(rows))

        self.assertEqual(output[("2026-06-04", "trend_combo")], "up/up/up")
        self.assertEqual(output[("2026-06-04", "state_name")], "主升浪")
        self.assertEqual(output[("2026-06-04", "raw_current_score")], "6")
        self.assertEqual(output[("2026-06-04", "current_score")], "100")
        self.assertEqual(output[("2026-06-04", "raw_transition_score")], "2")
        self.assertAlmostEqual(float(output[("2026-06-04", "transition_score")]), 16.67, places=2)
        self.assertEqual(output[("2026-06-04", "transition_label")], "周线趋势改善")

    def test_mature_main_uptrend_with_daily_pullback(self) -> None:
        rows = _trend_rows(
            [
                ("2026-06-03", "up", "up", "up", 6, 12, 20),
                ("2026-06-04", "up", "up", "down", 6, 12, 5),
            ]
        )

        output = _rows_by_date_and_metric(calculate_trend_score_rows(rows))

        self.assertEqual(output[("2026-06-04", "trend_combo")], "up/up/down")
        self.assertEqual(output[("2026-06-04", "state_name")], "主升回调")
        self.assertEqual(output[("2026-06-04", "raw_current_score")], "4")
        self.assertAlmostEqual(float(output[("2026-06-04", "current_score")]), 66.67, places=2)
        self.assertEqual(output[("2026-06-04", "raw_transition_score")], "-2")
        self.assertAlmostEqual(float(output[("2026-06-04", "transition_score")]), -16.67, places=2)
        self.assertEqual(output[("2026-06-04", "transition_label")], "日线由上行反转为下行")
        self.assertAlmostEqual(float(output[("2026-06-04", "duration_score")]), 70.83, places=2)
        self.assertAlmostEqual(float(output[("2026-06-04", "raw_final_trend_score")]), 64.17, places=2)

    def test_monthly_confirmation_enters_main_uptrend(self) -> None:
        rows = _trend_rows(
            [
                ("2026-06-03", "neutral", "up", "up", 0, 8, 10),
                ("2026-06-04", "up", "up", "up", 1, 8, 10),
            ]
        )

        output = _rows_by_date_and_metric(calculate_trend_score_rows(rows))

        self.assertEqual(output[("2026-06-04", "trend_combo")], "up/up/up")
        self.assertEqual(output[("2026-06-04", "state_name")], "主升浪")
        self.assertEqual(output[("2026-06-04", "raw_current_score")], "6")
        self.assertEqual(output[("2026-06-04", "current_score")], "100")
        self.assertEqual(output[("2026-06-04", "raw_transition_score")], "3")
        self.assertEqual(output[("2026-06-04", "transition_score")], "25")
        self.assertEqual(output[("2026-06-04", "transition_label")], "月线趋势改善")

    def test_chinese_trends_duration_aliases_and_first_row_transition(self) -> None:
        rows = [
            _row("2026-06-04", "daily_trend", "下行趋势"),
            _row("2026-06-04", "daily_trend_duration", "5"),
            _row("2026-06-04", "weekly_trend", "无趋势"),
            _row("2026-06-04", "weekly_trend_duration", "10"),
            _row("2026-06-04", "monthly_trend", "上行趋势"),
            _row("2026-06-04", "monthly_trend_duration", "29"),
        ]

        output = _rows_by_date_and_metric(calculate_trend_score_rows(rows))

        self.assertEqual(output[("2026-06-04", "trend_combo")], "up/neutral/down")
        self.assertEqual(output[("2026-06-04", "monthly_trend_bars")], "29")
        self.assertEqual(output[("2026-06-04", "weekly_trend_bars")], "10")
        self.assertEqual(output[("2026-06-04", "daily_trend_bars")], "5")
        self.assertEqual(output[("2026-06-04", "raw_transition_score")], "0")
        self.assertEqual(output[("2026-06-04", "transition_label")], "状态未变化")

    def test_missing_required_field_raises_clear_error(self) -> None:
        rows = _trend_rows([("2026-06-04", "up", "up", "up", 6, 12, 20)])
        rows = [row for row in rows if row["metric_name"] != "daily_trend_duration"]

        with self.assertRaisesRegex(ValueError, "missing trend score fields.*daily_trend_bars"):
            calculate_trend_score_rows(rows)


class RelativeStrengthScoreTests(unittest.TestCase):
    def test_lag_to_lead_uses_raw_inputs_and_full_maturity_bonus(self) -> None:
        rows = _relative_rows(
            [
                ("2026-06-04", 100, 100, 100, "Lead", "Lag", 1, 15),
            ]
        )

        output = _rows_by_date_and_metric(calculate_rs_score_rows(rows))

        self.assertEqual(output[("2026-06-04", "state_transition")], "Lag->Lead")
        self.assertEqual(output[("2026-06-04", "relative_signal_type")], "strong_reversal_to_lead")
        self.assertEqual(output[("2026-06-04", "base_transition_score")], "120")
        self.assertEqual(output[("2026-06-04", "freshness_factor")], "1")
        self.assertEqual(output[("2026-06-04", "previous_maturity_factor")], "1")
        self.assertEqual(output[("2026-06-04", "transition_score")], "120")
        self.assertEqual(output[("2026-06-04", "rs_score")], "103")

    def test_lead_to_lag_applies_time_adjusted_transition_score(self) -> None:
        rows = _relative_rows(
            [
                ("2026-06-04", 100, 100, 100, "lag", "lead", 6, 7.5),
            ]
        )

        output = _rows_by_date_and_metric(calculate_rs_score_rows(rows))

        self.assertEqual(output[("2026-06-04", "state_transition")], "Lead->Lag")
        self.assertEqual(output[("2026-06-04", "relative_signal_type")], "leadership_collapse")
        self.assertEqual(output[("2026-06-04", "base_transition_score")], "-120")
        self.assertAlmostEqual(float(output[("2026-06-04", "freshness_factor")]), 0.37, places=2)
        self.assertEqual(output[("2026-06-04", "previous_maturity_factor")], "0.50")
        self.assertAlmostEqual(float(output[("2026-06-04", "transition_score")]), -22.07, places=2)
        self.assertAlmostEqual(float(output[("2026-06-04", "rs_score")]), 81.69, places=2)

    def test_rs_score_weights_relative_strength_above_early_reversal(self) -> None:
        rows = _relative_rows(
            [
                ("2026-06-04", 10, 50, 90, "Lead", "Lag", 1, 15),
            ]
        )

        output = _rows_by_date_and_metric(calculate_rs_score_rows(rows))

        self.assertEqual(output[("2026-06-04", "transition_score")], "120")
        self.assertEqual(output[("2026-06-04", "rs_score")], "66.50")

    def test_same_state_is_rejected(self) -> None:
        rows = _relative_rows(
            [
                ("2026-06-04", 100, 100, 100, "Lead", "Lead", 1, 15),
            ]
        )

        with self.assertRaisesRegex(ValueError, "must differ"):
            calculate_rs_score_rows(rows)

    def test_duration_must_be_at_least_one(self) -> None:
        rows = _relative_rows(
            [
                ("2026-06-04", 100, 100, 100, "Lead", "Lag", 0, 15),
            ]
        )

        with self.assertRaisesRegex(ValueError, "invalid current_relative_state_duration"):
            calculate_rs_score_rows(rows)


class ProcessedTrendScoreIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workdir = Path(self.temp_dir.name)
        config_src = (ROOT / "config.yaml").read_text(encoding="utf-8")
        self.config_path = self.workdir / "config.yaml"
        self.config_path.write_text(config_src, encoding="utf-8")
        self.config = load_config(self.config_path)
        bootstrap_directories(self.config)
        self.pipeline = IngestionPipeline(self.config)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_examples_build_processed_series_without_touching_source_series(self) -> None:
        self.pipeline.reparse_path(ROOT / "examples")
        source_file = self.workdir / "data" / "series" / "core" / "10Y1.csv"
        before = source_file.read_text(encoding="utf-8")

        written_paths = build_processed_series_with_trend_scores(self.config.storage_root)

        self.assertTrue(written_paths)
        self.assertEqual(source_file.read_text(encoding="utf-8"), before)
        processed_file = self.workdir / "data" / "processed" / "series" / "core" / "10Y1.csv"
        self.assertTrue(processed_file.exists())
        metric_names = _metric_names(processed_file)
        self.assertIn("trend_combo", metric_names)
        self.assertIn("state_name", metric_names)
        self.assertIn("raw_final_trend_score", metric_names)
        self.assertIn("capped_final_trend_score", metric_names)
        self.assertIn("transition_label", metric_names)
        self.assertIn("rs_score", metric_names)
        self.assertIn("state_transition", metric_names)
        self.assertIn("relative_signal_type", metric_names)
        self.assertIn("base_transition_score", metric_names)


def _trend_rows(records: list[tuple[str, str, str, str, int, int, int]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for date, monthly, weekly, daily, monthly_bars, weekly_bars, daily_bars in records:
        rows.extend(
            [
                _row(date, "monthly_trend", monthly),
                _row(date, "weekly_trend", weekly),
                _row(date, "daily_trend", daily),
                _row(date, "monthly_trend_duration", str(monthly_bars)),
                _row(date, "weekly_trend_duration", str(weekly_bars)),
                _row(date, "daily_trend_duration", str(daily_bars)),
            ]
        )
    return rows


def _relative_rows(records: list[tuple[str, float, float, float, str, str, float, float]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for (
        date,
        early_reversal,
        strength_momentum,
        relative_strength,
        current_state,
        previous_state,
        current_duration,
        previous_duration,
    ) in records:
        rows.extend(
            [
                _row(date, "early_reversal", str(early_reversal)),
                _row(date, "strength_momentum", str(strength_momentum)),
                _row(date, "relative_strength", str(relative_strength)),
                _row(date, "current_relative_state", current_state),
                _row(date, "previous_relative_state", previous_state),
                _row(date, "current_relative_state_duration", str(current_duration)),
                _row(date, "previous_relative_state_duration", str(previous_duration)),
            ]
        )
    return rows


def _row(date: str, metric_name: str, metric_value: str) -> dict[str, str]:
    return {
        "date": date,
        "dataset_type": "core",
        "asset_code": "TEST",
        "asset_name": "Test Asset",
        "metric_name": metric_name,
        "metric_value": metric_value,
    }


def _rows_by_date_and_metric(rows: list[dict[str, str]]) -> dict[tuple[str, str], str]:
    return {
        (row["date"], row["metric_name"]): row["metric_value"]
        for row in rows
    }


def _metric_names(path: Path) -> set[str]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return {row["metric_name"] for row in csv.DictReader(handle)}


if __name__ == "__main__":
    unittest.main()
