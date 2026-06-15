from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from typing import Callable, Iterable

REQUIRED_FIELDS = {
    "current_leverage_state",
    "current_leverage_state_duration",
    "leverage_value",
}

OPTIONAL_FIELDS = {
    "leverage_value_change_d1",
}

INPUT_FIELD_ALIASES: dict[str, str] = {}

OUTPUT_FIELDS = [
    "funding_current_leverage_state",
    "funding_current_leverage_state_duration",
    "funding_leverage_value",
    "position_score",
    "velocity_1d",
    "velocity_5d",
    "velocity_10d",
    "long_velocity_1d_score",
    "long_velocity_5d_score",
    "long_velocity_10d_score",
    "long_velocity_score",
    "short_velocity_1d_score",
    "short_velocity_5d_score",
    "short_velocity_10d_score",
    "short_velocity_score",
    "velocity_window_count",
    "maturity_score",
    "long_funding_score",
    "short_funding_score",
    "funding_direction",
    "funding_score",
    "funding_signal_direction",
    "funding_signal_strength",
    "funding_signal_rank",
    "funding_signal_rank_pct",
    "funding_signal_bucket",
]

LEVERAGE_STATES = {
    "加杠杆": "long",
    "去杠杆": "short",
}

LEGACY_DIRECTIONS = {
    "long": "long_candidate",
    "short": "short_candidate",
}

VELOCITY_WINDOWS = (1, 5, 10)
VELOCITY_WEIGHTS = {
    1: 0.2,
    5: 0.5,
    10: 0.3,
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
    """Calculate Funding Score V1 rows from long-format asset rows."""
    grouped = _group_input_rows(rows)
    scored_by_scope: dict[tuple[str, str], list[dict[str, str | float]]] = defaultdict(list)

    for asset_key, rows_by_date in grouped.items():
        history: list[tuple[str, dict[str, str]]] = []
        for date in sorted(rows_by_date):
            values = rows_by_date[date]
            missing = sorted(REQUIRED_FIELDS - set(values))
            if missing:
                asset_label = f"{asset_key.dataset_type}/{asset_key.asset_code}/{asset_key.asset_name}"
                raise ValueError(f"missing funding score fields for {asset_label} {date}: {', '.join(missing)}")

            calculated = _calculate_base_values(
                asset_key,
                date,
                values,
                history,
                validate_leverage_change=validate_leverage_change,
            )
            if int(calculated["velocity_window_count"]) > 0:
                scored_by_scope[(asset_key.dataset_type, date)].append(calculated)
            history.append((date, values))

    for scope_rows in scored_by_scope.values():
        _apply_percentile_scores(scope_rows)
        _apply_scores(scope_rows)

    output_rows: list[dict[str, str]] = []
    for dataset_type, date in sorted(scored_by_scope):
        scope_rows = scored_by_scope[(dataset_type, date)]
        _apply_rankings(scope_rows)
        for values in sorted(scope_rows, key=lambda item: (str(item["asset_code"]), str(item["asset_name"]))):
            output_rows.extend(_to_metric_rows(date, values))
    return output_rows


def _group_input_rows(rows: Iterable[dict[str, str]]) -> dict[AssetKey, dict[str, dict[str, str]]]:
    accepted_fields = REQUIRED_FIELDS | OPTIONAL_FIELDS
    grouped: dict[AssetKey, dict[str, dict[str, str]]] = defaultdict(lambda: defaultdict(dict))
    for row in rows:
        metric_name = str(row.get("metric_name", "")).strip()
        normalized_metric = INPUT_FIELD_ALIASES.get(metric_name, metric_name)
        if normalized_metric not in accepted_fields:
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
    history: list[tuple[str, dict[str, str]]],
    *,
    validate_leverage_change: bool,
) -> dict[str, str | float]:
    current_leverage_state = _normalize_leverage_state(values["current_leverage_state"])
    direction = LEVERAGE_STATES[current_leverage_state]
    leverage_value = _parse_float(values["leverage_value"], "leverage_value")
    leverage_duration = _parse_duration(
        values["current_leverage_state_duration"],
        "current_leverage_state_duration",
    )
    velocities: dict[int, float] = {}
    for window in VELOCITY_WINDOWS:
        if len(history) >= window:
            previous_values = history[-window][1]
            previous_leverage_value = _parse_float(previous_values["leverage_value"], f"leverage_value_t-{window}")
            velocities[window] = leverage_value - previous_leverage_value

    if validate_leverage_change and 1 in velocities and values.get("leverage_value_change_d1", ""):
        leverage_value_change = _parse_float(values["leverage_value_change_d1"], "leverage_value_change_d1")
        if not math.isclose(
            leverage_value_change,
            velocities[1],
            rel_tol=0.0,
            abs_tol=LEVERAGE_CHANGE_TOLERANCE,
        ):
            asset_label = f"{asset_key.dataset_type}/{asset_key.asset_code}/{asset_key.asset_name}"
            raise ValueError(
                "leverage_value_change_d1 mismatch for "
                f"{asset_label} {date}: field={leverage_value_change}, calculated={velocities[1]}"
            )

    return {
        "dataset_type": asset_key.dataset_type,
        "asset_code": asset_key.asset_code,
        "asset_name": asset_key.asset_name,
        "funding_current_leverage_state": current_leverage_state,
        "funding_current_leverage_state_duration": leverage_duration,
        "funding_leverage_value": leverage_value,
        "velocity_1d": velocities.get(1, math.nan),
        "velocity_5d": velocities.get(5, math.nan),
        "velocity_10d": velocities.get(10, math.nan),
        "velocity_window_count": len(velocities),
        "maturity_score": _maturity_score(leverage_duration),
        "funding_direction": direction,
        "funding_signal_direction": LEGACY_DIRECTIONS[direction],
    }


