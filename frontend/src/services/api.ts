import type { AssetsResponse, ConfigResponse, DatesResponse, MacroHistoryResponse, MacroOverviewResponse, PlaybackResponse } from "./contracts";

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(path);
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
  return response.json() as Promise<T>;
}

export function fetchConfig() {
  return getJson<ConfigResponse>("/api/config");
}

export function fetchDates() {
  return getJson<DatesResponse>("/api/dates");
}

export function fetchAssets() {
  return getJson<AssetsResponse>("/api/assets");
}

export function fetchPlayback(start?: string, end?: string) {
  const params = new URLSearchParams();
  if (start) params.set("start", start);
  if (end) params.set("end", end);
  const suffix = params.size ? `?${params.toString()}` : "";
  return getJson<PlaybackResponse>(`/api/playback${suffix}`);
}

export function fetchMacroOverview() {
  return getJson<MacroOverviewResponse>("/api/macro/overview");
}

export function fetchMacroHistory(seriesId: string, start?: string) {
  const params = new URLSearchParams({ series_id: seriesId });
  if (start) params.set("start", start);
  return getJson<MacroHistoryResponse>(`/api/macro/history?${params.toString()}`);
}
