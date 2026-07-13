// The data seam. VITE_DATA_MODE=static (the GitHub Pages demo) resolves the
// DuckDB-WASM client through a dynamic import — dead-branch-eliminated from
// the default api build, code-split into a lazy chunk in static builds. The
// self-hosted bundle is byte-for-byte unaffected.

import { apiClient } from "./api-client";
import type {
  CompanyDetail,
  CsvExport,
  DataClient,
  DemoManifest,
  FieldInfo,
  Preset,
  ProviderInfo,
  ScreenResponse,
  SearchHit,
  StatusResponse,
} from "./types";

export const STATIC_MODE = import.meta.env.VITE_DATA_MODE === "static";

let clientPromise: Promise<DataClient> | null = null;

export function getClient(): Promise<DataClient> {
  if (clientPromise === null) {
    clientPromise =
      import.meta.env.VITE_DATA_MODE === "static"
        ? import("./static-client").then((m) => m.createStaticClient())
        : Promise.resolve(apiClient);
  }
  return clientPromise;
}

export async function screen(
  query: string,
  sort: string | null,
  page: number,
  pageSize: number,
): Promise<ScreenResponse> {
  return (await getClient()).screen(query, sort, page, pageSize);
}

export async function exportCsv(
  query: string,
  sort: string | null,
  columns?: string[],
): Promise<CsvExport> {
  return (await getClient()).exportCsv(query, sort, columns);
}

export async function presets(): Promise<Preset[]> {
  return (await getClient()).presets();
}

export async function company(symbol: string): Promise<CompanyDetail | null> {
  return (await getClient()).company(symbol);
}

export async function status(): Promise<StatusResponse> {
  return (await getClient()).status();
}

export async function providers(): Promise<ProviderInfo[]> {
  return (await getClient()).providers();
}

export async function search(q: string): Promise<SearchHit[]> {
  return (await getClient()).search(q);
}

export async function fields(): Promise<FieldInfo[]> {
  return (await getClient()).fields();
}

export async function manifest(): Promise<DemoManifest | null> {
  return (await getClient()).manifest();
}

export { DslApiError } from "./types";
export type {
  CompanyDetail,
  CsvExport,
  DataClient,
  DemoManifest,
  DslErrorDetail,
  FieldInfo,
  IngestHeartbeat,
  Preset,
  ProviderInfo,
  ScreenResponse,
  SearchHit,
  StatusResponse,
} from "./types";
