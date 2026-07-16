// T-019 — the crawl observatory: coverage %, freshness histogram, req/h
// vs budget gauge, provider health, last-cycle failures, ESEF matching.
// Hand-rolled SVG on tokens (no chart lib); skeletons while loading;
// the no-heartbeat state teaches instead of showing nothing. The page
// also hosts the Appearance section — whatever state the crawl is in,
// that section never disappears. (The provider inventory is deliberately
// NOT in the UI: sources are an operator concern, docs/DATA-SOURCES.md.)

import { useEffect, useState } from "react";
import { status, type StatusResponse } from "../data";
import type { ThemePref } from "../theme";
import { AppearanceSection } from "./AppearanceSection";

interface Props {
  pref: ThemePref;
  onPref: (pref: ThemePref) => void;
}

const FRESHNESS_ORDER = ["<7d", "<30d", "<90d", "stale", "never"];

function Bars({ data }: { data: { label: string; value: number; warn?: boolean }[] }) {
  const max = Math.max(1, ...data.map((d) => d.value));
  return (
    <table className="bars">
      <tbody>
        {data.map((d) => (
          <tr key={d.label}>
            <th scope="row">{d.label}</th>
            <td className="bars-track">
              <svg aria-hidden="true" width="100%" height="10" preserveAspectRatio="none">
                <rect
                  className={d.warn ? "bar warn" : "bar"}
                  x="0"
                  y="1"
                  height="8"
                  width={`${Math.max(0.5, (100 * d.value) / max)}%`}
                />
              </svg>
            </td>
            <td className="bars-count">{d.value.toLocaleString("en-US")}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function Skeleton() {
  return (
    <div className="view-body" aria-busy="true">
      {[0, 1, 2].map((i) => (
        <div key={i} className="skeleton-block" />
      ))}
    </div>
  );
}

const REFRESH_MS = 30_000;

export function StatusView({ pref, onPref }: Props) {
  const [data, setData] = useState<StatusResponse | null>(null);
  const [failed, setFailed] = useState(false);
  const [fetchedAt, setFetchedAt] = useState<number | null>(null);

  // the observatory stays live: an operator watching a crawl should never
  // have to hammer reload — refresh every 30 s while the tab is visible
  useEffect(() => {
    let alive = true;
    const load = () =>
      status()
        .then((s) => {
          if (!alive) return;
          setData(s);
          setFetchedAt(Date.now());
          setFailed(false);
        })
        .catch(() => alive && setFailed(true));
    load();
    const interval = setInterval(() => {
      if (!document.hidden) load();
    }, REFRESH_MS);
    return () => {
      alive = false;
      clearInterval(interval);
    };
  }, []);

  return (
    <section className="view">
      <h2>Status</h2>
      {failed ? (
        <div className="error-banner" role="alert">
          API unreachable — is the api service running on :8000?
        </div>
      ) : !data ? (
        <Skeleton />
      ) : !data.ingest || Object.keys(data.ingest).length === 0 ? (
        <div className="teach">
          <p>
            No crawl heartbeat yet. The ingest service writes{" "}
            <code>data/status.json</code> once it starts.
          </p>
          <p>
            Start the stack with <code>docker compose up</code> — the universe
            bootstraps first, then the Europe-first crawl begins.
          </p>
        </div>
      ) : (
        <Observatory data={data} fetchedAt={fetchedAt} />
      )}
      <AppearanceSection pref={pref} onPref={onPref} />
    </section>
  );
}

function Observatory({ data, fetchedAt }: { data: StatusResponse; fetchedAt: number | null }) {
  const ingest = data.ingest ?? {};
  const freshness = FRESHNESS_ORDER.filter((b) => ingest.freshness?.[b] !== undefined).map(
    (b) => ({ label: b, value: ingest.freshness?.[b] ?? 0, warn: b === "stale" }),
  );
  const used = ingest.requests_last_hour ?? 0;
  const budget = ingest.budget_per_hour ?? 0;
  const budgetPct = budget > 0 ? Math.min(100, (100 * used) / budget) : 0;

  return (
    <>
      <p className="meta">
        {ingest.ts
          ? `crawl heartbeat ${new Date(Number(ingest.ts) * 1000).toISOString().replace("T", " ").slice(0, 19)} UTC · `
          : ""}
        view refreshed{" "}
        {fetchedAt ? new Date(fetchedAt).toISOString().slice(11, 19) : "—"} UTC · auto-refreshes
        every 30 s
      </p>
      <div className="view-body status-columns">
        <div>
          <h3>Coverage</h3>
          <p className="stat-line">
            <strong className="stat">{ingest.coverage_pct ?? 0} %</strong>
            <span className="meta">
              {(ingest.crawled ?? 0).toLocaleString("en-US")} of{" "}
              {(ingest.universe ?? data.universe ?? 0).toLocaleString("en-US")} companies crawled
              · snapshot {data.snapshot ? "published" : "pending"}
            </span>
          </p>
          {data.by_region && (
            <table className="kv">
              <tbody>
                {Object.entries(data.by_region).map(([region, count]) => (
                  <tr key={region}>
                    <th scope="row">{region}</th>
                    <td>{count.toLocaleString("en-US")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          <h3>Freshness</h3>
          {freshness.length ? <Bars data={freshness} /> : <p className="meta">no crawl data yet</p>}
        </div>

        <div>
          <h3>Rate budget</h3>
          <p className="stat-line">
            <strong className="stat">
              {used} / {budget}
            </strong>
            <span className="meta">requests last hour vs hourly budget</span>
          </p>
          <svg aria-hidden="true" className="gauge" width="100%" height="10" preserveAspectRatio="none">
            <rect className="gauge-track" x="0" y="1" width="100%" height="8" />
            <rect className="gauge-fill" x="0" y="1" width={`${budgetPct}%`} height="8" />
          </svg>

          <h3>Provider health</h3>
          <table className="kv">
            <tbody>
              {Object.entries(ingest.providers ?? {}).map(([id, health]) => (
                <tr key={id}>
                  <th scope="row">{id}</th>
                  <td>
                    <span className={health === "healthy" ? "pill pill-ok" : "pill pill-warn"}>
                      {health}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          <h3>Last cycle</h3>
          <table className="kv">
            <tbody>
              <tr>
                <th scope="row">fetched</th>
                <td>{ingest.last_cycle?.fetched ?? 0}</td>
              </tr>
              <tr>
                <th scope="row">failed</th>
                <td className={ingest.last_cycle?.failed ? "num-bad" : ""}>
                  {ingest.last_cycle?.failed ?? 0}
                </td>
              </tr>
              {ingest.esef_resolved !== undefined && (
                <tr>
                  <th scope="row">ESEF matched</th>
                  <td>{ingest.esef_resolved}</td>
                </tr>
              )}
              {ingest.esef_unmatched !== undefined && (
                <tr>
                  <th scope="row">ESEF unmatched</th>
                  <td className={ingest.esef_unmatched ? "num-warn" : ""}>{ingest.esef_unmatched}</td>
                </tr>
              )}
              {ingest.edgar_resolved !== undefined && (
                <tr>
                  <th scope="row">EDGAR matched</th>
                  <td>{ingest.edgar_resolved}</td>
                </tr>
              )}
              {ingest.edgar_unmatched !== undefined && (
                <tr>
                  <th scope="row">EDGAR unmatched</th>
                  <td className={ingest.edgar_unmatched ? "num-warn" : ""}>{ingest.edgar_unmatched}</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}