def _apply_percentile_scores(rows: list[dict[str, str | float]]) -> None:
    _assign_percentile(rows, "funding_leverage_value", "position_score")
    for window in VELOCITY_WINDOWS:
        source = f"velocity_{window}d"
        _assign_percentile(rows, source, f"long_velocity_{window}d_score")
        _assign_percentile(rows, source, f"short_velocity_{window}d_score", transform=lambda value: -value)


def _apply_scores(rows: list[dict[str, str | float]]) -> None:
    for row in rows:
        long_velocity_score = _weighted_velocity_score(row, "long")
        short_velocity_score = _weighted_velocity_score(row, "short")
        position_score = float(row["position_score"])
        maturity_score = float(row["maturity_score"])
        long_funding_score = (
            0.4 * long_velocity_score
            + 0.4 * maturity_score
            + 0.2 * (100 - position_score)
        )
        short_funding_score = (
            0.4 * short_velocity_score
            + 0.4 * maturity_score
            + 0.2 * position_score
        )
        row["long_velocity_score"] = long_velocity_score
        row["short_velocity_score"] = short_velocity_score
        row["long_funding_score"] = long_funding_score if row["funding_direction"] == "long" else math.nan
        row["short_funding_score"] = short_funding_score if row["funding_direction"] == "short" else math.nan
        row["funding_score"] = long_funding_score if row["funding_direction"] == "long" else short_funding_score
        row["funding_signal_strength"] = row["funding_score"]
        _validate_score_range(row, "position_score")
        _validate_score_range(row, "maturity_score")
        _validate_score_range(row, "funding_score")


def _weighted_velocity_score(row: dict[str, str | float], prefix: str) -> float:
    available: list[tuple[float, float]] = []
    for window in VELOCITY_WINDOWS:
        score = float(row[f"{prefix}_velocity_{window}d_score"])
        if math.isfinite(score):
            available.append((VELOCITY_WEIGHTS[window], score))
    if not available:
        return math.nan
    total_weight = sum(weight for weight, _score in available)
    return sum((weight / total_weight) * score for weight, score in available)


def _apply_rankings(rows: list[dict[str, str | float]]) -> None:
    rows_by_direction: dict[str, list[dict[str, str | float]]] = defaultdict(list)
    for row in rows:
        rows_by_direction[str(row["funding_direction"])].append(row)

    for direction_rows in rows_by_direction.values():
        ranked = sorted(
            direction_rows,
            key=lambda item: (
                -float(item["funding_score"]),
                -float(item["velocity_window_count"]),
                str(item["asset_code"]),
            ),
        )
        total = len(ranked)
        denominator = max(total, 1)
        for index, row in enumerate(ranked, start=1):
            rank_pct = index / denominator
            row["funding_signal_rank"] = index
            row["funding_signal_rank_pct"] = rank_pct
            row["funding_signal_bucket"] = _bucket(float(row["funding_score"]), rank_pct)


def _assign_percentile(
    rows: list[dict[str, str | float]],
    source_field: str,
    target_field: str,
    *,
    transform: Callable[[float], float] | None = None,
) -> None:
    values: list[tuple[int, float]] = []
    for index, row in enumerate(rows):
        value = float(row[source_field])
        if math.isfinite(value):
            values.append((index, transform(value) if transform is not None else value))

    for row in rows:
        row[target_field] = math.nan

    if not values:
        return
    if len(values) == 1:
        rows[values[0][0]][target_field] = 50.0
        return

    sorted_values = sorted(values, key=lambda item: item[1])
    ranks: dict[int, float] = {}
    cursor = 0
    while cursor < len(sorted_values):
        end = cursor + 1
        while end < len(sorted_values) and sorted_values[end][1] == sorted_values[cursor][1]:
            end += 1
        average_rank = (cursor + end - 1) / 2
        percentile = average_rank / (len(sorted_values) - 1) * 100
        for index in range(cursor, end):
            ranks[sorted_values[index][0]] = percentile
        cursor = end

    for index, percentile in ranks.items():
        rows[index][target_field] = percentile


def _maturity_score(duration: float) -> float:
    if duration <= 1:
        return 20.0
    if duration <= 4:
        return 20 + (duration - 1) / 3 * 80
    if duration <= 10:
        return 100.0
    if duration <= 20:
        return 100 - (duration - 10) / 10 * 50
    if duration <= 30:
        return 50 - (duration - 20) / 10 * 40
    return 10.0


def _bucket(funding_score: float, rank_pct: float) -> str:
    if funding_score <= 0 or rank_pct > 0.70:
        return "weak"
    if rank_pct <= 0.10:
        return "strong"
    if rank_pct <= 0.30:
        return "watch"
    return "neutral"


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


def _validate_score_range(row: dict[str, str | float], field_name: str) -> None:
    value = float(row[field_name])
    if not 0 <= value <= 100:
        asset_label = f"{row['dataset_type']}/{row['asset_code']}/{row['asset_name']}"
        raise ValueError(f"{field_name} out of range for {asset_label}: {value}")


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
    if not math.isfinite(float(value)):
        return ""
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.2f}"
