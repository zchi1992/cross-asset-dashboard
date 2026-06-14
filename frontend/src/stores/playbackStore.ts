import { create } from "zustand";
import { persist } from "zustand/middleware";

type PlaybackState = {
  availableDates: string[];
  currentIndex: number;
  isPlaying: boolean;
  speed: number;
  setDates: (dates: string[]) => void;
  setIndex: (index: number) => void;
  setPlaying: (isPlaying: boolean) => void;
  setSpeed: (speed: number) => void;
  playFromStart: () => void;
  first: () => void;
  previous: () => void;
  next: () => void;
  latest: () => void;
};

export const usePlaybackStore = create<PlaybackState>()(
  persist(
    (set, get) => ({
      availableDates: [],
      currentIndex: 0,
      isPlaying: false,
      speed: 1,
      setDates: (availableDates) =>
        set((state) => {
          const previousLastIndex = state.availableDates.length - 1;
          const wasLatest = previousLastIndex < 0 || state.currentIndex >= previousLastIndex;
          return {
            availableDates,
            currentIndex: availableDates.length
              ? wasLatest
                ? availableDates.length - 1
                : Math.min(state.currentIndex, availableDates.length - 1)
              : 0,
          };
        }),
      setIndex: (currentIndex) =>
        set((state) => ({
          currentIndex: Math.max(0, Math.min(currentIndex, state.availableDates.length - 1)),
          isPlaying: false,
        })),
      setPlaying: (isPlaying) => set({ isPlaying }),
      setSpeed: (speed) => set({ speed }),
      playFromStart: () => set({ currentIndex: 0, isPlaying: true }),
      first: () => set({ currentIndex: 0, isPlaying: false }),
      previous: () => set((state) => ({ currentIndex: Math.max(0, state.currentIndex - 1), isPlaying: false })),
      next: () =>
        set((state) => ({
          currentIndex: Math.min(state.availableDates.length - 1, state.currentIndex + 1),
          isPlaying: false,
        })),
      latest: () => set((state) => ({ currentIndex: Math.max(0, state.availableDates.length - 1), isPlaying: false })),
    }),
    {
      name: "local-asset-terminal-playback",
      partialize: (state) => ({ currentIndex: state.currentIndex, speed: state.speed }),
    },
  ),
);

export function selectedDate() {
  const { availableDates, currentIndex } = usePlaybackStore.getState();
  return availableDates[currentIndex] ?? "";
}
