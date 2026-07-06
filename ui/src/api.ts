// FR-007 — typed client for the crible API (same-origin).

export interface ScreenResponse {
  rows: Record<string, unknown>[];
  total: number;
  page: number;
  tookMs: number;
  hint?: string;
}

export interface DslErrorDetail {
  error: string;
  position: number | null;
  hint: string | null;
}

export interface Preset {
  id: string;
  name: string;
  description: string;
  dsl: string;
}

export interface CompanyDetail {
  profile: Record<string, unknown>;
  periods: Record<string, unknown>[];
}

export class DslApiError extends Error {
  detail: DslErrorDetail;
  constructor(detail: DslErrorDetail) {
    super(detail.error);
    this.detail = detail;
  }
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

export async function status(): Promise<Record<string, unknown>> {
  const response = await fetch("/api/status");
  return (await response.json()) as Record<string, unknown>;
}
