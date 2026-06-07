from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable

from .trend_score import SERIES_COLUMNS

REQUIRED_FIELDS = {
    "current_leverage_state",
    "current_leverage_state_duration",
    "current_leverage_state_return",
    "previous_leverage_state",
    "previous_leverage_state_return",
    "leverage_value",
    "leverage_value_change_d1",
    "current_relative_state",
    "current_relative_state_duration",
    "current_relative_state_return",
    "previous_relative_state",
    "previous_relative_state_duration",
    "previous_relative_state_return",
}

INPUT_FIELD_ALIASES: dict[str, str] = {}

OUTPUT_FIELDS = [
    "funding_current_leverage_state",
    "funding_current_leverage_state_duration",
    "funding_current_leverage_state_return",
    "funding_previous_leverage_state",
    "funding_previous_leverage_state_return",
    "funding_current_relative_state",
    "funding_current_relative_state_duration",
    "funding_current_relative_state_return",
    "funding_previous_relative_state",
    "funding_previous_relative_state_duration",
    "funding_previous_relative_state_return",
    "funding_leverage_value",
    "funding_leverage_value_change",
    "funding_relative_return_change",
    "funding_leverage_change_z",
    "funding_return_change_z",
    "long_funding_lead_score",
    "short_funding_lead_score",
    "funding_signal_direction",
    "funding_signal_strength",
    "funding_duration_priority",
    "funding_signal_bucket",
    "funding_signal_rank",
    "funding_signal_rank_pct",
]

LEVERAGE_STATES = {
    "加杠杆": "long_candidate",
    "去杠杆": "short_candidate",
}

LEVERAGE_CHANGE_TOLERANCE = 1e-6


@dataclass(frozen=True)
class AssetKey:
    dataset_type: str
    asset_code: str
    asset_name: str


def calculate_funding_lead_score_rows(
    rows: Iterable[dict[str, str]],
    *,
    validate_leverage_change: bool = True,
) -> list[dict[str, str]]:
    """Calculate funding lead score rows from long-format asset rows."""
    grouped = _group_input_rows(rows)
    scored_by_scope: dict[tuple[str, str], list[dict[str, str | float]]] = defaultdict(list)

    for asset_key, rows_by_date in grouped.items():
        previous: dict[str, str] | None = None
        for date in sorted(rows_by_date):
            values = rows_by_date[date]
            missing = sorted(REQUIRED_FIELDS - set(values))
            if missing:
                asset_label = f"{asset_key.dataset_type}/{asset_key.asset_code}/{asset_key.asset_name}"
                raise ValueError(f"missing funding lead score fields for {asset_label} {date}: {', '.join(missing)}")
            if previous is None:
                previous = values
                continue

            calculated = _calculate_base_values(
                asset_key,
                date,
                values,
                previous,
                validate_leverage_change=validate_leverage_change,
            )
            scored_by_scope[(asset_key.dataset_type, date)].append(calculated)
            previous = values

    for scope_rows in scored_by_scope.values():
        _apply_zscores(scope_rows)
        _apply_scores(scope_rows)

    output_rows: list[dict[str, str]] = []
    for dataset_type, date in sorted(scored_by_scope):
        scope_rows = scored_by_scope[(dataset_type, date)]
        _apply_rankings(scope_rows)
        for values in sorted(scope_rows, key=lambda item: (str(item["asset_code"]), str(item["asset_name"]))):
            output_rows.extend(_to_metric_rows(date, values))
    return output_rows


def _group_input_rows(rows: Iterable[dict[str, str]]) -> dict[AssetKey, dict[str, dict[str, str]]]:
    grouped: dict[AssetKey, dict[str, dict[str, str]]] = defaultdict(lambda: defaultdict(dict))
    for row in rows:
        metric_name = str(row.get("metric_name", "")).strip()
        normalized_metric = INPUT_FIELD_ALIASES.get(metric_name, metric_name)
        if normalized_metric not in REQUIRED_FIELDS:
            continue
        key = AssetKey(
            dataset_type=str(row.get("dataset_type", "")),
            asset_code=str(row.get("asset_code", "")),
            asset_name=str(row.get("asset_name", "")),
        )
        date = str(row.get("date", ""))
        grouped[key][date][normalized_metric] = str(row.get("metric_value", "")).strip()
    return grouped


