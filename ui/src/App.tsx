// FR-007 / T-016 — the one-window shell: wordmark · view pills · status
// pill · theme toggle, over the active view (screener / status).
// The company drawer is deep-linked at #/company/:symbol over the screener,
// and the screen itself is a permalink (#/?q=…&sort=…): refresh, bookmark
// and share restore the exact query and engine sort. Sorting and paging run
// in the engine — never a client-side sort of one fetched page. Errors keep
// the previous results visible; export downloads the FULL result set of the
// current query (all pages) via /api/screen.csv.

import { useEffect, useMemo, useRef, useState } from "react";
import {
  DslApiError,
  STATIC_MODE,
  exportCsv,
  fields,
  screen,
  status,
  type DslErrorDetail,
  type FieldInfo,
  type ScreenResponse,
  type StatusResponse,
} from "./data";
import { ColumnPicker } from "./components/ColumnPicker";
import { CompanyDrawer } from "./components/CompanyDrawer";
import { CoverageBanner } from "./components/CoverageBanner";
import { PresetsMenu } from "./components/PresetsMenu";
import { QueryBuilder } from "./components/QueryBuilder";
import { QueryBar } from "./components/QueryBar";
import { ResultsGrid } from "./components/ResultsGrid";
import { SearchBox } from "./components/SearchBox";
import { StatusView } from "./components/StatusView";
import { ThemeToggle } from "./components/ThemeToggle";
import { Wordmark } from "./components/Wordmark";
import { isHiddenField } from "./data/field-catalog";
import { fieldsInQuery } from "./dsl/fields";
import { pushQueryHistory } from "./query-history";
import { hashFor, parseHash, useHashRoute } from "./router";
import {
  applyTheme,
  effectiveTheme,
  loadThemePref,
  prefersLight,
  saveThemePref,
  watchSystemTheme,
} from "./theme";

export const DEFAULT_COLUMNS = [
  "symbol", "name", "country", "sector",
  "composite_rank", "piotroski_f", "altman_z", "beneish_m",
  "return_on_equity", "net_profit_margin", "debt_to_equity_ratio",
];
// a preset's curated columns REPLACE the visible set on top of this base
export const IDENTITY_COLUMNS = ["symbol", "name", "country", "sector"];
const DEFAULT_QUERY = "piotroski_f >= 7";
export const PAGE_SIZE = 500;

