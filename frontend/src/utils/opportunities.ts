import type { SnapshotItem } from "../services/contracts";

export const OPPORTUNITY_DISPLAY_LIMIT = 10;
export const RANK_CHANGE_OFFSETS = [1, 5, 10] as const;

export type OpportunityScreen = "strongLong" | "candidateLong";
export type RankChangeOffset = (typeof RANK_CHANGE_OFFSETS)[number];
export type RankChangeKey = `rank_change_${RankChangeOffset}d`;
export type RankChanges = Record<RankChangeKey, string>;

export type RankedOpportunity = {
  item: SnapshotItem;
  rank: number;
  rankChanges: RankChanges;
};

export type OpportunityMarker = {
  strongLong: boolean;
  candidateLong: boolean;
};

type OpportunityRanker = (items: SnapshotItem[]) => SnapshotItem[];

export function rankStrongLongOpportunities(items: SnapshotItem[]) {
  return dedupeOpportunities([...items].filter(isStrongLongOpportunity).sort(compareStrongLong));
}

export function rankCandidateLongOpportunities(items: SnapshotItem[]) {
  return dedupeOpportunities([...items].filter(isCandidateLongOpportunity).sort(compareCandidateLong));
}

export function buildRankChanges(
  frames: Record<string, SnapshotItem[]>,
  dates: string[],
  currentIndex: number,
  screen: OpportunityScreen,
) {
  const ranker = rankerForScreen(screen);
  const currentDate = dates[currentIndex];
  const currentRanked = currentDate ? ranker(frames[currentDate] ?? []) : [];
  const changesByKey = new Map<string, RankChanges>();

  currentRanked.forEach((item, index) => {
    const currentRank = index + 1;
    const changes = emptyRankChanges();
    for (const offset of RANK_CHANGE_OFFSETS) {
      const previousIndex = currentIndex - offset;
      const key = `rank_change_${offset}d` as RankChangeKey;
      if (previousIndex < 0) {
        changes[key] = "NEW";
        continue;
      }
      const previousDate = dates[previousIndex];
      const previousRanks = ranksByAssetKey(ranker(frames[previousDate] ?? []));
      changes[key] = rankChangeLabel(previousRanks.get(opportunityAssetKey(item)), currentRank);
    }
    changesByKey.set(opportunityAssetKey(item), changes);
  });

  return changesByKey;
}

export function buildRankedOpportunityRows(
  items: SnapshotItem[],
  rankChanges: Map<string, RankChanges>,
  ranker: OpportunityRanker,
): RankedOpportunity[] {
  return ranker(items).map((item, index) => ({
    item,
    rank: index + 1,
    rankChanges: rankChanges.get(opportunityAssetKey(item)) ?? emptyRankChanges(),
  }));
}

export function topOpportunities(rows: RankedOpportunity[], limit = OPPORTUNITY_DISPLAY_LIMIT) {
  return rows.slice(0, limit);
}

export function buildOpportunityMarkers(
  strongRows: RankedOpportunity[],
  candidateRows: RankedOpportunity[],
  limit = OPPORTUNITY_DISPLAY_LIMIT,
) {
  const markers = new Map<string, OpportunityMarker>();
  const mark = (row: RankedOpportunity, screen: OpportunityScreen) => {
    const key = opportunityAssetKey(row.item);
    const current = markers.get(key) ?? { strongLong: false, candidateLong: false };
    markers.set(key, {
      ...current,
      [screen]: true,
    });
  };

  topOpportunities(strongRows, limit).forEach((row) => mark(row, "strongLong"));
  topOpportunities(candidateRows, limit).forEach((row) => mark(row, "candidateLong"));
  return markers;
}

export function opportunityAssetKey(item: SnapshotItem) {
  return `${item.symbol.trim()}::${item.asset_name.trim()}`;
}

function rankerForScreen(screen: OpportunityScreen): OpportunityRanker {
  return screen === "strongLong" ? rankStrongLongOpportunities : rankCandidateLongOpportunities;
}

