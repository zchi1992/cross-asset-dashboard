from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from src.macro_pipeline.calculations import (
    calculate_curve_factors,
    calculate_hy_ig_spread,
    observation_changes,
)


CURVE_FACTOR_META = {
    "level_10y": ("Level 10Y", "%"),
    "slope_2s10s": ("Slope 2Y-10Y", "bp"),
    "curvature_2s5s10s": ("Curvature 2Y-5Y-10Y", "bp"),
}
SPREAD_SERIES = {"HY_OAS", "IG_OAS", "HY_IG"}
STRESS_SERIES = {"NFCI", "OFR_FSI"}


def load_macro_dataset(storage_root: str | Path, macro_config: dict[str, Any]) -> dict[str, Any]:
    processed_root = Path(storage_root) / str(macro_config.get("processed_path", "processed/macro"))
    curves = _read_csv(processed_root / "curve_points.csv")
    credit = _read_csv(processed_root / "credit.csv")
    state_path = _resolve_source_state_path(Path(storage_root), macro_config)
    source_states = _read_json_list(state_path)
    return {"curves": curves, "credit": credit, "source_states": source_states}


def build_macro_overview(
    dataset: dict[str, Any],
    macro_config: dict[str, Any],
    *,
    as_of: str | None = None,
) -> dict[str, Any]:
    curve_history = _curve_factor_history(dataset["curves"], as_of=as_of)
    curve_cards: list[dict[str, Any]] = []
    for region in sorted(curve_history):
        dates = sorted(curve_history[region])
        if not dates:
            continue
        observed_at = dates[-1]
        current = curve_history[region][observed_at]
        factor_cards = []
        for factor_id, (label, unit) in CURVE_FACTOR_META.items():
            history = [curve_history[region][item]["factors"][factor_id] for item in dates]
            changes = observation_changes(history)
            if unit == "%":
                changes = {key: value * 100.0 if value is not None else None for key, value in changes.items()}
            factor_cards.append(
                {
                    "series_id": f"CURVE.{region}.{factor_id}",
                    "label": label,
                    "value": current["factors"][factor_id],
                    "unit": unit,
                    "changes": changes,
                    "status": _curve_status(factor_id, changes.get("change_20"), macro_config),
                }
            )
        curve_cards.append(
            {
                "region": region,
                "region_name": current["region_name"],
                "observed_at": observed_at,
                "curve_type": current["curve_type"],
                "source_id": current["source_id"],
                "source_name": current["source_name"],
                "source_url": current["source_url"],
                "points": current["points"],
                "factors": factor_cards,
            }
        )

    credit_history = _credit_history(dataset["credit"], as_of=as_of)
    credit_cards = []
    for series_id, rows in sorted(credit_history.items()):
        if not rows:
            continue
        current = rows[-1]
        values = [float(row["value"]) for row in rows]
        windows = (1, 4) if current["frequency"] == "quarterly" else (1, 5, 20)
        changes = observation_changes(values, windows=windows)
        if series_id in {"HY_OAS", "IG_OAS"}:
            changes = {key: value * 100.0 if value is not None else None for key, value in changes.items()}
        credit_cards.append(
            {
                **current,
                "changes": changes,
                "status": _credit_status(series_id, changes, macro_config),
            }
        )

    source_states = _source_states(dataset, curve_cards, credit_cards, macro_config)
    latest_dates = [item["observed_at"] for item in curve_cards + credit_cards]
    return {
        "as_of": max(latest_dates) if latest_dates else None,
        "curves": curve_cards,
        "credit": credit_cards,
        "sources": source_states,
    }


def build_macro_history(
    dataset: dict[str, Any],
    series_id: str,
    *,
    start: str | None = None,
    end: str | None = None,
) -> dict[str, Any] | None:
    if series_id.startswith("CURVE."):
        parts = series_id.split(".", 2)
        if len(parts) != 3 or parts[2] not in CURVE_FACTOR_META:
            return None
        region, factor_id = parts[1], parts[2]
        history = _curve_factor_history(dataset["curves"])
        if region not in history:
            return None
        points = [
            {"date": observed_at, "value": values["factors"][factor_id]}
            for observed_at, values in sorted(history[region].items())
            if _within(observed_at, start, end)
        ]
        label, unit = CURVE_FACTOR_META[factor_id]
        return {"series_id": series_id, "label": label, "unit": unit, "points": points}

    history = _credit_history(dataset["credit"])
    rows = history.get(series_id)
    if rows is None:
        return None
    points = [
        {"date": row["observed_at"], "value": row["value"]}
        for row in rows
        if _within(row["observed_at"], start, end)
    ]
    latest = rows[-1]
    return {"series_id": series_id, "label": latest["label"], "unit": latest["unit"], "points": points}


