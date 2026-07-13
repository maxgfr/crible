// FR-007 — typed client for the crible API (same-origin FastAPI). This is
// the self-hosted default; the Pages demo swaps in static-client instead.

import {
  DslApiError,
  type CompanyDetail,
  type CsvExport,
  type DataClient,
  type DemoManifest,
  type DslErrorDetail,
  type FieldInfo,
  type Preset,
  type ProviderInfo,
  type ScreenResponse,
  type SearchHit,
  type StatusResponse,
} from "./types";

export async function screen(
  query: string,
  sort: string | null,
  page: number,
  pageSize: number,
): Promise<ScreenResponse> {
  const response = await fetch("/api/screen", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, sort, page, page_size: pageSize }),
  });
  if (response.status === 422) {
    const body = await response.json();
    throw new DslApiError(body.detail as DslErrorDetail);
  }
  if (!response.ok) throw new Error(`API error ${response.status}`);
  return (await response.json()) as ScreenResponse;
}

export function exportCsvUrl(query: string, sort: string | null, columns?: string[]): string {
  const params = new URLSearchParams({ query });
  if (sort) params.set("sort", sort);
  if (columns && columns.length) params.set("columns", columns.join(","));
  return `/api/screen.csv?${params.toString()}`;
}

export async function presets(): Promise<Preset[]> {
  const response = await fetch("/api/presets");
  return (await response.json()) as Preset[];
}

export async function company(symbol: string): Promise<CompanyDetail | null> {
  const response = await fetch(`/api/company/${encodeURIComponent(symbol)}`);
  if (response.status === 404) return null;
  return (await response.json()) as CompanyDetail;
}

export async function status(): Promise<StatusResponse> {
  const response = await fetch("/api/status");
  return (await response.json()) as StatusResponse;
}

export async function providers(): Promise<ProviderInfo[]> {
  const response = await fetch("/api/providers");
  return (await response.json()) as ProviderInfo[];
}

export async function search(q: string): Promise<SearchHit[]> {
  const response = await fetch(`/api/search?${new URLSearchParams({ q }).toString()}`);
  if (!response.ok) return [];
  return (await response.json()) as SearchHit[];
}

export async function fields(): Promise<FieldInfo[]> {
  const response = await fetch("/api/fields");
  if (!response.ok) return [];
  const body = (await response.json()) as unknown;
  return Array.isArray(body) ? (body as FieldInfo[]) : [];
}

export const apiClient: DataClient = {
  screen,
  presets,
  company,
  status,
  providers,
  search,
  fields,
  async exportCsv(query, sort, columns): Promise<CsvExport> {
    return { url: exportCsvUrl(query, sort, columns) };
  },
  async manifest(): Promise<DemoManifest | null> {
    return null; // live API — not a static demo
  },
};
