import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { FundingState, RelativeStrengthState } from "../services/contracts";

type FilterState = {
  assetClass: string;
  fundingStates: FundingState[];
  rsStates: RelativeStrengthState[];
  searchText: string;
  setAssetClass: (value: string) => void;
  setFundingStates: (value: FundingState[]) => void;
  setRsStates: (value: RelativeStrengthState[]) => void;
  setSearchText: (value: string) => void;
  resetFilters: (defaults: Pick<FilterState, "assetClass" | "fundingStates" | "rsStates">) => void;
};

export const useFilterStore = create<FilterState>()(
  persist(
    (set) => ({
      assetClass: "",
      fundingStates: ["Leveraging", "Deleveraging"],
      rsStates: ["Lag", "Weakening", "Improving", "Lead"],
      searchText: "",
      setAssetClass: (assetClass) => set({ assetClass }),
      setFundingStates: (fundingStates) => set({ fundingStates }),
      setRsStates: (rsStates) => set({ rsStates }),
      setSearchText: (searchText) => set({ searchText }),
      resetFilters: (defaults) => set({ ...defaults, searchText: "" }),
    }),
    {
      name: "local-asset-terminal-filters",
      partialize: (state) => ({
        assetClass: state.assetClass,
        fundingStates: state.fundingStates,
        rsStates: state.rsStates,
      }),
    },
  ),
);
