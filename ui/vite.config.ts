/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// FR-007 — SPA served by the FastAPI api service in production (ui/dist).
// The GitHub Pages demo builds with VITE_BASE=/crible/ VITE_DATA_MODE=static.
export default defineConfig({
  base: process.env.VITE_BASE ?? "/",
  // literal replacement so the unused mode's client (and duckdb-wasm's ~77 MB
  // of assets) is dead-branch-eliminated from the build entirely
  define: {
    "import.meta.env.VITE_DATA_MODE": JSON.stringify(process.env.VITE_DATA_MODE ?? "api"),
  },
  plugins: [react()],
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
