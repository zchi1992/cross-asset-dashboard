import { memo, useEffect, useMemo, useRef } from "react";
import * as echarts from "echarts";
import type { ECharts, EChartsOption } from "echarts";
import type { SnapshotItem } from "../services/contracts";
import { assetKey, trajectoryForAssetKey } from "../utils/filtering";

const DENSE_ASSET_THRESHOLD = 250;
const DENSE_SYMBOL_SIZE = 10;
const NORMAL_SYMBOL_SIZE = 16;

type Props = {
  items: SnapshotItem[];
  frames: Record<string, SnapshotItem[]>;
  dates: string[];
  currentIndex: number;
  selectedSymbol: string | null;
  scoreRanges: {
    rs_score: number[];
    funding_score: number[];
    trend_score: number[];
  };
  attentionTags: Map<string, string>;
  onSelect: (symbol: string) => void;
  onClear: () => void;
};

export const CrossAssetScatter = memo(function CrossAssetScatter({
  items,
  frames,
  dates,
  currentIndex,
  selectedSymbol,
  scoreRanges,
  attentionTags,
  onSelect,
  onClear,
}: Props) {
  const elementRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<ECharts | null>(null);
  const yRange = scoreRanges.funding_score;
  const isDense = items.length >= DENSE_ASSET_THRESHOLD;

  const assetData = useMemo(() => {
    return items.map((item) => ({
      name: assetKey(item),
      value: [item.rs_score, clamp(item.funding_score, yRange), item.trend_score],
      label: {
        show: assetKey(item) !== selectedSymbol && attentionTags.has(assetKey(item)),
        color: "#ffc247",
        fontSize: 12,
        fontWeight: 700,
      },
      itemStyle: {
        opacity: selectedSymbol && assetKey(item) !== selectedSymbol ? 0.24 : 1,
        borderColor: "#f4f4ee",
        borderWidth: isDense ? 1 : 1.8,
        shadowBlur: isDense ? 0 : 12,
        shadowColor: trendGlow(item.trend_score),
      },
    }));
  }, [attentionTags, isDense, items, selectedSymbol, yRange]);

  const itemBySymbol = useMemo(() => new Map(items.map((item) => [assetKey(item), item])), [items]);

  const baseOption = useMemo<EChartsOption>(() => {
    const xRange = scoreRanges.rs_score;

    return {
      backgroundColor: "#000000",
      animation: !isDense,
      animationDurationUpdate: isDense ? 0 : 140,
      grid: { left: 66, right: 122, top: 34, bottom: 58 },
      toolbox: {
        right: 18,
        top: 2,
        itemSize: 15,
        iconStyle: { borderColor: "#e7a23a" },
        emphasis: { iconStyle: { borderColor: "#ffffff" } },
        feature: {
          dataZoom: {
            yAxisIndex: "none",
            title: { zoom: "Zoom", back: "Back" },
          },
          restore: { title: "Reset Zoom" },
        },
      },
      dataZoom: [
        {
          type: "inside",
          xAxisIndex: 0,
          filterMode: "filter",
          zoomOnMouseWheel: true,
          moveOnMouseMove: true,
          throttle: isDense ? 80 : 30,
        },
        {
          type: "inside",
          yAxisIndex: 0,
          filterMode: "filter",
          zoomOnMouseWheel: true,
          moveOnMouseMove: true,
          throttle: isDense ? 80 : 30,
        },
      ],
      tooltip: {
        trigger: "item",
        triggerOn: isDense ? "click" : "mousemove|click",
        backgroundColor: "#050505",
        borderColor: "#b37a22",
        padding: [8, 10],
        textStyle: { color: "#f1f3f0", fontSize: 12, fontFamily: "Inter, system-ui, sans-serif" },
        formatter: (params) => {
          const point = Array.isArray(params) ? params[0] : params;
          const key = String(point.name ?? "");
          const item = itemBySymbol.get(key);
          if (!item) return "";
          return [
            `<b>${item.symbol}</b> ${item.asset_name}`,
            `Asset Class: ${item.asset_class}`,
            `Trend Score: ${item.trend_score.toFixed(2)}`,
            `RS Score: ${item.rs_score.toFixed(2)}`,
            `RS State: ${item.rs_state}`,
            `Funding Score: ${item.funding_score.toFixed(2)}`,
            `Funding State: ${item.funding_state}`,
          ].join("<br/>");
        },
      },
      xAxis: {
        name: "Relative Strength Score",
        nameLocation: "middle",
        nameGap: 34,
        min: xRange[0],
        max: xRange[1],
        splitNumber: 8,
        splitLine: { lineStyle: { color: "#46535a", type: "dotted", opacity: 0.72 } },
        axisLine: { lineStyle: { color: "#b9c5c9" } },
        axisTick: { lineStyle: { color: "#b9c5c9" } },
        axisLabel: { color: "#d8dde0", fontSize: 11 },
        nameTextStyle: { color: "#e8a33a", fontSize: 12 },
      },
      yAxis: {
        name: "Funding Score",
        min: yRange[0],
        max: yRange[1],
        splitNumber: 8,
        splitLine: { lineStyle: { color: "#46535a", type: "dotted", opacity: 0.72 } },
        axisLine: { lineStyle: { color: "#b9c5c9" } },
        axisTick: { lineStyle: { color: "#b9c5c9" } },
        axisLabel: { color: "#d8dde0", fontSize: 11 },
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
            borderColor: "#f4f4ee",
            borderWidth: isDense ? 1 : 1.8,
            shadowBlur: isDense ? 0 : 12,
            shadowColor: "rgba(255, 176, 0, 0.48)",
          },
          label: {
            show: false,
            formatter: (params) => {
              const symbol = String(params.name ?? "");
              const item = itemBySymbol.get(symbol);
              const label = item?.symbol ?? symbol;
              const tag = attentionTags.get(symbol);
              return tag ? `${label} ${tag}` : label;
            },
            color: "#ffc247",
            position: "top",
            distance: 7,
            fontSize: 12,
            fontWeight: 700,
            textBorderColor: "#000000",
            textBorderWidth: 1,
            textShadowBlur: 7,
            textShadowColor: "#000000",
          },
          data: assetData,
          encode: { x: 0, y: 1 },
          labelLayout: { hideOverlap: true },
          emphasis: {
            focus: "self",
            scale: !isDense,
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
  }, [assetData, attentionTags, isDense, itemBySymbol, scoreRanges.rs_score, yRange]);

  const selectedTrajectory = useMemo(
    () => (selectedSymbol && dates.length ? trajectoryForAssetKey(frames, dates, currentIndex, selectedSymbol) : []),
    [currentIndex, dates, frames, selectedSymbol],
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
          data: selectedTrajectory.map(({ date, item }) => [item.rs_score, clamp(item.funding_score, yRange), date]),
          symbol: "circle",
          symbolSize: (_value, params) => (params.dataIndex === selectedTrajectory.length - 1 ? 15 : 7),
          lineStyle: { color: "#ffcc45", width: 2.4, opacity: selectedTrajectory.length ? 0.96 : 0 },
          itemStyle: { color: "#ffcc45", borderColor: "#ffffff", borderWidth: 1.5, shadowBlur: 8, shadowColor: "#ffcc45" },
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
                  name: assetKey(selectedItem),
                  value: [selectedItem.rs_score, clamp(selectedItem.funding_score, yRange), selectedItem.trend_score],
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
            borderColor: "#fff27a",
            borderWidth: 3,
            shadowBlur: 18,
            shadowColor: "#ffcc45",
          },
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
  }, [currentIndex, dates, frames, itemBySymbol, selectedSymbol, selectedTrajectory, yRange]);

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
    chartRef.current?.setOption(baseOption, { notMerge: false, lazyUpdate: true });
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
    const blankHandler = (event: { target?: unknown }) => {
      if (!event.target) onClear();
    };
    chart.on("click", clickHandler);
    chart.getZr().on("click", blankHandler);
    return () => {
      chart.off("click", clickHandler);
      chart.getZr().off("click", blankHandler);
    };
  }, [onClear, onSelect]);

  return <div ref={elementRef} className="scatter-chart" />;
});

function trendColor(score: number) {
  if (score >= 40) return "#ffb000";
  if (score <= -40) return "#2f86ff";
  return "#d6d2c5";
}

function trendGlow(score: number) {
  if (score >= 40) return "rgba(255, 176, 0, 0.72)";
  if (score <= -40) return "rgba(47, 134, 255, 0.72)";
  return "rgba(255, 255, 255, 0.45)";
}

function clamp(value: number, range: number[]) {
  return Math.max(range[0], Math.min(value, range[1]));
}
