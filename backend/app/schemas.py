from __future__ import annotations

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "1.0.0"


class ReadinessResponse(BaseModel):
    status: str
    reason: str | None = None
    date_count: int = 0
    asset_count: int = 0
    latest_date: str | None = None


class ScoreRanges(BaseModel):
    rs_score: list[float] = Field(default_factory=lambda: [-100, 100])
    funding_score: list[float] = Field(default_factory=lambda: [-100, 100])
    leverage_velocity_score: list[float] = Field(default_factory=lambda: [-100, 100])
    trend_score: list[float] = Field(default_factory=lambda: [-100, 100])


class DefaultFilters(BaseModel):
    asset_class: str
    funding_states: list[str]
    rs_states: list[str]


class PlaybackSettings(BaseModel):
    speeds: list[float]
    default_speed: float
    loop_playback: bool = False


class ConfigResponse(BaseModel):
    score_ranges: ScoreRanges
    default_filters: DefaultFilters
    playback: PlaybackSettings
    asset_classes: list[str]
    funding_states: list[str]
    rs_states: list[str]


class DatesResponse(BaseModel):
    dates: list[str]


class AssetMetadata(BaseModel):
    symbol: str
    name: str
    asset_class: str


class AssetsResponse(BaseModel):
    assets: list[AssetMetadata]


class SnapshotItem(BaseModel):
    symbol: str
    asset_name: str
    asset_class: str
    trend_score: float
    rs_score: float
    early_reversal: float
    strength_momentum: float
    relative_strength: float
    rs_state: str
    funding_score: float
    funding_state: str
    leverage_value: float
    leverage_velocity: float
    leverage_velocity_score: float
    trend_state: str | None = None
    monthly_trend: str | None = None
    weekly_trend: str | None = None
    daily_trend: str | None = None
    long_candidate: bool = False
    short_candidate: bool = False


class SnapshotResponse(BaseModel):
    date: str
    items: list[SnapshotItem]


class PlaybackResponse(BaseModel):
    dates: list[str]
    frames: dict[str, list[SnapshotItem]]