def _curve_factor_history(rows: list[dict[str, str]], *, as_of: str | None = None) -> dict[str, dict[str, dict[str, Any]]]:
    grouped: dict[tuple[str, str], list[dict[str, str]]] = {}
    for row in rows:
        observed_at = row.get("date", "")
        if not observed_at or (as_of and observed_at > as_of):
            continue
        grouped.setdefault((row.get("region", ""), observed_at), []).append(row)
    history: dict[str, dict[str, dict[str, Any]]] = {}
    for (region, observed_at), values in grouped.items():
        try:
            points_by_tenor = {float(row["tenor_years"]): float(row["value"]) for row in values}
        except (KeyError, ValueError):
            continue
        factors = calculate_curve_factors(points_by_tenor)
        if not region or factors is None:
            continue
        first = values[0]
        history.setdefault(region, {})[observed_at] = {
            "region_name": first.get("region_name", region),
            "curve_type": first.get("curve_type", "government"),
            "source_id": first.get("source_id", "unknown"),
            "source_name": first.get("source_name", first.get("source_id", "unknown")),
            "source_url": first.get("source_url", ""),
            "points": [
                {"tenor_years": tenor, "value": value}
                for tenor, value in sorted(points_by_tenor.items())
            ],
            "factors": factors,
        }
    return history


def _credit_history(rows: list[dict[str, str]], *, as_of: str | None = None) -> dict[str, list[dict[str, Any]]]:
    history: dict[str, list[dict[str, Any]]] = {}
    raw_by_date: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        observed_at = row.get("date", "")
        series_id = row.get("series_id", "")
        if not observed_at or not series_id or (as_of and observed_at > as_of):
            continue
        try:
            value = float(row["value"])
        except (KeyError, ValueError):
            continue
        item = {
            "series_id": series_id,
            "label": row.get("label", series_id),
            "observed_at": observed_at,
            "value": value,
            "unit": row.get("unit", "index"),
            "frequency": row.get("frequency", "daily"),
            "source_id": row.get("source_id", "unknown"),
            "source_name": row.get("source_name", row.get("source_id", "unknown")),
            "source_url": row.get("source_url", ""),
        }
        history.setdefault(series_id, []).append(item)
        raw_by_date[(series_id, observed_at)] = item
    for items in history.values():
        items.sort(key=lambda item: item["observed_at"])

    hy_dates = {item["observed_at"] for item in history.get("HY_OAS", [])}
    ig_dates = {item["observed_at"] for item in history.get("IG_OAS", [])}
    derived = []
    for observed_at in sorted(hy_dates & ig_dates):
        hy = raw_by_date[("HY_OAS", observed_at)]
        ig = raw_by_date[("IG_OAS", observed_at)]
        derived.append(
            {
                "series_id": "HY_IG",
                "label": "HY - IG OAS",
                "observed_at": observed_at,
                "value": calculate_hy_ig_spread(hy["value"], ig["value"]),
                "unit": "bp",
                "frequency": "daily",
                "source_id": "fred",
                "source_name": "FRED / ICE BofA",
                "source_url": "https://fred.stlouisfed.org/",
            }
        )
    if derived:
        history["HY_IG"] = derived
    return history


def _source_states(dataset, curves, credit, macro_config):
    if dataset["source_states"]:
        return dataset["source_states"]
    latest: dict[str, dict[str, Any]] = {}
    for item in curves + credit:
        source_id = item["source_id"]
        if source_id not in latest or item["observed_at"] > latest[source_id]["latest_observation_at"]:
            latest[source_id] = {
                "source_id": source_id,
                "source_name": item["source_name"],
                "status": "fresh",
                "last_success_at": item["observed_at"],
                "latest_observation_at": item["observed_at"],
                "message": None,
            }
    return sorted(latest.values(), key=lambda item: item["source_id"])


def _curve_status(factor_id: str, change: float | None, config: dict[str, Any]) -> str:
    if change is None:
        return "observe"
    threshold = float(config.get("thresholds", {}).get("curve_change_bp", 10.0))
    if abs(change) < threshold:
        return "stable"
    if factor_id == "slope_2s10s":
        return "steepening" if change > 0 else "flattening"
    if factor_id == "curvature_2s5s10s":
        return "curvature_rising" if change > 0 else "curvature_falling"
    return "rising" if change > 0 else "falling"


def _credit_status(series_id: str, changes: dict[str, float | None], config: dict[str, Any]) -> str:
    thresholds = config.get("thresholds", {})
    if series_id == "SLOOS":
        change = changes.get("change_1")
        threshold = float(thresholds.get("sloos_change_pp", 5.0))
    else:
        change = changes.get("change_20")
        threshold = float(
            thresholds.get("credit_spread_change_bp", 10.0)
            if series_id in SPREAD_SERIES
            else thresholds.get("stress_index_change", 0.25)
        )
    if change is None:
        return "observe"
    if abs(change) < threshold:
        return "stable"
    return "pressure" if change > 0 else "support"


def _resolve_source_state_path(storage_root: Path, macro_config: dict[str, Any]) -> Path:
    configured = Path(str(macro_config.get("source_state_path", "../state/macro_sources.json")))
    return configured if configured.is_absolute() else (storage_root / configured).resolve()


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _read_json_list(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return value if isinstance(value, list) else []


def _within(value: str, start: str | None, end: str | None) -> bool:
    return (start is None or value >= start) and (end is None or value <= end)
