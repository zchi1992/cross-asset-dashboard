import { useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import * as echarts from "echarts";
import { fetchMacroHistory, fetchMacroOverview } from "../services/api";
import type { MacroChanges, MacroCurve, MacroHistoryResponse } from "../services/contracts";

type Period = "1M" | "3M" | "1Y" | "3Y" | "5Y";
const PERIOD_DAYS: Record<Period, number> = { "1M": 31, "3M": 93, "1Y": 366, "3Y": 1096, "5Y": 1827 };

export function MacroMap({ active }: { active: boolean }) {
  const [period, setPeriod] = useState<Period>("1Y");
  const [selectedSeries, setSelectedSeries] = useState("");
  const overview = useQuery({
    queryKey: ["macro-overview"],
    queryFn: fetchMacroOverview,
    enabled: active,
    staleTime: 60_000,
    refetchInterval: active ? 300_000 : false,
  });
  const firstSeries = overview.data?.curves[0]?.factors[0]?.series_id ?? overview.data?.credit[0]?.series_id ?? "";
  useEffect(() => {
    if (!selectedSeries && firstSeries) setSelectedSeries(firstSeries);
  }, [firstSeries, selectedSeries]);
  const start = useMemo(() => {
    const asOf = overview.data?.as_of;
    if (!asOf) return undefined;
    const value = new Date(`${asOf}T00:00:00Z`);
    value.setUTCDate(value.getUTCDate() - PERIOD_DAYS[period]);
    return value.toISOString().slice(0, 10);
  }, [overview.data?.as_of, period]);
  const history = useQuery({
    queryKey: ["macro-history", selectedSeries, start],
    queryFn: () => fetchMacroHistory(selectedSeries, start),
    enabled: active && Boolean(selectedSeries),
    staleTime: 60_000,
  });

  return (
    <section className="macro-map" hidden={!active} aria-label="宏观地图">
      <header className="macro-map-header">
        <div><span>MACRO MAP</span><h1>宏观地图</h1></div>
        <p>G5 利率曲线、曲线因子与信用压力 · 各来源保留独立数据日期</p>
      </header>
      {overview.isLoading && <div className="macro-message">Loading macro indicators...</div>}
      {overview.error && <div className="macro-error">宏观数据暂不可用；Market Map 与 Opportunities 不受影响。</div>}
      {overview.data && (
        <>
          <section className="macro-source-strip" aria-label="宏观来源状态">
            <SummaryCard label="曲线市场" value={`${overview.data.curves.length}/5`} detail={`最新 ${overview.data.as_of ?? "-"}`} />
            <SummaryCard label="信用指标" value={String(overview.data.credit.length)} detail="公开宏观信用组" />
            <SummaryCard label="有效来源" value={String(overview.data.sources.filter((item) => item.status === "fresh").length)} detail={`${overview.data.sources.length} sources`} />
            <SummaryCard label="待更新/异常" value={String(overview.data.sources.filter((item) => item.status !== "fresh").length)} detail="查看每卡 as-of" />
          </section>

          <SectionTitle title="RATES / CURVES · 全球利率曲线" />
          <section className="macro-curve-grid">
            {overview.data.curves.map((curve) => <CurveCard key={curve.region} curve={curve} onSelect={setSelectedSeries} selected={selectedSeries} />)}
          </section>

          <SectionTitle title="CREDIT / STRESS · 信用与压力" />
          <section className="macro-credit-grid">
            {overview.data.credit.map((item) => (
              <button key={item.series_id} className={`macro-card macro-credit-card ${selectedSeries === item.series_id ? "selected" : ""}`} onClick={() => setSelectedSeries(item.series_id)}>
                <span className="macro-card-kicker">{item.frequency.toUpperCase()}</span>
                <strong>{item.label}</strong>
                <b>{formatValue(item.value, item.unit)}</b>
                <small>{item.observed_at} · {item.source_name}</small>
                <em className={`macro-status ${item.status}`}>{formatStatus(item.status)}</em>
                <ChangeRow changes={item.changes} unit={item.unit} />
              </button>
            ))}
          </section>

          <section className="macro-detail">
            <div className="macro-detail-toolbar">
              <div><span>HISTORY</span><strong>{history.data?.label ?? selectedSeries}</strong></div>
              <div className="macro-periods">{(["1M", "3M", "1Y", "3Y", "5Y"] as Period[]).map((value) => <button key={value} className={period === value ? "active" : ""} onClick={() => setPeriod(value)}>{value}</button>)}</div>
            </div>
            {history.error ? <div className="macro-error">历史序列加载失败</div> : <MacroHistoryChart data={history.data} />}
          </section>

          <footer className="macro-disclaimer">This product uses the FRED® API but is not endorsed or certified by the Federal Reserve Bank of St. Louis. ICE BofA top-level data is for internal use only.</footer>
        </>
      )}
    </section>
  );
}

function CurveCard({ curve, onSelect, selected }: { curve: MacroCurve; onSelect: (id: string) => void; selected: string }) {
  return <article className="macro-card macro-curve-card">
    <div className="macro-card-title"><div><span>{curve.region}</span><strong>{curve.region_name}</strong></div><small>{curve.observed_at}</small></div>
    <CurveProfile curve={curve} />
    <div className="macro-factor-grid">{curve.factors.map((factor) => <button key={factor.series_id} className={selected === factor.series_id ? "selected" : ""} onClick={() => onSelect(factor.series_id)}><span>{factor.label}</span><b>{formatValue(factor.value, factor.unit)}</b><em>{formatStatus(factor.status)}</em></button>)}</div>
    <small>{curve.curve_type} · {curve.source_name}</small>
  </article>;
}

function CurveProfile({ curve }: { curve: MacroCurve }) {
  const values = curve.points.map((point) => point.value);
  const min = Math.min(...values) - 0.1;
  const max = Math.max(...values) + 0.1;
  const coords = curve.points.map((point, index) => `${18 + index * (264 / Math.max(1, curve.points.length - 1))},${92 - ((point.value - min) / Math.max(0.01, max - min)) * 70}`).join(" ");
  return <svg className="macro-curve-profile" role="img" aria-label={`${curve.region_name} yield curve`} viewBox="0 0 300 112"><line x1="18" y1="92" x2="282" y2="92" /><polyline points={coords} />{curve.points.map((point, index) => <g key={point.tenor_years}><circle cx={18 + index * (264 / Math.max(1, curve.points.length - 1))} cy={92 - ((point.value - min) / Math.max(0.01, max - min)) * 70} r="3" /><text x={18 + index * (264 / Math.max(1, curve.points.length - 1))} y="108" textAnchor="middle">{point.tenor_years}Y</text></g>)}</svg>;
}

function MacroHistoryChart({ data }: { data?: MacroHistoryResponse }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current || !data) return;
    const chart = echarts.init(ref.current);
    chart.setOption({ backgroundColor: "transparent", animation: false, grid: { top: 24, right: 28, bottom: 38, left: 52 }, tooltip: { trigger: "axis" }, xAxis: { type: "category", data: data.points.map((point) => point.date), axisLabel: { color: "#7a7a74" }, axisLine: { lineStyle: { color: "#383838" } } }, yAxis: { type: "value", name: data.unit, nameTextStyle: { color: "#e7a23a" }, axisLabel: { color: "#7a7a74" }, splitLine: { lineStyle: { color: "#181818" } } }, series: [{ type: "line", data: data.points.map((point) => point.value), symbol: "none", lineStyle: { color: "#e7a23a", width: 2 } }] });
    const observer = new ResizeObserver(() => chart.resize()); observer.observe(ref.current);
    return () => { observer.disconnect(); chart.dispose(); };
  }, [data]);
  return <div ref={ref} className="macro-history-chart" role="img" aria-label={data ? `${data.label} history` : "Macro history loading"} />;
}

