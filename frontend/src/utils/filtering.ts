import type { SnapshotItem } from "../services/contracts";

export const GS_EXEMPT_FILTER = "gs_exempt";

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
) {
  const normalizedAssetClass = assetClass.trim().toLowerCase();
  const normalizedFundingStates = new Set(fundingStates.map((value) => value.trim().toLowerCase()));
  const normalizedRsStates = new Set(rsStates.map((value) => value.trim().toLowerCase()));
  return items.filter((item) => {
    return (
      matchesAssetFilter(item, normalizedAssetClass) &&
      normalizedFundingStates.has(item.funding_state.toLowerCase()) &&
      normalizedRsStates.has(item.rs_state.toLowerCase())
    );
  });
}

export function filterFramesByAssetFilter(frames: Record<string, SnapshotItem[]>, assetFilter: string) {
  return Object.fromEntries(
    Object.entries(frames).map(([date, items]) => [date, items.filter((item) => matchesAssetFilter(item, assetFilter))]),
  );
}

export function matchesAssetFilter(item: SnapshotItem, assetFilter: string) {
  const normalized = assetFilter.trim().toLowerCase();
  if (!normalized) return true;
  if (normalized === GS_EXEMPT_FILTER) return item.is_gs_exempt;
  return item.asset_class.toLowerCase() === normalized;
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
