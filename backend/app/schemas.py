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


class TaxonomyOption(BaseModel):
    code: str
    label_en: str
    label_zh: str
    parent_codes: list[str] = Field(default_factory=list)


class TaxonomyOptions(BaseModel):
    primary_categories: list[TaxonomyOption] = Field(default_factory=list)
    secondary_categories: list[TaxonomyOption] = Field(default_factory=list)
    tertiary_categories: list[TaxonomyOption] = Field(default_factory=list)
    regions: list[TaxonomyOption] = Field(default_factory=list)


class ConfigResponse(BaseModel):
    score_ranges: ScoreRanges
    default_filters: DefaultFilters
    playback: PlaybackSettings
    asset_classes: list[str]
    funding_states: list[str]
    rs_states: list[str]
    taxonomy: TaxonomyOptions = Field(default_factory=TaxonomyOptions)


class DatesResponse(BaseModel):
    dates: list[str]


class AssetMetadata(BaseModel):
    symbol: str
    name: str
    asset_class: str
    primary_category: str = "unclassified"
    secondary_category: str | None = None
    tertiary_categories: list[str] = Field(default_factory=list)
    regions: list[str] = Field(default_factory=list)


class AssetsResponse(BaseModel):
    assets: list[AssetMetadata]


class SnapshotItem(BaseModel):
    symbol: str
    asset_name: str
    asset_class: str
    is_gs_exempt: bool = False
    primary_category: str = "unclassified"
    secondary_category: str | None = None
    tertiary_categories: list[str] = Field(default_factory=list)
    regions: list[str] = Field(default_factory=list)
    trend_score: float
    close_position_vs_60d: float | None = None
    rs_score: float
    early_reversal: float
    strength_momentum: float
    relative_strength: float
    rs_state: str
    funding_score: float
    funding_state: str
    leverage_value: float
    leverage_duration: float | None = None
    leverage_velocity: float
    leverage_velocity_score: float
    funding_signal_strength: float | None = None
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


class MacroSourceStatus(BaseModel):
    source_id: str
    source_name: str
    status: str
    last_success_at: str | None = None
    latest_observation_at: str | None = None
    message: str | None = None


class MacroReadinessResponse(BaseModel):
    status: str
    reason: str | None = None
    curve_count: int = 0
    credit_count: int = 0
    sources: list[MacroSourceStatus] = Field(default_factory=list)


class MacroChangeSet(BaseModel):
    change_1: float | None = None
    change_4: float | None = None
    change_5: float | None = None
    change_20: float | None = None


class MacroCurvePoint(BaseModel):
    tenor_years: float
    value: float


class MacroCurveFactor(BaseModel):
    series_id: str
    label: str
    value: float
    unit: str
    changes: MacroChangeSet
    status: str


class MacroCurveCard(BaseModel):
    region: str
    region_name: str
    observed_at: str
    curve_type: str
    source_id: str
    source_name: str
    source_url: str
    points: list[MacroCurvePoint]
    factors: list[MacroCurveFactor]


class MacroCreditCard(BaseModel):
    series_id: str
    label: str
    observed_at: str
    value: float
    unit: str
    frequency: str
    source_id: str
    source_name: str
    source_url: str
    changes: MacroChangeSet
    status: str


class MacroOverviewResponse(BaseModel):
    as_of: str | None = None
    curves: list[MacroCurveCard]
    credit: list[MacroCreditCard]
    sources: list[MacroSourceStatus]


class MacroHistoryPoint(BaseModel):
    date: str
    value: float


class MacroHistoryResponse(BaseModel):
    series_id: str
    label: str
    unit: str
    points: list[MacroHistoryPoint]


class PortfolioAccount(BaseModel):
    account_id_masked: str
    base_currency: str
    net_liquidation: float | None = None
    maint_margin_req: float | None = None
    sma: float | None = None
    excess_liquidity: float | None = None
    available_funds: float | None = None
    buying_power: float | None = None
    gross_position_value: float | None = None
    cushion: float | None = None


class PortfolioAssetLink(BaseModel):
    symbol: str
    name: str
    asset_class: str


class PortfolioPosition(BaseModel):
    conid: str
    symbol: str
    local_symbol: str
    sec_type: str
    last_trade_date_or_contract_month: str = ""
    strike: float | None = None
    right: str = ""
    multiplier: float | None = None
    exchange: str = ""
    primary_exchange: str = ""
    currency: str = ""
    quantity: float
    market_price: float | None = None
    market_value: float | None = None
    average_cost: float | None = None
    unrealized_pnl: float | None = None
    realized_pnl: float | None = None
    option_delta: float | None = None
    option_gamma: float | None = None
    option_theta: float | None = None
    option_vega: float | None = None
    portfolio_weight: float | None = None
    stop_loss_price: float | None = None
    stop_status: str
    planned_loss_at_stop: float | None = None
    remaining_risk_to_stop: float | None = None
    risk_eligible: bool
    link_status: str
    linked_asset: PortfolioAssetLink | None = None


class PortfolioRiskSummary(BaseModel):
    leverage_ratio: float | None = None
    maintenance_margin_ratio: float | None = None
    excess_liquidity_ratio: float | None = None
    largest_position_concentration: float | None = None
    planned_loss_at_stop: float
    remaining_risk_to_stop: float
    eligible_position_count: int
    covered_position_count: int
    eligible_market_value: float
    covered_market_value: float
    coverage_ratio: float | None = None


class PortfolioResponse(BaseModel):
    status: str
    message: str | None = None
    snapshot_date: str | None = None
    captured_at: str | None = None
    sync_source: str | None = None
    source_file: str | None = None
    account: PortfolioAccount | None = None
    risk: PortfolioRiskSummary | None = None
    positions: list[PortfolioPosition] = Field(default_factory=list)


class StopLossUpdate(BaseModel):
    stop_loss_price: float | None = None
