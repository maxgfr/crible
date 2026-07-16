// The static data client behind the hosted screener: the SAME DataClient
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
  type SiteManifest,
  type FieldInfo,
  type PriceBar,
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
  "dataset not published yet — the nightly refresh publishes the first snapshot";

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

  let runnerPromise: Promise<QueryRunner> | null = null;
  let manifestPromise: Promise<SiteManifest | null> | null = null;
  let describePromise: Promise<FieldInfo[]> | null = null;

  const manifest = (): Promise<SiteManifest | null> => {
    manifestPromise ??= fetchImpl(`${base}data/manifest.json`)
      .then((r) => (r.ok ? (r.json() as Promise<SiteManifest>) : null))
      .catch(() => null);
    return manifestPromise;
  };

  // the DuckDB runner needs the price-shard list up front (views are created
  // at connect time) — resolve it from the manifest before booting DuckDB
  const makeRunner =
    options.runner ??
    (async () => {
      const shards = (await manifest())?.prices?.shards.map((s) => s.file) ?? [];
      return import("./duckdb").then((m) => m.createDuckDbRunner(base, shards));
    });

  const runner = (): Promise<QueryRunner> => {
    runnerPromise ??= makeRunner();
    return runnerPromise;
  };

  // one DESCRIBE feeds both the DSL whitelist and the query builder's field
  // list — the two can never drift from the published schema
  const describe = (): Promise<FieldInfo[]> => {
    describePromise ??= runner().then(async (r) => {
      const rows = await r.query("DESCRIBE snapshot_latest");
      return rows.map((row) => ({
        name: String(row.column_name),
        type: String(row.column_type ?? "").toUpperCase().includes("VARCHAR")
          ? ("string" as const)
          : ("number" as const),
      }));
    });
    return describePromise;
  };

  const whitelist = async (): Promise<Set<string>> =>
    new Set((await describe()).map((f) => f.name));

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
      // blank query = no filter (the grammar itself rejects empty input)
      const [where, params] = query.trim()
        ? compileQuery(parse(query), fields)
        : (["TRUE", []] as [string, (number | string)[]]);
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

    async fields(): Promise<FieldInfo[]> {
      if (!(await published())) return [];
      return describe();
    },

    async prices(symbol): Promise<PriceBar[]> {
      // no prices block → no `prices` view was registered; nothing to query
      if (!(await manifest())?.prices) return [];
      const r = await runner();
      // strftime in SQL keeps the shape byte-identical to the API contract
      const rows = await r.query(
        "SELECT strftime(date, '%Y-%m-%d') AS date, open, high, low, close," +
          " adj_close, volume, source FROM prices WHERE symbol = ? ORDER BY date",
        [symbol],
      );
      return rows.map(normalizeRow) as unknown as PriceBar[];
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

    async requestFetch(): Promise<never> {
      // the hosted demo has no ingest service behind it — the drawer hides
      // the button in static mode, this is only the honest contract
      throw new Error("on-demand fetch needs a self-hosted ingest service");
    },
  };
}