const VIEWS = [
  { view: "screener" as const, label: "Screener", hash: "#/" },
  { view: "status" as const, label: "Status", hash: "#/status" },
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
  const [themePref, setThemePref] = useState(() => loadThemePref());
  const [systemLight, setSystemLight] = useState(() => prefersLight());
  const theme = effectiveTheme(themePref, systemLight);
  const [query, setQuery] = useState(() => route.q ?? DEFAULT_QUERY);
  const [ranQuery, setRanQuery] = useState<string | null>(null);
  const [sort, setSort] = useState<string | null>(route.sort);
  const [page, setPage] = useState(1);
  const [result, setResult] = useState<ScreenResponse | null>(null);
  const [error, setError] = useState<DslErrorDetail | null>(null);
  const [running, setRunning] = useState(false);
  const [visibleColumns, setVisibleColumns] = useState<string[]>(DEFAULT_COLUMNS);
  const [statusData, setStatusData] = useState<StatusResponse | null>(null);
  const [statusLine, setStatusLine] = useState("");
  const [fieldInfos, setFieldInfos] = useState<FieldInfo[]>([]);
  const [exporting, setExporting] = useState(false);
  const queryInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => watchSystemTheme(() => setSystemLight(prefersLight())), []);

  useEffect(() => {
    applyTheme(theme);
    saveThemePref(themePref);
  }, [theme, themePref]);

  // The single screening entry point: runs the query in the engine and makes
  // the URL remember the screen (replace — a run is not a history entry).
  const runScreen = async (q: string, sortNext: string | null, pageNext: number) => {
    setRunning(true);
    setError(null);
    try {
      const response = await screen(q, sortNext, pageNext, PAGE_SIZE);
      setResult(response);
      setRanQuery(q);
      setSort(sortNext);
      setPage(pageNext);
      pushQueryHistory(q);
      // a screen always surfaces the fields it filtered on (union — never
      // removes what the user picked; chains after a preset's replace)
      setVisibleColumns((prev) => {
        const extra = fieldsInQuery(q).filter((field) => !prev.includes(field));
        return extra.length ? [...prev, ...extra] : prev;
      });
      // sync the URL from the CURRENT hash (never a stale closure): keep the
      // open drawer, and never hijack the status/providers views
      const current = parseHash(window.location.hash);
      if (current.view === "screener") {
        navigate({ ...current, q, sort: sortNext }, { replace: true });
      }
    } catch (err) {
      if (err instanceof DslApiError) setError(err.detail);
      else setError({ error: String(err), position: null, hint: "is the API reachable?" });
      // previous results intentionally stay visible
    } finally {
      setRunning(false);
    }
  };

  const run = (dsl?: string) => runScreen(dsl ?? query, sort, 1);

  const toggleSort = (column: string) => {
    const next = sort === `-${column}` ? column : sort === column ? null : `-${column}`;
    runScreen(ranQuery ?? query, next, 1);
  };

  useEffect(() => {
    runScreen(route.q ?? DEFAULT_QUERY, route.sort, 1);
    fields()
      .then((fs) => setFieldInfos(fs.filter((f) => !isHiddenField(f.name))))
      .catch(() => {});
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

  // A hand-edited or history-navigated URL re-runs its screen (the guard on
  // ranQuery breaks the loop: runScreen writes the same q back via replace).
  useEffect(() => {
    if (route.view !== "screener" || route.q === null || running) return;
    if (ranQuery !== null && route.q !== ranQuery) {
      setQuery(route.q);
      runScreen(route.q, route.sort, 1);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [route.q]);

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
        navigate({ ...route, company: null });
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [route]);

  const availableColumns = useMemo(
    () =>
      result?.rows.length
        ? Object.keys(result.rows[0]).filter((c) => !isHiddenField(c))
        : DEFAULT_COLUMNS,
    [result],
  );
  // symbol is the row's identity (and its keyboard path into the drawer) —
  // it stays visible no matter what the picker says
  const columns = [
    "symbol",
    ...visibleColumns.filter((c) => c !== "symbol" && availableColumns.includes(c)),
  ];

  const firstRun =
    statusData?.snapshot === false && !(result && result.total > 0);

  const totalPages = result ? Math.max(1, Math.ceil(result.total / PAGE_SIZE)) : 1;
  const firstRow = result ? (page - 1) * PAGE_SIZE + 1 : 0;
  const lastRow = result ? Math.min(page * PAGE_SIZE, result.total) : 0;

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
        <SearchBox
          onPick={(symbol) =>
            navigate({ view: route.view, company: symbol, q: route.q, sort: route.sort })
          }
        />
        <span className="status-pill">{statusLine}</span>
        <ThemeToggle pref={themePref} onPref={setThemePref} />
      </header>

      {STATIC_MODE && <CoverageBanner />}

      {route.view === "screener" && (
        <>
          <QueryBar
            value={query}
            onChange={setQuery}
            onRun={() => run()}
            running={running}
            error={firstRun ? null : error}
            inputRef={queryInputRef}
            fields={fieldInfos}
          />
          <QueryBuilder
            fields={fieldInfos}
            onApply={(dsl) => {
              setQuery(dsl);
              run(dsl);
            }}
          />
          <div className="toolbar">
            <PresetsMenu
              currentQuery={query}
              activeDsl={ranQuery}
              onPick={(preset) => {
                setQuery(preset.dsl);
                // curated columns replace the visible set (identity stays);
                // presets without one fall back to the DSL-union in runScreen
                if (preset.columns?.length) {
                  setVisibleColumns([...new Set([...IDENTITY_COLUMNS, ...preset.columns])]);
                }
                run(preset.dsl);
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
                {result.total === 0
                  ? "0 rows"
                  : `rows ${firstRow.toLocaleString("en-US")}–${lastRow.toLocaleString("en-US")} of ${result.total.toLocaleString("en-US")}`}
                {" · "}
                {result.tookMs} ms
                {result.hint ? ` · ${result.hint}` : ""}
              </span>
            )}
            {result && !firstRun && totalPages > 1 && (
              <span className="pager" role="group" aria-label="Result pages">
                <button
                  aria-label="Previous page"
                  disabled={running || page <= 1}
                  onClick={() => runScreen(ranQuery ?? query, sort, page - 1)}
                >
                  ‹
                </button>
                <span className="meta">
                  page {page} / {totalPages}
                </span>
                <button
                  aria-label="Next page"
                  disabled={running || page >= totalPages}
                  onClick={() => runScreen(ranQuery ?? query, sort, page + 1)}
                >
                  ›
                </button>
              </span>
            )}
            <button
              disabled={!ranQuery || !result?.total || exporting}
              onClick={async () => {
                if (ranQuery === null || exporting) return;
                setExporting(true);
                try {
                  const csv = await exportCsv(ranQuery, sort, columns);
                  if ("url" in csv) {
                    window.location.assign(csv.url);
                  } else {
                    const url = URL.createObjectURL(csv.blob);
                    const link = document.createElement("a");
                    link.href = url;
                    link.download = csv.filename;
                    link.click();
                    URL.revokeObjectURL(url);
                  }
                } catch (err) {
                  setError({
                    error: `export failed: ${String(err)}`,
                    position: null,
                    hint: "try again — the engine may still be loading",
                  });
                } finally {
                  setExporting(false);
                }
              }}
            >
              {exporting ? "Exporting…" : "Export all results (CSV)"}
            </button>
          </div>
          {firstRun && statusData ? (
            <FirstRun statusData={statusData} />
          ) : !result && running ? (
            /* the engine (DuckDB-WASM in static mode) is still booting — never
               show a false "No matching rows" as the first paint */
            <div className="grid-wrap" aria-busy="true">
              <p className="meta">Running the first screen…</p>
            </div>
          ) : (
            <ResultsGrid
              rows={result?.rows ?? []}
              columns={columns}
              selected={route.company}
              onSelect={(symbol) =>
                navigate({ view: "screener", company: symbol, q: ranQuery, sort })
              }
              sort={sort}
              onSort={toggleSort}
              hrefFor={(symbol) =>
                hashFor({ view: "screener", company: symbol, q: ranQuery, sort })
              }
            />
          )}
        </>
      )}

      {route.view === "status" && <StatusView pref={themePref} onPref={setThemePref} />}

      {route.company && (
        <CompanyDrawer
          symbol={route.company}
          onClose={() => navigate({ ...route, company: null })}
        />
      )}
    </div>
  );
}
