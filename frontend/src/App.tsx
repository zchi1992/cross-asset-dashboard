import { memo, useEffect, useState, useMemo } from "react";
import type { CSSProperties, PointerEvent as ReactPointerEvent } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchAssets, fetchConfig, fetchDates, fetchPlayback } from "./services/api";
import type { FundingState, RelativeStrengthState, SnapshotItem, TaxonomyOptions } from "./services/contracts";
import { CrossAssetScatter } from "./components/CrossAssetScatter";
import { MacroMap } from "./components/MacroMap";
import { useFilterStore } from "./stores/filterStore";
import { usePlaybackStore } from "./stores/playbackStore";
import { useSelectionStore } from "./stores/selectionStore";
import {
  assetKeyWithCollisions,
  duplicateAssetBaseKeys,
  CN_REGION_FILTER,
  filterFramesByAssetFilter,
  filterItems,
  GS_EXEMPT_FILTER,
  matchesSearch,
} from "./utils/filtering";
import { buildAvailableTaxonomyOptions, pruneSelection, taxonomyOptionLabel } from "./utils/taxonomy";
import {
  buildOpportunityMarkers,
  buildRankChanges,
  buildRankedOpportunityRows,
  OPPORTUNITY_DISPLAY_LIMIT,
  rankCandidateLongOpportunities,
  rankCandidateShortOpportunities,
  rankStrongLongOpportunities,
  rankStrongShortOpportunities,
  topOpportunities,
  type RankedOpportunity,
} from "./utils/opportunities";

const RS_COMPONENT_SERIES: MiniChartSeries[] = [
  { metric: "early_reversal", label: "early_reversal", color: "var(--rs-early-reversal)" },
  { metric: "strength_momentum", label: "strength_momentum", color: "var(--rs-strength-momentum)" },
  { metric: "relative_strength", label: "relative_strength", color: "var(--rs-relative-strength)" },
];
const MINI_CHART_WIDTH = 360;
const MINI_CHART_HEIGHT = 184;
const MINI_CHART_PLOT = {
  top: 12,
  right: 16,
  bottom: 34,
  left: 42,
};
const RS_THRESHOLD_VALUES = [120, 100, 80];
const EMPTY_TAXONOMY_OPTIONS: TaxonomyOptions = {
  primary_categories: [],
  secondary_categories: [],
  tertiary_categories: [],
  regions: [],
};

type ActiveView = "macroMap" | "marketMap" | "opportunities";

