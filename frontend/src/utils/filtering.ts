import type { SnapshotItem } from "../services/contracts";
import type { VelocityFilter } from "../services/contracts";

const FAST_VELOCITY_THRESHOLD = 70;

export function matchesSearch(item: SnapshotItem, query: string) {
  const normalized = query.trim().toLowerCase();
  if (!normalized) return true;
  return `${item.symbol} ${item.asset_name}`.toLowerCase().includes(normalized);
}

export function assetKey(item: SnapshotItem) {
  return assetKeyWithCollisions(item);
}

export function assetKeyWithCollisions(item: SnapshotItem, duplicateAssetBaseKeys: Set<string> = new Set()) {
  const baseKey = assetBaseKey(item);
  return duplicateAssetBaseKeys.has(baseKey) ? `${baseKey}::${item.asset_name}` : baseKey;
}

export function duplicateAssetBaseKeys(frames: Record<string, SnapshotItem[]>) {
  const namesByBaseKey = new Map<string, Set<string>>();
  for (const items of Object.values(frames)) {
    for (const item of items) {
      const baseKey = assetBaseKey(item);
      const names = namesByBaseKey.get(baseKey);
      if (names) {
        names.add(item.asset_name);
      } else {
        namesByBaseKey.set(baseKey, new Set([item.asset_name]));
      }
    }
  }
  return new Set([...namesByBaseKey].filter(([, names]) => names.size > 1).map(([baseKey]) => baseKey));
}

function assetBaseKey(item: SnapshotItem) {
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

export function trajectoryForAssetKey(
  frames: Record<string, SnapshotItem[]>,
  dates: string[],
  currentIndex: number,
  selectedAssetKey: string,
  duplicateAssetBaseKeys: Set<string> = new Set(),
) {
  return dates
    .slice(Math.max(0, currentIndex - 29), currentIndex + 1)
    .map((date) => ({
      date,
      item: frames[date]?.find((entry) => assetKeyWithCollisions(entry, duplicateAssetBaseKeys) === selectedAssetKey),
    }))
    .filter((entry): entry is { date: string; item: SnapshotItem } => Boolean(entry.item));
}
