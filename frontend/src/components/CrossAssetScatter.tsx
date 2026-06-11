import { useEffect, useMemo, useRef } from "react";
import * as echarts from "echarts";
import type { ECharts, EChartsOption } from "echarts";
import type { SnapshotItem } from "../services/contracts";
import { matchesSearch, trajectoryForSymbol } from "../utils/filtering";

type Props = {
  items: SnapshotItem[];
  frames: Record<string, SnapshotItem[]>;
  dates: string[];
  currentIndex: number;
  searchText: string;
  selectedSymbol: string | null;
  scoreRanges: {
    rs_score: number[];
    funding_score: number[];
    trend_score: number[];
  };
  onSelect: (symbol: string) => void;
  onClear: () => void;
};

export function CrossAssetScatter({
  items,
  frames,
  dates,
  currentIndex,
  searchText,
  selectedSymbol,
  scoreRanges,
  onSelect,
  onClear,
}: Props) {
  const elementRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<ECharts | null>(null);

  const option = useMemo<EChartsOption>(() => {
    const selectedTrajectory =
      selectedSymbol && dates.length ? trajectoryForSymbol(frames, dates, currentIndex, selectedSymbol) : [];
    const hasSearch = Boolean(searchText.trim());
    const itemBySymbol = new Map(items.map((item) => [item.symbol, item]));
    const xRange = scoreRanges.rs_score;
    const yRange = scoreRanges.funding_score;

    return {
      backgroundColor: "#000000",
      animationDurationUpdate: 140,
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
        { type: "inside", xAxisIndex: 0, filterMode: "none", zoomOnMouseWheel: true, moveOnMouseMove: true },
        { type: "inside", yAxisIndex: 0, filterMode: "none", zoomOnMouseWheel: true, moveOnMouseMove: true },
      ],
      tooltip: {
        trigger: "item",
        backgroundColor: "#050505",
        borderColor: "#b37a22",
        padding: [8, 10],
        textStyle: { color: "#f1f3f0", fontSize: 12, fontFamily: "Inter, system-ui, sans-serif" },
        formatter: (params) => {
          const point = Array.isArray(params) ? params[0] : params;
          const symbol = String(point.name ?? "");
          const item = itemBySymbol.get(symbol);
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
          id: "trajectory",
          type: "line",
          data: selectedTrajectory.map(({ date, item }) => [item.rs_score, clamp(item.funding_score, yRange), date]),
          symbol: "circle",
          symbolSize: (value, params) => (params.dataIndex === selectedTrajectory.length - 1 ? 15 : 7),
          lineStyle: { color: "#ffcc45", width: 2.4, opacity: 0.96 },
          itemStyle: { color: "#ffcc45", borderColor: "#ffffff", borderWidth: 1.5, shadowBlur: 8, shadowColor: "#ffcc45" },
          emphasis: { disabled: true },
          tooltip: { show: false },
          z: 2,
        },
        {
          id: "assets",
          type: "scatter",
          symbol: "circle",
          symbolSize: (_value, params) => {
            const name = String(params.name ?? "");
            if (name === selectedSymbol) return 24;
            const item = itemBySymbol.get(name);
            if (item && hasSearch && matchesSearch(item, searchText)) return 20;
            return 16;
          },
          itemStyle: {
            color: (params) => {
              const value = Array.isArray(params.value) ? params.value : [];
              return trendColor(Number(value[2] ?? 0));
            },
            opacity: 1,
            borderColor: "#f4f4ee",
            borderWidth: 1.8,
            shadowBlur: 12,
            shadowColor: "rgba(255, 176, 0, 0.48)",
          },
          label: {
            show: true,
            formatter: "{b}",
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
          data: items.map((item) => {
            const isSelected = item.symbol === selectedSymbol;
            const isDimmedBySelection = Boolean(selectedSymbol && !isSelected);
            const isDimmedBySearch = hasSearch && !matchesSearch(item, searchText);
            return {
              name: item.symbol,
              value: [item.rs_score, clamp(item.funding_score, yRange), item.trend_score],
              label: {
                color: isSelected ? "#fff27a" : isDimmedBySelection ? "rgba(255, 194, 71, 0.18)" : "#ffc247",
                fontSize: isSelected ? 14 : 12,
                fontWeight: isSelected ? 800 : 700,
              },
              itemStyle: {
                opacity:
                  isDimmedBySearch ? 0.18 : isDimmedBySelection ? 0.16 : 1,
                borderColor: isSelected ? "#fff27a" : isDimmedBySelection ? "rgba(244,244,238,0.24)" : "#f4f4ee",
                borderWidth: isSelected ? 3 : 1.8,
                shadowBlur: isSelected ? 16 : isDimmedBySelection ? 2 : 12,
                shadowColor: isSelected ? "#ffcc45" : isDimmedBySelection ? "rgba(255,255,255,0.14)" : trendGlow(item.trend_score),
              },
            };
          }),
          encode: { x: 0, y: 1 },
          labelLayout: { hideOverlap: true },
          emphasis: {
            focus: "self",
            scale: true,
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
  }, [currentIndex, dates, frames, items, scoreRanges, searchText, selectedSymbol]);

  useEffect(() => {
    if (!elementRef.current) return;
    chartRef.current = echarts.init(elementRef.current, "dark");
    const resize = () => chartRef.current?.resize();
    window.addEventListener("resize", resize);
    return () => {
      window.removeEventListener("resize", resize);
      chartRef.current?.dispose();
      chartRef.current = null;
    };
  }, []);

  useEffect(() => {
    chartRef.current?.setOption(option, { notMerge: false, lazyUpdate: true });
  }, [option]);

  useEffect(() => {
    const chart = chartRef.current;
    if (!chart) return;
    const clickHandler = (params: echarts.ECElementEvent) => {
      if (params.seriesId === "assets") {
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
}

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
