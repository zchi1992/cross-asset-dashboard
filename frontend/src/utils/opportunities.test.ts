import { describe, expect, it } from "vitest";
import type { SnapshotItem } from "../services/contracts";
import {
  buildOpportunityMarkers,
  buildRankChanges,
  buildRankedOpportunityRows,
  rankCandidateLongOpportunities,
  rankCandidateShortOpportunities,
  rankStrongLongOpportunities,
  rankStrongShortOpportunities,
  topOpportunities,
} from "./opportunities";

function item(overrides: Partial<SnapshotItem> = {}): SnapshotItem {
  const symbol = overrides.symbol ?? "BASE";
  return {
    symbol,
    asset_name: overrides.asset_name ?? `Asset ${symbol}`,
    asset_class: overrides.asset_class ?? "core",
    is_gs_exempt: overrides.is_gs_exempt ?? false,
    trend_score: 45,
    rs_score: 72,
    early_reversal: 112,
    strength_momentum: 85,
    relative_strength: 88,
    rs_state: "Improving",
    funding_score: 51,
    funding_state: "Leveraging",
    leverage_value: 51,
    leverage_duration: 3,
    leverage_velocity: 4,
    leverage_velocity_score: 66,
    funding_signal_strength: 51,
    trend_state: "主升浪",
    monthly_trend: "up",
    weekly_trend: "up",
    daily_trend: "up",
    long_candidate: true,
    short_candidate: false,
    ...overrides,
  };
}

function shortItem(overrides: Partial<SnapshotItem> = {}): SnapshotItem {
  return item({
    early_reversal: 88,
    rs_state: "Weakening",
    funding_state: "Deleveraging",
    leverage_velocity: -4,
    weekly_trend: "up",
    daily_trend: "down",
    long_candidate: false,
    short_candidate: true,
    ...overrides,
  });
}

