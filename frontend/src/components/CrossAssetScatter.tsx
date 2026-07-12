import { memo, useEffect, useMemo, useRef } from "react";
import * as echarts from "echarts";
import type { ECharts, EChartsOption } from "echarts";
import type { SnapshotItem } from "../services/contracts";
import { assetKeyWithCollisions, trajectoryForAssetKey } from "../utils/filtering";
import { opportunityAssetKey, type OpportunityMarker } from "../utils/opportunities";

const DENSE_ASSET_THRESHOLD = 250;
const DENSE_SYMBOL_SIZE = 10;
const NORMAL_SYMBOL_SIZE = 16;
const GRID = { left: 66, right: 122, top: 34, bottom: 58 };
const TOOLBOX_RIGHT = 112;
const X_RANGE: [number, number] = [70, 140];
const Y_RANGE: [number, number] = [0, 100];
const LEVERAGING_BORDER = "#ff5d5d";
const DELEVERAGING_BORDER = "transparent";

type Props = {
  items: SnapshotItem[];
  frames: Record<string, SnapshotItem[]>;
  dates: string[];
  currentIndex: number;
  selectedSymbol: string | null;
  duplicateAssetKeys: Set<string>;
  opportunityMarkers: Map<string, OpportunityMarker>;
  onSelect: (symbol: string) => void;
  onClear: () => void;
};

