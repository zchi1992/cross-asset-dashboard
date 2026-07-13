import { describe, expect, it } from "vitest";
import type { SnapshotItem, TaxonomyOptions } from "../services/contracts";
import { buildAvailableTaxonomyOptions, pruneSelection, taxonomyOptionLabel } from "./taxonomy";

const taxonomy: TaxonomyOptions = {
  primary_categories: [
    { code: "equity", label_en: "Equity", label_zh: "股票", parent_codes: [] },
    { code: "bond", label_en: "Bond", label_zh: "债券", parent_codes: [] },
  ],
  secondary_categories: [
    { code: "equity.large_cap", label_en: "Large Cap", label_zh: "大盘", parent_codes: ["equity"] },
    { code: "bond.sovereign", label_en: "Sovereign", label_zh: "主权债", parent_codes: ["bond"] },
  ],
  tertiary_categories: [
    { code: "style.growth", label_en: "Growth", label_zh: "成长", parent_codes: ["equity.large_cap"] },
  ],
  regions: [
    { code: "US", label_en: "US", label_zh: "美国", parent_codes: [] },
    { code: "CN", label_en: "China", label_zh: "中国", parent_codes: [] },
  ],
};

function item(overrides: Partial<SnapshotItem>): SnapshotItem {
  return {
    symbol: "AAA",
    asset_name: "Fixture",
    asset_class: "core",
    is_gs_exempt: false,
    primary_category: "equity",
    secondary_category: "equity.large_cap",
    tertiary_categories: ["style.growth"],
    regions: ["US"],
    trend_score: 1,
    rs_score: 1,
    early_reversal: 1,
    strength_momentum: 1,
    relative_strength: 1,
    rs_state: "Lead",
    funding_score: 1,
    funding_state: "Leveraging",
    leverage_value: 1,
    leverage_velocity: 1,
    leverage_velocity_score: 1,
    long_candidate: false,
    short_candidate: false,
    ...overrides,
  };
}

describe("taxonomy option helpers", () => {
  it("cascades secondary and tertiary options from selected parents", () => {
    const items = [item({}), item({ symbol: "BBB", primary_category: "bond", secondary_category: "bond.sovereign", tertiary_categories: [], regions: ["CN"] })];
    const options = buildAvailableTaxonomyOptions(items, taxonomy, {
      primaryCategories: ["equity"],
      secondaryCategories: ["equity.large_cap"],
      tertiaryCategories: [],
      regions: [],
    });

    expect(options.secondary_categories.map((option) => option.code)).toEqual(["equity.large_cap"]);
    expect(options.tertiary_categories.map((option) => option.code)).toEqual(["style.growth"]);
    expect(options.regions.map((option) => option.code)).toEqual(["US", "CN"]);
  });

  it("prunes stale values and formats bilingual labels", () => {
    expect(pruneSelection(["equity", "missing"], taxonomy.primary_categories)).toEqual(["equity"]);
    expect(taxonomyOptionLabel(taxonomy.primary_categories[0])).toBe("股票 Equity");
  });
});
