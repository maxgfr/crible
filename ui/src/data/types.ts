// FR-007 — the shared data contract. One DataClient interface, two
// implementations: api-client (same-origin FastAPI, the self-hosted default)
// and static-client (DuckDB-WASM over published Parquet, the hosted site).

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
  /** grid columns the preset surfaces on pick; optional — older published
   *  presets.json (and custom presets) don't carry it */
  columns?: string[] | null;
}

export interface CompanyDetail {
  profile: Record<string, unknown>;
  periods: Record<string, unknown>[];
}

export interface IngestHeartbeat {
  universe?: number;
  crawled?: number;
  coverage_pct?: number;
  freshness?: Record<string, number>;
  requests_last_hour?: number;
  budget_per_hour?: number;
  last_cycle?: { fetched: number; failed: number };
  providers?: Record<string, string>;
  esef_resolved?: number;
  esef_unmatched?: number;
  edgar_resolved?: number;
  edgar_unmatched?: number;
  ts?: number;
}

export interface StatusResponse {
  universe?: number;
  by_region?: Record<string, number>;
  ingest?: IngestHeartbeat;
  snapshot?: boolean;
  generated_at?: number;
}

export interface ProviderInfo {
  id: string;
  kind: "keyless" | "free-key" | "paid";
  key_env_var: string | null;
  enabled: boolean;
}

export interface FieldInfo {
  name: string;
  type: "number" | "string";
}

export interface SearchHit {
  symbol: string;
  name: string | null;
  country: string | null;
  sector: string | null;
}

export interface PriceShard {
  file: string;
  rows: number;
  bytes: number;
  min_symbol: string;
  max_symbol: string;
}

export interface PriceManifest {
  symbols: number;
  bars: number;
  window_days: number;
  max_date: string;
  shards: PriceShard[];
}

export interface SiteManifest {
  schema: number;
  generated_at: number;
  universe_rows: number;
  snapshot_rows: number;
  snapshot_symbols: number;
  prices: PriceManifest | null;
  sample: string[];
  commit: string | null;
}

/** One daily bar — the drawer price chart's input. Fields are nullable
 *  because Stooq has no adjusted close and some sources omit volume. */
export interface PriceBar {
  date: string;
  open: number | null;
  high: number | null;
  low: number | null;
  close: number | null;
  adj_close: number | null;
  volume: number | null;
  source: string;
}

export class DslApiError extends Error {
  detail: DslErrorDetail;
  constructor(detail: DslErrorDetail) {
    super(detail.error);
    this.detail = detail;
  }
}

/** api mode navigates to a server URL; static mode hands back a Blob. */
export type CsvExport = { url: string } | { blob: Blob; filename: string };

export interface DataClient {
  screen(query: string, sort: string | null, page: number, pageSize: number): Promise<ScreenResponse>;
  exportCsv(query: string, sort: string | null, columns?: string[]): Promise<CsvExport>;
  presets(): Promise<Preset[]>;
  company(symbol: string): Promise<CompanyDetail | null>;
  status(): Promise<StatusResponse>;
  providers(): Promise<ProviderInfo[]>;
  search(q: string): Promise<SearchHit[]>;
  /** snapshot columns + coarse types — the query builder's field list */
  fields(): Promise<FieldInfo[]>;
  /** published daily bars for one symbol, oldest first — [] when it has none */
  prices(symbol: string): Promise<PriceBar[]>;
  /** static mode only — null while the nightly refresh has not published yet */
  manifest(): Promise<SiteManifest | null>;
}
