import { beforeEach, describe, expect, it, vi } from "vitest";

const values = new Map<string, string>();

beforeEach(() => {
  vi.restoreAllMocks();
  vi.spyOn(console, "error").mockImplementation(() => undefined);
  values.clear();
  vi.resetModules();
  const localStorage = {
    getItem: (key: string) => values.get(key) ?? null,
    setItem: (key: string, value: string) => values.set(key, value),
    removeItem: (key: string) => values.delete(key),
    clear: () => values.clear(),
    key: (index: number) => [...values.keys()][index] ?? null,
    get length() { return values.size; },
  };
  vi.stubGlobal("localStorage", localStorage);
  vi.stubGlobal("window", { localStorage });
});

describe("filter store taxonomy state", () => {
  it("persists taxonomy selections and clears them on reset", async () => {
    const { useFilterStore } = await import("./filterStore");
    const partialize = useFilterStore.persist.getOptions().partialize;
    if (!partialize) throw new Error("filter persistence must define partialize");
    const persisted = partialize({
      ...useFilterStore.getState(),
      primaryCategories: ["equity"],
      secondaryCategories: ["equity.large_cap"],
      tertiaryCategories: ["style.growth"],
      regions: ["US_CA"],
    });
    expect(persisted).toMatchObject({
      primaryCategories: ["equity"],
      secondaryCategories: ["equity.large_cap"],
      tertiaryCategories: ["style.growth"],
      regions: ["US_CA"],
    });

    useFilterStore.getState().resetFilters({
      assetClass: "core",
      fundingStates: ["Leveraging", "Deleveraging"],
      rsStates: ["Lag", "Weakening", "Improving", "Lead"],
    });
    expect(useFilterStore.getState()).toMatchObject({
      primaryCategories: [],
      secondaryCategories: [],
      tertiaryCategories: [],
      regions: [],
    });
  });
});
