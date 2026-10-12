// FR-007 — typed client for the crible API (same-origin FastAPI). This is
// the self-hosted default; static mode swaps in static-client instead.

import {
  DslApiError,
  type CompanyDetail,
  type CsvExport,
  type DataClient,
  type FetchQueued,
  type SiteManifest,
  type DslErrorDetail,
  type FieldInfo,
  type FunnelCount,
  type PriceBar,
  type Preset,
  type ProviderInfo,
  type ScreenResponse,
  type SearchHit,
  type StatusResponse,
} from "./types";

// a non-2xx answer is an error, never data: the message carries the status
// and the server's own `detail` when it sent one (FastAPI's error shape)
async function apiError(response: Response, what = "API error"): Promise<Error> {
  let detail = "";
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (body && body.detail !== undefined) {
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    }
  } catch {
    /* no JSON body — the status alone */
  }
  return new Error(`${what} ${response.status}${detail ? `: ${detail}` : ""}`);
}

async function okJson<T>(response: Response): Promise<T> {
  if (!response.ok) throw await apiError(response);
  return (await response.json()) as T;
}

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
  return okJson<ScreenResponse>(response);
}

export function exportCsvUrl(query: string, sort: string | null, columns?: string[]): string {
  const params = new URLSearchParams({ query });
  if (sort) params.set("sort", sort);
  if (columns && columns.length) params.set("columns", columns.join(","));
  return `/api/screen.csv?${params.toString()}`;
}

export async function presets(): Promise<Preset[]> {
  return okJson<Preset[]>(await fetch("/api/presets"));
}

export async function company(symbol: string): Promise<CompanyDetail | null> {
  const response = await fetch(`/api/company/${encodeURIComponent(symbol)}`);
  if (response.status === 404) return null;
  return okJson<CompanyDetail>(response);
}

export async function status(): Promise<StatusResponse> {
  return okJson<StatusResponse>(await fetch("/api/status"));
}

export async function providers(): Promise<ProviderInfo[]> {
  return okJson<ProviderInfo[]>(await fetch("/api/providers"));
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

export async function prices(symbol: string): Promise<PriceBar[]> {
  const response = await fetch(`/api/prices/${encodeURIComponent(symbol)}`);
  if (!response.ok) return [];
  const body = (await response.json()) as unknown;
  return Array.isArray(body) ? (body as PriceBar[]) : [];
}

export async function requestFetch(symbol: string): Promise<FetchQueued> {
  const response = await fetch(`/api/fetch/${encodeURIComponent(symbol)}`, { method: "POST" });
  if (!response.ok) throw await apiError(response, "fetch request refused");
  return (await response.json()) as FetchQueued;
}

// the API has no aggregate endpoint: one total-only screen per count, in
// order, stopping once the cumulative funnel is empty (nothing after it
// can matter)
export async function funnel(clauses: string[]): Promise<FunnelCount[]> {
  const out: FunnelCount[] = [];
  for (let i = 0; i < clauses.length; i += 1) {
    const alone = (await screen(clauses[i], null, 1, 1)).total;
    const cumulative = (await screen(clauses.slice(0, i + 1).join(" AND "), null, 1, 1)).total;
    out.push({ clause: clauses[i], alone, cumulative });
    if (cumulative === 0) break;
  }
  return out;
}

export const apiClient: DataClient = {
  // the server returns every column — the projection hint is static-only
  screen: (query, sort, page, pageSize) => screen(query, sort, page, pageSize),
  funnel,
  presets,
  company,
  status,
  providers,
  search,
  fields,
  prices,
  requestFetch,
  async exportCsv(query, sort, columns): Promise<CsvExport> {
    return { url: exportCsvUrl(query, sort, columns) };
  },
  async manifest(): Promise<SiteManifest | null> {
    return null; // live API — not a static build
  },
};
