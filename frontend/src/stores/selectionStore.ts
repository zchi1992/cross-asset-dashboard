import { create } from "zustand";

type SelectionState = {
  selectedSymbol: string | null;
  showTrajectory: boolean;
  selectSymbol: (symbol: string) => void;
  clearSelection: () => void;
};

export const useSelectionStore = create<SelectionState>((set) => ({
  selectedSymbol: null,
  showTrajectory: false,
  selectSymbol: (selectedSymbol) => set({ selectedSymbol, showTrajectory: true }),
  clearSelection: () => set({ selectedSymbol: null, showTrajectory: false }),
}));
