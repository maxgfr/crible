// The static data client behind the GitHub Pages demo: the SAME DataClient
// contract as api-client, but the DSL compiles in the browser (ui/src/dsl —
// golden-locked to the Python compiler) and queries run in DuckDB-WASM over
// the published Parquet artifacts. JSON surfaces (presets/status/providers/
// manifest) are plain files exported by `crible export-site`.

import { compileQuery, compileSort } from "../dsl/compiler";
import { DslError, parse } from "../dsl/parser";
import {
  DslApiError,
  type CompanyDetail,
  type CsvExport,
  type DataClient,
  type DemoManifest,
  type Preset,
  type ProviderInfo,
  type ScreenResponse,
  type SearchHit,
  type StatusResponse,
} from "./types";

export interface QueryRunner {
  query(sql: string, params?: unknown[]): Promise<Record<string, unknown>[]>;
}

export interface StaticClientOptions {
  runner?: () => Promise<QueryRunner>;
  fetchImpl?: typeof fetch;
  baseUrl?: string;
}

const MAX_LIMIT = 10_000; // mirrors crible.store.MAX_LIMIT
const NOT_PUBLISHED_HINT =
  "demo data not published yet — the nightly refresh publishes the first snapshot";

function normalizeValue(value: unknown): unknown {
  if (typeof value === "bigint") return Number(value);
  return value;
}

function normalizeRow(row: Record<string, unknown>): Record<string, unknown> {
  return Object.fromEntries(Object.entries(row).map(([k, v]) => [k, normalizeValue(v)]));
}

function csvCell(value: unknown): string {
  if (value === null || value === undefined) return "";
  const text = String(value);
  return /[",\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
}

export function createStaticClient(options: StaticClientOptions = {}): DataClient {
  const base = options.baseUrl ?? import.meta.env.BASE_URL;
  const fetchImpl = options.fetchImpl ?? fetch.bind(globalThis);
  const makeRunner =
    options.runner ?? (() => import("./duckdb").then((m) => m.createDuckDbRunner(base)));

  let runnerPromise: Promise<QueryRunner> | null = null;
  let manifestPromise: Promise<DemoManifest | null> | null = null;
  let whitelistPromise: Promise<Set<string>> | null = null;

  const manifest = (): Promise<DemoManifest | null> => {
    manifestPromise ??= fetchImpl(`${base}data/manifest.json`)
      .then((r) => (r.ok ? (r.json() as Promise<DemoManifest>) : null))
      .catch(() => null);
    return manifestPromise;
  };

  const runner = (): Promise<QueryRunner> => {
    runnerPromise ??= makeRunner();
    return runnerPromise;
  };

  const whitelist = async (): Promise<Set<string>> => {
    whitelistPromise ??= runner().then(async (r) => {
      const rows = await r.query("DESCRIBE snapshot_latest");
      return new Set(rows.map((row) => String(row.column_name)));
    });
    return whitelistPromise;
  };

  const published = async (): Promise<boolean> => (await manifest()) !== null;

  const json = async <T>(name: string, fallback: T): Promise<T> => {
    try {
      const response = await fetchImpl(`${base}data/${name}`);
      return response.ok ? ((await response.json()) as T) : fallback;
    } catch {
      return fallback;
    }
  };

  const runScreen = async (
    query: string,
    sort: string | null,
    limit: number,
    offset: number,
  ): Promise<{ rows: Record<string, unknown>[]; total: number }> => {
    const fields = await whitelist();
    try {
      const [where, params] = compileQuery(parse(query), fields);
      const order = compileSort(sort, fields);
      const r = await runner();
      const rows = await r.query(
        `SELECT * FROM snapshot_latest WHERE ${where}${order} LIMIT ${limit} OFFSET ${offset}`,
        params,
      );
      const counted = await r.query(
        `SELECT count(*) AS total FROM snapshot_latest WHERE ${where}`,
        params,
      );
      return { rows: rows.map(normalizeRow), total: Number(counted[0]?.total ?? 0) };
    } catch (err) {
      if (err instanceof DslError) {
        // the exact 422 detail the FastAPI handler produces
        throw new DslApiError({ error: err.message, position: err.position, hint: err.hint });
      }
      throw err;
    }
  };

  return {
    manifest,

    async screen(query, sort, page, pageSize): Promise<ScreenResponse> {
      if (!(await published())) {
        return { rows: [], total: 0, page, tookMs: 0, hint: NOT_PUBLISHED_HINT };
      }
      const started = performance.now();
      const limit = Math.min(pageSize, MAX_LIMIT);
      const { rows, total } = await runScreen(query, sort, limit, (page - 1) * pageSize);
      const tookMs = Math.round((performance.now() - started) * 100) / 100;
      return { rows, total, page, tookMs };
    },

    async exportCsv(query, sort, columns): Promise<CsvExport> {
      const { rows } = await runScreen(query, sort, MAX_LIMIT, 0);
      const keep =
        columns && columns.length
          ? columns.filter((c) => rows.length === 0 || c in rows[0])
          : Object.keys(rows[0] ?? {});
      const lines = [keep.join(",")];
      for (const row of rows) lines.push(keep.map((c) => csvCell(row[c])).join(","));
      const blob = new Blob([lines.join("\n") + "\n"], { type: "text/csv" });
      return { blob, filename: "crible-screen.csv" };
    },

    async presets(): Promise<Preset[]> {
      return json<Preset[]>("presets.json", []);
    },

    async company(symbol): Promise<CompanyDetail | null> {
      if (!(await published())) return null;
      const r = await runner();
      const profiles = await r.query("SELECT * FROM universe WHERE symbol = ?", [symbol]);
      const periods = await r.query(
        "SELECT * FROM snapshot_all WHERE symbol = ? ORDER BY period DESC",
        [symbol],
      );
      if (profiles.length === 0 && periods.length === 0) return null;
      const profile =
        profiles.length > 0
          ? normalizeRow(profiles[0])
          : Object.fromEntries(
              ["symbol", "name", "country", "region", "sector"].map((k) => [
                k,
                normalizeRow(periods[0])[k] ?? null,
              ]),
            );
      return { profile, periods: periods.map(normalizeRow) };
    },

    async status(): Promise<StatusResponse> {
      if (!(await published())) return { snapshot: false };
      return json<StatusResponse>("status.json", { snapshot: false });
    },

    async providers(): Promise<ProviderInfo[]> {
      return json<ProviderInfo[]>("providers.json", []);
    },

    async search(q): Promise<SearchHit[]> {
      if (!q.trim() || !(await published())) return [];
      const r = await runner();
      const rows = await r.query(
        "SELECT symbol, name, country, sector FROM universe" +
          " WHERE symbol ILIKE ? OR name ILIKE ? ORDER BY symbol LIMIT ?",
        [`%${q.trim()}%`, `%${q.trim()}%`, 20],
      );
      return rows.map(normalizeRow) as unknown as SearchHit[];
    },
  };
}