function SummaryCard({ label, value, detail }: { label: string; value: string; detail: string }) { return <div className="macro-summary-card"><span>{label}</span><strong>{value}</strong><small>{detail}</small></div>; }
function SectionTitle({ title }: { title: string }) { return <h2 className="macro-section-title">{title}</h2>; }
function ChangeRow({ changes, unit }: { changes: MacroChanges; unit: string }) { return <span className="macro-change-row"><span>1 {formatChange(changes.change_1, unit)}</span><span>5 {formatChange(changes.change_5 ?? changes.change_4, unit)}</span><span>20 {formatChange(changes.change_20, unit)}</span></span>; }
function formatValue(value: number, unit: string) { return unit === "bp" ? `${value.toFixed(0)}bp` : `${value.toFixed(2)}${unit === "percent" || unit === "%" ? "%" : unit === "pp" ? "pp" : ""}`; }
function formatChange(value: number | null | undefined, unit: string) { if (value == null) return "--"; const suffix = unit === "bp" || unit === "percent" || unit === "%" ? "bp" : unit === "pp" ? "pp" : ""; return `${value >= 0 ? "+" : ""}${value.toFixed(1)}${suffix}`; }
function formatStatus(value: string) { return ({ stable: "稳定", observe: "观察", rising: "上行", falling: "下行", steepening: "陡峭化", flattening: "平坦化", curvature_rising: "曲率上升", curvature_falling: "曲率下降", pressure: "压力", support: "支撑" } as Record<string, string>)[value] ?? value; }
