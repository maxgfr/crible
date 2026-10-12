// The static data client behind the hosted screener: the SAME DataClient
// contract as api-client, but the DSL compiles in the browser (ui/src/dsl —
// golden-locked to the Python compiler) and queries run in DuckDB-WASM over
// the published Parquet artifacts. JSON surfaces (presets/status/providers/
// manifest) are plain files exported by `crible export-site`.

import { compileQuery, compileSort, fieldKind } from "../dsl/compiler";
import { DslError, parse } from "../dsl/parser";
import {
  DslApiError,
  type CompanyDetail,
  type CsvExport,
  type DataClient,
  type SiteManifest,
  type FieldInfo,
  type FunnelCount,
  type PriceBar,
  type Preset,
  type ProviderInfo,
  type QueryRunner,
  type ScreenResponse,
  type SearchHit,
  type StatusResponse,
} from "./types";

export type { QueryRunner } from "./types";

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

// the window column carrying the full match count on every page row
const TOTAL_COLUMN = "__total";

function csvCell(value: unknown): string {
  if (value === null || value === undefined) return "";
  let text = String(value);
  // company names are third-party text: a leading = + - @ would run as a
  // spreadsheet formula — neutralise it (numbers stay numbers)
  if (typeof value === "string" && /^[=+\-@]/.test(text)) text = `'${text}`;
  return /[",\r\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
}

// a cached promise must never cache a FAILURE: reset on rejection so the
// next call retries (a wasm/network blip is not fatal for the page's life)
function retryable<T>(make: () => Promise<T>): () => Promise<T> {
  let cached: Promise<T> | null = null;
  return () => {
    cached ??= make().catch((err: unknown) => {
      cached = null;
      throw err;
    });
    return cached;
  };
}

export function createStaticClient(options: StaticClientOptions = {}): DataClient {
  const base = options.baseUrl ?? import.meta.env.BASE_URL;
  const fetchImpl = options.fetchImpl ?? fetch.bind(globalThis);

  // a 404 is a real "not published yet" (cached); a network error is not —
  // it rejects inside, resolves null outside, and is retried next call
  const loadManifest = retryable(() =>
    fetchImpl(`${base}data/manifest.json`).then((r) =>
      r.ok ? (r.json() as Promise<SiteManifest>) : null,
    ),
  );
  const manifest = (): Promise<SiteManifest | null> => loadManifest().catch(() => null);

  // the DuckDB runner needs the price-shard list up front (views are created
  // at connect time) — resolve it from the manifest before booting DuckDB
  const makeRunner =
    options.runner ??
    (async () => {
      const shards = (await manifest())?.prices?.shards.map((s) => s.file) ?? [];
      return import("./duckdb").then((m) => m.createDuckDbRunner(base, shards));
    });

  const runner = retryable(makeRunner);

  // one DESCRIBE feeds both the DSL whitelist and the query builder's field
  // list — the two can never drift from the published schema
  const schema = retryable(() =>
    runner().then(async (r) => {
      const rows = await r.query("DESCRIBE snapshot_latest");
      return rows.map((row) => ({ name: String(row.column_name), kind: fieldKind(String(row.column_type ?? "")) }));
    }),
  );
  const describe = async () =>
    (await schema()).map((f) => ({
      name: f.name,
      type: f.kind === "string" ? ("string" as const) : ("number" as const),
    }));

  const whitelist = async (): Promise<Set<string>> => new Set((await schema()).map((f) => f.name));
  // field → kind: the compiler rejects a literal of the wrong type (422 parity)
  const fieldTypes = async (): Promise<Record<string, string>> =>
    Object.fromEntries((await schema()).map((f) => [f.name, f.kind]));

  const published = async (): Promise<boolean> => (await manifest()) !== null;

  const json = async <T>(name: string, fallback: T): Promise<T> => {
    try {
      const response = await fetchImpl(`${base}data/${name}`);
      return response.ok ? ((await response.json()) as T) : fallback;
    } catch {
      return fallback;
    }
  };

  // blank query = no filter (the grammar itself rejects empty input)
  const compileWhere = (
    query: string,
    fields: Set<string>,
    types: Record<string, string>,
  ): [string, (number | string)[]] => (query.trim() ? compileQuery(parse(query), fields, types) : ["TRUE", []]);

  // the exact 422 detail the FastAPI handler produces
  const asApiError = (err: unknown): unknown =>
    err instanceof DslError
      ? new DslApiError({ error: err.message, position: err.position, hint: err.hint })
      : err;

  const runScreen = async (
    query: string,
    sort: string | null,
    limit: number,
    offset: number,
    columns?: string[],
  ): Promise<{ rows: Record<string, unknown>[]; total: number }> => {
    const fields = await whitelist();
    const types = await fieldTypes();
    try {
      const [where, params] = compileWhere(query, fields, types);
      const order = compileSort(sort, fields);
      // project only what the grid shows (+ symbol, the row identity) —
      // whitelisted identifiers only, so quoting them is safe
      const projection = columns
        ? [...new Set(["symbol", ...columns])]
            .filter((c) => fields.has(c))
            .map((c) => `"${c}"`)
            .join(", ")
        : "*";
      const r = await runner();
      // rows + the full match count in ONE pass: the window runs before LIMIT
      const rows = await r.query(
        `SELECT ${projection}, count(*) OVER () AS "${TOTAL_COLUMN}"` +
          ` FROM snapshot_latest WHERE ${where}${order} LIMIT ${limit} OFFSET ${offset}`,
        params,
      );
      let total = Number(rows[0]?.[TOTAL_COLUMN] ?? 0);
      if (rows.length === 0 && offset > 0) {
        // past the last page: no row carries the count — ask for it alone
        const counted = await r.query(
          `SELECT count(*) AS total FROM snapshot_latest WHERE ${where}`,
          params,
        );
        total = Number(counted[0]?.total ?? 0);
      }
      const clean = rows.map((row) => {
        const { [TOTAL_COLUMN]: _total, ...rest } = row;
        return normalizeRow(rest);
      });
      return { rows: clean, total };
    } catch (err) {
      throw asApiError(err);
    }
  };

  // the zero-result funnel in ONE aggregate scan: a count_if per clause
  // alone and per cumulative prefix — instead of 2 screens per clause
  const runFunnel = async (clauses: string[]): Promise<FunnelCount[]> => {
    const fields = await whitelist();
    const types = await fieldTypes();
    try {
      const compiled = clauses.map((clause) => compileWhere(clause, fields, types));
      const selects: string[] = [];
      const params: (number | string)[] = [];
      compiled.forEach(([where, clauseParams], i) => {
        selects.push(`count_if(${where}) AS alone_${i}`);
        params.push(...clauseParams);
        const prefix = compiled.slice(0, i + 1);
        selects.push(
          `count_if(${prefix.map(([w]) => `(${w})`).join(" AND ")}) AS cumulative_${i}`,
        );
        for (const [, p] of prefix) params.push(...p);
      });
      const r = await runner();
      const [row] = await r.query(`SELECT ${selects.join(", ")} FROM snapshot_latest`, params);
      const out: FunnelCount[] = [];
      for (let i = 0; i < clauses.length; i += 1) {
        const cumulative = Number(row?.[`cumulative_${i}`] ?? 0);
        out.push({ clause: clauses[i], alone: Number(row?.[`alone_${i}`] ?? 0), cumulative });
        if (cumulative === 0) break; // same shape as the API path
      }
      return out;
    } catch (err) {
      throw asApiError(err);
    }
  };

  return {
    manifest,

    async screen(query, sort, page, pageSize, columns): Promise<ScreenResponse> {
      if (!(await published())) {
        return { rows: [], total: 0, page, tookMs: 0, hint: NOT_PUBLISHED_HINT };
      }
      const started = performance.now();
      const limit = Math.min(pageSize, MAX_LIMIT);
      const { rows, total } = await runScreen(query, sort, limit, (page - 1) * pageSize, columns);
      const tookMs = Math.round((performance.now() - started) * 100) / 100;
      return { rows, total, page, tookMs };
    },

    async funnel(clauses): Promise<FunnelCount[]> {
      if (clauses.length === 0 || !(await published())) return [];
      return runFunnel(clauses);
    },

    async exportCsv(query, sort, columns): Promise<CsvExport> {
      const { rows } = await runScreen(query, sort, MAX_LIMIT, 0, columns?.length ? columns : undefined);
      const keep =
        columns && columns.length
          ? columns.filter((c) => rows.length === 0 || c in rows[0])
          : Object.keys(rows[0] ?? {});
      const lines = [keep.map(csvCell).join(",")];
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
