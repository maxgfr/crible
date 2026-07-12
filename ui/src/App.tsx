// FR-007 / T-016 — the one-window shell: wordmark · view pills · status
// pill · theme toggle, over the active view (screener / status / providers).
// The company drawer is deep-linked at #/company/:symbol over the screener.
// Errors keep the previous results visible; export downloads the FULL
// result set of the current query (all pages) via /api/screen.csv.

import { useEffect, useMemo, useRef, useState } from "react";
import {
  DslApiError,
  exportCsvUrl,
  screen,
  status,
  type DslErrorDetail,
  type ScreenResponse,
  type StatusResponse,
} from "./api";
import { ColumnPicker } from "./components/ColumnPicker";
import { CompanyDrawer } from "./components/CompanyDrawer";
import { PresetsMenu } from "./components/PresetsMenu";
import { ProvidersView } from "./components/ProvidersView";
import { QueryBar } from "./components/QueryBar";
import { ResultsGrid } from "./components/ResultsGrid";
import { StatusView } from "./components/StatusView";
import { ThemeToggle } from "./components/ThemeToggle";
import { Wordmark } from "./components/Wordmark";
import { useHashRoute } from "./router";
import { applyTheme, loadTheme, saveTheme, toggled } from "./theme";

const DEFAULT_COLUMNS = [
  "symbol", "name", "country", "sector",
  "piotroski_f", "altman_z", "beneish_m",
  "return_on_equity", "net_profit_margin", "debt_to_equity_ratio",
];
const DEFAULT_QUERY = "piotroski_f >= 7";

const VIEWS = [
  { view: "screener" as const, label: "Screener", hash: "#/" },
  { view: "status" as const, label: "Status", hash: "#/status" },
  { view: "providers" as const, label: "Providers", hash: "#/providers" },
];

function FirstRun({ statusData }: { statusData: StatusResponse }) {
  const coverage = statusData.ingest?.coverage_pct ?? 0;
  const crawled = statusData.ingest?.crawled;
  const universe = statusData.ingest?.universe ?? statusData.universe;
  return (
    <div className="grid-wrap">
      <div className="teach firstrun">
        <h3>The first crawl is running</h3>
        <p>
          <strong className="stat">{coverage} %</strong> of the universe covered
          {crawled !== undefined && universe
            ? ` — ${crawled.toLocaleString("en-US")} of ${universe.toLocaleString("en-US")} companies`
            : ""}
          .
        </p>
        <p>
          Screens return rows as soon as the first snapshot publishes, and grow with
          coverage. Watch progress in the <a href="#/status">Status view</a>.
        </p>
      </div>
    </div>
  );
}

export default function App() {
  const [route, navigate] = useHashRoute();
  const [theme, setTheme] = useState(() => loadTheme());
  const [query, setQuery] = useState(DEFAULT_QUERY);
  const [ranQuery, setRanQuery] = useState<string | null>(null);
  const [result, setResult] = useState<ScreenResponse | null>(null);
  const [error, setError] = useState<DslErrorDetail | null>(null);
  const [running, setRunning] = useState(false);
  const [visibleColumns, setVisibleColumns] = useState<string[]>(DEFAULT_COLUMNS);
  const [statusData, setStatusData] = useState<StatusResponse | null>(null);
  const [statusLine, setStatusLine] = useState("");
  const queryInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    applyTheme(theme);
    saveTheme(theme);
  }, [theme]);

  const run = async (dsl?: string) => {
    const q = dsl ?? query;
    setRunning(true);
    setError(null);
    try {
      const response = await screen(q, null, 1, 500);
      setResult(response);
      setRanQuery(q);
    } catch (err) {
      if (err instanceof DslApiError) setError(err.detail);
      else setError({ error: String(err), position: null, hint: "is the API reachable?" });
      // previous results intentionally stay visible
    } finally {
      setRunning(false);
    }
  };

  useEffect(() => {
    run(DEFAULT_QUERY);
    status()
      .then((s) => {
        setStatusData(s);
        const universe = s.universe ?? "?";
        const snapshot = s.snapshot ? "snapshot ✓" : "no snapshot yet";
        setStatusLine(`universe ${universe} · ${snapshot}`);
      })
      .catch(() => setStatusLine("api unreachable"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      const typing =
        target instanceof HTMLInputElement ||
        target instanceof HTMLTextAreaElement ||
        (target instanceof HTMLElement && target.isContentEditable);
      if (event.key === "/" && !typing && route.view === "screener" && !route.company) {
        event.preventDefault();
        queryInputRef.current?.focus();
      }
      if (event.key === "Escape" && route.company) {
        navigate({ view: route.view, company: null });
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [route]);

  const availableColumns = useMemo(
    () => (result?.rows.length ? Object.keys(result.rows[0]) : DEFAULT_COLUMNS),
    [result],
  );
  const columns = visibleColumns.filter((c) => availableColumns.includes(c));

  const firstRun =
    statusData?.snapshot === false && !(result && result.total > 0);

  return (
    <div className="app">
      <header className="topbar">
        <a className="wordmark-link" href="#/" aria-label="crible — screener">
          <Wordmark />
        </a>
        <nav className="views" aria-label="Views">
          {VIEWS.map((v) => (
            <a
              key={v.view}
              href={v.hash}
              aria-current={route.view === v.view ? "page" : undefined}
            >
              {v.label}
            </a>
          ))}
        </nav>
        <span className="spacer" />
        <span className="status-pill">{statusLine}</span>
        <ThemeToggle theme={theme} onToggle={() => setTheme((t) => toggled(t))} />
      </header>

      {route.view === "screener" && (
        <>
          <QueryBar
            value={query}
            onChange={setQuery}
            onRun={() => run()}
            running={running}
            error={firstRun ? null : error}
            inputRef={queryInputRef}
          />
          <div className="toolbar">
            <PresetsMenu
              currentQuery={query}
              onPick={(dsl) => {
                setQuery(dsl);
                run(dsl);
              }}
            />
            <ColumnPicker
              available={availableColumns}
              visible={visibleColumns}
              onChange={setVisibleColumns}
            />
            <span className="spacer" />
            {result && !firstRun && (
              <span className="meta">
                {result.rows.length} of {result.total} rows · {result.tookMs} ms
                {result.hint ? ` · ${result.hint}` : ""}
              </span>
            )}
            <a href={ranQuery ? exportCsvUrl(ranQuery, null, columns) : "#"}>
              <button disabled={!ranQuery || !result?.total}>Export all results (CSV)</button>
            </a>
          </div>
          {firstRun && statusData ? (
            <FirstRun statusData={statusData} />
          ) : (
            <ResultsGrid
              rows={result?.rows ?? []}
              columns={columns.length ? columns : ["symbol"]}
              selected={route.company}
              onSelect={(symbol) => navigate({ view: "screener", company: symbol })}
            />
          )}
        </>
      )}

      {route.view === "status" && <StatusView />}
      {route.view === "providers" && <ProvidersView theme={theme} onTheme={setTheme} />}

      {route.company && (
        <CompanyDrawer
          symbol={route.company}
          onClose={() => navigate({ view: route.view, company: null })}
        />
      )}
    </div>
  );
}
