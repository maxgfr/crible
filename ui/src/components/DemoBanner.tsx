// Static (GitHub Pages) mode only — says exactly what this demo is: the real
// screener running in the browser on DuckDB-WASM, refreshed nightly from
// keyless open sources, fundamentals limited to the bootstrap sample.

import { useEffect, useState } from "react";
import { manifest, type DemoManifest } from "../data";

const REPO = "https://github.com/maxgfr/crible";

export function DemoBanner() {
  const [data, setData] = useState<DemoManifest | null | "loading">("loading");

  useEffect(() => {
    manifest().then(setData).catch(() => setData(null));
  }, []);

  if (data === "loading") return null;

  if (data === null) {
    return (
      <div className="demo-banner" role="note">
        <strong>Demo:</strong> data not published yet — the nightly refresh publishes the
        first snapshot. <a href={REPO}>Self-host the full screener →</a>
      </div>
    );
  }

  const refreshed = new Date(data.generated_at * 1000).toISOString().slice(0, 10);
  return (
    <div className="demo-banner" role="note">
      <strong>In-browser demo</strong> — DuckDB-WASM over open data (yfinance ·
      FinanceDatabase · filings.xbrl.org · GLEIF), refreshed nightly ({refreshed}).
      Fundamentals cover a {data.snapshot_symbols}-company sample of the{" "}
      {data.universe_rows.toLocaleString("en-US")}-listing universe —{" "}
      <a href={REPO}>self-host for the full crawl →</a>
    </div>
  );
}
