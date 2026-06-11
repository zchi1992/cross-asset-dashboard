import { useEffect, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchAssets, fetchConfig, fetchDates, fetchPlayback } from "./services/api";
import type { FundingState, RelativeStrengthState } from "./services/contracts";
import { CrossAssetScatter } from "./components/CrossAssetScatter";
import { useFilterStore } from "./stores/filterStore";
import { usePlaybackStore } from "./stores/playbackStore";
import { useSelectionStore } from "./stores/selectionStore";
import { filterItems, matchesSearch } from "./utils/filtering";

export function App() {
  const configQuery = useQuery({ queryKey: ["config"], queryFn: fetchConfig });
  const datesQuery = useQuery({ queryKey: ["dates"], queryFn: fetchDates });
  const assetsQuery = useQuery({ queryKey: ["assets"], queryFn: fetchAssets });
  const playbackQuery = useQuery({ queryKey: ["playback"], queryFn: () => fetchPlayback() });

  const assetClass = useFilterStore((state) => state.assetClass);
  const fundingStates = useFilterStore((state) => state.fundingStates);
  const rsStates = useFilterStore((state) => state.rsStates);
  const searchText = useFilterStore((state) => state.searchText);
  const setAssetClass = useFilterStore((state) => state.setAssetClass);
  const setFundingStates = useFilterStore((state) => state.setFundingStates);
  const setRsStates = useFilterStore((state) => state.setRsStates);
  const setSearchText = useFilterStore((state) => state.setSearchText);
  const resetFilters = useFilterStore((state) => state.resetFilters);

  const availableDates = usePlaybackStore((state) => state.availableDates);
  const currentIndex = usePlaybackStore((state) => state.currentIndex);
  const isPlaying = usePlaybackStore((state) => state.isPlaying);
  const speed = usePlaybackStore((state) => state.speed);
  const setDates = usePlaybackStore((state) => state.setDates);
  const setIndex = usePlaybackStore((state) => state.setIndex);
  const setPlaying = usePlaybackStore((state) => state.setPlaying);
  const setSpeed = usePlaybackStore((state) => state.setSpeed);
  const playFromStart = usePlaybackStore((state) => state.playFromStart);
  const first = usePlaybackStore((state) => state.first);
  const previous = usePlaybackStore((state) => state.previous);
  const next = usePlaybackStore((state) => state.next);
  const latest = usePlaybackStore((state) => state.latest);

  const selectedSymbol = useSelectionStore((state) => state.selectedSymbol);
  const selectSymbol = useSelectionStore((state) => state.selectSymbol);
  const clearSelection = useSelectionStore((state) => state.clearSelection);

  useEffect(() => {
    if (datesQuery.data?.dates.length) {
      setDates(datesQuery.data.dates);
    }
  }, [datesQuery.data, setDates]);

  useEffect(() => {
    const config = configQuery.data;
    if (!config) return;
    if (!config.asset_classes.includes(assetClass)) {
      const normalized = config.asset_classes.find((value) => value.toLowerCase() === assetClass.toLowerCase());
      setAssetClass(normalized ?? config.default_filters.asset_class);
    }
    const validFundingStates = fundingStates.filter((value) => config.funding_states.includes(value));
    if (validFundingStates.length !== fundingStates.length) {
      setFundingStates(validFundingStates);
    }
    const validRsStates = rsStates.filter((value) => config.rs_states.includes(value));
    if (validRsStates.length !== rsStates.length) {
      setRsStates(validRsStates);
    }
  }, [assetClass, configQuery.data, fundingStates, rsStates, setAssetClass, setFundingStates, setRsStates]);

  useEffect(() => {
    if (!isPlaying) return;
    const delay = Math.max(100, 1000 / speed);
    const timer = window.setInterval(() => {
      const state = usePlaybackStore.getState();
      if (state.currentIndex >= state.availableDates.length - 1) {
        state.setPlaying(false);
        return;
      }
      usePlaybackStore.setState({ currentIndex: state.currentIndex + 1 });
    }, delay);
    return () => window.clearInterval(timer);
  }, [isPlaying, speed]);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        if (searchText) setSearchText("");
        clearSelection();
      }
      if (event.key === "Enter" && searchText.trim()) {
        const match = currentItems.find((item) => matchesSearch(item, searchText));
        if (match) selectSymbol(match.symbol);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  });

  const currentDate = availableDates[currentIndex] ?? "";
  const frames = playbackQuery.data?.frames ?? {};
  const currentItems = frames[currentDate] ?? [];
  const hasSearch = Boolean(searchText.trim());
  const filteredItems = useMemo(
    () =>
      hasSearch
        ? currentItems.filter((item) => matchesSearch(item, searchText))
        : filterItems(currentItems, assetClass, fundingStates, rsStates),
    [assetClass, currentItems, fundingStates, hasSearch, rsStates, searchText],
  );
  const selectedCurrentItem = selectedSymbol ? currentItems.find((item) => item.symbol === selectedSymbol) : null;
  const chartItems = useMemo(
    () => (selectedSymbol ? (selectedCurrentItem ? [selectedCurrentItem] : []) : filteredItems),
    [filteredItems, selectedCurrentItem, selectedSymbol],
  );

  const isBootLoading = configQuery.isLoading || datesQuery.isLoading;
  const error = configQuery.error || datesQuery.error || playbackQuery.error || assetsQuery.error;
  const config = configQuery.data;
  const assetCount = assetsQuery.data?.assets.length ?? currentItems.length;
  const isPlaybackLoading = playbackQuery.isLoading;
  const isPlaybackReady = Boolean(playbackQuery.data);
  const canUsePlayback = isPlaybackReady && availableDates.length > 0;
  const emptyMessage = isPlaybackLoading ? "Loading playback data..." : "No assets match the selected filters";

  if (isBootLoading) {
    return <main className="terminal-shell terminal-message">Loading terminal data...</main>;
  }

  if (error || !config) {
    return (
      <main className="terminal-shell terminal-message">
        <section className="error-panel">
          <strong>Backend service is offline</strong>
          <span>Start it with scripts/run_market_map_dashboard.sh, then refresh this page.</span>
        </section>
      </main>
    );
  }

  return (
    <main className="terminal-shell">
      <section className="filter-bar">
        <label>
          <span>Search</span>
          <input value={searchText} onChange={(event) => setSearchText(event.target.value)} placeholder="Symbol or asset name" />
        </label>
        <label>
          <span>Asset Class</span>
          <select value={assetClass} onChange={(event) => setAssetClass(event.target.value)}>
            {config.asset_classes.map((value) => (
              <option key={value} value={value}>
                {formatAssetClass(value)}
              </option>
            ))}
          </select>
        </label>
        <MultiSelect
          title="Funding State"
          values={config.funding_states}
          selected={fundingStates}
          onChange={(value) => setFundingStates(value as FundingState[])}
        />
        <MultiSelect
          title="Relative Strength State"
          values={config.rs_states}
          selected={rsStates}
          onChange={(value) => setRsStates(value as RelativeStrengthState[])}
        />
        <button
          className="reset-button"
          onClick={() => {
            resetFilters({
              assetClass: config.default_filters.asset_class,
              fundingStates: config.default_filters.funding_states,
              rsStates: config.default_filters.rs_states,
            });
            clearSelection();
          }}
        >
          Reset
        </button>
      </section>

      <section className="workspace">
        <div className="workspace-topline">
          <span>{currentDate}</span>
          <span>{chartItems.length} visible / {currentItems.length} frame / {assetCount} assets / {availableDates.length} dates</span>
        </div>
        <div className="chart-frame">
          <CrossAssetScatter
            items={chartItems}
            frames={frames}
            dates={availableDates}
            currentIndex={currentIndex}
            searchText={searchText}
            selectedSymbol={selectedSymbol}
            scoreRanges={config.score_ranges}
            onSelect={selectSymbol}
            onClear={clearSelection}
          />
          <div className="trend-legend" aria-hidden="true">
            <span>Weak</span>
            <div />
            <span>Strong</span>
          </div>
        </div>
        {!chartItems.length && <div className="empty-state">{emptyMessage}</div>}
      </section>

      <section className="playback-bar">
        <button onClick={first} disabled={!canUsePlayback}>First</button>
        <button onClick={previous} disabled={!canUsePlayback}>Previous</button>
        <button className="primary-button" onClick={() => (isPlaying ? setPlaying(false) : playFromStart())} disabled={!canUsePlayback}>
          {isPlaying ? "Pause" : "Play"}
        </button>
        <button onClick={next} disabled={!canUsePlayback}>Next</button>
        <button onClick={latest} disabled={!canUsePlayback}>Latest</button>
        <label>
          <span>Speed</span>
          <select value={speed} onChange={(event) => setSpeed(Number(event.target.value))}>
            {config.playback.speeds.map((value) => (
              <option key={value} value={value}>
                {value}x
              </option>
            ))}
          </select>
        </label>
        <input
          className="date-slider"
          type="range"
          min={0}
          max={Math.max(0, availableDates.length - 1)}
          value={currentIndex}
          disabled={!canUsePlayback}
          onChange={(event) => setIndex(Number(event.target.value))}
        />
        <input
          type="date"
          value={currentDate}
          disabled={!canUsePlayback}
          onChange={(event) => {
            const index = availableDates.indexOf(event.target.value);
            if (index >= 0) setIndex(index);
          }}
        />
        <strong>{currentDate}</strong>
      </section>
    </main>
  );
}

function MultiSelect({
  title,
  values,
  selected,
  onChange,
}: {
  title: string;
  values: string[];
  selected: string[];
  onChange: (selected: string[]) => void;
}) {
  return (
    <div className="multi-select" role="group" aria-label={title}>
      <span className="control-title">{title}</span>
      <div className="multi-options">
        {values.map((value) => (
          <label key={value}>
            <input
              type="checkbox"
              checked={selected.includes(value)}
              onChange={(event) => {
                const next = event.target.checked ? [...selected, value] : selected.filter((item) => item !== value);
                onChange(next);
              }}
            />
            <span>{value}</span>
          </label>
        ))}
      </div>
    </div>
  );
}

function formatAssetClass(value: string) {
  return value
    .split(/[_-]/)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}
