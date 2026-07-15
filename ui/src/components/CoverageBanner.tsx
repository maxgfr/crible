// Static-mode coverage line: a neutral, honest statement of what the hosted
// screener currently covers — the real screener running in the browser on
// DuckDB-WASM, refreshed nightly from keyless open sources. No upsell.

import { useEffect, useState } from "react";
import { manifest, type SiteManifest } from "../data";

export function CoverageBanner() {
  const [data, setData] = useState<SiteManifest | null | "loading">("loading");

  useEffect(() => {
    manifest().then(setData).catch(() => setData(null));
  }, []);

  if (data === "loading") return null;

  if (data === null) {
    return (
      <div className="coverage-banner" role="note">
        Dataset not published yet — the nightly refresh publishes the first snapshot.
      </div>
    );
  }

  const refreshed = new Date(data.generated_at * 1000).toISOString().slice(0, 10);
  const universe = data.universe_rows.toLocaleString("en-US");
  const priceCoverage = data.prices
    ? ` · daily prices for ${data.prices.symbols.toLocaleString("en-US")}`
    : "";
  const REGION_LABEL: Record<string, string> = { europe: "EU", us: "US", world: "world" };
  const byRegion = data.snapshot_by_region
    ? ` (${Object.entries(data.snapshot_by_region)
        .filter(([, n]) => n > 0)
        .map(([region, n]) => `${REGION_LABEL[region] ?? region} ${n.toLocaleString("en-US")}`)
        .join(" · ")})`
    : "";
  return (
    <div className="coverage-banner" role="note">
      Fundamentals for {data.snapshot_symbols.toLocaleString("en-US")} companies{byRegion} —
      audited filings (SEC · ESEF) plus a polite crawl, growing nightly{priceCoverage} · all{" "}
      {universe} listings searchable · refreshed {refreshed} · runs entirely in your browser
      (DuckDB-WASM) · <a href="#/status">why not everything?</a>
    </div>
  );
}
