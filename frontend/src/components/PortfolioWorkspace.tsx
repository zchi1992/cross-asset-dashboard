import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { fetchPortfolio, syncPortfolio, updatePortfolioStopLoss } from "../services/api";
import type { PortfolioAssetLink, PortfolioPosition } from "../services/contracts";

type SortKey = "symbol" | "sec_type" | "quantity" | "market_price" | "market_value" | "average_cost" |
  "unrealized_pnl" | "portfolio_weight" | "stop_loss_price" | "planned_loss_at_stop" | "remaining_risk_to_stop";
type SortDirection = "ascending" | "descending";
type PositionRow =
  | { kind: "position"; position: PortfolioPosition }
  | { kind: "option-group"; symbol: string; positions: PortfolioPosition[] };

const sortableColumns: { key: SortKey; label: string }[] = [
  { key: "symbol", label: "标的" }, { key: "sec_type", label: "类型" }, { key: "quantity", label: "数量" },
  { key: "market_price", label: "市价" }, { key: "market_value", label: "市值" },
  { key: "average_cost", label: "平均成本" }, { key: "unrealized_pnl", label: "未实现盈亏" },
  { key: "portfolio_weight", label: "权重" }, { key: "stop_loss_price", label: "止损价" },
  { key: "planned_loss_at_stop", label: "成本至止损亏损" },
  { key: "remaining_risk_to_stop", label: "当前剩余风险" },
];