export const CrossAssetScatter = memo(function CrossAssetScatter({
  items,
  frames,
  dates,
  currentIndex,
  selectedSymbol,
  duplicateAssetKeys,
  opportunityMarkers,
  onSelect,
}: Props) {
  const elementRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<ECharts | null>(null);
  const isDense = items.length >= DENSE_ASSET_THRESHOLD;

  const assetData = useMemo(() => {
    const visibleItems = selectedSymbol
      ? items.filter((item) => assetKeyWithCollisions(item, duplicateAssetKeys) === selectedSymbol)
      : items;
    return visibleItems.map((item) => ({
      name: assetKeyWithCollisions(item, duplicateAssetKeys),
      value: [item.rs_score, clamp(item.funding_score, Y_RANGE), item.trend_score],
      label: {
        show:
          assetKeyWithCollisions(item, duplicateAssetKeys) !== selectedSymbol &&
          opportunityMarkers.has(opportunityAssetKey(item)),
      },
      itemStyle: {
        opacity: selectedSymbol && assetKeyWithCollisions(item, duplicateAssetKeys) !== selectedSymbol ? 0.24 : 1,
        borderColor: fundingBorder(item.funding_state),
        borderWidth: isDense ? 1.4 : 2,
      },
    }));
  }, [duplicateAssetKeys, isDense, items, opportunityMarkers, selectedSymbol]);

  const itemBySymbol = useMemo(
    () => new Map(items.map((item) => [assetKeyWithCollisions(item, duplicateAssetKeys), item])),
    [duplicateAssetKeys, items],
  );

  const baseOption = useMemo<EChartsOption>(() => {
    return {
      backgroundColor: "#000000",
      animation: false,
      animationDurationUpdate: 0,
      grid: GRID,
      toolbox: {
        right: TOOLBOX_RIGHT,
        top: 2,
        itemSize: 15,
        iconStyle: { borderColor: "#e7a23a" },
        emphasis: { iconStyle: { borderColor: "#ffffff" } },
        feature: {
          dataZoom: {
            title: { zoom: "", back: "" },
          },
          myResetZoom: {
            title: "",
            icon: "M3.8,33.4 M47,18.9h9.8V8.7 M56.3,20.1 C52.1,9,40.5,0.6,26.8,2.1C12.6,3.7,1.6,16.2,2.1,30.6 M13,41.1H3.1v10.2 M3.7,39.9c4.2,11.1,15.8,19.5,29.5,18 c14.2-1.6,25.2-14.1,24.7-28.5",
            onclick: () => {
              chartRef.current?.dispatchAction({
                type: "dataZoom",
                batch: [
                  { dataZoomId: "xZoom", start: 0, end: 100 },
                  { dataZoomId: "yZoom", start: 0, end: 100 },
                ],
              });
            },
          },
        },
      },
      dataZoom: [
        {
          id: "xZoom",
          type: "inside",
          xAxisIndex: 0,
          filterMode: "none",
          zoomOnMouseWheel: true,
          moveOnMouseMove: true,
          moveOnMouseWheel: false,
          minValueSpan: 2,
        },
        {
          id: "yZoom",
          type: "inside",
          yAxisIndex: 0,
          filterMode: "none",
          zoomOnMouseWheel: true,
          moveOnMouseMove: true,
          moveOnMouseWheel: false,
          minValueSpan: 2,
        },
      ],
      tooltip: {
        trigger: "item",
        triggerOn: "mousemove|click",
        backgroundColor: "#050505",
        borderColor: "#b37a22",
        padding: [8, 10],
        textStyle: { color: "#f1f3f0", fontSize: 12, fontFamily: "Inter, system-ui, sans-serif" },
        formatter: (params) => {
          const point = Array.isArray(params) ? params[0] : params;
          const key = String(point.name ?? "");
          const item = itemBySymbol.get(key);
          if (!item) return "";
          return `<b>${item.symbol}</b> ${item.asset_name}`;
        },
      },
      xAxis: {
        name: "Relative Strength Score",
        nameLocation: "middle",
        nameGap: 34,
        min: X_RANGE[0],
        max: X_RANGE[1],
        splitNumber: 8,
        splitLine: { lineStyle: { color: "#46535a", type: "dotted", opacity: 0.72 } },
        axisLine: { lineStyle: { color: "#b9c5c9" } },
        axisTick: { lineStyle: { color: "#b9c5c9" } },
        axisLabel: { color: "#d8dde0", fontSize: 11, formatter: formatAxisLabel },
        nameTextStyle: { color: "#e8a33a", fontSize: 12 },
      },
      yAxis: {
        name: "Leverage Value",
        min: Y_RANGE[0],
        max: Y_RANGE[1],
        splitNumber: 8,
        splitLine: { lineStyle: { color: "#46535a", type: "dotted", opacity: 0.72 } },
        axisLine: { lineStyle: { color: "#b9c5c9" } },
        axisTick: { lineStyle: { color: "#b9c5c9" } },
        axisLabel: { color: "#d8dde0", fontSize: 11, formatter: formatAxisLabel },
        nameTextStyle: { color: "#e8a33a", fontSize: 12 },
      },
      series: [
        {
          id: "assets",
          type: "scatter",
          symbol: "circle",
          symbolSize: isDense ? DENSE_SYMBOL_SIZE : NORMAL_SYMBOL_SIZE,
          progressive: isDense ? 600 : 0,
          progressiveThreshold: DENSE_ASSET_THRESHOLD,
          progressiveChunkMode: "mod",
          itemStyle: {
            color: (params) => {
              const value = Array.isArray(params.value) ? params.value : [];
              return trendColor(Number(value[2] ?? 0));
            },
            opacity: 1,
            borderWidth: isDense ? 1.4 : 2,
          },
          label: {
            show: false,
            formatter: (params) => {
              const symbol = String(params.name ?? "");
              const item = itemBySymbol.get(symbol);
              if (!item) return symbol;
              return formatOpportunityLabel(item.symbol, opportunityMarkers.get(opportunityAssetKey(item)));
            },
            color: "#f1f1ec",
            position: "top",
            distance: 7,
            fontSize: 12,
            fontWeight: 700,
            textBorderColor: "#000000",
            textBorderWidth: 1,
            textShadowBlur: 7,
            textShadowColor: "#000000",
            rich: {
              strongLong: { color: "#ffbf47", fontWeight: 800 },
              candidateLong: { color: "#65d6b2", fontWeight: 800 },
            },
          },
          data: assetData,
          encode: { x: 0, y: 1 },
          labelLayout: { hideOverlap: true },
          emphasis: {
            focus: "self",
            scale: false,
            label: {
              show: true,
              color: "#ffffff",
              fontWeight: 800,
              textBorderColor: "#000000",
              textBorderWidth: 4,
            },
          },
          z: 3,
        },
      ],
    };
  }, [assetData, isDense, itemBySymbol, opportunityMarkers]);

  const selectedTrajectory = useMemo(
    () =>
      selectedSymbol && dates.length
        ? trajectoryForAssetKey(frames, dates, currentIndex, selectedSymbol, duplicateAssetKeys)
        : [],
    [currentIndex, dates, duplicateAssetKeys, frames, selectedSymbol],
  );

  const dynamicOption = useMemo<EChartsOption>(() => {
    const selectedItem =
      selectedTrajectory.length > 0
        ? selectedTrajectory[selectedTrajectory.length - 1].item
        : selectedSymbol
          ? itemBySymbol.get(selectedSymbol)
          : null;
    return {
      series: [
        {
          id: "trajectory",
          type: "line",
          data: selectedTrajectory.map(({ date, item }) => ({
            value: [item.rs_score, clamp(item.funding_score, Y_RANGE), date],
            itemStyle: { borderColor: fundingBorder(item.funding_state) },
          })),
          symbol: "circle",
          symbolSize: (_value, params) => (params.dataIndex === selectedTrajectory.length - 1 ? 15 : 7),
          lineStyle: { color: "#ffcc45", width: 2.4, opacity: selectedTrajectory.length ? 0.96 : 0 },
          itemStyle: {
            color: "#ffcc45",
            borderWidth: 1.5,
          },
          animation: false,
          emphasis: { disabled: true },
          tooltip: { show: false },
          z: 4,
        },
        {
          id: "selectedAsset",
          type: "scatter",
          symbol: "circle",
          symbolSize: 26,
          data: selectedItem
            ? [
                {
                  name: assetKeyWithCollisions(selectedItem, duplicateAssetKeys),
                  value: [selectedItem.rs_score, clamp(selectedItem.funding_score, Y_RANGE), selectedItem.trend_score],
                  label: {
                    show: true,
                    color: "#fff27a",
                    fontSize: 14,
                    fontWeight: 800,
                  },
                },
              ]
            : [],
          itemStyle: {
            color: "#ffcc45",
            borderColor: fundingBorder(selectedItem?.funding_state),
            borderWidth: 3,
          },
          animation: false,
          emphasis: { scale: false },
          label: {
            show: true,
            formatter: (params) => itemBySymbol.get(String(params.name ?? ""))?.symbol ?? String(params.name ?? ""),
            position: "top",
            distance: 8,
            textBorderColor: "#000000",
            textBorderWidth: 3,
          },
          tooltip: { show: false },
          z: 5,
        },
      ],
    };
  }, [itemBySymbol, selectedSymbol, selectedTrajectory, duplicateAssetKeys]);

  useEffect(() => {
    if (!elementRef.current) return;
    chartRef.current = echarts.init(elementRef.current, "dark", {
      renderer: "canvas",
      useDirtyRect: false,
    });
    const resize = () => chartRef.current?.resize();
    const observer = new ResizeObserver(resize);
    observer.observe(elementRef.current);
    window.addEventListener("resize", resize);
    return () => {
      observer.disconnect();
      window.removeEventListener("resize", resize);
      chartRef.current?.dispose();
      chartRef.current = null;
    };
  }, []);

  useEffect(() => {
    const chart = chartRef.current;
    if (!chart) return;
    chart.setOption(baseOption, { notMerge: false, lazyUpdate: true });
  }, [baseOption]);

  useEffect(() => {
    chartRef.current?.setOption(dynamicOption, { notMerge: false, lazyUpdate: true });
  }, [dynamicOption]);

  useEffect(() => {
    const chart = chartRef.current;
    if (!chart) return;
    const clickHandler = (params: echarts.ECElementEvent) => {
      if (params.seriesId === "assets" || params.seriesId === "selectedAsset") {
        const symbol = String(params.name ?? "");
        if (symbol) onSelect(symbol);
      }
    };
    chart.on("click", clickHandler);
    return () => {
      chart.off("click", clickHandler);
    };
  }, [onSelect]);

  return (
    <div
      ref={elementRef}
      className="scatter-chart"
      role="img"
      aria-label="Market map scatter plot. Relative Strength Score ranges from 70 to 140; Leverage Value ranges from 0 to 100. Scroll to zoom, drag to pan, or use Box Zoom."
    />
  );
});

function trendColor(score: number) {
  if (score >= 40) return "#ffb000";
  if (score <= -40) return "#2f86ff";
  return "#d6d2c5";
}

function formatOpportunityLabel(symbol: string, marker?: OpportunityMarker) {
  if (!marker) return symbol;
  const labels = [
    marker.strongLong ? "{strongLong|强势多头}" : "",
    marker.candidateLong ? "{candidateLong|候选多头}" : "",
  ].filter(Boolean);
  return `${symbol} ${labels.join(" / ")}`;
}

function fundingBorder(state: SnapshotItem["funding_state"] | undefined) {
  return state === "Leveraging" ? LEVERAGING_BORDER : DELEVERAGING_BORDER;
}

function formatAxisLabel(value: number | string) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return "";
  if (Math.abs(numeric) >= 1000) return numeric.toFixed(0);
  if (Math.abs(numeric) >= 100) return numeric.toFixed(1);
  return numeric.toFixed(1).replace(/\.0$/, "");
}

function clamp(value: number, range: readonly number[]) {
  return Math.max(range[0], Math.min(value, range[1]));
}
