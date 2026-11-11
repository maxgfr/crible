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

  // the manifest is published data, not code: a missing field drops its
  // clause — it threw a RangeError here and took the whole app down
  const count = (n: unknown) => (typeof n === "number" && Number.isFinite(n) ? n.toLocaleString("en-US") : null);
  const stamp = typeof data.generated_at === "number" ? new Date(data.generated_at * 1000) : null;
  const refreshed = stamp && !Number.isNaN(stamp.getTime()) ? ` · refreshed ${stamp.toISOString().slice(0, 10)}` : "";
  const universe = count(data.universe_rows);
  const searchable = universe ? ` · all ${universe} listings searchable` : "";
  const companies = count(data.snapshot_symbols) ?? "the covered";
  const priceSymbols = count(data.prices?.symbols);
  const priceCoverage = priceSymbols ? ` · daily prices for ${priceSymbols}` : "";
  const REGION_LABEL: Record<string, string> = { europe: "EU", us: "US", world: "world" };
  const byRegion = data.snapshot_by_region
    ? ` (${Object.entries(data.snapshot_by_region)
        .filter(([, n]) => typeof n === "number" && n > 0)
        .map(([region, n]) => `${REGION_LABEL[region] ?? region} ${n.toLocaleString("en-US")}`)
        .join(" · ")})`
    : "";
  return (
    <div className="coverage-banner" role="note">
      Fundamentals for {companies} companies{byRegion} — audited filings (SEC · ESEF) plus a
      polite crawl, growing nightly{priceCoverage}{searchable}{refreshed} · runs entirely in
      your browser (DuckDB-WASM) · <a href="#/status">why not everything?</a>
    </div>
  );
}
