// The static (DuckDB-WASM) data client behind the hosted screener: same
// contract as the FastAPI client — same response shapes, same DslApiError
// detail — over an injected query runner (no wasm in jsdom) and static JSON.

import { beforeEach, describe, expect, it, vi } from "vitest";
import { createStaticClient } from "../data/static-client";
import type { QueryRunner } from "../data/static-client";
import { DslApiError } from "../data/types";

// name → DuckDB column type, as DESCRIBE reports them
const SCHEMA: Record<string, string> = {
  symbol: "VARCHAR", name: "VARCHAR", country: "VARCHAR", sector: "VARCHAR",
  piotroski_f: "BIGINT", altman_z: "DOUBLE", period: "VARCHAR",
};
const WHITELIST = Object.keys(SCHEMA);

const ROWS = [
  { symbol: "AIR.PA", name: "Airbus, SAS", country: "FR", sector: "Industrials", piotroski_f: 8n },
  { symbol: "SAP.DE", name: "SAP", country: "DE", sector: "Tech", piotroski_f: 7 },
];

const PROFILE = { symbol: "AIR.PA", name: "Airbus", country: "FR", region: "europe", sector: "Industrials" };

function scriptedRunner() {
  const calls: { sql: string; params: unknown[] }[] = [];
  const runner: QueryRunner = {
    async query(sql: string, params: unknown[] = []) {
      calls.push({ sql, params });
      if (sql.startsWith("DESCRIBE")) {
        return WHITELIST.map((c) => ({ column_name: c, column_type: SCHEMA[c] }));
      }
      if (sql.includes("count(*)")) return [{ total: 2n }];
      if (sql.includes("FROM snapshot_all")) {
        return params[0] === "AIR.PA" ? [{ symbol: "AIR.PA", period: "2025", piotroski_f: 8 }] : [];
      }
      if (sql.includes("FROM universe") && sql.includes("ILIKE")) {
        return [{ symbol: "AIR.PA", name: "Airbus", country: "FR", sector: "Industrials" }];
      }
      if (sql.includes("FROM universe")) {
        return params[0] === "AIR.PA" || params[0] === "NOFIN.PA" ? [PROFILE] : [];
      }
      if (sql.includes("FROM prices")) {
        return params[0] === "AIR.PA"
          ? [
              { date: "2026-03-02", open: 100, high: 101, low: 99, close: 100.5,
                adj_close: 100.4, volume: 1000n, source: "yfinance" },
            ]
          : [];
      }
      return ROWS;
    },
  };
  return { runner, calls };
}

function stubFetch(files: Record<string, unknown>) {
  const impl = vi.fn(async (url: string) => {
    const name = String(url).split("/").pop() ?? "";
    if (name in files) return { ok: true, status: 200, json: async () => files[name] };
    return { ok: false, status: 404, json: async () => ({}) };
  });
  return impl as unknown as typeof fetch;
}

const PRICES_BLOCK = {
  symbols: 1, bars: 1, window_days: 400, max_date: "2026-03-02",
  shards: [{ file: "prices-00.parquet", rows: 1, bytes: 512, min_symbol: "AIR.PA", max_symbol: "AIR.PA" }],
};
const FILES = {
  "manifest.json": { schema: 2, generated_at: 1e9, snapshot_symbols: 2, prices: PRICES_BLOCK },
  "presets.json": [{ id: "quality", name: "Quality", description: "d", dsl: "piotroski_f >= 7" }],
  "status.json": { universe: 8, snapshot: true, ingest: { coverage_pct: 1.2 } },
  "providers.json": [{ id: "yfinance", kind: "keyless", key_env_var: null, enabled: true }],
};

function makeClient(runner: QueryRunner, files: Record<string, unknown> = FILES) {
  return createStaticClient({ runner: async () => runner, fetchImpl: stubFetch(files), baseUrl: "/" });
}

