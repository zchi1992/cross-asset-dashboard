export type FundingState = "Leveraging" | "Deleveraging";
export type RelativeStrengthState = "Lag" | "Weakening" | "Improving" | "Lead";

export type TaxonomyOption = {
  code: string;
  label_en: string;
  label_zh: string;
  parent_codes: string[];
};

export type TaxonomyOptions = {
  primary_categories: TaxonomyOption[];
  secondary_categories: TaxonomyOption[];
  tertiary_categories: TaxonomyOption[];
  regions: TaxonomyOption[];
};

export type ConfigResponse = {
  score_ranges: {
    rs_score: [number, number] | number[];
    funding_score: [number, number] | number[];
    leverage_velocity_score: [number, number] | number[];
    trend_score: [number, number] | number[];
  };
  default_filters: {
    asset_class: string;
    funding_states: FundingState[];
    rs_states: RelativeStrengthState[];
  };
  playback: {
    speeds: number[];
    default_speed: number;
    loop_playback: boolean;
  };
  asset_classes: string[];
  funding_states: FundingState[];
  rs_states: RelativeStrengthState[];
  taxonomy: TaxonomyOptions;
};

export type AssetMetadata = {
  symbol: string;
  name: string;
  asset_class: string;
  primary_category: string;
  secondary_category: string | null;
  tertiary_categories: string[];
  regions: string[];
};

export type SnapshotItem = {
  symbol: string;
  asset_name: string;
  asset_class: string;
  is_gs_exempt: boolean;
  primary_category: string;
  secondary_category: string | null;
  tertiary_categories: string[];
  regions: string[];
  trend_score: number;
  close_position_vs_60d?: number | null;
  rs_score: number;
  early_reversal: number;
  strength_momentum: number;
  relative_strength: number;
  rs_state: RelativeStrengthState;
  funding_score: number;
  funding_state: FundingState;
  leverage_value: number;
  leverage_duration?: number | null;
  leverage_velocity: number;
  leverage_velocity_score: number;
  funding_signal_strength?: number | null;
  trend_state?: string | null;
  monthly_trend?: string | null;
  weekly_trend?: string | null;
  daily_trend?: string | null;
  long_candidate: boolean;
  short_candidate: boolean;
};

export type DatesResponse = { dates: string[] };
export type AssetsResponse = { assets: AssetMetadata[] };
export type SnapshotResponse = { date: string; items: SnapshotItem[] };
export type PlaybackResponse = { dates: string[]; frames: Record<string, SnapshotItem[]> };

export type MacroSourceStatus = {
  source_id: string;
  source_name: string;
  status: "fresh" | "lagging" | "error" | "unconfigured" | string;
  last_success_at?: string | null;
  latest_observation_at?: string | null;
  message?: string | null;
};

export type MacroChanges = {
  change_1?: number | null;
  change_4?: number | null;
  change_5?: number | null;
  change_20?: number | null;
};

export type MacroFactor = {
  series_id: string;
  label: string;
  value: number;
  unit: string;
  changes: MacroChanges;
  status: string;
};

export type MacroCurve = {
  region: string;
  region_name: string;
  observed_at: string;
  curve_type: string;
  source_id: string;
  source_name: string;
  source_url: string;
  points: { tenor_years: number; value: number }[];
  factors: MacroFactor[];
};

export type MacroCredit = {
  series_id: string;
  label: string;
  observed_at: string;
  value: number;
  unit: string;
  frequency: string;
  source_id: string;
  source_name: string;
  source_url: string;
  changes: MacroChanges;
  status: string;
};

export type MacroOverviewResponse = {
  as_of?: string | null;
  curves: MacroCurve[];
  credit: MacroCredit[];
  sources: MacroSourceStatus[];
};

export type MacroHistoryResponse = {
  series_id: string;
  label: string;
  unit: string;
  points: { date: string; value: number }[];
};

export type PortfolioAccount = {
  account_id_masked: string;
  base_currency: string;
  net_liquidation?: number | null;
  maint_margin_req?: number | null;
  sma?: number | null;
  excess_liquidity?: number | null;
  available_funds?: number | null;
  buying_power?: number | null;
  gross_position_value?: number | null;
  cushion?: number | null;
};

export type PortfolioAssetLink = {
  symbol: string;
  name: string;
  asset_class: string;
};

export type PortfolioPosition = {
  conid: string;
  symbol: string;
  local_symbol: string;
  sec_type: string;
  last_trade_date_or_contract_month: string;
  strike?: number | null;
  right: string;
  multiplier?: number | null;
  exchange: string;
  primary_exchange: string;
  currency: string;
  quantity: number;
  market_price?: number | null;
  market_value?: number | null;
  average_cost?: number | null;
  unrealized_pnl?: number | null;
  realized_pnl?: number | null;
  option_delta?: number | null;
  option_gamma?: number | null;
  option_theta?: number | null;
  option_vega?: number | null;
  portfolio_weight?: number | null;
  stop_loss_price?: number | null;
  stop_status: string;
  planned_loss_at_stop?: number | null;
  remaining_risk_to_stop?: number | null;
  risk_eligible: boolean;
  link_status: string;
  linked_asset?: PortfolioAssetLink | null;
};

export type PortfolioRiskSummary = {
  leverage_ratio?: number | null;
  maintenance_margin_ratio?: number | null;
  excess_liquidity_ratio?: number | null;
  largest_position_concentration?: number | null;
  planned_loss_at_stop: number;
  remaining_risk_to_stop: number;
  eligible_position_count: number;
  covered_position_count: number;
  eligible_market_value: number;
  covered_market_value: number;
  coverage_ratio?: number | null;
};

export type PortfolioResponse = {
  status: "ready" | "stale" | "no_snapshot" | "error";
  message?: string | null;
  snapshot_date?: string | null;
  captured_at?: string | null;
  sync_source?: string | null;
  source_file?: string | null;
  account?: PortfolioAccount | null;
  risk?: PortfolioRiskSummary | null;
  positions: PortfolioPosition[];
};
