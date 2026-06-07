from __future__ import annotations

import csv
from pathlib import Path

from .relative_strength import (
    INPUT_FIELD_ALIASES as RS_INPUT_FIELD_ALIASES,
    REQUIRED_FIELDS as RS_REQUIRED_FIELDS,
    calculate_rs_score_rows,
)
from .trend_score import (
    INPUT_FIELD_ALIASES as TREND_INPUT_FIELD_ALIASES,
    REQUIRED_FIELDS as TREND_REQUIRED_FIELDS,
    SERIES_COLUMNS,
    calculate_trend_score_rows,
)
from ..utils import ensure_dir


def build_processed_series_with_trend_scores(
    storage_root: Path,
    dataset_types: list[str] | None = None,
) -> list[Path]:
    """Build processed per-asset series files with trend and rs score metrics."""
    selected_dataset_types = dataset_types or ["core", "instruments"]
    written_paths: list[Path] = []
    for dataset_type in selected_dataset_types:
        source_dir = storage_root / "series" / dataset_type
        if not source_dir.exists():
            continue
        target_dir = ensure_dir(storage_root / "processed" / "series" / dataset_type)
        for source_path in sorted(source_dir.iterdir()):
            if source_path.suffix.lower() != ".csv":
                continue
            source_rows = _read_csv_rows(source_path)
            trend_rows = calculate_trend_score_rows(_complete_rows(source_rows, TREND_INPUT_FIELD_ALIASES, TREND_REQUIRED_FIELDS))
            rs_rows = calculate_rs_score_rows(_complete_rows(source_rows, RS_INPUT_FIELD_ALIASES, RS_REQUIRED_FIELDS))
            output_rows = trend_rows + rs_rows
            if not output_rows:
                continue
            target_path = target_dir / source_path.name
            _write_csv_rows(target_path, output_rows)
            written_paths.append(target_path)
    return written_paths


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _complete_rows(
    rows: list[dict[str, str]],
    input_field_aliases: dict[str, str],
    required_fields: set[str],
) -> list[dict[str, str]]:
    fields_by_date: dict[str, dict[str, str]] = {}
    for row in rows:
        metric_name = str(row.get("metric_name", "")).strip()
        normalized_metric = input_field_aliases.get(metric_name, metric_name)
        if normalized_metric not in required_fields:
            continue
        date = str(row.get("date", ""))
        fields_by_date.setdefault(date, {})[normalized_metric] = str(row.get("metric_value", "")).strip()

    complete_dates = {
        date
        for date, values in fields_by_date.items()
        if required_fields <= set(values) and all(values[field] for field in required_fields)
    }
    return [row for row in rows if str(row.get("date", "")) in complete_dates]


def _write_csv_rows(path: Path, rows: list[dict[str, str]]) -> None:
    ensure_dir(path.parent)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=SERIES_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
