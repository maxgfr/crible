// DuckDB-WASM bootstrap (static mode) over a mocked engine — jsdom has no
// wasm: the EH bundle only (no MVP fallback shipped), snapshot_latest
// materialised ONCE at init, shard names SQL-escaped, and a failed init
// never leaks its worker.

import { beforeEach, describe, expect, it, vi } from "vitest";
import duckdbSource from "../data/duckdb.ts?raw";

const state = vi.hoisted(() => ({
  sql: [] as string[],
  failInstantiate: false,
  terminated: 0,
}));

vi.mock("@duckdb/duckdb-wasm", () => {
  class AsyncDuckDB {
    async instantiate() {
      if (state.failInstantiate) throw new Error("wasm instantiate failed");
    }
    async registerFileURL() {}
    async connect() {
      return {
        query: async (sql: string) => {
          state.sql.push(sql);
          return { toArray: () => [] };
        },
        prepare: async () => ({ query: async () => ({ toArray: () => [] }), close: async () => {} }),
      };
    }
  }
  return {
    AsyncDuckDB,
    VoidLogger: class {},
    DuckDBDataProtocol: { HTTP: 4 },
    selectBundle: async (bundles: Record<string, unknown>) => bundles.eh ?? bundles.mvp,
  };
});

class FakeWorker {
  constructor(public url: string) {}
  terminate() {
    state.terminated += 1;
  }
}

beforeEach(() => {
  state.sql.length = 0;
  state.failInstantiate = false;
  state.terminated = 0;
  vi.stubGlobal("Worker", FakeWorker);
});

describe("createDuckDbRunner", () => {
  it("materialises snapshot_latest once as a table, not a per-query view", async () => {
    const { createDuckDbRunner } = await import("../data/duckdb");
    await createDuckDbRunner("/");
    expect(state.sql.some((s) => /CREATE TABLE snapshot_latest AS/.test(s))).toBe(true);
    expect(state.sql.some((s) => /CREATE VIEW snapshot_latest/.test(s))).toBe(false);
  });

  it("escapes quotes in manifest shard names", async () => {
    const { createDuckDbRunner } = await import("../data/duckdb");
    await createDuckDbRunner("/", ["prices-00.parquet", "it's.parquet"]);
    const view = state.sql.find((s) => s.includes("CREATE VIEW prices"));
    expect(view).toContain("'it''s.parquet'");
  });

  it("terminates the worker when init fails", async () => {
    state.failInstantiate = true;
    const { createDuckDbRunner } = await import("../data/duckdb");
    await expect(createDuckDbRunner("/")).rejects.toThrow(/instantiate/);
    expect(state.terminated).toBe(1);
  });

  it("ships the EH bundle only — no MVP wasm in the static build", () => {
    expect(duckdbSource).not.toMatch(/duckdb-mvp|browser-mvp/);
  });
});

describe("self-hosted extensions", () => {
  it("loads parquet from the site's own duckdb-ext folder first", async () => {
    const { createDuckDbRunner } = await import("../data/duckdb");
    await createDuckDbRunner("/crible/");
    const set = state.sql.find((s) => s.startsWith("SET custom_extension_repository"));
    expect(set).toMatch(/\/crible\/duckdb-ext'$/);
    expect(state.sql.indexOf("LOAD parquet")).toBeGreaterThan(state.sql.indexOf(set!));
    expect(state.sql.indexOf("LOAD parquet")).toBeLessThan(
      state.sql.findIndex((s) => s.includes("read_parquet('snapshot.parquet')")),
    );
  });

  it("the pinned extension version is the one the wasm bundle carries", async () => {
    const { readFileSync } = await import("node:fs");
    const manifest = JSON.parse(readFileSync("duckdb-extensions.json", "utf8"));
    const wasm = readFileSync("node_modules/@duckdb/duckdb-wasm/dist/duckdb-eh.wasm");
    expect(wasm.includes(Buffer.from(manifest.duckdb))).toBe(true);
  });
});