beforeEach(() => vi.restoreAllMocks());

describe("static client — screen", () => {
  it("compiles the DSL locally, binds params, paginates, normalizes BigInt", async () => {
    const { runner, calls } = scriptedRunner();
    const client = makeClient(runner);
    const result = await client.screen("piotroski_f >= 7", null, 1, 500);

    expect(result.total).toBe(2);
    expect(result.page).toBe(1);
    expect(typeof result.tookMs).toBe("number");
    expect(result.rows[0].piotroski_f).toBe(8); // BigInt → number
    const select = calls.find((c) => c.sql.includes("SELECT * FROM snapshot_latest"));
    expect(select?.sql).toContain('"piotroski_f" >= ?');
    expect(select?.sql).toContain("LIMIT 500 OFFSET 0");
    expect(select?.params).toEqual([7]);
  });

  it("applies page/page_size like the server (offset = (page-1)*size)", async () => {
    const { runner, calls } = scriptedRunner();
    const client = makeClient(runner);
    await client.screen("piotroski_f >= 7", null, 3, 100);
    const select = calls.find((c) => c.sql.includes("SELECT * FROM snapshot_latest"));
    expect(select?.sql).toContain("LIMIT 100 OFFSET 200");
  });

  it("screens the full snapshot when the query is blank — no filter", async () => {
    const { runner, calls } = scriptedRunner();
    const result = await makeClient(runner).screen("   ", null, 1, 500);
    expect(result.total).toBe(2);
    expect(result.rows).toHaveLength(2);
    const select = calls.find((c) => c.sql.includes("SELECT * FROM snapshot_latest"));
    expect(select?.sql).toContain("WHERE TRUE");
    expect(select?.params).toEqual([]);
  });

  it("throws the same DslApiError detail shape as the API", async () => {
    const { runner } = scriptedRunner();
    const client = makeClient(runner);
    const err = await client.screen("piotroski > 7", null, 1, 500).then(
      () => null,
      (e) => e,
    );
    expect(err).toBeInstanceOf(DslApiError);
    expect(err.detail.error).toContain("unknown field 'piotroski'");
    expect(err.detail.position).toBe(0);
    expect(err.detail.hint).toBe("did you mean 'piotroski_f'?");
  });
});

describe("static client — company / search", () => {
  it("returns profile + periods DESC for a crawled symbol", async () => {
    const { runner, calls } = scriptedRunner();
    const client = makeClient(runner);
    const detail = await client.company("AIR.PA");
    expect(detail?.profile.symbol).toBe("AIR.PA");
    expect(detail?.periods).toHaveLength(1);
    const periods = calls.find((c) => c.sql.includes("FROM snapshot_all"));
    expect(periods?.sql).toContain("ORDER BY period DESC");
    expect(periods?.params).toEqual(["AIR.PA"]);
  });

  it("returns empty periods for a universe-only symbol and null for unknown", async () => {
    const { runner } = scriptedRunner();
    const client = makeClient(runner);
    const universeOnly = await client.company("NOFIN.PA");
    expect(universeOnly?.periods).toEqual([]);
    expect(await client.company("NOPE")).toBeNull();
  });

  it("searches the universe by symbol/name substring", async () => {
    const { runner, calls } = scriptedRunner();
    const client = makeClient(runner);
    const hits = await client.search("air");
    expect(hits).toEqual([{ symbol: "AIR.PA", name: "Airbus", country: "FR", sector: "Industrials" }]);
    const search = calls.find((c) => c.sql.includes("ILIKE"));
    expect(search?.params).toEqual(["%air%", "%air%", 20]);
  });
});

