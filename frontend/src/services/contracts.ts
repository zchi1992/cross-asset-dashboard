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
