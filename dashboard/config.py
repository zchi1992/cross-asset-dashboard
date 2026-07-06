from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.zsxq_pipeline.config import Config, load_config


DEFAULT_MARKET_MAP_CONFIG: dict[str, Any] = {
    "dataset_types": ["core", "instruments"],
    "fields": {
        "asset_id": "asset_code",
        "asset_name": "asset_name",
        "asset_class": "dataset_type",
        "trend_score": "capped_final_trend_score",
        "trend_state": "state_name",
        "rs_score": "rs_score",
        "early_reversal": "early_reversal",
        "strength_momentum": "strength_momentum",
        "relative_strength": "relative_strength",
        "rs_state": "current_relative_state",
        "flow_score": "funding_leverage_value",
        "flow_state": "funding_signal_direction",
        "leverage_value": "funding_leverage_value",
        "leverage_velocity": "leverage_velocity",
        "leverage_velocity_score": "leverage_velocity_score",
    },
    "quadrants": {
        "x_midline": 0,
        "y_midline": 0,
    },
    "thresholds": {
        "long_trend_threshold": 70,
        "long_rs_threshold": 70,
        "long_flow_threshold": 50,
        "short_trend_threshold": -70,
        "short_rs_threshold": -70,
        "short_flow_threshold": -50,
    },
    "size": {
        "min": 8,
        "max": 42,
    },
    "colors": {
        "Leveraging": "#1f9d55",
        "Deleveraging": "#d64545",
        "Neutral": "#7a869a",
    },
    "symbols": {
        "core": "circle",
        "instruments": "diamond",
    },
}


@dataclass(frozen=True)
class DashboardConfig:
    repo_config: Config
    market_map: dict[str, Any]

    @property
    def storage_root(self) -> Path:
        return self.repo_config.storage_root


def load_dashboard_config(path: str | Path = "config.yaml") -> DashboardConfig:
    repo_config = load_config(path)
    dashboard_raw = repo_config.raw.get("dashboard", {})
    market_map_raw = dashboard_raw.get("market_map", {})
    return DashboardConfig(
        repo_config=repo_config,
        market_map=_deep_merge(DEFAULT_MARKET_MAP_CONFIG, market_map_raw),
    )


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for key, value in base.items():
        if isinstance(value, dict):
            merged[key] = _deep_merge(value, {})
        elif isinstance(value, list):
            merged[key] = list(value)
        else:
            merged[key] = value

    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        elif isinstance(value, list):
            merged[key] = list(value)
        else:
            merged[key] = value
    return merged
