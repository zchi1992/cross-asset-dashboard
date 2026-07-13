export type FundingState = "Leveraging" | "Deleveraging";
export type RelativeStrengthState = "Lag" | "Weakening" | "Improving" | "Lead";

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
};

export type AssetMetadata = {
  symbol: string;
  name: string;
  asset_class: string;
};

export type SnapshotItem = {
  symbol: string;
  asset_name: string;
  asset_class: string;
  is_gs_exempt: boolean;
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
