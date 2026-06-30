import type { SnapshotItem } from "../services/contracts";
import type { VelocityFilter } from "../services/contracts";

const FAST_VELOCITY_THRESHOLD = 70;

export function matchesSearch(item: SnapshotItem, query: string) {
  const normalized = query.trim().toLowerCase();
  if (!normalized) return true;
  return `${item.symbol} ${item.asset_name}`.toLowerCase().includes(normalized);
}

export function assetKey(item: SnapshotItem) {
  return `${item.asset_class}::${item.symbol}`;
}

export function filterItems(
  items: SnapshotItem[],
  assetClass: string,
  fundingStates: string[],
  rsStates: string[],
  velocityFilter: VelocityFilter = "All",
) {
  const normalizedAssetClass = assetClass.trim().toLowerCase();
  const normalizedFundingStates = new Set(fundingStates.map((value) => value.trim().toLowerCase()));
  const normalizedRsStates = new Set(rsStates.map((value) => value.trim().toLowerCase()));
  return items.filter((item) => {
    return (
      (!normalizedAssetClass || item.asset_class.toLowerCase() === normalizedAssetClass) &&
      normalizedFundingStates.has(item.funding_state.toLowerCase()) &&
      normalizedRsStates.has(item.rs_state.toLowerCase()) &&
      matchesVelocityFilter(item, velocityFilter)
    );
  });
}

function matchesVelocityFilter(item: SnapshotItem, velocityFilter: VelocityFilter) {
  if (velocityFilter === "Fast Leveraging") {
    return item.leverage_velocity_score >= FAST_VELOCITY_THRESHOLD;
  }
  if (velocityFilter === "Fast Deleveraging") {
    return item.leverage_velocity_score <= -FAST_VELOCITY_THRESHOLD;
  }
  if (velocityFilter === "Active") {
    return Math.abs(item.leverage_velocity_score) >= FAST_VELOCITY_THRESHOLD;
  }
  return true;
}

export function trajectoryForAssetKey(frames: Record<string, SnapshotItem[]>, dates: string[], currentIndex: number, selectedAssetKey: string) {
  return dates
    .slice(Math.max(0, currentIndex - 29), currentIndex + 1)
    .map((date) => ({ date, item: frames[date]?.find((entry) => assetKey(entry) === selectedAssetKey) }))
    .filter((entry): entry is { date: string; item: SnapshotItem } => Boolean(entry.item));
}
