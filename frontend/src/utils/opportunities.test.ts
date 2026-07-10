import { describe, expect, it } from "vitest";
import type { SnapshotItem } from "../services/contracts";
import {
  buildRankChanges,
  buildRankedOpportunityRows,
  rankCandidateLongOpportunities,
  rankStrongLongOpportunities,
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
});
