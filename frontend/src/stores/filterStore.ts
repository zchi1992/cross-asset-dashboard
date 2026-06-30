import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { FundingState, RelativeStrengthState, VelocityFilter } from "../services/contracts";

type FilterState = {
  assetClass: string;
  fundingStates: FundingState[];
  rsStates: RelativeStrengthState[];
  velocityFilter: VelocityFilter;
  searchText: string;
  setAssetClass: (value: string) => void;
  setFundingStates: (value: FundingState[]) => void;
  setRsStates: (value: RelativeStrengthState[]) => void;
  setVelocityFilter: (value: VelocityFilter) => void;
  setSearchText: (value: string) => void;
  resetFilters: (defaults: Pick<FilterState, "assetClass" | "fundingStates" | "rsStates">) => void;
};

export const useFilterStore = create<FilterState>()(
  persist(
    (set) => ({
      assetClass: "",
      fundingStates: ["Leveraging", "Deleveraging"],
      rsStates: ["Lag", "Weakening", "Improving", "Lead"],
      velocityFilter: "All",
      searchText: "",
      setAssetClass: (assetClass) => set({ assetClass }),
      setFundingStates: (fundingStates) => set({ fundingStates }),
      setRsStates: (rsStates) => set({ rsStates }),
      setVelocityFilter: (velocityFilter) => set({ velocityFilter }),
      setSearchText: (searchText) => set({ searchText }),
      resetFilters: (defaults) => set({ ...defaults, velocityFilter: "All", searchText: "" }),
    }),
    {
      name: "local-asset-terminal-filters",
      partialize: (state) => ({
        assetClass: state.assetClass,
        fundingStates: state.fundingStates,
        rsStates: state.rsStates,
        velocityFilter: state.velocityFilter,
      }),
    },
  ),
);
