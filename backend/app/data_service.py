from __future__ import annotations

from functools import lru_cache
import os
from pathlib import Path

from dashboard.config import load_dashboard_config
from dashboard.data_loader import available_dates, load_market_map_rows
from dashboard.macro_loader import build_macro_history, build_macro_overview, load_macro_dataset

from .schemas import (
    AssetMetadata,
    ConfigResponse,
    DefaultFilters,
    PlaybackSettings,
    ScoreRanges,
    SnapshotItem,
    TaxonomyOptions,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH_ENV = "CROSS_ASSET_CONFIG_PATH"
FUNDING_STATES = ["Leveraging", "Deleveraging"]
RS_STATES = ["Lag", "Weakening", "Improving", "Lead"]


def resolve_config_path(config_path: str | Path | None = None) -> Path:
    if config_path is not None:
        return Path(config_path).expanduser().resolve()
    configured = os.environ.get(CONFIG_PATH_ENV)
    if configured:
        return Path(configured).expanduser().resolve()
    return (REPO_ROOT / "config.yaml").resolve()


def load_config_response(config_path: str | Path | None = None) -> ConfigResponse:
    rows = load_rows(config_path)
    dashboard_config = load_dashboard_config(resolve_config_path(config_path))
    taxonomy = dashboard_config.taxonomy_options
    asset_classes = sorted({str(row["asset_class"]) for row in rows}) or ["core", "instruments"]
    return ConfigResponse(
        score_ranges=ScoreRanges(
            rs_score=_score_range(rows, "rs_score", default=[-100, 100]),
            funding_score=_score_range(rows, "flow_score", default=[-100, 100], lower_quantile=0.005, upper_quantile=0.995),
            leverage_velocity_score=_score_range(rows, "leverage_velocity_score", default=[-100, 100]),
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
        taxonomy=TaxonomyOptions(**taxonomy),
    )


def load_rows(config_path: str | Path | None = None) -> tuple[dict, ...]:
    resolved_path, signature = _cache_context(config_path)
    return _load_rows_cached(str(resolved_path), signature)


@lru_cache(maxsize=4)
def _load_rows_cached(config_path: str, _signature: tuple) -> tuple[dict, ...]:
    dashboard_config = load_dashboard_config(config_path)
    rows = load_market_map_rows(
        dashboard_config.storage_root,
        dashboard_config.market_map,
        taxonomy_path=dashboard_config.taxonomy_path,
        taxonomy_registry_path=dashboard_config.taxonomy_registry_path,
    )
    return tuple(rows)


def _cache_context(config_path: str | Path | None = None) -> tuple[Path, tuple]:
    resolved_path = resolve_config_path(config_path)
    dashboard_config = load_dashboard_config(resolved_path)
    signature = (
        _file_signature(resolved_path),
        _data_signature(dashboard_config.storage_root, dashboard_config.market_map),
        _optional_file_signature(dashboard_config.taxonomy_path),
        _optional_file_signature(dashboard_config.taxonomy_registry_path),
    )
    return resolved_path, signature


def _file_signature(path: Path) -> tuple[str, int, int]:
    stat = path.stat()
    return (str(path), stat.st_mtime_ns, stat.st_size)


def _optional_file_signature(path: Path) -> tuple[str, int, int]:
    try:
        return _file_signature(path)
    except FileNotFoundError:
        return (str(path), -1, -1)


def _data_signature(storage_root: str | Path, market_map_config: dict) -> tuple:
    root = Path(storage_root)
    dataset_types = market_map_config.get("dataset_types", ["core", "instruments"])
    parts: list[tuple[str, int, int]] = []
    for dataset_type in dataset_types:
        source_dir = root / "processed" / "series" / str(dataset_type)
        if not source_dir.exists():
            parts.append((str(source_dir), -1, -1))
            continue
        for source_path in sorted(source_dir.glob("*.csv")):
            try:
                stat = source_path.stat()
            except FileNotFoundError:
                continue
            parts.append((str(source_path), stat.st_mtime_ns, stat.st_size))
    gs_exempt_dir = root / "gs_exempt_list"
    gs_exempt_paths = [
        gs_exempt_dir / "gs_exempt_list.xlsx",
        gs_exempt_dir / "gs_exempt_list.csv",
    ]
    matched_gs_exempt_path = False
    for source_path in gs_exempt_paths:
        if not source_path.exists():
            continue
        matched_gs_exempt_path = True
        try:
            stat = source_path.stat()
        except FileNotFoundError:
            continue
        parts.append((str(source_path), stat.st_mtime_ns, stat.st_size))
    if not matched_gs_exempt_path:
        parts.append((str(gs_exempt_dir), -1, -1))
    return tuple(parts)


def get_dates(config_path: str | Path | None = None) -> list[str]:
    return available_dates(list(load_rows(config_path)))


def get_assets(config_path: str | Path | None = None) -> list[AssetMetadata]:
    latest_by_identity: dict[tuple[str, str, str], AssetMetadata] = {}
    for row in load_rows(config_path):
        symbol = str(row["asset_id"])
        identity = (str(row["asset_class"]), symbol, str(row["asset_name"]))
        latest_by_identity[identity] = AssetMetadata(
            symbol=symbol,
            name=str(row["asset_name"]),
            asset_class=str(row["asset_class"]),
            primary_category=str(row.get("primary_category") or "unclassified"),
            secondary_category=str(row["secondary_category"]) if row.get("secondary_category") else None,
            tertiary_categories=[str(value) for value in row.get("tertiary_categories", [])],
            regions=[str(value) for value in row.get("regions", [])],
        )
    return sorted(
        latest_by_identity.values(),
        key=lambda asset: (asset.asset_class, asset.symbol, asset.name),
    )


def get_asset_identities(config_path: str | Path | None = None) -> list[AssetMetadata]:
    identities: dict[tuple[str, str, str], AssetMetadata] = {}
    for row in load_rows(config_path):
        asset = AssetMetadata(
            symbol=str(row["asset_id"]),
            name=str(row["asset_name"]),
            asset_class=str(row["asset_class"]),
        )
        identities[(asset.asset_class, asset.symbol, asset.name)] = asset
    return sorted(identities.values(), key=lambda asset: (asset.asset_class, asset.symbol, asset.name))


def get_portfolio_context(
    config_path: str | Path | None = None,
) -> tuple[Path, Path, dict[str, object]]:
    dashboard_config = load_dashboard_config(resolve_config_path(config_path))
    portfolio_config = dashboard_config.repo_config.raw.get("dashboard", {}).get("portfolio", {})
    return (
        dashboard_config.repo_config.storage_root,
        dashboard_config.repo_config.state_root,
        portfolio_config if isinstance(portfolio_config, dict) else {},
    )


def get_snapshot(date: str, config_path: str | Path | None = None) -> list[SnapshotItem]:
    return list(_load_frames(config_path)[1].get(date, []))


def get_playback(
    start: str | None,
    end: str | None,
    config_path: str | Path | None = None,
) -> tuple[list[str], dict[str, list[SnapshotItem]]]:
    dates, all_frames = _load_frames(config_path)
    if start is not None:
        dates = [date for date in dates if date >= start]
    if end is not None:
        dates = [date for date in dates if date <= end]
    frames = {date: all_frames.get(date, []) for date in dates}
    return dates, frames


def _load_frames(
    config_path: str | Path | None = None,
) -> tuple[list[str], dict[str, list[SnapshotItem]]]:
    resolved_path, signature = _cache_context(config_path)
    return _load_frames_cached(str(resolved_path), signature)


@lru_cache(maxsize=4)
def _load_frames_cached(
    config_path: str,
    signature: tuple,
) -> tuple[list[str], dict[str, list[SnapshotItem]]]:
    frames: dict[str, list[SnapshotItem]] = {}
    for row in _load_rows_cached(config_path, signature):
        date = str(row["date"])
        frames.setdefault(date, []).append(_to_snapshot_item(row))
    return sorted(frames), frames


def get_readiness(config_path: str | Path | None = None) -> dict[str, object]:
    rows = load_rows(config_path)
    dates = available_dates(list(rows))
    assets = {str(row["asset_id"]) for row in rows}
    if not rows or not dates or not assets:
        return {
            "status": "not_ready",
            "reason": "no_processed_data",
            "date_count": len(dates),
            "asset_count": len(assets),
            "latest_date": dates[-1] if dates else None,
        }
    return {
        "status": "ready",
        "reason": None,
        "date_count": len(dates),
        "asset_count": len(assets),
        "latest_date": dates[-1],
    }


def get_macro_readiness(config_path: str | Path | None = None) -> dict[str, object]:
    overview = get_macro_overview(config_path=config_path)
    curve_count = len(overview["curves"])
    credit_count = len(overview["credit"])
    sources = overview["sources"]
    if not curve_count and not credit_count:
        return {
            "status": "not_ready",
            "reason": "no_macro_data",
            "curve_count": 0,
            "credit_count": 0,
            "sources": sources,
        }
    degraded = any(item.get("status") in {"error", "lagging", "unconfigured"} for item in sources)
    return {
        "status": "degraded" if degraded else "ready",
        "reason": "partial_sources" if degraded else None,
        "curve_count": curve_count,
        "credit_count": credit_count,
        "sources": sources,
    }


def load_macro_data(config_path: str | Path | None = None) -> dict:
    resolved_path, signature = _macro_cache_context(config_path)
    return _load_macro_data_cached(str(resolved_path), signature)


@lru_cache(maxsize=4)
def _load_macro_data_cached(config_path: str, _signature: tuple) -> dict:
    dashboard_config = load_dashboard_config(config_path)
    return load_macro_dataset(dashboard_config.storage_root, dashboard_config.macro)


def get_macro_overview(as_of: str | None = None, config_path: str | Path | None = None) -> dict:
    resolved_path = resolve_config_path(config_path)
    dashboard_config = load_dashboard_config(resolved_path)
    return build_macro_overview(load_macro_data(resolved_path), dashboard_config.macro, as_of=as_of)


def get_macro_history(
    series_id: str,
    start: str | None = None,
    end: str | None = None,
    config_path: str | Path | None = None,
) -> dict | None:
    return build_macro_history(load_macro_data(config_path), series_id, start=start, end=end)


def _macro_cache_context(config_path: str | Path | None = None) -> tuple[Path, tuple]:
    resolved_path = resolve_config_path(config_path)
    dashboard_config = load_dashboard_config(resolved_path)
    processed_root = dashboard_config.storage_root / str(dashboard_config.macro.get("processed_path", "processed/macro"))
    parts = [_file_signature(resolved_path)]
    for filename in ("curve_points.csv", "credit.csv"):
        path = processed_root / filename
        parts.append(_optional_file_signature(path))
    state_path = Path(str(dashboard_config.macro.get("source_state_path", "../state/macro_sources.json")))
    if not state_path.is_absolute():
        state_path = (dashboard_config.storage_root / state_path).resolve()
    parts.append(_optional_file_signature(state_path))
    return resolved_path, tuple(parts)


def _optional_file_signature(path: Path) -> tuple[str, int, int]:
    try:
        return _file_signature(path)
    except FileNotFoundError:
        return (str(path), -1, -1)


def _to_snapshot_item(row: dict) -> SnapshotItem:
    return SnapshotItem(
        symbol=str(row["asset_id"]),
        asset_name=str(row["asset_name"]),
        asset_class=str(row["asset_class"]),
        is_gs_exempt=bool(row.get("is_gs_exempt")),
        primary_category=str(row.get("primary_category") or "unclassified"),
        secondary_category=str(row["secondary_category"]) if row.get("secondary_category") else None,
        tertiary_categories=[str(value) for value in row.get("tertiary_categories", [])],
        regions=[str(value) for value in row.get("regions", [])],
        trend_score=float(row["trend_score"]),
        close_position_vs_60d=_optional_float(row.get("close_position_vs_60d")),
        rs_score=float(row["rs_score"]),
        early_reversal=float(row["early_reversal"]),
        strength_momentum=float(row["strength_momentum"]),
        relative_strength=float(row["relative_strength"]),
        rs_state=str(row["rs_state"]),
        funding_score=float(row["flow_score"]),
        funding_state=str(row["flow_state"]),
        leverage_value=float(row["leverage_value"]),
        leverage_duration=_optional_float(row.get("leverage_duration")),
        leverage_velocity=float(row["leverage_velocity"]),
        leverage_velocity_score=float(row["leverage_velocity_score"]),
        funding_signal_strength=_optional_float(row.get("funding_signal_strength")),
        trend_state=str(row.get("trend_state") or ""),
        monthly_trend=str(row.get("monthly_trend") or ""),
        weekly_trend=str(row.get("weekly_trend") or ""),
        daily_trend=str(row.get("daily_trend") or ""),
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


def _optional_float(value: object) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _quantile_value(values: list[float], quantile: float) -> float:
    index = round((len(values) - 1) * min(max(quantile, 0), 1))
    return values[index]