export function App() {
  const refreshPolicy = {
    refetchInterval: 15_000,
    refetchOnWindowFocus: "always" as const,
    staleTime: 0,
  };
  const configQuery = useQuery({ queryKey: ["config"], queryFn: fetchConfig, ...refreshPolicy });
  const datesQuery = useQuery({ queryKey: ["dates"], queryFn: fetchDates, ...refreshPolicy });
  const assetsQuery = useQuery({ queryKey: ["assets"], queryFn: fetchAssets, ...refreshPolicy });
  const playbackQuery = useQuery({ queryKey: ["playback"], queryFn: () => fetchPlayback(), ...refreshPolicy });

  const assetClass = useFilterStore((state) => state.assetClass);
  const fundingStates = useFilterStore((state) => state.fundingStates);
  const rsStates = useFilterStore((state) => state.rsStates);
  const primaryCategories = useFilterStore((state) => state.primaryCategories);
  const secondaryCategories = useFilterStore((state) => state.secondaryCategories);
  const tertiaryCategories = useFilterStore((state) => state.tertiaryCategories);
  const regions = useFilterStore((state) => state.regions);
  const searchText = useFilterStore((state) => state.searchText);
  const setAssetClass = useFilterStore((state) => state.setAssetClass);
  const setFundingStates = useFilterStore((state) => state.setFundingStates);
  const setRsStates = useFilterStore((state) => state.setRsStates);
  const setPrimaryCategories = useFilterStore((state) => state.setPrimaryCategories);
  const setSecondaryCategories = useFilterStore((state) => state.setSecondaryCategories);
  const setTertiaryCategories = useFilterStore((state) => state.setTertiaryCategories);
  const setRegions = useFilterStore((state) => state.setRegions);
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
  const [detailPanelWidth, setDetailPanelWidth] = useState(360);
  const [activeView, setActiveView] = useState<ActiveView>("macroMap");
  const [opportunityAssetFilter, setOpportunityAssetFilter] = useState("");

  useEffect(() => {
    if (datesQuery.data?.dates.length) {
      setDates(datesQuery.data.dates);
    }
  }, [datesQuery.data, setDates]);

  useEffect(() => {
    if (playbackQuery.data?.dates.length) {
      setDates(playbackQuery.data.dates);
    }
  }, [playbackQuery.data, setDates]);

  useEffect(() => {
    const config = configQuery.data;
    if (!config) return;
    const assetFilterOptions = buildAssetFilterOptions(config.asset_classes);
    if (!assetFilterOptions.includes(assetClass)) {
      const normalized = assetFilterOptions.find((value) => value.toLowerCase() === assetClass.toLowerCase());
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
        if (match) selectSymbol(assetKeyWithCollisions(match, duplicateAssetKeys));
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  });

  const currentDate = availableDates[currentIndex] ?? "";
  const frames = playbackQuery.data?.frames ?? {};
  const allPlaybackItems = useMemo(() => Object.values(frames).flat(), [frames]);
  const taxonomySelection = useMemo(
    () => ({ primaryCategories, secondaryCategories, tertiaryCategories, regions }),
    [primaryCategories, regions, secondaryCategories, tertiaryCategories],
  );
  const availableTaxonomyOptions = useMemo(
    () =>
      buildAvailableTaxonomyOptions(
        allPlaybackItems,
        configQuery.data?.taxonomy ?? EMPTY_TAXONOMY_OPTIONS,
        taxonomySelection,
      ),
    [allPlaybackItems, configQuery.data?.taxonomy, taxonomySelection],
  );
  const opportunityFrames = useMemo(
    () => filterFramesByAssetFilter(frames, opportunityAssetFilter),
    [frames, opportunityAssetFilter],
  );
  const duplicateAssetKeys = useMemo(() => duplicateAssetBaseKeys(frames), [frames]);
  const currentItems = frames[currentDate] ?? [];
  const opportunityCurrentItems = opportunityFrames[currentDate] ?? [];
  const currentItemBySymbol = useMemo(
    () => new Map(currentItems.map((item) => [assetKeyWithCollisions(item, duplicateAssetKeys), item])),
    [currentItems, duplicateAssetKeys],
  );
  const historyBySymbol = useMemo(
    () => buildHistoryBySymbol(frames, availableDates, duplicateAssetKeys),
    [availableDates, duplicateAssetKeys, frames],
  );
  const hasSearch = Boolean(searchText.trim());
  const filteredItems = useMemo(
    () =>
      hasSearch
        ? currentItems.filter((item) => matchesSearch(item, searchText))
        : filterItems(currentItems, assetClass, fundingStates, rsStates, taxonomySelection),
    [assetClass, currentItems, fundingStates, hasSearch, rsStates, searchText, taxonomySelection],
  );

  useEffect(() => {
    if (!playbackQuery.data) return;
    const nextPrimary = pruneSelection(primaryCategories, availableTaxonomyOptions.primary_categories);
    const nextSecondary = pruneSelection(secondaryCategories, availableTaxonomyOptions.secondary_categories);
    const nextTertiary = pruneSelection(tertiaryCategories, availableTaxonomyOptions.tertiary_categories);
    const nextRegions = pruneSelection(regions, availableTaxonomyOptions.regions);
    if (!sameValues(nextPrimary, primaryCategories)) setPrimaryCategories(nextPrimary);
    if (!sameValues(nextSecondary, secondaryCategories)) setSecondaryCategories(nextSecondary);
    if (!sameValues(nextTertiary, tertiaryCategories)) setTertiaryCategories(nextTertiary);
    if (!sameValues(nextRegions, regions)) setRegions(nextRegions);
  }, [
    availableTaxonomyOptions,
    playbackQuery.data,
    primaryCategories,
    regions,
    secondaryCategories,
    setPrimaryCategories,
    setRegions,
    setSecondaryCategories,
    setTertiaryCategories,
    tertiaryCategories,
  ]);
  const selectedCurrentItem = selectedSymbol ? currentItemBySymbol.get(selectedSymbol) ?? null : null;
  const chartItems = filteredItems;
  const selectedHistory = useMemo(
    () =>
      selectedSymbol
        ? (historyBySymbol.get(selectedSymbol) ?? []).filter((entry) => entry.index <= currentIndex)
        : [],
    [currentIndex, historyBySymbol, selectedSymbol],
  );
  const strongLongRankChanges = useMemo(
    () => buildRankChanges(opportunityFrames, availableDates, currentIndex, "strongLong"),
    [availableDates, currentIndex, opportunityFrames],
  );
  const candidateLongRankChanges = useMemo(
    () => buildRankChanges(opportunityFrames, availableDates, currentIndex, "candidateLong"),
    [availableDates, currentIndex, opportunityFrames],
  );
  const strongShortRankChanges = useMemo(
    () => buildRankChanges(opportunityFrames, availableDates, currentIndex, "strongShort"),
    [availableDates, currentIndex, opportunityFrames],
  );
  const candidateShortRankChanges = useMemo(
    () => buildRankChanges(opportunityFrames, availableDates, currentIndex, "candidateShort"),
    [availableDates, currentIndex, opportunityFrames],
  );
  const strongLongRows = useMemo(
    () => buildRankedOpportunityRows(opportunityCurrentItems, strongLongRankChanges, rankStrongLongOpportunities),
    [opportunityCurrentItems, strongLongRankChanges],
  );
  const candidateLongRows = useMemo(
    () => buildRankedOpportunityRows(opportunityCurrentItems, candidateLongRankChanges, rankCandidateLongOpportunities),
    [candidateLongRankChanges, opportunityCurrentItems],
  );
  const strongShortRows = useMemo(
    () => buildRankedOpportunityRows(opportunityCurrentItems, strongShortRankChanges, rankStrongShortOpportunities),
    [opportunityCurrentItems, strongShortRankChanges],
  );
  const candidateShortRows = useMemo(
    () => buildRankedOpportunityRows(opportunityCurrentItems, candidateShortRankChanges, rankCandidateShortOpportunities),
    [candidateShortRankChanges, opportunityCurrentItems],
  );
  const opportunityMarkers = useMemo(
    () => buildOpportunityMarkers(strongLongRows, candidateLongRows, strongShortRows, candidateShortRows),
    [candidateLongRows, candidateShortRows, strongLongRows, strongShortRows],
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
      <ViewTabs activeView={activeView} onChange={setActiveView} />

      <MacroMap active={activeView === "macroMap"} />

      {activeView === "macroMap" ? null : activeView === "marketMap" ? (
        <section className="filter-bar">
          <SearchControl value={searchText} onCommit={setSearchText} />
          <label>
            <span>Asset Class</span>
            <select value={assetClass} onChange={(event) => setAssetClass(event.target.value)}>
              {buildAssetFilterOptions(config.asset_classes).map((value) => (
                <option key={value} value={value}>
                  {formatAssetClass(value)}
                </option>
              ))}
            </select>
          </label>
          <MultiSelect
            title="一级类别 / Primary"
            values={availableTaxonomyOptions.primary_categories.map((option) => option.code)}
            labels={taxonomyLabels(availableTaxonomyOptions.primary_categories)}
            selected={primaryCategories}
            onChange={setPrimaryCategories}
            compact
          />
          <MultiSelect
            title="二级类别 / Secondary"
            values={availableTaxonomyOptions.secondary_categories.map((option) => option.code)}
            labels={taxonomyLabels(availableTaxonomyOptions.secondary_categories)}
            selected={secondaryCategories}
            onChange={setSecondaryCategories}
            compact
          />
          <MultiSelect
            title="三级类别 / Tertiary"
            values={availableTaxonomyOptions.tertiary_categories.map((option) => option.code)}
            labels={taxonomyLabels(availableTaxonomyOptions.tertiary_categories)}
            selected={tertiaryCategories}
            onChange={setTertiaryCategories}
            compact
          />
          <MultiSelect
            title="地区 / Region"
            values={availableTaxonomyOptions.regions.map((option) => option.code)}
            labels={taxonomyLabels(availableTaxonomyOptions.regions)}
            selected={regions}
            onChange={setRegions}
            compact
          />
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
      ) : (
        <section className="opportunity-bar">
          <label>
            <span>Asset Class</span>
            <select value={opportunityAssetFilter} onChange={(event) => setOpportunityAssetFilter(event.target.value)}>
              <option value="">All Assets</option>
              {buildOpportunityAssetFilterOptions(config.asset_classes).map((value) => (
                <option key={value} value={value}>
                  {formatAssetClass(value)}
                </option>
              ))}
            </select>
          </label>
          <span className="opportunity-title">Trading Opportunities</span>
          <strong>
            Long {strongLongRows.length} strong / {candidateLongRows.length} candidate · Short {strongShortRows.length} strong / {candidateShortRows.length} candidate
          </strong>
          <span>{opportunityCurrentItems.length} selected / {currentItems.length} frame assets</span>
        </section>
      )}

      {activeView === "macroMap" ? null : activeView === "marketMap" ? (
        <section className="workspace">
          <div className="workspace-topline">
            <span>{currentDate}</span>
            <span>{chartItems.length} visible / {currentItems.length} frame / {assetCount} assets / {availableDates.length} dates</span>
          </div>
          <div
            className={`workspace-body ${selectedCurrentItem ? "with-detail" : ""}`}
            style={{ "--detail-panel-width": `${detailPanelWidth}px` } as CSSProperties}
          >
            <div className="chart-frame">
              <CrossAssetScatter
                items={chartItems}
                frames={frames}
                dates={availableDates}
                currentIndex={currentIndex}
                selectedSymbol={selectedSymbol}
                duplicateAssetKeys={duplicateAssetKeys}
                opportunityMarkers={opportunityMarkers}
                onSelect={selectSymbol}
                onClear={clearSelection}
              />
              <div
                className="trend-legend"
                role="img"
                aria-label="Trend score color scale with thresholds at minus 40 and 40"
              >
                <div className="trend-legend-scale" />
                <div className="trend-legend-thresholds">
                  <span>−40</span>
                  <span>40</span>
                </div>
              </div>
            </div>
            {selectedCurrentItem && (
              <AssetDetailOverlay
                item={selectedCurrentItem}
                history={selectedHistory}
                onClose={clearSelection}
                onResize={(event) => startPanelResize(event, detailPanelWidth, setDetailPanelWidth)}
              />
            )}
          </div>
          {!chartItems.length && <div className="empty-state">{emptyMessage}</div>}
        </section>
      ) : (
        <OpportunitiesWorkspace
          currentDate={currentDate}
          selectedAssetCount={opportunityCurrentItems.length}
          frameAssetCount={currentItems.length}
          dateCount={availableDates.length}
          strongLongRows={strongLongRows}
          candidateLongRows={candidateLongRows}
          strongShortRows={strongShortRows}
          candidateShortRows={candidateShortRows}
          selectedSymbol={selectedSymbol}
          selectedItem={selectedCurrentItem}
          selectedHistory={selectedHistory}
          duplicateAssetKeys={duplicateAssetKeys}
          detailPanelWidth={detailPanelWidth}
          onSelect={(item) => selectSymbol(assetKeyWithCollisions(item, duplicateAssetKeys))}
          onClose={clearSelection}
          onResize={(event) => startPanelResize(event, detailPanelWidth, setDetailPanelWidth)}
        />
      )}

      {activeView !== "macroMap" && <section className="playback-bar">
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
      </section>}
    </main>
  );
}

function ViewTabs({ activeView, onChange }: { activeView: ActiveView; onChange: (view: ActiveView) => void }) {
  return (
    <section className="view-tabs" role="tablist" aria-label="Dashboard views">
      <button
        type="button"
        role="tab"
        aria-selected={activeView === "macroMap"}
        className={activeView === "macroMap" ? "active" : ""}
        onClick={() => onChange("macroMap")}
      >
        宏观地图
      </button>
      <button
        type="button"
        role="tab"
        aria-selected={activeView === "marketMap"}
        className={activeView === "marketMap" ? "active" : ""}
        onClick={() => onChange("marketMap")}
      >
        Market Map
      </button>
      <button
        type="button"
        role="tab"
        aria-selected={activeView === "opportunities"}
        className={activeView === "opportunities" ? "active" : ""}
        onClick={() => onChange("opportunities")}
      >
        交易机会
      </button>
    </section>
  );
}

function OpportunitiesWorkspace({
  currentDate,
  selectedAssetCount,
  frameAssetCount,
  dateCount,
  strongLongRows,
  candidateLongRows,
  strongShortRows,
  candidateShortRows,
  selectedSymbol,
  selectedItem,
  selectedHistory,
  duplicateAssetKeys,
  detailPanelWidth,
  onSelect,
  onClose,
  onResize,
}: {
  currentDate: string;
  selectedAssetCount: number;
  frameAssetCount: number;
  dateCount: number;
  strongLongRows: RankedOpportunity[];
  candidateLongRows: RankedOpportunity[];
  strongShortRows: RankedOpportunity[];
  candidateShortRows: RankedOpportunity[];
  selectedSymbol: string | null;
  selectedItem: SnapshotItem | null;
  selectedHistory: HistoryPoint[];
  duplicateAssetKeys: Set<string>;
  detailPanelWidth: number;
  onSelect: (item: SnapshotItem) => void;
  onClose: () => void;
  onResize: (event: ReactPointerEvent<HTMLButtonElement>) => void;
}) {
  return (
    <section className="workspace opportunities-workspace">
      <div className="workspace-topline">
        <span>{currentDate}</span>
        <span>
          Long {strongLongRows.length}/{candidateLongRows.length} · Short {strongShortRows.length}/{candidateShortRows.length} strong/candidate / {selectedAssetCount} selected / {frameAssetCount} frame / {dateCount} dates
        </span>
      </div>
      <div
        className="opportunities-body"
        style={{ "--detail-panel-width": `${detailPanelWidth}px` } as CSSProperties}
      >
        <div className="opportunities-layout">
          <div className="opportunity-row">
            <OpportunitySection title="强势做多" rows={strongLongRows} testId="strong-long" selectedSymbol={selectedSymbol} duplicateAssetKeys={duplicateAssetKeys} onSelect={onSelect} />
            <OpportunitySection title="候选做多" rows={candidateLongRows} testId="candidate-long" selectedSymbol={selectedSymbol} duplicateAssetKeys={duplicateAssetKeys} onSelect={onSelect} />
          </div>
          <div className="opportunity-row">
            <OpportunitySection title="强势做空" rows={strongShortRows} testId="strong-short" selectedSymbol={selectedSymbol} duplicateAssetKeys={duplicateAssetKeys} onSelect={onSelect} />
            <OpportunitySection title="候选做空" rows={candidateShortRows} testId="candidate-short" selectedSymbol={selectedSymbol} duplicateAssetKeys={duplicateAssetKeys} onSelect={onSelect} />
          </div>
        </div>
        {selectedItem && (
          <AssetDetailOverlay
            item={selectedItem}
            history={selectedHistory}
            onClose={onClose}
            onResize={onResize}
          />
        )}
      </div>
    </section>
  );
}

function OpportunitySection({
  title,
  rows,
  testId,
  selectedSymbol,
  duplicateAssetKeys,
  onSelect,
}: {
  title: string;
  rows: RankedOpportunity[];
  testId: string;
  selectedSymbol: string | null;
  duplicateAssetKeys: Set<string>;
  onSelect: (item: SnapshotItem) => void;
}) {
  const visibleRows = topOpportunities(rows);
  return (
    <section className="opportunity-section" data-testid={`${testId}-section`}>
      <header>
        <h2>{title}</h2>
        <span>{rows.length} total / top {Math.min(rows.length, OPPORTUNITY_DISPLAY_LIMIT)} shown</span>
      </header>
      <OpportunityTable
        rows={visibleRows}
        testId={testId}
        selectedSymbol={selectedSymbol}
        duplicateAssetKeys={duplicateAssetKeys}
        onSelect={onSelect}
      />
    </section>
  );
}

function OpportunityTable({
  rows,
  testId,
  selectedSymbol,
  duplicateAssetKeys,
  onSelect,
}: {
  rows: RankedOpportunity[];
  testId: string;
  selectedSymbol: string | null;
  duplicateAssetKeys: Set<string>;
  onSelect: (item: SnapshotItem) => void;
}) {
  return (
    <div className="opportunity-table-wrap">
      <table className="opportunity-table" data-testid={`${testId}-table`}>
        <thead>
          <tr>
            <th>标的类型</th>
            <th>标的代码</th>
            <th>名称</th>
            <th>趋势状态名称</th>
            <th>趋势分</th>
            <th>比价分</th>
            <th>当前杠杆状态</th>
            <th>当前杠杆持续时间</th>
            <th>杠杆速率</th>
            <th>杠杆速率分</th>
            <th>1日总排名变化</th>
            <th>5日总排名变化</th>
            <th>10日总排名变化</th>
          </tr>
        </thead>
        <tbody>
          {rows.length ? (
            rows.map((row) => {
              const rowSymbol = assetKeyWithCollisions(row.item, duplicateAssetKeys);
              const isSelected = rowSymbol === selectedSymbol;
              return (
                <tr
                  key={`${row.rank}-${row.item.asset_class}-${row.item.symbol}-${row.item.asset_name}`}
                  data-testid={`${testId}-row`}
                  className={isSelected ? "is-selected" : ""}
                  aria-selected={isSelected}
                  tabIndex={0}
                  onClick={() => onSelect(row.item)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      onSelect(row.item);
                    }
                  }}
                >
                  <td>{row.item.asset_class}</td>
                  <td className="numeric-cell">{row.item.symbol}</td>
                  <td>{row.item.asset_name}</td>
                  <td>{row.item.trend_state || "-"}</td>
                  <td className="numeric-cell">{formatMaybeNumber(row.item.trend_score)}</td>
                  <td className="numeric-cell">{formatMaybeNumber(row.item.rs_score)}</td>
                  <td>{row.item.funding_state}</td>
                  <td className="numeric-cell">{formatMaybeNumber(row.item.leverage_duration)}</td>
                  <td className="numeric-cell">{formatMaybeNumber(row.item.leverage_velocity)}</td>
                  <td className="numeric-cell">{formatMaybeNumber(row.item.leverage_velocity_score)}</td>
                  <OpportunityRankCell value={row.rankChanges.rank_change_1d} />
                  <OpportunityRankCell value={row.rankChanges.rank_change_5d} />
                  <OpportunityRankCell value={row.rankChanges.rank_change_10d} />
                </tr>
              );
            })
          ) : (
            <tr>
              <td colSpan={13} className="empty-row">No matching opportunities</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

function OpportunityRankCell({ value }: { value: string }) {
  return <td className={`numeric-cell rank-change ${rankChangeClass(value)}`}>{value}</td>;
}

function MultiSelect({
  title,
  values,
  labels = {},
  compact = false,
  selected,
  onChange,
}: {
  title: string;
  values: string[];
  labels?: Record<string, string>;
  compact?: boolean;
  selected: string[];
  onChange: (selected: string[]) => void;
}) {
  const choices = values.map((value) => (
    <label key={value}>
      <input
        type="checkbox"
        checked={selected.includes(value)}
        onChange={(event) => {
          const next = event.target.checked ? [...selected, value] : selected.filter((item) => item !== value);
          onChange(next);
        }}
      />
      <span>{labels[value] ?? value}</span>
    </label>
  ));
  if (compact) {
    return (
      <div className="multi-select compact" role="group" aria-label={title}>
        <span className="control-title">{title}</span>
        <details>
          <summary>{selected.length ? `${selected.length} selected` : "All"}</summary>
          <div className="multi-options">{choices}</div>
        </details>
      </div>
    );
  }
  return (
    <div className="multi-select" role="group" aria-label={title}>
      <span className="control-title">{title}</span>
      <div className="multi-options">
        {choices}
      </div>
    </div>
  );
}

function taxonomyLabels(options: TaxonomyOptions[keyof TaxonomyOptions]) {
  return Object.fromEntries(options.map((option) => [option.code, taxonomyOptionLabel(option)]));
}

function sameValues(left: string[], right: string[]) {
  return left.length === right.length && left.every((value, index) => value === right[index]);
}

const SearchControl = memo(function SearchControl({
  value,
  onCommit,
}: {
  value: string;
  onCommit: (value: string) => void;
}) {
  const [draft, setDraft] = useState(value);

  useEffect(() => {
    setDraft(value);
  }, [value]);

  useEffect(() => {
    if (draft === value) return;
    const timer = window.setTimeout(() => onCommit(draft), 300);
    return () => window.clearTimeout(timer);
  }, [draft, onCommit, value]);

  return (
    <label>
      <span>Search</span>
      <input
        value={draft}
        onBlur={() => onCommit(draft)}
        onChange={(event) => setDraft(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter") onCommit(draft);
          if (event.key === "Escape") {
            setDraft("");
            onCommit("");
          }
        }}
        placeholder="Symbol or asset name"
      />
    </label>
  );
});

function formatAssetClass(value: string) {
  if (value === GS_EXEMPT_FILTER) return "GS Exempt";
  if (value === CN_REGION_FILTER) return "中国";
  return value
    .split(/[_-]/)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function buildAssetFilterOptions(assetClasses: string[]) {
  return [...assetClasses, GS_EXEMPT_FILTER];
}

function buildOpportunityAssetFilterOptions(assetClasses: string[]) {
  return [...assetClasses, CN_REGION_FILTER, GS_EXEMPT_FILTER];
}

function formatMaybeNumber(value?: number | null) {
  return typeof value === "number" && Number.isFinite(value) ? value.toFixed(1) : "-";
}

function rankChangeClass(value: string) {
  if (value === "NEW") return "is-new";
  if (value.startsWith("+")) return "is-positive";
  if (value.startsWith("-")) return "is-negative";
  return "is-flat";
}

type HistoryPoint = { date: string; item: SnapshotItem };
type IndexedHistoryPoint = HistoryPoint & { index: number };
type MiniChartMetric =
  | "trend_score"
  | "rs_score"
  | "early_reversal"
  | "strength_momentum"
  | "relative_strength"
  | "funding_score"
  | "leverage_value"
  | "leverage_velocity"
  | "leverage_velocity_score";
type MiniChartSeries = { metric: MiniChartMetric; label: string; color: string };

function buildHistoryBySymbol(
  frames: Record<string, SnapshotItem[]>,
  dates: string[],
  duplicateAssetKeys: Set<string>,
) {
  const historyBySymbol = new Map<string, IndexedHistoryPoint[]>();
  dates.forEach((date, index) => {
    for (const item of frames[date] ?? []) {
      const key = assetKeyWithCollisions(item, duplicateAssetKeys);
      const history = historyBySymbol.get(key);
      const entry = { date, index, item };
      if (history) {
        history.push(entry);
      } else {
        historyBySymbol.set(key, [entry]);
      }
    }
  });
  return historyBySymbol;
}

function classifyAsset(item: SnapshotItem) {
  const tags: string[] = [];
  if (item.trend_score >= 70 && item.rs_score >= 70 && item.leverage_velocity_score >= 70) tags.push("高置信做多");
  if (item.trend_score <= -70 && item.rs_score <= -70 && item.leverage_velocity_score <= -70) tags.push("高置信做空");
  if (item.leverage_velocity_score >= 70) tags.push("快速加杠杆");
  if (item.leverage_velocity_score <= -70) tags.push("快速去杠杆");
  return tags;
}

function AssetDetailOverlay({
  item,
  history,
  onClose,
  onResize,
}: {
  item: SnapshotItem;
  history: HistoryPoint[];
  onClose: () => void;
  onResize: (event: ReactPointerEvent<HTMLButtonElement>) => void;
}) {
  return (
    <>
      <button className="panel-resizer" aria-label="Resize detail panel" onPointerDown={onResize} />
      <AssetDetailPanel item={item} history={history} tags={classifyAsset(item)} onClose={onClose} />
    </>
  );
}

function AssetDetailPanel({
  item,
  history,
  tags,
  onClose,
}: {
  item: SnapshotItem;
  history: HistoryPoint[];
  tags: string[];
  onClose: () => void;
}) {
  const latestPoints = history.slice(-30);
  const shortTrend = formatTrendValue(item.daily_trend);
  const mediumTrend = formatTrendValue(item.weekly_trend);
  const longTrend = formatTrendValue(item.monthly_trend);
  return (
    <aside className="detail-panel">
      <header>
        <div>
          <span>{item.symbol}</span>
          <strong>{item.asset_name}</strong>
        </div>
        <button onClick={onClose} aria-label="Close detail panel">Close</button>
      </header>
      {tags.length > 0 && (
        <div className="tag-row">
          {tags.map((tag) => (
            <span key={tag}>{tag}</span>
          ))}
        </div>
      )}
      <div className="detail-grid">
        <Metric label="趋势分" value={item.trend_score} />
        <Metric label="收盘价对比60日位置" value={formatClosePosition(item.close_position_vs_60d)} />
        <Metric label="比价强度" value={item.rs_score} />
        <Metric label="杠杆资金水平" value={item.leverage_value} />
        <Metric label="比价状态" value={item.rs_state} />
        <Metric label="资金状态" value={item.funding_state} />
        <Metric label="趋势状态" value={item.trend_state || "-"} />
      </div>
      <div className="trend-strip">
        <Metric label="短频" value={shortTrend} />
        <Metric label="中频" value={mediumTrend} />
        <Metric label="长频" value={longTrend} />
      </div>
      <MiniHistoryChart title="趋势分变化" points={latestPoints} metric="trend_score" variant="line" />
      <MiniMultiHistoryChart title="比价分变化" points={latestPoints} series={RS_COMPONENT_SERIES} />
      <MiniHistoryChart title="杠杆资金水位变化" points={latestPoints} metric="leverage_value" variant="line" />
    </aside>
  );
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="metric-cell">
      <span>{label}</span>
      <strong>{typeof value === "number" ? value.toFixed(1) : value}</strong>
    </div>
  );
}

function MiniHistoryChart({
  title,
  points,
  metric,
  variant = "dots",
}: {
  title: string;
  points: HistoryPoint[];
  metric: MiniChartMetric;
  variant?: "dots" | "line";
}) {
  const values = points.map((point) => Number(point.item[metric] ?? 0)).filter(Number.isFinite);
  const scale = buildMiniChartScale(values, { minPadding: metric === "funding_score" ? 0.4 : 2 });
  const yTicks = buildYAxisTicks(scale.min, scale.max);
  const dateTicks = buildDateTicks(points);
  const chartPoints = points.map((point, index) => {
    const x = xForIndex(index, points.length);
    const y = yForValue(Number(point.item[metric] ?? 0), scale);
    const opacity = 0.18 + ((index + 1) / Math.max(points.length, 1)) * 0.82;
    return { date: point.date, x, y, opacity };
  });
  const pathData = chartPoints.map((point, index) => `${index === 0 ? "M" : "L"} ${point.x} ${point.y}`).join(" ");
  return (
    <section className="mini-chart">
      <h2>{title}</h2>
      <svg viewBox={`0 0 ${MINI_CHART_WIDTH} ${MINI_CHART_HEIGHT}`} role="img" aria-label={title}>
        <MiniChartAxes scale={scale} yTicks={yTicks} dateTicks={dateTicks} />
        {variant === "line" ? (
          <path className="mini-chart-path" d={pathData} />
        ) : (
          chartPoints.map((point) => (
            <circle key={`${point.date}-${metric}`} cx={point.x} cy={point.y} r={2.6} opacity={point.opacity} />
          ))
        )}
      </svg>
    </section>
  );
}

function MiniMultiHistoryChart({ title, points, series }: { title: string; points: HistoryPoint[]; series: MiniChartSeries[] }) {
  const values = points.flatMap((point) =>
    series.map((item) => Number(point.item[item.metric] ?? 0)).filter(Number.isFinite),
  );
  const scale = buildMiniChartScale(values, { forcedValues: RS_THRESHOLD_VALUES, minPadding: 2 });
  const yTicks = buildYAxisTicks(scale.min, scale.max, RS_THRESHOLD_VALUES);
  const dateTicks = buildDateTicks(points);
  return (
    <section className="mini-chart">
      <h2>{title}</h2>
      <div className="mini-chart-legend">
        {series.map((item) => (
          <span key={item.metric}>
            <i className="mini-chart-swatch" style={{ backgroundColor: item.color }} aria-hidden="true" />
            {item.label}
          </span>
        ))}
      </div>
      <svg viewBox={`0 0 ${MINI_CHART_WIDTH} ${MINI_CHART_HEIGHT}`} role="img" aria-label={title}>
        <MiniChartAxes scale={scale} yTicks={yTicks} dateTicks={dateTicks} />
        {RS_THRESHOLD_VALUES.map((value) => (
          <line
            key={`rs-threshold-${value}`}
            className={`mini-chart-threshold${value === 100 ? " is-baseline" : ""}`}
            x1={MINI_CHART_PLOT.left}
            y1={yForValue(value, scale)}
            x2={MINI_CHART_WIDTH - MINI_CHART_PLOT.right}
            y2={yForValue(value, scale)}
          />
        ))}
        {series.map((item) => {
          const pathData = points
            .map((point, index) => {
              const value = Number(point.item[item.metric] ?? 0);
              const x = xForIndex(index, points.length);
              const y = yForValue(value, scale);
              return `${index === 0 ? "M" : "L"} ${x} ${y}`;
            })
            .join(" ");
          return <path key={item.metric} className="mini-chart-path" d={pathData} style={{ stroke: item.color }} />;
        })}
      </svg>
    </section>
  );
}

function MiniChartAxes({
  scale,
  yTicks,
  dateTicks,
}: {
  scale: MiniChartScale;
  yTicks: number[];
  dateTicks: MiniDateTick[];
}) {
  const xAxisY = MINI_CHART_HEIGHT - MINI_CHART_PLOT.bottom;
  const xStart = scale.plotLeft;
  const xEnd = scale.plotRight;
  return (
    <g aria-hidden="true">
      {yTicks.map((value) => {
        const y = yForValue(value, scale);
        return (
          <g key={`y-${value}`}>
            <line className="mini-chart-grid" x1={xStart} y1={y} x2={xEnd} y2={y} />
            <text className="mini-chart-axis-label mini-chart-y-label" x={xStart - 7} y={y}>
              {formatAxisNumber(value)}
            </text>
          </g>
        );
      })}
      <line className="mini-chart-axis" x1={xStart} y1={scale.plotTop} x2={xStart} y2={xAxisY} />
      <line className="mini-chart-axis" x1={xStart} y1={xAxisY} x2={xEnd} y2={xAxisY} />
      {dateTicks.map((tick) => (
        <g key={`x-${tick.date}-${tick.index}`}>
          <line className="mini-chart-tick" x1={tick.x} y1={xAxisY} x2={tick.x} y2={xAxisY + 4} />
          <text className="mini-chart-axis-label mini-chart-x-label" x={tick.x} y={xAxisY + 7} textAnchor={tick.anchor}>
            {tick.label}
          </text>
        </g>
      ))}
    </g>
  );
}

type MiniChartScale = {
  min: number;
  max: number;
  span: number;
  plotTop: number;
  plotBottom: number;
  plotLeft: number;
  plotRight: number;
};
type MiniDateTick = { date: string; index: number; x: number; label: string; anchor: "start" | "middle" | "end" };

function buildMiniChartScale(values: number[], options: { forcedValues?: number[]; minPadding?: number } = {}): MiniChartScale {
  const finiteValues = values.filter(Number.isFinite);
  const forcedValues = (options.forcedValues ?? []).filter(Number.isFinite);
  const allValues = [...finiteValues, ...forcedValues];
  let rawMin = allValues.length ? Math.min(...allValues) : 0;
  let rawMax = allValues.length ? Math.max(...allValues) : 1;
  if (rawMin === rawMax) {
    rawMin -= 1;
    rawMax += 1;
  }
  const range = rawMax - rawMin;
  const padding = Math.max(range * 0.14, options.minPadding ?? 2);
  const min = rawMin - padding;
  const max = rawMax + padding;
  return {
    min,
    max,
    span: Math.max(max - min, 1),
    plotTop: MINI_CHART_PLOT.top,
    plotBottom: MINI_CHART_HEIGHT - MINI_CHART_PLOT.bottom,
    plotLeft: MINI_CHART_PLOT.left,
    plotRight: MINI_CHART_WIDTH - MINI_CHART_PLOT.right,
  };
}

function buildYAxisTicks(min: number, max: number, forcedTicks: number[] = []) {
  const niceTicks = buildNiceTicks(min, max, 4);
  return [...new Set([...niceTicks, ...forcedTicks.filter((value) => value >= min && value <= max)])].sort((a, b) => a - b);
}

function buildNiceTicks(min: number, max: number, preferredCount: number) {
  const span = max - min;
  if (!Number.isFinite(span) || span <= 0) return [min];
  const step = niceStep(span / Math.max(preferredCount - 1, 1));
  const start = Math.ceil(min / step) * step;
  const end = Math.floor(max / step) * step;
  const ticks: number[] = [];
  for (let value = start; value <= end + step * 0.5; value += step) {
    ticks.push(roundTick(value));
  }
  if (ticks.length >= 2) return ticks;
  return [roundTick(min), roundTick(max)];
}

function niceStep(value: number) {
  const exponent = Math.floor(Math.log10(value));
  const magnitude = 10 ** exponent;
  const fraction = value / magnitude;
  if (fraction <= 1) return magnitude;
  if (fraction <= 2) return 2 * magnitude;
  if (fraction <= 5) return 5 * magnitude;
  return 10 * magnitude;
}

function roundTick(value: number) {
  return Number(value.toFixed(6));
}

function buildDateTicks(points: HistoryPoint[], maxTicks = 5): MiniDateTick[] {
  if (!points.length) return [];
  const tickCount = Math.min(maxTicks, points.length);
  if (tickCount === 1) {
    return [
      {
        date: points[0].date,
        index: 0,
        x: xForIndex(0, points.length),
        label: formatMiniDate(points[0].date),
        anchor: "middle",
      },
    ];
  }
  const indexes = Array.from({ length: tickCount }, (_, index) => Math.round((index / (tickCount - 1)) * (points.length - 1)));
  return [...new Set(indexes)].map((index) => {
    const point = points[index];
    return {
      date: point.date,
      index,
      x: xForIndex(index, points.length),
      label: formatMiniDate(point.date),
      anchor: index === 0 ? "start" : index === points.length - 1 ? "end" : "middle",
    };
  });
}

function formatMiniDate(date: string) {
  const match = date.match(/^\d{4}-(\d{2})-(\d{2})$/);
  return match ? `${match[1]}-${match[2]}` : date;
}

function formatAxisNumber(value: number) {
  if (Math.abs(value) >= 100 || Number.isInteger(value)) return value.toFixed(0);
  if (Math.abs(value) >= 10) return value.toFixed(1);
  return value.toFixed(2);
}

function xForIndex(index: number, total: number) {
  if (total <= 1) return (MINI_CHART_PLOT.left + MINI_CHART_WIDTH - MINI_CHART_PLOT.right) / 2;
  return MINI_CHART_PLOT.left + (index / (total - 1)) * (MINI_CHART_WIDTH - MINI_CHART_PLOT.left - MINI_CHART_PLOT.right);
}

function yForValue(value: number, scale: MiniChartScale) {
  return scale.plotBottom - ((value - scale.min) / scale.span) * (scale.plotBottom - scale.plotTop);
}

function startPanelResize(
  event: ReactPointerEvent<HTMLButtonElement>,
  startWidth: number,
  setWidth: (value: number) => void,
) {
  event.preventDefault();
  const startX = event.clientX;
  const maxWidth = Math.max(340, Math.min(760, window.innerWidth - 460));
  const onMove = (moveEvent: PointerEvent) => {
    setWidth(clampNumber(startWidth + startX - moveEvent.clientX, 300, maxWidth));
  };
  const onUp = () => {
    document.body.classList.remove("is-resizing-panel");
    window.removeEventListener("pointermove", onMove);
    window.removeEventListener("pointerup", onUp);
  };
  document.body.classList.add("is-resizing-panel");
  window.addEventListener("pointermove", onMove);
  window.addEventListener("pointerup", onUp);
}

function clampNumber(value: number, min: number, max: number) {
  return Math.max(min, Math.min(value, max));
}

function formatTrendValue(value?: string | null) {
  const normalized = String(value ?? "").trim().toLowerCase();
  if (normalized === "up") return "上行";
  if (normalized === "down") return "下行";
  if (normalized === "neutral") return "无趋势";
  return value || "-";
}

function formatClosePosition(value?: number | null) {
  if (value == null || !Number.isFinite(value)) return "-";
  return value.toFixed(4);
}