function isStrongLongOpportunity(item: SnapshotItem) {
  return (
    (item.rs_state === "Lead" || item.rs_state === "Improving") &&
    item.early_reversal > 100 &&
    item.funding_state === "Leveraging" &&
    item.trend_score > 20 &&
    normalizeTrend(item.weekly_trend) === "up"
  );
}

function isCandidateLongOpportunity(item: SnapshotItem) {
  return (
    item.rs_state === "Improving" &&
    item.early_reversal > 100 &&
    item.trend_score > 20 &&
    normalizeTrend(item.daily_trend) !== "down" &&
    normalizeTrend(item.weekly_trend) !== "down" &&
    (item.funding_state === "Leveraging" ||
      (item.funding_state === "Deleveraging" && finiteNumber(item.leverage_velocity, -Infinity) > -5))
  );
}

function compareStrongLong(a: SnapshotItem, b: SnapshotItem) {
  return (
    compareAscending(finiteNumber(a.leverage_duration, Infinity), finiteNumber(b.leverage_duration, Infinity)) ||
    compareDescending(fundingSignalStrength(a), fundingSignalStrength(b)) ||
    compareDescending(a.trend_score, b.trend_score) ||
    compareAssetIdentity(a, b)
  );
}

function compareCandidateLong(a: SnapshotItem, b: SnapshotItem) {
  return (
    compareAscending(fundingStateSort(a), fundingStateSort(b)) ||
    compareAscending(leveragingDurationSort(a), leveragingDurationSort(b)) ||
    compareDescending(deleveragingVelocitySort(a), deleveragingVelocitySort(b)) ||
    compareDescending(a.early_reversal, b.early_reversal) ||
    compareAscending(a.strength_momentum, b.strength_momentum) ||
    compareAscending(a.relative_strength, b.relative_strength) ||
    compareAscending(fundingSignalStrength(a), fundingSignalStrength(b)) ||
    compareDescending(a.leverage_velocity, b.leverage_velocity) ||
    compareAssetIdentity(a, b)
  );
}

function fundingStateSort(item: SnapshotItem) {
  if (item.funding_state === "Leveraging") return 0;
  if (item.funding_state === "Deleveraging") return 1;
  return 2;
}

function leveragingDurationSort(item: SnapshotItem) {
  return item.funding_state === "Leveraging" ? finiteNumber(item.leverage_duration, Infinity) : Infinity;
}

function deleveragingVelocitySort(item: SnapshotItem) {
  return item.funding_state === "Deleveraging" ? finiteNumber(item.leverage_velocity, -Infinity) : -Infinity;
}

function fundingSignalStrength(item: SnapshotItem) {
  return finiteNumber(item.funding_signal_strength, item.funding_score);
}

function compareAssetIdentity(a: SnapshotItem, b: SnapshotItem) {
  return (
    a.asset_class.localeCompare(b.asset_class) ||
    a.symbol.localeCompare(b.symbol) ||
    a.asset_name.localeCompare(b.asset_name)
  );
}

function dedupeOpportunities(items: SnapshotItem[]) {
  const seen = new Set<string>();
  return items.filter((item) => {
    const key = opportunityAssetKey(item);
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function ranksByAssetKey(items: SnapshotItem[]) {
  return new Map(items.map((item, index) => [opportunityAssetKey(item), index + 1]));
}

function rankChangeLabel(previousRank: number | undefined, currentRank: number) {
  if (previousRank == null) return "NEW";
  const change = previousRank - currentRank;
  return change > 0 ? `+${change}` : String(change);
}

function emptyRankChanges(): RankChanges {
  return {
    rank_change_1d: "NEW",
    rank_change_5d: "NEW",
    rank_change_10d: "NEW",
  };
}

function normalizeTrend(value?: string | null) {
  return String(value ?? "").trim().toLowerCase();
}

function finiteNumber(value: unknown, fallback: number) {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

function compareAscending(a: number, b: number) {
  return a - b;
}

function compareDescending(a: number, b: number) {
  return b - a;
}