describe("opportunity screening utilities", () => {
  it("filters and sorts strong long opportunities by the markdown rules", () => {
    const ranked = rankStrongLongOpportunities([
      item({ symbol: "LATE", leverage_duration: 4, funding_signal_strength: 95, trend_score: 90 }),
      item({ symbol: "FRESH", leverage_duration: 1, funding_signal_strength: 20, trend_score: 25 }),
      item({ symbol: "STRONGER", leverage_duration: 2, funding_signal_strength: 80, trend_score: 40 }),
      item({ symbol: "WEAKER", leverage_duration: 2, funding_signal_strength: 60, trend_score: 99 }),
      item({ symbol: "NO_ER", early_reversal: 100 }),
      item({ symbol: "NO_FLOW", funding_state: "Deleveraging" }),
      item({ symbol: "NO_WEEKLY", weekly_trend: "neutral" }),
    ]);

    expect(ranked.map((entry) => entry.symbol)).toEqual(["FRESH", "STRONGER", "WEAKER", "LATE"]);
  });

  it("deduplicates strong longs by symbol and asset name after ranking", () => {
    const ranked = rankStrongLongOpportunities([
      item({ symbol: "DUP", asset_name: "Duplicate Asset", asset_class: "core", leverage_duration: 8 }),
      item({ symbol: "DUP", asset_name: "Duplicate Asset", asset_class: "instruments", leverage_duration: 1 }),
      item({ symbol: "DUP", asset_name: "Different Asset", asset_class: "core", leverage_duration: 2 }),
    ]);

    expect(ranked.map((entry) => `${entry.asset_class}:${entry.symbol}:${entry.asset_name}`)).toEqual([
      "instruments:DUP:Duplicate Asset",
      "core:DUP:Different Asset",
    ]);
  });

  it("ranks candidate longs with leveraging before mild deleveraging", () => {
    const ranked = rankCandidateLongOpportunities([
      item({ symbol: "DEL_WEAK", funding_state: "Deleveraging", leverage_velocity: -6 }),
      item({ symbol: "DEL_FAST", funding_state: "Deleveraging", leverage_velocity: -1 }),
      item({ symbol: "LEV_SLOW", funding_state: "Leveraging", leverage_duration: 5 }),
      item({ symbol: "LEV_FAST", funding_state: "Leveraging", leverage_duration: 1 }),
      item({ symbol: "DEL_SLOW", funding_state: "Deleveraging", leverage_velocity: -3 }),
      item({ symbol: "BROKEN_TREND", daily_trend: "down" }),
    ]);

    expect(ranked.map((entry) => entry.symbol)).toEqual(["LEV_FAST", "LEV_SLOW", "DEL_FAST", "DEL_SLOW"]);
  });

  it("deduplicates candidate longs by symbol and asset name after ranking", () => {
    const ranked = rankCandidateLongOpportunities([
      item({ symbol: "DUP", asset_name: "Duplicate Asset", asset_class: "core", leverage_duration: 5 }),
      item({ symbol: "DUP", asset_name: "Duplicate Asset", asset_class: "instruments", leverage_duration: 1 }),
      item({ symbol: "UNIQUE", asset_name: "Unique Asset", leverage_duration: 2 }),
    ]);

    expect(ranked.map((entry) => `${entry.asset_class}:${entry.symbol}:${entry.asset_name}`)).toEqual([
      "instruments:DUP:Duplicate Asset",
      "core:UNIQUE:Unique Asset",
    ]);
  });

  it("filters and sorts strong shorts by fresh deleveraging then leverage value", () => {
    const ranked = rankStrongShortOpportunities([
      shortItem({ symbol: "LATE", leverage_duration: 4, leverage_value: 90 }),
      shortItem({ symbol: "FRESH", leverage_duration: 1, leverage_value: 20 }),
      shortItem({ symbol: "BIGGER", leverage_duration: 2, leverage_value: 80 }),
      shortItem({ symbol: "SMALLER", leverage_duration: 2, leverage_value: 60 }),
      shortItem({ symbol: "MISSING", leverage_duration: null, leverage_value: 99 }),
      shortItem({ symbol: "NO_ER", early_reversal: 100 }),
      shortItem({ symbol: "NO_TREND_SCORE", trend_score: 20 }),
      shortItem({ symbol: "NO_DAILY_DOWN", daily_trend: "neutral" }),
      shortItem({ symbol: "NO_FLOW", funding_state: "Leveraging" }),
      shortItem({ symbol: "NO_RS", rs_state: "Improving" }),
    ]);

    expect(ranked.map((entry) => entry.symbol)).toEqual(["FRESH", "BIGGER", "SMALLER", "LATE", "MISSING"]);
  });

  it("ranks candidate shorts with deleveraging before low-speed leveraging", () => {
    const ranked = rankCandidateShortOpportunities([
      shortItem({ symbol: "DEL_LATE", leverage_duration: 4, leverage_value: 90, daily_trend: "neutral" }),
      shortItem({ symbol: "DEL_SMALL", leverage_duration: 2, leverage_value: 60, daily_trend: "neutral" }),
      shortItem({ symbol: "DEL_BIG", leverage_duration: 2, leverage_value: 80, daily_trend: "neutral" }),
      shortItem({ symbol: "DEL_FRESH", leverage_duration: 1, leverage_value: 20, daily_trend: "neutral" }),
      shortItem({ symbol: "LEV_FAST", funding_state: "Leveraging", leverage_velocity: 4, leverage_value: 90, weekly_trend: "down", daily_trend: "up" }),
      shortItem({ symbol: "LEV_SLOW", funding_state: "Leveraging", leverage_velocity: 1, leverage_value: 20, daily_trend: "neutral" }),
      shortItem({ symbol: "NO_VELOCITY", funding_state: "Leveraging", leverage_velocity: 5, daily_trend: "neutral" }),
      shortItem({ symbol: "BOTH_UP", weekly_trend: "up", daily_trend: "up" }),
      shortItem({ symbol: "NO_ER", early_reversal: 100, daily_trend: "neutral" }),
      shortItem({ symbol: "NO_TREND_SCORE", trend_score: 20, daily_trend: "neutral" }),
    ]);

    expect(ranked.map((entry) => entry.symbol)).toEqual([
      "DEL_FRESH",
      "DEL_BIG",
      "DEL_SMALL",
      "DEL_LATE",
      "LEV_SLOW",
      "LEV_FAST",
    ]);
  });

  it("accepts a candidate short when either daily or weekly trend is not up", () => {
    const ranked = rankCandidateShortOpportunities([
      shortItem({ symbol: "DAILY_NEUTRAL", daily_trend: "neutral", weekly_trend: "up" }),
      shortItem({ symbol: "WEEKLY_DOWN", funding_state: "Leveraging", leverage_velocity: 2, daily_trend: "up", weekly_trend: "down" }),
      shortItem({ symbol: "BOTH_UP", daily_trend: "up", weekly_trend: "up" }),
    ]);

    expect(ranked.map((entry) => entry.symbol)).toEqual(["DAILY_NEUTRAL", "WEEKLY_DOWN"]);
  });

  it("deduplicates candidate shorts by symbol and asset name after ranking", () => {
    const ranked = rankCandidateShortOpportunities([
      shortItem({ symbol: "DUP", asset_name: "Duplicate Asset", asset_class: "core", leverage_duration: 5 }),
      shortItem({ symbol: "DUP", asset_name: "Duplicate Asset", asset_class: "instruments", leverage_duration: 1 }),
      shortItem({ symbol: "UNIQUE", asset_name: "Unique Asset", leverage_duration: 2 }),
    ]);

    expect(ranked.map((entry) => `${entry.asset_class}:${entry.symbol}:${entry.asset_name}`)).toEqual([
      "instruments:DUP:Duplicate Asset",
      "core:UNIQUE:Unique Asset",
    ]);
  });

  it("computes opportunity-list rank changes against available date offsets", () => {
    const dates = Array.from({ length: 11 }, (_, index) => `2026-06-${String(18 + index).padStart(2, "0")}`);
    const current = [
      item({ symbol: "A", leverage_duration: 1 }),
      item({ symbol: "B", leverage_duration: 2 }),
      item({ symbol: "C", leverage_duration: 3 }),
      item({ symbol: "D", leverage_duration: 4 }),
    ];
    const frames: Record<string, SnapshotItem[]> = {
      [dates[0]]: [item({ symbol: "A", leverage_duration: 1 })],
      [dates[5]]: [item({ symbol: "A", leverage_duration: 1 })],
      [dates[9]]: [
        item({ symbol: "B", leverage_duration: 1 }),
        item({ symbol: "A", leverage_duration: 2 }),
        item({ symbol: "X", leverage_duration: 3 }),
        item({ symbol: "D", leverage_duration: 4 }),
      ],
      [dates[10]]: current,
    };

    const changes = buildRankChanges(frames, dates, 10, "candidateLong");
    const rows = buildRankedOpportunityRows(current, changes, rankCandidateLongOpportunities);

    expect(rows.find((row) => row.item.symbol === "A")?.rankChanges).toEqual({
      rank_change_1d: "+1",
      rank_change_5d: "0",
      rank_change_10d: "0",
    });
    expect(rows.find((row) => row.item.symbol === "B")?.rankChanges.rank_change_1d).toBe("-1");
    expect(rows.find((row) => row.item.symbol === "C")?.rankChanges.rank_change_1d).toBe("NEW");
    expect(rows.find((row) => row.item.symbol === "D")?.rankChanges.rank_change_1d).toBe("0");
  });

  it("tracks rank changes across core and instruments duplicates by symbol and asset name", () => {
    const dates = ["2026-06-18", "2026-06-19"];
    const frames: Record<string, SnapshotItem[]> = {
      [dates[0]]: [
        item({ symbol: "A", asset_name: "Same Asset", asset_class: "core", leverage_duration: 1 }),
        item({ symbol: "B", asset_name: "Other Asset", leverage_duration: 2 }),
      ],
      [dates[1]]: [
        item({ symbol: "A", asset_name: "Same Asset", asset_class: "instruments", leverage_duration: 1 }),
        item({ symbol: "B", asset_name: "Other Asset", leverage_duration: 2 }),
      ],
    };

    const changes = buildRankChanges(frames, dates, 1, "candidateLong");
    const rows = buildRankedOpportunityRows(frames[dates[1]], changes, rankCandidateLongOpportunities);

    expect(rows.find((row) => row.item.symbol === "A")?.rankChanges.rank_change_1d).toBe("0");
  });

  it("computes rank changes independently for candidate shorts", () => {
    const dates = ["2026-06-01", "2026-06-02"];
    const frames = {
      [dates[0]]: [shortItem({ symbol: "A", leverage_duration: 2 }), shortItem({ symbol: "B", leverage_duration: 1 })],
      [dates[1]]: [shortItem({ symbol: "A", leverage_duration: 1 }), shortItem({ symbol: "C", leverage_duration: 2 })],
    };

    const changes = buildRankChanges(frames, dates, 1, "candidateShort");
    const rows = buildRankedOpportunityRows(frames[dates[1]], changes, rankCandidateShortOpportunities);

    expect(rows.find((row) => row.item.symbol === "A")?.rankChanges.rank_change_1d).toBe("+1");
    expect(rows.find((row) => row.item.symbol === "C")?.rankChanges.rank_change_1d).toBe("NEW");
  });

  it("limits opportunity display rows to the top ten", () => {
    const rows = buildRankedOpportunityRows(
      Array.from({ length: 12 }, (_, index) => item({ symbol: `ASSET${index + 1}`, leverage_duration: index + 1 })),
      new Map(),
      rankCandidateLongOpportunities,
    );

    expect(topOpportunities(rows)).toHaveLength(10);
    expect(topOpportunities(rows).map((row) => row.item.symbol)).toContain("ASSET10");
    expect(topOpportunities(rows).map((row) => row.item.symbol)).not.toContain("ASSET11");
  });

  it("marks the top ten from both opportunity screens and preserves overlaps", () => {
    const strongRows = buildRankedOpportunityRows(
      Array.from({ length: 11 }, (_, index) => item({ symbol: `STRONG${index + 1}`, leverage_duration: index + 1 })),
      new Map(),
      rankStrongLongOpportunities,
    );
    const candidateRows = buildRankedOpportunityRows(
      [item({ symbol: "STRONG1" }), item({ symbol: "CANDIDATE_ONLY" })],
      new Map(),
      rankCandidateLongOpportunities,
    );

    const markers = buildOpportunityMarkers(strongRows, candidateRows);

    expect(markers.get("STRONG1::Asset STRONG1")).toEqual({ strongLong: true, candidateLong: true });
    expect(markers.get("CANDIDATE_ONLY::Asset CANDIDATE_ONLY")).toEqual({
      strongLong: false,
      candidateLong: true,
    });
    expect(markers.has("STRONG11::Asset STRONG11")).toBe(false);
  });
});
