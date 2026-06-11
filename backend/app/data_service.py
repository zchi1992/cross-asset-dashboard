from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from dashboard.config import load_dashboard_config
from dashboard.data_loader import available_dates, load_market_map_rows

from .schemas import AssetMetadata, ConfigResponse, DefaultFilters, PlaybackSettings, ScoreRanges, SnapshotItem


REPO_ROOT = Path(__file__).resolve().parents[2]
FUNDING_STATES = ["Leveraging", "Deleveraging"]
RS_STATES = ["Lag", "Weakening", "Improving", "Lead"]


def load_config_response() -> ConfigResponse:
    rows = load_rows()
    asset_classes = sorted({str(row["asset_class"]) for row in rows}) or ["core", "instruments"]
    return ConfigResponse(
        score_ranges=ScoreRanges(
            rs_score=_score_range(rows, "rs_score", default=[-100, 100]),
            funding_score=_score_range(rows, "flow_score", default=[-100, 100], lower_quantile=0.005, upper_quantile=0.995),
            trend_score=[-100, 100],
        ),
        default_filters=DefaultFilters(
            asset_class=asset_classes[0],
            funding_states=FUNDING_STATES,
            rs_states=RS_STATES,
        ),
        playback=PlaybackSettings(speeds=[0.5, 1, 2, 5], default_speed=1),
        asset_classes=asset_classes,
        funding_states=FUNDING_STATES,
        rs_states=RS_STATES,
    )


@lru_cache(maxsize=1)
def load_rows() -> tuple[dict, ...]:
    dashboard_config = load_dashboard_config(REPO_ROOT / "config.yaml")
    rows = load_market_map_rows(dashboard_config.storage_root, dashboard_config.market_map)
    return tuple(rows)


def get_dates() -> list[str]:
    return available_dates(list(load_rows()))


def get_assets() -> list[AssetMetadata]:
    latest_by_symbol: dict[str, AssetMetadata] = {}
    for row in load_rows():
        symbol = str(row["asset_id"])
        latest_by_symbol[symbol] = AssetMetadata(
            symbol=symbol,
            name=str(row["asset_name"]),
            asset_class=str(row["asset_class"]),
        )
    return sorted(latest_by_symbol.values(), key=lambda asset: (asset.asset_class, asset.symbol))


def get_snapshot(date: str) -> list[SnapshotItem]:
    return [_to_snapshot_item(row) for row in load_rows() if row["date"] == date]


def get_playback(start: str | None, end: str | None) -> tuple[list[str], dict[str, list[SnapshotItem]]]:
    dates = get_dates()
    if start is not None:
        dates = [date for date in dates if date >= start]
    if end is not None:
        dates = [date for date in dates if date <= end]
    frames = {date: get_snapshot(date) for date in dates}
    return dates, frames


def _to_snapshot_item(row: dict) -> SnapshotItem:
    return SnapshotItem(
        symbol=str(row["asset_id"]),
        asset_name=str(row["asset_name"]),
        asset_class=str(row["asset_class"]),
        trend_score=float(row["trend_score"]),
        rs_score=float(row["rs_score"]),
        rs_state=str(row["rs_state"]),
        funding_score=float(row["flow_score"]),
        funding_state=str(row["flow_state"]),
        trend_state=str(row.get("trend_state") or ""),
        long_candidate=bool(row.get("long_candidate")),
        short_candidate=bool(row.get("short_candidate")),
    )


def _score_range(
    rows: tuple[dict, ...],
    field: str,
    *,
    default: list[float],
    lower_quantile: float = 0,
    upper_quantile: float = 1,
) -> list[float]:
    values = [float(row[field]) for row in rows if row.get(field) not in {None, ""}]
    if not values:
        return default
    values = sorted(values)
    low = _quantile_value(values, lower_quantile)
    high = _quantile_value(values, upper_quantile)
    if low == high:
        return [low - 1, high + 1]
    padding = max((high - low) * 0.05, 1)
    return [round(low - padding, 2), round(high + padding, 2)]


def _quantile_value(values: list[float], quantile: float) -> float:
    index = round((len(values) - 1) * min(max(quantile, 0), 1))
    return values[index]
