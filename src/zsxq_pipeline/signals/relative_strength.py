from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable

from .trend_score import SERIES_COLUMNS

SCORE_FIELDS = ("early_reversal", "strength_momentum", "relative_strength")
STATE_FIELDS = ("current_relative_state", "previous_relative_state")
DURATION_FIELDS = ("current_state_duration", "previous_state_duration")
INPUT_FIELD_ALIASES = {
    "current_state_duration": "current_relative_state_duration",
    "previous_state_duration": "previous_relative_state_duration",
}
REQUIRED_FIELDS = set(SCORE_FIELDS) | set(STATE_FIELDS) | {
    "current_relative_state_duration",
    "previous_relative_state_duration",
}

STATE_LABELS = {
    "lead": "Lead",
    "weakening": "Weakening",
    "improving": "Improving",
    "lag": "Lag",
}

TRANSITIONS = {
    ("Lag", "Lead"): (120, "strong_reversal_to_lead"),
    ("Weakening", "Lead"): (110, "renewed_leadership"),
    ("Lag", "Improving"): (100, "low_level_improvement"),
    ("Improving", "Lead"): (100, "improvement_confirmed"),
    ("Weakening", "Improving"): (60, "weakness_repairing"),
    ("Lead", "Improving"): (30, "leadership_cooling_but_positive"),
    ("Lag", "Weakening"): (-40, "weak_to_unstable"),
    ("Improving", "Weakening"): (-60, "improvement_failed"),
    ("Lead", "Weakening"): (-90, "leadership_losing_momentum"),
    ("Improving", "Lag"): (-90, "reversal_failed_to_lag"),
    ("Weakening", "Lag"): (-100, "weakness_confirmed"),
    ("Lead", "Lag"): (-120, "leadership_collapse"),
}

OUTPUT_FIELDS = [
    "rs_score",
    "early_reversal",
    "strength_momentum",
    "relative_strength",
    "current_relative_state",
    "previous_relative_state",
    "current_state_duration",
    "previous_state_duration",
    "transition_score",
    "base_transition_score",
    "state_transition",
    "relative_signal_type",
    "freshness_factor",
    "previous_maturity_factor",
]


@dataclass(frozen=True)
class AssetKey:
    dataset_type: str
    asset_code: str
    asset_name: str


def calculate_rs_score_rows(rows: Iterable[dict[str, str]]) -> list[dict[str, str]]:
    """Calculate relative strength score rows from existing long-format asset rows."""
    grouped = _group_input_rows(rows)
    output_rows: list[dict[str, str]] = []
    for asset_key, rows_by_date in grouped.items():
        for date in sorted(rows_by_date):
            values = rows_by_date[date]
            missing = sorted(REQUIRED_FIELDS - set(values))
            if missing:
                asset_label = f"{asset_key.dataset_type}/{asset_key.asset_code}/{asset_key.asset_name}"
                raise ValueError(f"missing rs score fields for {asset_label} {date}: {', '.join(missing)}")

            calculated = _calculate_date_values(values)
            output_rows.extend(_to_metric_rows(asset_key, date, calculated))
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
        grouped[key][date][normalized_metric] = str(row.get("metric_value", ""))
    return grouped


def _calculate_date_values(values: dict[str, str]) -> dict[str, str | float]:
    early_reversal = _parse_float(values["early_reversal"], "early_reversal")
    strength_momentum = _parse_float(values["strength_momentum"], "strength_momentum")
    relative_strength = _parse_float(values["relative_strength"], "relative_strength")
    current_state = _normalize_state(values["current_relative_state"])
    previous_state = _normalize_state(values["previous_relative_state"])
    current_duration = _parse_duration(
        values["current_relative_state_duration"],
        "current_relative_state_duration",
    )
    previous_duration = _parse_duration(
        values["previous_relative_state_duration"],
        "previous_relative_state_duration",
    )

    if current_state == previous_state:
        raise ValueError(f"current_relative_state must differ from previous_relative_state: {current_state}")

    transition = (previous_state, current_state)
    if transition not in TRANSITIONS:
        raise ValueError(f"unsupported relative state transition: {previous_state}->{current_state}")

    base_transition_score, signal_type = TRANSITIONS[transition]
    freshness_factor = math.exp(-(current_duration - 1) / 5)
    previous_maturity_factor = min(previous_duration / 15, 1)
    transition_score = base_transition_score * freshness_factor * previous_maturity_factor
    rs_score = (
        0.35 * early_reversal
        + 0.30 * strength_momentum
        + 0.20 * relative_strength
        + 0.15 * transition_score
    )

    return {
        "rs_score": rs_score,
        "early_reversal": early_reversal,
        "strength_momentum": strength_momentum,
        "relative_strength": relative_strength,
        "current_relative_state": current_state,
        "previous_relative_state": previous_state,
        "current_state_duration": current_duration,
        "previous_state_duration": previous_duration,
        "transition_score": transition_score,
        "base_transition_score": base_transition_score,
        "state_transition": f"{previous_state}->{current_state}",
        "relative_signal_type": signal_type,
        "freshness_factor": freshness_factor,
        "previous_maturity_factor": previous_maturity_factor,
    }


def _normalize_state(value: str) -> str:
    text = str(value).strip()
    normalized = STATE_LABELS.get(text.lower())
    if normalized is None:
        raise ValueError(f"unsupported relative state: {value}")
    return normalized


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


def _to_metric_rows(asset_key: AssetKey, date: str, values: dict[str, str | float]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for field in OUTPUT_FIELDS:
        rows.append(
            {
                "date": date,
                "dataset_type": asset_key.dataset_type,
                "asset_code": asset_key.asset_code,
                "asset_name": asset_key.asset_name,
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