def _calculate_base_values(
    asset_key: AssetKey,
    date: str,
    values: dict[str, str],
    previous: dict[str, str],
    *,
    validate_leverage_change: bool,
) -> dict[str, str | float]:
    current_leverage_state = _normalize_leverage_state(values["current_leverage_state"])
    direction = LEVERAGE_STATES[current_leverage_state]
    leverage_value = _parse_float(values["leverage_value"], "leverage_value")
    previous_leverage_value = _parse_float(previous["leverage_value"], "previous leverage_value")
    leverage_value_change = _parse_float(values["leverage_value_change_d1"], "leverage_value_change_d1")
    calculated_leverage_change = leverage_value - previous_leverage_value
    if validate_leverage_change and not math.isclose(
        leverage_value_change,
        calculated_leverage_change,
        rel_tol=0.0,
        abs_tol=LEVERAGE_CHANGE_TOLERANCE,
    ):
        asset_label = f"{asset_key.dataset_type}/{asset_key.asset_code}/{asset_key.asset_name}"
        raise ValueError(
            "leverage_value_change_d1 mismatch for "
            f"{asset_label} {date}: field={leverage_value_change}, calculated={calculated_leverage_change}"
        )

    current_relative_return = _parse_float(values["current_relative_state_return"], "current_relative_state_return")
    previous_relative_return = _parse_float(
        previous["current_relative_state_return"],
        "previous current_relative_state_return",
    )
    relative_return_change = current_relative_return - previous_relative_return
    current_leverage_duration = _parse_duration(
        values["current_leverage_state_duration"],
        "current_leverage_state_duration",
    )

    return {
        "dataset_type": asset_key.dataset_type,
        "asset_code": asset_key.asset_code,
        "asset_name": asset_key.asset_name,
        "funding_current_leverage_state": current_leverage_state,
        "funding_current_leverage_state_duration": current_leverage_duration,
        "funding_current_leverage_state_return": _parse_float(
            values["current_leverage_state_return"],
            "current_leverage_state_return",
        ),
        "funding_previous_leverage_state": _normalize_leverage_state(values["previous_leverage_state"]),
        "funding_previous_leverage_state_return": _parse_float(
            values["previous_leverage_state_return"],
            "previous_leverage_state_return",
        ),
        "funding_current_relative_state": values["current_relative_state"],
        "funding_current_relative_state_duration": _parse_duration(
            values["current_relative_state_duration"],
            "current_relative_state_duration",
        ),
        "funding_current_relative_state_return": current_relative_return,
        "funding_previous_relative_state": values["previous_relative_state"],
        "funding_previous_relative_state_duration": _parse_duration(
            values["previous_relative_state_duration"],
            "previous_relative_state_duration",
        ),
        "funding_previous_relative_state_return": _parse_float(
            values["previous_relative_state_return"],
            "previous_relative_state_return",
        ),
        "funding_leverage_value": leverage_value,
        "funding_leverage_value_change": leverage_value_change,
        "funding_relative_return_change": relative_return_change,
        "funding_signal_direction": direction,
        "funding_duration_priority": 1 if 5 <= current_leverage_duration <= 15 else 0,
    }


def _apply_zscores(rows: list[dict[str, str | float]]) -> None:
    leverage_values = [float(row["funding_leverage_value_change"]) for row in rows]
    return_values = [float(row["funding_relative_return_change"]) for row in rows]
    leverage_zscores = _zscores(leverage_values)
    return_zscores = _zscores(return_values)
    for row, leverage_z, return_z in zip(rows, leverage_zscores, return_zscores):
        row["funding_leverage_change_z"] = leverage_z
        row["funding_return_change_z"] = return_z


def _apply_scores(rows: list[dict[str, str | float]]) -> None:
    for row in rows:
        leverage_z = float(row["funding_leverage_change_z"])
        return_z = float(row["funding_return_change_z"])
        long_score = leverage_z - return_z
        short_score = -leverage_z + return_z
        row["long_funding_lead_score"] = long_score
        row["short_funding_lead_score"] = short_score
        if row["funding_signal_direction"] == "long_candidate":
            row["funding_signal_strength"] = long_score
        else:
            row["funding_signal_strength"] = short_score


def _apply_rankings(rows: list[dict[str, str | float]]) -> None:
    rows_by_direction: dict[str, list[dict[str, str | float]]] = defaultdict(list)
    for row in rows:
        rows_by_direction[str(row["funding_signal_direction"])].append(row)

    for direction_rows in rows_by_direction.values():
        ranked = sorted(
            direction_rows,
            key=lambda item: (
                -int(item["funding_duration_priority"]),
                -float(item["funding_signal_strength"]),
                -float(item["funding_current_leverage_state_duration"]),
                str(item["asset_code"]),
            ),
        )
        total = len(ranked)
        denominator = max(total, 1)
        for index, row in enumerate(ranked, start=1):
            rank_pct = index / denominator
            row["funding_signal_rank"] = index
            row["funding_signal_rank_pct"] = rank_pct
            row["funding_signal_bucket"] = _bucket(float(row["funding_signal_strength"]), rank_pct)


def _bucket(signal_strength: float, rank_pct: float) -> str:
    if signal_strength <= 0 or rank_pct > 0.70:
        return "weak"
    if rank_pct <= 0.10:
        return "strong"
    if rank_pct <= 0.30:
        return "watch"
    return "neutral"


def _zscores(values: list[float]) -> list[float]:
    if not values:
        return []
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    stddev = math.sqrt(variance)
    if stddev == 0:
        return [0.0 for _ in values]
    return [(value - mean) / stddev for value in values]


def _normalize_leverage_state(value: str) -> str:
    text = str(value).strip()
    if text not in LEVERAGE_STATES:
        raise ValueError(f"unsupported leverage state: {value}")
    return text


def _parse_float(value: str, field_name: str) -> float:
    try:
        return float(str(value).strip())
    except ValueError as exc:
        raise ValueError(f"invalid {field_name}: {value}") from exc


def _parse_duration(value: str, field_name: str) -> float:
    duration = _parse_float(value, field_name)
    if duration < 1:
        raise ValueError(f"invalid {field_name}: {value}")
    return duration


def _to_metric_rows(date: str, values: dict[str, str | float]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for field in OUTPUT_FIELDS:
        rows.append(
            {
                "date": date,
                "dataset_type": str(values["dataset_type"]),
                "asset_code": str(values["asset_code"]),
                "asset_name": str(values["asset_name"]),
                "metric_name": field,
                "metric_value": _format_value(values[field]),
            }
        )
    return rows


def _format_value(value: str | float) -> str:
    if isinstance(value, str):
        return value
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.2f}"
