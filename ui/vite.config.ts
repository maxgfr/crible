/// <reference types="vitest/config" />
import { mkdir, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { defineConfig, type Plugin } from "vite";
import react from "@vitejs/plugin-react";
import extensions from "./duckdb-extensions.json";

const STATIC_MODE = (process.env.VITE_DATA_MODE ?? "api") === "static";

// Static mode: DuckDB-WASM loads its parquet extension at runtime. Fetched
// from extensions.duckdb.org it breaks behind a blocker, a CSP or offline, so
// the build copies the (signed, unmodified) extension next to the site and
// the runtime points custom_extension_repository at it.
function selfHostDuckDbExtensions(): Plugin {
  let outDir = "dist";
  return {
    name: "crible-self-host-duckdb-extensions",
    apply: "build",
    configResolved(config) {
      outDir = config.build.outDir;
    },
    async closeBundle() {
      if (!STATIC_MODE) return;
      for (const name of extensions.extensions) {
        const path = `${extensions.duckdb}/${extensions.platform}/${name}.duckdb_extension.wasm`;
        const response = await fetch(`https://extensions.duckdb.org/${path}`);
        if (!response.ok) throw new Error(`duckdb extension ${path}: HTTP ${response.status}`);
        const target = join(outDir, "duckdb-ext", path);
        await mkdir(dirname(target), { recursive: true });
        await writeFile(target, Buffer.from(await response.arrayBuffer()));
      }
    },
  };
}

// FR-007 — SPA served by the FastAPI api service in production (ui/dist).
// The GitHub Pages demo builds with VITE_BASE=/crible/ VITE_DATA_MODE=static.
export default defineConfig({
  base: process.env.VITE_BASE ?? "/",
  // literal replacement so the unused mode's client (and duckdb-wasm's ~77 MB
  // of assets) is dead-branch-eliminated from the build entirely
  define: {
    "import.meta.env.VITE_DATA_MODE": JSON.stringify(process.env.VITE_DATA_MODE ?? "api"),
  },
  plugins: [react(), selfHostDuckDbExtensions()],
  server: {
    proxy: {
      "/api": "http://localhost:8000",
      "/healthz": "http://localhost:8000",
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test-setup.ts"],
  },
});
