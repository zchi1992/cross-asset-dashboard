import { describe, expect, it } from "vitest";
import type { SnapshotItem } from "../services/contracts";
import { assetKey, filterItems, matchesSearch, trajectoryForAssetKey } from "./filtering";

const item: SnapshotItem = {
  symbol: "GLD",
  asset_name: "SPDR Gold Shares",
  asset_class: "core",
  trend_score: 74,
  rs_score: 38,
  rs_state: "Lead",
  funding_score: 51,
  funding_state: "Leveraging",
  leverage_value: 51,
  leverage_velocity: 3.4,
  leverage_velocity_score: 82,
  long_candidate: true,
  short_candidate: false,
};

describe("filtering utilities", () => {
  it("matches symbol and asset name search text", () => {
    expect(matchesSearch(item, "gld")).toBe(true);
    expect(matchesSearch(item, "gold")).toBe(true);
    expect(matchesSearch(item, "oil")).toBe(false);
  });

  it("combines filter groups with AND semantics", () => {
    expect(filterItems([item], "core", ["Leveraging"], ["Lead"])).toHaveLength(1);
    expect(filterItems([item], "Core", ["leveraging"], ["lead"])).toHaveLength(1);
    expect(filterItems([item], "instruments", ["Leveraging"], ["Lead"])).toHaveLength(0);
    expect(filterItems([item], "core", ["Deleveraging"], ["Lead"])).toHaveLength(0);
    expect(filterItems([item], "core", ["Leveraging"], ["Lag"])).toHaveLength(0);
    expect(filterItems([item], "core", [], ["Lead"])).toHaveLength(0);
    expect(filterItems([item], "core", ["Leveraging"], [])).toHaveLength(0);
  });

  it("filters leverage velocity opportunities", () => {
    const fastDeleveraging = {
      ...item,
      symbol: "OIL",
      funding_state: "Deleveraging" as const,
      leverage_velocity_score: -88,
    };
    const quiet = { ...item, symbol: "TLT", leverage_velocity_score: 12 };

    expect(filterItems([item, fastDeleveraging, quiet], "core", ["Leveraging", "Deleveraging"], ["Lead"], "Fast Leveraging")).toEqual([item]);
    expect(filterItems([item, fastDeleveraging, quiet], "core", ["Leveraging", "Deleveraging"], ["Lead"], "Fast Deleveraging")).toEqual([fastDeleveraging]);
    expect(filterItems([item, fastDeleveraging, quiet], "core", ["Leveraging", "Deleveraging"], ["Lead"], "Active")).toEqual([item, fastDeleveraging]);
  });

  it("returns the trailing 30 available frame points for a symbol", () => {
    const dates = Array.from({ length: 35 }, (_, index) => `2026-05-${String(index + 1).padStart(2, "0")}`);
    const frames = Object.fromEntries(dates.map((date) => [date, [{ ...item, rs_score: dates.indexOf(date), funding_score: 1 }]]));

    const trajectory = trajectoryForAssetKey(frames, dates, 34, assetKey(item));

    expect(trajectory).toHaveLength(30);
    expect(trajectory[0].date).toBe("2026-05-06");
    expect(trajectory[29].date).toBe("2026-05-35");
  });

  it("keeps trajectories separate for duplicate symbols in different asset classes", () => {
    const instrumentItem = { ...item, asset_class: "instruments", asset_name: "Gold Futures", rs_score: 99 };
    const frames = {
      "2026-05-01": [item, instrumentItem],
    };

    const trajectory = trajectoryForAssetKey(frames, ["2026-05-01"], 0, assetKey(instrumentItem));

    expect(trajectory).toHaveLength(1);
    expect(trajectory[0].item.asset_class).toBe("instruments");
    expect(trajectory[0].item.asset_name).toBe("Gold Futures");
  });
});
