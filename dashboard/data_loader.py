from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Iterable

from .scoring_rules import is_long_candidate, is_short_candidate, normalize_flow_state


MARKET_MAP_COLUMNS = [
    "date",
    "asset_id",
    "asset_name",
    "asset_class",
    "trend_score",
    "rs_score",
    "flow_score",
    "trend_state",
    "rs_state",
    "flow_state",
    "long_candidate",
    "short_candidate",
]


def load_market_map_rows(
    storage_root: str | Path,
    market_map_config: dict[str, Any],
    *,
    dataset_types: Iterable[str] | None = None,
) -> list[dict[str, Any]]:
    """Load processed long-format series into one wide row per asset/date."""
    root = Path(storage_root)
    selected_dataset_types = list(dataset_types or market_map_config.get("dataset_types", ["core", "instruments"]))
    fields = market_map_config["fields"]
    thresholds = market_map_config["thresholds"]
    required_metrics = {
        fields["trend_score"],
        fields["trend_state"],
        fields["rs_score"],
        fields["rs_state"],
        fields["flow_score"],
        fields["flow_state"],
    }

    grouped: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for dataset_type in selected_dataset_types:
        source_dir = root / "processed" / "series" / dataset_type
        if not source_dir.exists():
            continue
        for source_path in sorted(source_dir.iterdir()):
            if source_path.suffix.lower() != ".csv":
                continue
            for row in _read_csv_rows(source_path):
                metric_name = str(row.get("metric_name", "")).strip()
                if metric_name not in required_metrics:
                    continue
                key = (
                    str(row.get("date", "")),
                    str(row.get("dataset_type", "")),
                    str(row.get("asset_code", "")),
                    str(row.get("asset_name", "")),
                )
                item = grouped.setdefault(
                    key,
                    {
                        "date": key[0],
                        "asset_id": key[2],
                        "asset_name": key[3],
                        "asset_class": key[1],
                        "_metrics": {},
                    },
                )
                item["_metrics"][metric_name] = str(row.get("metric_value", "")).strip()

    rows: list[dict[str, Any]] = []
    for item in grouped.values():
        metrics = item["_metrics"]
        if not required_metrics <= set(metrics):
            continue
        try:
            output = {
                "date": item["date"],
                "asset_id": item["asset_id"],
                "asset_name": item["asset_name"],
                "asset_class": item["asset_class"],
                "trend_score": _parse_float(metrics[fields["trend_score"]]),
                "rs_score": _parse_float(metrics[fields["rs_score"]]),
                "flow_score": _parse_float(metrics[fields["flow_score"]]),
                "trend_state": metrics[fields["trend_state"]],
                "rs_state": metrics[fields["rs_state"]],
                "flow_state": normalize_flow_state(metrics[fields["flow_state"]]),
            }
        except ValueError:
            continue
        output["long_candidate"] = is_long_candidate(output, thresholds)
        output["short_candidate"] = is_short_candidate(output, thresholds)
        rows.append(output)

    return sorted(rows, key=lambda row: (row["date"], row["asset_class"], row["asset_id"], row["asset_name"]))


def available_dates(rows: list[dict[str, Any]]) -> list[str]:
    return sorted({str(row["date"]) for row in rows})


def filter_market_map_rows(
    rows: list[dict[str, Any]],
    *,
    date: str | None = None,
    asset_classes: set[str] | None = None,
    flow_states: set[str] | None = None,
    trend_range: tuple[float, float] | None = None,
    rs_range: tuple[float, float] | None = None,
    flow_range: tuple[float, float] | None = None,
) -> list[dict[str, Any]]:
    filtered = rows
    if date is not None:
        filtered = [row for row in filtered if row["date"] == date]
    if asset_classes:
        filtered = [row for row in filtered if row["asset_class"] in asset_classes]
    if flow_states:
        filtered = [row for row in filtered if row["flow_state"] in flow_states]
    if trend_range is not None:
        filtered = [row for row in filtered if trend_range[0] <= row["trend_score"] <= trend_range[1]]
    if rs_range is not None:
        filtered = [row for row in filtered if rs_range[0] <= row["rs_score"] <= rs_range[1]]
    if flow_range is not None:
        filtered = [row for row in filtered if flow_range[0] <= row["flow_score"] <= flow_range[1]]
    return filtered


def matching_asset_ids(rows: list[dict[str, Any]], query: str) -> set[str]:
    terms = [term.strip().lower() for term in query.replace(",", "\n").splitlines() if term.strip()]
    if not terms:
        return set()
    matches: set[str] = set()
    for row in rows:
        haystack = f"{row['asset_id']} {row['asset_name']}".lower()
        if any(term in haystack for term in terms):
            matches.add(str(row["asset_id"]))
    return matches


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _parse_float(value: str) -> float:
    return float(str(value).strip())

