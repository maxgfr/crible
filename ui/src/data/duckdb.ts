// DuckDB-WASM bootstrap for the static demo — self-hosted bundles (Vite ?url
// imports, no CDN: the demo stays fully served from GitHub Pages) reading the
// published Parquet artifacts over HTTP range requests. The snapshot_latest
// view is copied verbatim from crible/runtime.py:mount_snapshot.

import * as duckdb from "@duckdb/duckdb-wasm";
import wasmMvp from "@duckdb/duckdb-wasm/dist/duckdb-mvp.wasm?url";
import wasmEh from "@duckdb/duckdb-wasm/dist/duckdb-eh.wasm?url";
import workerMvp from "@duckdb/duckdb-wasm/dist/duckdb-browser-mvp.worker.js?url";
import workerEh from "@duckdb/duckdb-wasm/dist/duckdb-browser-eh.worker.js?url";
import type { QueryRunner } from "./static-client";

const BUNDLES: duckdb.DuckDBBundles = {
  mvp: { mainModule: wasmMvp, mainWorker: workerMvp },
  eh: { mainModule: wasmEh, mainWorker: workerEh },
};

export async function createDuckDbRunner(base: string): Promise<QueryRunner> {
  const bundle = await duckdb.selectBundle(BUNDLES);
  const worker = new Worker(bundle.mainWorker!);
  const db = new duckdb.AsyncDuckDB(new duckdb.VoidLogger(), worker);
  await db.instantiate(bundle.mainModule, bundle.pthreadWorker);

  const url = (name: string) => new URL(`${base}data/${name}`, document.baseURI).href;
  await db.registerFileURL(
    "universe.parquet", url("universe.parquet"), duckdb.DuckDBDataProtocol.HTTP, false,
  );
  await db.registerFileURL(
    "snapshot.parquet", url("snapshot.parquet"), duckdb.DuckDBDataProtocol.HTTP, false,
  );

  const conn = await db.connect();
  await conn.query("CREATE VIEW universe AS SELECT * FROM read_parquet('universe.parquet')");
  await conn.query("CREATE VIEW snapshot_all AS SELECT * FROM read_parquet('snapshot.parquet')");
  await conn.query(`
    CREATE VIEW snapshot_latest AS
    SELECT * EXCLUDE (_rn) FROM (
        SELECT s.*,
               row_number() OVER (PARTITION BY s.symbol ORDER BY s.period DESC) AS _rn
        FROM snapshot_all s
    ) WHERE _rn = 1
  `);

  return {
    async query(sql: string, params: unknown[] = []): Promise<Record<string, unknown>[]> {
      if (params.length === 0) {
        const table = await conn.query(sql);
        return table.toArray().map((row) => row.toJSON() as Record<string, unknown>);
      }
      const statement = await conn.prepare(sql);
      try {
        const table = await statement.query(...params);
        return table.toArray().map((row) => row.toJSON() as Record<string, unknown>);
      } finally {
        await statement.close();
      }
    },
  };
}