describe("static client — CSV export", () => {
  it("exports the full result set as a Blob with the selected columns, quoted", async () => {
    const { runner, calls } = scriptedRunner();
    const client = makeClient(runner);
    const result = await client.exportCsv("piotroski_f >= 7", null, ["symbol", "name"]);
    expect("blob" in result).toBe(true);
    if (!("blob" in result)) throw new Error("expected blob");
    expect(result.filename).toBe("crible-screen.csv");
    // jsdom's Blob has no .text() — read through FileReader instead
    const text = await new Promise<string>((resolve) => {
      const reader = new FileReader();
      reader.onload = () => resolve(String(reader.result));
      reader.readAsText(result.blob);
    });
    expect(text.split("\n")[0]).toBe("symbol,name");
    expect(text).toContain('"Airbus, SAS"'); // comma → quoted
    const select = calls.find((c) => c.sql.includes("SELECT * FROM snapshot_latest"));
    expect(select?.sql).toContain("LIMIT 10000");
  });
});

describe("static client — fields", () => {
  it("derives the query builder field list from one DESCRIBE (types included)", async () => {
    const { runner, calls } = scriptedRunner();
    const client = makeClient(runner);
    const fields = await client.fields();
    const byName = Object.fromEntries(fields.map((f) => [f.name, f.type]));
    expect(byName.symbol).toBe("string");
    expect(byName.piotroski_f).toBe("number");
    expect(byName.altman_z).toBe("number");
    // the whitelist reuses the same DESCRIBE — screens don't re-describe
    await client.screen("piotroski_f >= 7", null, 1, 10);
    expect(calls.filter((c) => c.sql.startsWith("DESCRIBE"))).toHaveLength(1);
  });

  it("returns no fields while the dataset is not published yet", async () => {
    const { runner } = scriptedRunner();
    const client = makeClient(runner, {}); // every fetch 404s
    expect(await client.fields()).toEqual([]);
  });
});

describe("static client — prices", () => {
  it("queries the prices view and normalizes BigInt volume", async () => {
    const { runner, calls } = scriptedRunner();
    const client = makeClient(runner);
    const bars = await client.prices("AIR.PA");
    expect(bars).toEqual([
      { date: "2026-03-02", open: 100, high: 101, low: 99, close: 100.5,
        adj_close: 100.4, volume: 1000, source: "yfinance" },
    ]);
    const query = calls.find((c) => c.sql.includes("FROM prices"));
    expect(query?.sql).toContain("ORDER BY date");
    expect(query?.params).toEqual(["AIR.PA"]);
  });

  it("returns [] for a symbol with no series", async () => {
    const { runner } = scriptedRunner();
    const client = makeClient(runner);
    expect(await client.prices("NOPE")).toEqual([]);
  });

  it("returns [] when the manifest carries no prices block", async () => {
    const { runner, calls } = scriptedRunner();
    const noPrices = { ...FILES, "manifest.json": { schema: 2, generated_at: 1e9, snapshot_symbols: 2, prices: null } };
    const client = makeClient(runner, noPrices);
    expect(await client.prices("AIR.PA")).toEqual([]);
    expect(calls.find((c) => c.sql.includes("FROM prices"))).toBeUndefined();
  });
});

describe("static client — JSON surfaces", () => {
  it("serves presets/status/providers from the exported files", async () => {
    const { runner } = scriptedRunner();
    const client = makeClient(runner);
    expect((await client.presets())[0].id).toBe("quality");
    expect((await client.status()).universe).toBe(8);
    expect((await client.providers())[0].id).toBe("yfinance");
  });

  it("degrades gracefully when the dataset is not published yet", async () => {
    const { runner } = scriptedRunner();
    const client = makeClient(runner, {}); // every fetch 404s
    const status = await client.status();
    expect(status.snapshot).toBe(false);
    const result = await client.screen("piotroski_f >= 7", null, 1, 500);
    expect(result.rows).toEqual([]);
    expect(result.total).toBe(0);
    expect(result.hint).toContain("not published yet");
    expect(await client.presets()).toEqual([]);
    expect(await client.company("AIR.PA")).toBeNull();
    expect(await client.search("air")).toEqual([]);
  });
});
