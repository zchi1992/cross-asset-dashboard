import { memo, useEffect, useState, useMemo } from "react";
import type { CSSProperties, PointerEvent as ReactPointerEvent } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchAssets, fetchConfig, fetchDates, fetchPlayback } from "./services/api";
import type { FundingState, RelativeStrengthState, SnapshotItem } from "./services/contracts";
import { CrossAssetScatter } from "./components/CrossAssetScatter";
import { useFilterStore } from "./stores/filterStore";
import { usePlaybackStore } from "./stores/playbackStore";
import { useSelectionStore } from "./stores/selectionStore";
import { assetKeyWithCollisions, duplicateAssetBaseKeys, filterItems, matchesSearch } from "./utils/filtering";

const RS_COMPONENT_SERIES: MiniChartSeries[] = [
  { metric: "early_reversal", label: "early_reversal", color: "var(--rs-early-reversal)" },
  { metric: "strength_momentum", label: "strength_momentum", color: "var(--rs-strength-momentum)" },
  { metric: "relative_strength", label: "relative_strength", color: "var(--rs-relative-strength)" },
];

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
  const [detailPanelWidth, setDetailPanelWidth] = useState(360);

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
        if (match) selectSymbol(assetKeyWithCollisions(match, duplicateAssetKeys));
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  });

  const currentDate = availableDates[currentIndex] ?? "";
  const frames = playbackQuery.data?.frames ?? {};
  const duplicateAssetKeys = useMemo(() => duplicateAssetBaseKeys(frames), [frames]);
  const currentItems = frames[currentDate] ?? [];
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
        : filterItems(currentItems, assetClass, fundingStates, rsStates),
    [assetClass, currentItems, fundingStates, hasSearch, rsStates, searchText],
  );
  const selectedCurrentItem = selectedSymbol ? currentItemBySymbol.get(selectedSymbol) ?? null : null;
  const chartItems = filteredItems;
  const attentionTags = useMemo(
    () => buildAttentionTags(currentItems, frames, availableDates, currentIndex, duplicateAssetKeys),
    [availableDates, currentIndex, currentItems, duplicateAssetKeys, frames],
  );
  const selectedHistory = useMemo(
    () =>
      selectedSymbol
        ? (historyBySymbol.get(selectedSymbol) ?? []).filter((entry) => entry.index <= currentIndex)
        : [],
    [currentIndex, historyBySymbol, selectedSymbol],
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
        <SearchControl value={searchText} onCommit={setSearchText} />
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
              scoreRanges={config.score_ranges}
              attentionTags={attentionTags}
              onSelect={selectSymbol}
              onClear={clearSelection}
            />
            <div className="trend-legend" aria-hidden="true">
              <span>Weak</span>
              <div />
              <span>Strong</span>
            </div>
          </div>
          {selectedCurrentItem && (
            <>
              <button
                className="panel-resizer"
                aria-label="Resize detail panel"
                onPointerDown={(event) => startPanelResize(event, detailPanelWidth, setDetailPanelWidth)}
              />
              <AssetDetailPanel
                item={selectedCurrentItem}
                history={selectedHistory}
                tags={classifyAsset(selectedCurrentItem)}
                onClose={clearSelection}
              />
            </>
          )}
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
  return value
    .split(/[_-]/)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
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

function buildAttentionTags(
  currentItems: SnapshotItem[],
  frames: Record<string, SnapshotItem[]>,
  dates: string[],
  currentIndex: number,
  duplicateAssetKeys: Set<string>,
) {
  const previousDate = dates[currentIndex - 1];
  const previousItems = previousDate ? frames[previousDate] ?? [] : [];
  const previousBySymbol = new Map(previousItems.map((item) => [assetKeyWithCollisions(item, duplicateAssetKeys), item]));
  const tags = new Map<string, string>();

  const strongest = [...currentItems]
    .sort((a, b) => compositeLongScore(b) - compositeLongScore(a))
    .slice(0, 5);
  strongest.forEach((item) => tags.set(assetKeyWithCollisions(item, duplicateAssetKeys), "三强"));

  const improving = currentItems
    .map((item) => ({ item, previous: previousBySymbol.get(assetKeyWithCollisions(item, duplicateAssetKeys)) }))
    .filter(({ item, previous }) => {
      return (
        previous?.funding_state === "Deleveraging" &&
        item.funding_state === "Leveraging" &&
        ["Lag", "Weakening"].includes(previous.rs_state) &&
        item.rs_state === "Improving"
      );
    })
    .sort((a, b) => transitionScore(b.item, b.previous) - transitionScore(a.item, a.previous))
    .slice(0, 5);
  improving.forEach(({ item }) => {
    const key = assetKeyWithCollisions(item, duplicateAssetKeys);
    tags.set(key, tags.has(key) ? `${tags.get(key)} 转强` : "转强");
  });

  const deteriorating = currentItems
    .map((item) => ({ item, previous: previousBySymbol.get(assetKeyWithCollisions(item, duplicateAssetKeys)) }))
    .filter(({ item, previous }) => {
      return (
        previous?.funding_state === "Leveraging" &&
        item.funding_state === "Deleveraging" &&
        ["Improving", "Lead"].includes(previous.rs_state) &&
        ["Lag", "Weakening"].includes(item.rs_state)
      );
    })
    .sort((a, b) => transitionScore(b.previous, b.item) - transitionScore(a.previous, a.item))
    .slice(0, 5);
  deteriorating.forEach(({ item }) => {
    const key = assetKeyWithCollisions(item, duplicateAssetKeys);
    tags.set(key, tags.has(key) ? `${tags.get(key)} 转弱` : "转弱");
  });

  return tags;
}

function compositeLongScore(item: SnapshotItem) {
  return item.trend_score + item.rs_score + item.leverage_velocity_score;
}

function transitionScore(current?: SnapshotItem, previous?: SnapshotItem) {
  if (!current || !previous) return -Infinity;
  return (
    Math.abs(current.funding_score - previous.funding_score) +
    Math.abs(current.leverage_velocity_score - previous.leverage_velocity_score) +
    Math.abs(current.rs_score - previous.rs_score) +
    Math.abs(current.trend_score - previous.trend_score) * 0.5 +
    Math.abs(rsRank(current.rs_state) - rsRank(previous.rs_state)) * 20
  );
}

function rsRank(state: RelativeStrengthState) {
  return { Lag: 0, Weakening: 1, Improving: 2, Lead: 3 }[state] ?? 0;
}

function classifyAsset(item: SnapshotItem) {
  const tags: string[] = [];
  if (item.trend_score >= 70 && item.rs_score >= 70 && item.leverage_velocity_score >= 70) tags.push("高置信多头");
  if (item.trend_score <= -70 && item.rs_score <= -70 && item.leverage_velocity_score <= -70) tags.push("高置信空头");
  if (item.leverage_velocity_score >= 70) tags.push("快速加杠杆");
  if (item.leverage_velocity_score <= -70) tags.push("快速去杠杆");
  if (item.funding_state === "Leveraging") tags.push("资金加杠杆");
  if (item.funding_state === "Deleveraging") tags.push("资金去杠杆");
  if (item.rs_state === "Lead") tags.push("比价领先");
  if (item.rs_state === "Improving") tags.push("比价改善");
  if (!tags.length) tags.push("观察");
  return tags;
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
      <div className="tag-row">
        {tags.map((tag) => (
          <span key={tag}>{tag}</span>
        ))}
      </div>
      <div className="detail-grid">
        <Metric label="趋势分" value={item.trend_score} />
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
  const rawMin = values.length ? Math.min(...values) : 0;
  const rawMax = values.length ? Math.max(...values) : 1;
  const range = rawMax - rawMin;
  const padding = Math.max(range * 0.16, metric === "funding_score" ? 0.4 : 2);
  const min = rawMin - padding;
  const max = rawMax + padding;
  const span = Math.max(max - min, 1);
  const width = 360;
  const height = 160;
  const inset = 12;
  const zeroLineY = min <= 0 && max >= 0 ? yForValue(0, min, span, height, inset) : height / 2;
  const chartPoints = points.map((point, index) => {
    const x = points.length <= 1 ? width / 2 : inset + (index / (points.length - 1)) * (width - inset * 2);
    const y = yForValue(Number(point.item[metric] ?? 0), min, span, height, inset);
    const opacity = 0.18 + ((index + 1) / Math.max(points.length, 1)) * 0.82;
    return { date: point.date, x, y, opacity };
  });
  const pathData = chartPoints.map((point, index) => `${index === 0 ? "M" : "L"} ${point.x} ${point.y}`).join(" ");
  return (
    <section className="mini-chart">
      <h2>{title}</h2>
      <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label={title}>
        <line x1={inset} y1={zeroLineY} x2={width - inset} y2={zeroLineY} />
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
  const rawMin = values.length ? Math.min(...values) : 0;
  const rawMax = values.length ? Math.max(...values) : 1;
  const range = rawMax - rawMin;
  const padding = Math.max(range * 0.16, 2);
  const min = rawMin - padding;
  const max = rawMax + padding;
  const span = Math.max(max - min, 1);
  const width = 360;
  const height = 160;
  const inset = 12;
  const zeroLineY = min <= 0 && max >= 0 ? yForValue(0, min, span, height, inset) : height / 2;
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
      <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label={title}>
        <line x1={inset} y1={zeroLineY} x2={width - inset} y2={zeroLineY} />
        {series.map((item) => {
          const pathData = points
            .map((point, index) => {
            const value = Number(point.item[item.metric] ?? 0);
            const x = points.length <= 1 ? width / 2 : inset + (index / (points.length - 1)) * (width - inset * 2);
            const y = yForValue(value, min, span, height, inset);
              return `${index === 0 ? "M" : "L"} ${x} ${y}`;
            })
            .join(" ");
          return <path key={item.metric} className="mini-chart-path" d={pathData} style={{ stroke: item.color }} />;
        })}
      </svg>
    </section>
  );
}

function yForValue(value: number, min: number, span: number, height: number, inset: number) {
  const plotHeight = height - inset * 2;
  return height - inset - ((value - min) / span) * plotHeight;
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
