import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { FundingState, RelativeStrengthState } from "../services/contracts";

type FilterState = {
  assetClass: string;
  fundingStates: FundingState[];
  rsStates: RelativeStrengthState[];
  primaryCategories: string[];
  secondaryCategories: string[];
  tertiaryCategories: string[];
  regions: string[];
  searchText: string;
  setAssetClass: (value: string) => void;
  setFundingStates: (value: FundingState[]) => void;
  setRsStates: (value: RelativeStrengthState[]) => void;
  setPrimaryCategories: (value: string[]) => void;
  setSecondaryCategories: (value: string[]) => void;
  setTertiaryCategories: (value: string[]) => void;
  setRegions: (value: string[]) => void;
  setSearchText: (value: string) => void;
  resetFilters: (defaults: Pick<FilterState, "assetClass" | "fundingStates" | "rsStates">) => void;
};

export const useFilterStore = create<FilterState>()(
  persist(
    (set) => ({
      assetClass: "",
      fundingStates: ["Leveraging", "Deleveraging"],
      rsStates: ["Lag", "Weakening", "Improving", "Lead"],
      primaryCategories: [],
      secondaryCategories: [],
      tertiaryCategories: [],
      regions: [],
      searchText: "",
      setAssetClass: (assetClass) => set({ assetClass }),
      setFundingStates: (fundingStates) => set({ fundingStates }),
      setRsStates: (rsStates) => set({ rsStates }),
      setPrimaryCategories: (primaryCategories) => set({ primaryCategories }),
      setSecondaryCategories: (secondaryCategories) => set({ secondaryCategories }),
      setTertiaryCategories: (tertiaryCategories) => set({ tertiaryCategories }),
      setRegions: (regions) => set({ regions }),
      setSearchText: (searchText) => set({ searchText }),
      resetFilters: (defaults) => set({
        ...defaults,
        primaryCategories: [],
        secondaryCategories: [],
        tertiaryCategories: [],
        regions: [],
        searchText: "",
      }),
    }),
    {
      name: "local-asset-terminal-filters",
      partialize: (state) => ({
        assetClass: state.assetClass,
        fundingStates: state.fundingStates,
        rsStates: state.rsStates,
        primaryCategories: state.primaryCategories,
        secondaryCategories: state.secondaryCategories,
        tertiaryCategories: state.tertiaryCategories,
        regions: state.regions,
      }),
    },
  ),
);