export function PortfolioWorkspace({ onOpenAsset }: { onOpenAsset: (asset: PortfolioAssetLink) => void }) {
  const queryClient = useQueryClient();
  const portfolioQuery = useQuery({
    queryKey: ["portfolio"],
    queryFn: fetchPortfolio,
    refetchOnWindowFocus: "always",
    staleTime: 0,
  });
  const [actionError, setActionError] = useState("");
  const [sort, setSort] = useState<{ key: SortKey; direction: SortDirection }>({ key: "symbol", direction: "ascending" });
  const [expandedOptions, setExpandedOptions] = useState<Set<string>>(() => new Set());
  const [detailView, setDetailView] = useState<"overview" | "options">("overview");
  const syncMutation = useMutation({
    mutationFn: syncPortfolio,
    onSuccess: (data) => {
      queryClient.setQueryData(["portfolio"], data);
      setActionError("");
    },
    onError: (error) => setActionError(error instanceof Error ? error.message : "同步失败"),
  });
  const stopMutation = useMutation({
    mutationFn: ({ conid, value }: { conid: string; value: number | null }) =>
      updatePortfolioStopLoss(conid, value),
    onSuccess: (data) => {
      queryClient.setQueryData(["portfolio"], data);
      setActionError("");
    },
    onError: (error) => setActionError(error instanceof Error ? error.message : "保存止损价失败"),
  });

  const data = portfolioQuery.data;
  const account = data?.account;
  const risk = data?.risk;
  const currency = account?.base_currency || "";
  const positionRows = useMemo(
    () => buildPositionRows(data?.positions ?? [], sort.key, sort.direction),
    [data?.positions, sort],
  );

  const changeSort = (key: SortKey) => {
    setSort((current) => current.key === key
      ? { key, direction: current.direction === "ascending" ? "descending" : "ascending" }
      : { key, direction: "ascending" });
  };

  const toggleOptionGroup = (symbol: string) => {
    setExpandedOptions((current) => {
      const next = new Set(current);
      if (next.has(symbol)) next.delete(symbol);
      else next.add(symbol);
      return next;
    });
  };

  return (
    <section className="portfolio-workspace" data-testid="portfolio-workspace">
      <header className="portfolio-header">
        <div>
          <span className={`portfolio-status is-${data?.status ?? "loading"}`}>
            {portfolioStatusLabel(data?.status)}
          </span>
          <h1>持仓</h1>
          <p>
            {data?.captured_at ? `采集时间 ${formatDateTime(data.captured_at)}` : "尚无持仓快照"}
            {data?.sync_source ? ` · ${syncSourceLabel(data.sync_source)}` : ""}
          </p>
        </div>
        <button
          type="button"
          className="primary-button portfolio-sync-button"
          disabled={syncMutation.isPending}
          onClick={() => syncMutation.mutate()}
        >
          {syncMutation.isPending ? "同步中…" : "同步"}
        </button>
      </header>

      {(actionError || portfolioQuery.error || data?.message) && (
        <div className="portfolio-alert" role="alert">
          {actionError || (portfolioQuery.error instanceof Error ? portfolioQuery.error.message : "") || data?.message}
        </div>
      )}

      {portfolioQuery.isLoading ? (
        <div className="empty-state">正在读取持仓快照…</div>
      ) : !account || !risk ? (
        <div className="empty-state">点击“同步”从已登录的 TWS 获取持仓。</div>
      ) : (
        <>
          <section className="portfolio-section">
            <h2>账户概览</h2>
            <div className="portfolio-metric-grid">
              <PortfolioMetric label="净清算价值" value={formatMoney(account.net_liquidation, currency)} />
              <PortfolioMetric label="维持保证金" value={formatMoney(account.maint_margin_req, currency)} />
              <PortfolioMetric label="SMA" value={formatMoney(account.sma, currency)} />
              <PortfolioMetric label="超额流动性" value={formatMoney(account.excess_liquidity, currency)} />
              <PortfolioMetric label="可用资金" value={formatMoney(account.available_funds, currency)} />
              <PortfolioMetric label="购买力" value={formatMoney(account.buying_power, currency)} />
              <PortfolioMetric label="持仓总价值" value={formatMoney(account.gross_position_value, currency)} />
              <PortfolioMetric label="流动性缓冲" value={formatPercent(account.cushion)} />
            </div>
          </section>

          <section className="portfolio-section">
            <h2>风控</h2>
            <div className="portfolio-metric-grid risk-grid">
              <PortfolioMetric label="杠杆率" value={formatRatio(risk.leverage_ratio)} />
              <PortfolioMetric label="维持保证金率" value={formatPercent(risk.maintenance_margin_ratio)} />
              <PortfolioMetric label="超额流动性率" value={formatPercent(risk.excess_liquidity_ratio)} />
              <PortfolioMetric label="最大单一持仓占比" value={formatPercent(risk.largest_position_concentration)} />
              <PortfolioMetric label="成本至止损亏损" value={formatMoney(risk.planned_loss_at_stop, currency)} />
              <PortfolioMetric label="当前剩余风险" value={formatMoney(risk.remaining_risk_to_stop, currency)} />
              <PortfolioMetric
                label="止损覆盖"
                value={`${risk.covered_position_count}/${risk.eligible_position_count} · ${formatPercent(risk.coverage_ratio)}`}
              />
              <PortfolioMetric label="已覆盖市值" value={formatMoney(risk.covered_market_value, currency)} />
            </div>
            <p className="portfolio-disclaimer">止损风险为计划估算，实际成交价格可能因跳空和流动性而不同。</p>
          </section>

          <section className="portfolio-section">
            <div className="portfolio-section-heading">
              <h2>持仓明细</h2>
              <span>{data.positions.length} 个持仓 · {account.account_id_masked}</span>
            </div>
            <div className="portfolio-detail-tabs" role="tablist" aria-label="持仓明细视图">
              <button type="button" role="tab" aria-selected={detailView === "overview"}
                className={detailView === "overview" ? "active" : ""} onClick={() => setDetailView("overview")}>概览</button>
              <button type="button" role="tab" aria-selected={detailView === "options"}
                className={detailView === "options" ? "active" : ""} onClick={() => setDetailView("options")}>期权</button>
            </div>
            {detailView === "overview" ? <>
            <div className="portfolio-table-wrap">
              <table className="portfolio-table">
                <thead>
                  <tr>
                    {sortableColumns.map((column) => (
                      <th key={column.key} aria-sort={sort.key === column.key ? sort.direction : "none"}>
                        <button type="button" className="portfolio-sort-button" onClick={() => changeSort(column.key)}>
                          {column.label}<span aria-hidden="true">{sort.key === column.key ? (sort.direction === "ascending" ? "▲" : "▼") : "↕"}</span>
                        </button>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {positionRows.flatMap((row) => {
                    if (row.kind === "position") return [renderPositionRow(row.position, currency, stopMutation, onOpenAsset)];
                    const expanded = expandedOptions.has(row.symbol);
                    const summary = optionGroupSummary(row.positions);
                    const linkedAsset = row.positions.find((position) => position.linked_asset)?.linked_asset;
                    return [
                      <tr key={`option-${row.symbol}`} className="portfolio-option-group-row">
                        <td>
                          <button
                            type="button"
                            className="portfolio-option-toggle"
                            aria-expanded={expanded}
                            aria-label={`${expanded ? "收起" : "展开"} ${row.symbol} 期权`}
                            onClick={() => toggleOptionGroup(row.symbol)}
                          ><span aria-hidden="true">{expanded ? "▾" : "▸"}</span><strong>{row.symbol}</strong></button>
                          {linkedAsset && <span className="portfolio-option-underlying">{linkedAsset.name}</span>}
                        </td>
                        <td>期权（{row.positions.length}）</td><td>{row.positions.length} 份合约</td><td>—</td>
                        <td>{formatMoney(summary.market_value, currency)}</td><td>—</td>
                        <td className={pnlClass(summary.unrealized_pnl)}>{formatMoney(summary.unrealized_pnl, currency)}</td>
                        <td>{formatPercent(summary.portfolio_weight)}</td><td>不适用</td><td>不适用</td><td>不适用</td>
                      </tr>,
                      ...(expanded ? row.positions.map((position) => renderPositionRow(
                        position, currency, stopMutation, onOpenAsset, true,
                      )) : []),
                    ];
                  })}
                </tbody>
              </table>
            </div>
            {!data.positions.length && <div className="empty-state">该账户当前没有持仓。</div>}
            </> : <OptionGreeksTable positions={data.positions} />}
          </section>
        </>
      )}
    </section>
  );
}

function OptionGreeksTable({ positions }: { positions: PortfolioPosition[] }) {
  const groups = aggregateOptionGreeks(positions);
  const [expanded, setExpanded] = useState<Set<string>>(() => new Set());
  const toggle = (symbol: string) => setExpanded((current) => {
    const next = new Set(current);
    if (next.has(symbol)) next.delete(symbol);
    else next.add(symbol);
    return next;
  });
  return <>
    <p className="portfolio-disclaimer option-greeks-note">
      Greeks 为 IBKR 模型值乘以持仓数量和合约乘数后的风险敞口；多空方向按正负相互抵消。
    </p>
    <div className="portfolio-table-wrap">
      <table className="portfolio-table option-greeks-table">
        <thead><tr><th>底层标的／合约</th><th>数量</th><th>Delta</th><th>Gamma</th><th>Theta</th><th>Vega</th></tr></thead>
        <tbody>{groups.flatMap((group) => {
          const isExpanded = expanded.has(group.symbol);
          return [<tr key={group.symbol} className="portfolio-option-group-row">
            <td><button type="button" className="portfolio-option-toggle" aria-expanded={isExpanded}
              aria-label={`${isExpanded ? "收起" : "展开"} ${group.symbol} Greeks`} onClick={() => toggle(group.symbol)}>
              <span aria-hidden="true">{isExpanded ? "▾" : "▸"}</span><strong>{group.symbol}</strong>
            </button></td><td>{group.contract_count} 份合约</td>
            <td className={pnlClass(group.delta)}>{formatGreek(group.delta)}</td>
            <td className={pnlClass(group.gamma)}>{formatGreek(group.gamma)}</td>
            <td className={pnlClass(group.theta)}>{formatGreek(group.theta)}</td>
            <td className={pnlClass(group.vega)}>{formatGreek(group.vega)}</td>
          </tr>, ...(isExpanded ? group.contracts.map((position) => <tr key={position.conid} className="option-greeks-child-row">
            <td><strong>{position.local_symbol || position.symbol}</strong></td><td>{formatNumber(position.quantity)}</td>
            <GreekExposureCell position={position} greek="option_delta" />
            <GreekExposureCell position={position} greek="option_gamma" />
            <GreekExposureCell position={position} greek="option_theta" />
            <GreekExposureCell position={position} greek="option_vega" />
          </tr>) : [])];
        })}</tbody>
      </table>
    </div>
    {!groups.length && <div className="empty-state">当前没有期权持仓。</div>}
  </>;
}

function GreekExposureCell({ position, greek }: {
  position: PortfolioPosition;
  greek: "option_delta" | "option_gamma" | "option_theta" | "option_vega";
}) {
  const value = positionGreekExposure(position, greek);
  return <td className={pnlClass(value)}>{formatGreek(value)}</td>;
}

export function aggregateOptionGreeks(positions: PortfolioPosition[]) {
  const grouped = new Map<string, PortfolioPosition[]>();
  positions.filter((position) => position.sec_type === "OPT" || position.sec_type === "FOP").forEach((position) => {
    grouped.set(position.symbol, [...(grouped.get(position.symbol) ?? []), position]);
  });
  return [...grouped.entries()].map(([symbol, contracts]) => ({
    symbol,
    contract_count: contracts.length,
    delta: greekExposure(contracts, "option_delta"),
    gamma: greekExposure(contracts, "option_gamma"),
    theta: greekExposure(contracts, "option_theta"),
    vega: greekExposure(contracts, "option_vega"),
    contracts,
  })).sort((a, b) => a.symbol.localeCompare(b.symbol));
}

function greekExposure(positions: PortfolioPosition[], key: "option_delta" | "option_gamma" | "option_theta" | "option_vega") {
  const exposures = positions.map((position) => positionGreekExposure(position, key));
  if (exposures.some((value) => value == null)) return null;
  return exposures.reduce<number>((sum, value) => sum + value!, 0);
}

function positionGreekExposure(position: PortfolioPosition, key: "option_delta" | "option_gamma" | "option_theta" | "option_vega") {
  return typeof position[key] === "number" && typeof position.multiplier === "number"
    ? position[key]! * position.quantity * position.multiplier : null;
}

function formatGreek(value: number | null) {
  return typeof value === "number" && Number.isFinite(value)
    ? value.toLocaleString("zh-CN", { maximumFractionDigits: 4 }) : "无法计算";
}

function renderPositionRow(
  position: PortfolioPosition,
  currency: string,
  stopMutation: {
    isPending: boolean;
    variables?: { conid: string; value: number | null };
    mutate: (variables: { conid: string; value: number | null }) => void;
  },
  onOpenAsset: (asset: PortfolioAssetLink) => void,
  optionChild = false,
) {
  return <tr key={position.conid} className={optionChild ? "portfolio-option-child-row" : undefined}>
    <td>
      {position.linked_asset ? (
        <button className="portfolio-asset-link" onClick={() => onOpenAsset(position.linked_asset!)}>
          <strong>{position.local_symbol || position.symbol}</strong><span>{position.linked_asset.name}</span>
        </button>
      ) : (
        <div className="portfolio-contract"><strong>{position.local_symbol || position.symbol}</strong>
          <span>{position.link_status === "ambiguous" ? "标的映射有歧义" : "暂无指标关联"}</span></div>
      )}
    </td>
    <td>{position.sec_type}</td><td>{formatNumber(position.quantity)}</td>
    <td>{formatMoney(position.market_price, position.currency)}</td><td>{formatMoney(position.market_value, currency)}</td>
    <td>{formatMoney(position.average_cost, position.currency)}</td>
    <td className={pnlClass(position.unrealized_pnl)}>{formatMoney(position.unrealized_pnl, currency)}</td>
    <td>{formatPercent(position.portfolio_weight)}</td>
    <td>{position.risk_eligible ? <StopLossInput position={position}
      saving={stopMutation.isPending && stopMutation.variables?.conid === position.conid}
      onSave={(value) => stopMutation.mutate({ conid: position.conid, value })} /> : "不适用"}</td>
    <td>{formatMoney(position.planned_loss_at_stop, currency)}</td>
    <td>{formatMoney(position.remaining_risk_to_stop, currency)}</td>
  </tr>;
}

export function buildPositionRows(positions: PortfolioPosition[], key: SortKey, direction: SortDirection): PositionRow[] {
  const optionGroups = new Map<string, PortfolioPosition[]>();
  const rows: PositionRow[] = [];
  positions.forEach((position) => {
    if (position.sec_type === "OPT" || position.sec_type === "FOP") {
      optionGroups.set(position.symbol, [...(optionGroups.get(position.symbol) ?? []), position]);
    } else rows.push({ kind: "position", position });
  });
  optionGroups.forEach((group, symbol) => rows.push({
    kind: "option-group", symbol, positions: [...group].sort((a, b) => compareValues(positionSortValue(a, key), positionSortValue(b, key), direction)),
  }));
  return rows.sort((a, b) => compareValues(rowSortValue(a, key), rowSortValue(b, key), direction));
}

function optionGroupSummary(positions: PortfolioPosition[]) {
  return {
    market_value: sumDefined(positions.map((position) => position.market_value)),
    unrealized_pnl: sumDefined(positions.map((position) => position.unrealized_pnl)),
    portfolio_weight: sumDefined(positions.map((position) => position.portfolio_weight)),
  };
}

function rowSortValue(row: PositionRow, key: SortKey): string | number | null {
  if (row.kind === "position") return positionSortValue(row.position, key);
  const summary = optionGroupSummary(row.positions);
  if (key === "symbol") return row.symbol;
  if (key === "sec_type") return "OPT";
  if (key === "quantity") return row.positions.length;
  if (key === "market_value" || key === "unrealized_pnl" || key === "portfolio_weight") return summary[key];
  return null;
}

function positionSortValue(position: PortfolioPosition, key: SortKey): string | number | null {
  if (key === "symbol") return position.local_symbol || position.symbol;
  return position[key] ?? null;
}

function compareValues(a: string | number | null, b: string | number | null, direction: SortDirection) {
  if (a == null && b == null) return 0;
  if (a == null) return 1;
  if (b == null) return -1;
  const result = typeof a === "number" && typeof b === "number" ? a - b : String(a).localeCompare(String(b), "zh-CN");
  return direction === "ascending" ? result : -result;
}

function sumDefined(values: (number | null | undefined)[]) {
  const defined = values.filter((value): value is number => typeof value === "number" && Number.isFinite(value));
  return defined.length ? defined.reduce((sum, value) => sum + value, 0) : null;
}

function StopLossInput({
  position,
  saving,
  onSave,
}: {
  position: PortfolioPosition;
  saving: boolean;
  onSave: (value: number | null) => void;
}) {
  const canonical = position.stop_loss_price == null ? "" : String(position.stop_loss_price);
  const [draft, setDraft] = useState(canonical);
  useEffect(() => setDraft(canonical), [canonical]);

  const commit = () => {
    const normalized = draft.trim();
    if (normalized === canonical) return;
    if (!normalized) {
      onSave(null);
      return;
    }
    const parsed = Number(normalized);
    if (!Number.isFinite(parsed) || parsed <= 0) {
      setDraft(canonical);
      return;
    }
    onSave(parsed);
  };
  return (
    <div className={`stop-loss-control is-${position.stop_status}`}>
      <input
        aria-label={`${position.local_symbol || position.symbol} 止损价`}
        type="number"
        min="0"
        step="any"
        value={draft}
        disabled={saving}
        placeholder="未设置"
        onBlur={commit}
        onChange={(event) => setDraft(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter") event.currentTarget.blur();
          if (event.key === "Escape") setDraft(canonical);
        }}
      />
      {position.stop_status === "breached" && <span>已触及</span>}
    </div>
  );
}

function PortfolioMetric({ label, value }: { label: string; value: string }) {
  return <div className="portfolio-metric"><span>{label}</span><strong>{value}</strong></div>;
}

function portfolioStatusLabel(status?: string) {
  if (status === "ready") return "快照可用";
  if (status === "stale") return "快照已过期";
  if (status === "error") return "快照异常";
  if (status === "no_snapshot") return "尚无快照";
  return "读取中";
}

function syncSourceLabel(source: string) {
  if (source === "manual") return "手工同步";
  if (source === "scheduled_2000") return "20:00 自动同步";
  if (source === "scheduled_2330") return "23:30 最终同步";
  return source;
}

function formatDateTime(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString("zh-CN", { hour12: false });
}

function formatMoney(value?: number | null, currency = "") {
  if (typeof value !== "number" || !Number.isFinite(value)) return "无法计算";
  return `${currency ? `${currency} ` : ""}${value.toLocaleString("zh-CN", { maximumFractionDigits: 2 })}`;
}

function formatNumber(value?: number | null) {
  return typeof value === "number" && Number.isFinite(value) ? value.toLocaleString("zh-CN", { maximumFractionDigits: 4 }) : "-";
}

function formatPercent(value?: number | null) {
  return typeof value === "number" && Number.isFinite(value) ? `${(value * 100).toFixed(1)}%` : "无法计算";
}

function formatRatio(value?: number | null) {
  return typeof value === "number" && Number.isFinite(value) ? `${value.toFixed(2)}x` : "无法计算";
}

function pnlClass(value?: number | null) {
  if (typeof value !== "number" || value === 0) return "";
  return value > 0 ? "is-positive" : "is-negative";
}
