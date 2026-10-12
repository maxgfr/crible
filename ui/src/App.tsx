// FR-007 / T-016 — the one-window shell: wordmark · view pills · status
// pill · theme toggle, over the active view (screener / status).
// The company drawer is deep-linked at #/company/:symbol over the screener,
// and the screen itself is a permalink (#/?q=…&sort=…): refresh, bookmark
// and share restore the exact query and engine sort. Sorting and paging run
// in the engine — never a client-side sort of one fetched page. Errors keep
// the previous results visible; export downloads the FULL result set of the
// current query (all pages) via /api/screen.csv. Only the LATEST screen
// request may land: an older response arriving late is dropped whole.

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
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
// blank = the whole covered universe (q="" is a real, shareable screen);
// the default sort is the engine's own published blend so the first paint
// reads "every company, strongest composite first" — NULLS LAST sinks
// symbols with missing pillars, and an explicit ?sort= in the URL wins
const DEFAULT_QUERY = "";
export const DEFAULT_SORT = "-composite_rank";
export const PAGE_SIZE = 500;
// one shared empty page — a fresh [] per render would defeat the grid's memo
const NO_ROWS: Record<string, unknown>[] = [];

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
  const [sort, setSort] = useState<string | null>(route.sort ?? DEFAULT_SORT);
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
  // the id of the latest screen request — any other response is stale
  const reqId = useRef(0);
  // latest-value refs: callbacks read them without re-memoising per keystroke
  const queryRef = useRef(query);
  queryRef.current = query;
  const visibleRef = useRef(visibleColumns);
  visibleRef.current = visibleColumns;

  useEffect(() => watchSystemTheme(() => setSystemLight(prefersLight())), []);

  useEffect(() => {
    applyTheme(theme);
    saveThemePref(themePref);
  }, [theme, themePref]);

  // The single screening entry point: runs the query in the engine and makes
  // the URL remember the screen (replace — a run is not a history entry).
  // `extraColumns` are columns the caller is about to show (a preset's
  // curated set): static mode only reads what is asked for.
  const runScreen = useCallback(async (
    q: string,
    sortNext: string | null,
    pageNext: number,
    extraColumns: string[] = [],
  ) => {
    const id = ++reqId.current;
    setRunning(true);
    setError(null);
    const wanted = [...new Set([...visibleRef.current, ...extraColumns, ...fieldsInQuery(q)])];
    try {
      const response = await screen(q, sortNext, pageNext, PAGE_SIZE, wanted);
      // a newer screen was started meanwhile — it owns result, sort, page, URL
      if (id !== reqId.current) return;
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
      if (id !== reqId.current) return;
      if (err instanceof DslApiError) setError(err.detail);
      else {
        // only a failed fetch (TypeError) means the API is unreachable — an
        // HTTP error already carries the server's own detail
        const hint = err instanceof TypeError ? "is the API reachable?" : null;
        setError({ error: String(err), position: null, hint });
      }
      // previous results intentionally stay visible
    } finally {
      if (id === reqId.current) setRunning(false);
    }
  }, [navigate]);

  const run = (dsl?: string, extraColumns?: string[]) =>
    runScreen(dsl ?? query, sort, 1, extraColumns);

  const toggleSort = useCallback((column: string) => {
    // like Enter and the pager: a sort click never supersedes the screen in
    // flight (it would re-sort the OLD query and drop the one just run)
    if (running) return;
    const next = sort === `-${column}` ? column : sort === column ? null : `-${column}`;
    runScreen(ranQuery ?? queryRef.current, next, 1);
  }, [running, sort, ranQuery, runScreen]);

  const selectCompany = useCallback(
    (symbol: string) => navigate({ view: "screener", company: symbol, q: ranQuery, sort }),
    [navigate, ranQuery, sort],
  );

  const companyHref = useCallback(
    (symbol: string) => hashFor({ view: "screener", company: symbol, q: ranQuery, sort }),
    [ranQuery, sort],
  );

  useEffect(() => {
    runScreen(route.q ?? DEFAULT_QUERY, route.sort ?? DEFAULT_SORT, 1);
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

  // A hand-edited or history-navigated URL re-runs its screen — a new q OR
  // only a new sort. The comparison with what last ran breaks the loop
  // (runScreen writes the same q/sort back via replace); an edit made while
  // a screen runs simply supersedes it (reqId).
  useEffect(() => {
    if (route.view !== "screener" || route.q === null || ranQuery === null) return;
    if (route.q !== ranQuery || route.sort !== sort) {
      setQuery(route.q);
      runScreen(route.q, route.sort, 1);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [route.q, route.sort]);

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

  // what the picker can offer: the page's own keys plus the schema's field
  // list — static mode projects only the visible columns, so the rows alone
  // no longer describe the whole snapshot
  const availableColumns = useMemo(() => {
    if (!result?.rows.length) return DEFAULT_COLUMNS;
    const names = new Set(Object.keys(result.rows[0]));
    for (const field of fieldInfos) names.add(field.name);
    return [...names].filter((c) => !isHiddenField(c));
  }, [result, fieldInfos]);
  // symbol is the row's identity (and its keyboard path into the drawer) —
  // it stays visible no matter what the picker says
  const columns = useMemo(
    () => [
      "symbol",
      ...visibleColumns.filter((c) => c !== "symbol" && availableColumns.includes(c)),
    ],
    [visibleColumns, availableColumns],
  );

  // static mode: a column picked AFTER (or while) the screen ran was not read —
  // re-read the same page with it once the engine is idle (the API always
  // returns every column). One attempt per column set: a failing re-read must
  // not retry forever.
  const rereadFor = useRef("");
  useEffect(() => {
    if (!STATIC_MODE || running || ranQuery === null || !result?.rows.length) return;
    const have = result.rows[0];
    const missing = visibleColumns.filter((c) => !(c in have) && availableColumns.includes(c));
    const key = missing.join(",");
    if (missing.length && rereadFor.current !== key) {
      rereadFor.current = key;
      runScreen(ranQuery, sort, page);
    }
  }, [visibleColumns, running, result, ranQuery, sort, page, availableColumns, runScreen]);

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
                const curated = preset.columns?.length
                  ? [...new Set([...IDENTITY_COLUMNS, ...preset.columns])]
                  : [];
                if (curated.length) setVisibleColumns(curated);
                run(preset.dsl, curated);
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
              disabled={ranQuery === null || !result?.total || exporting}
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
              rows={result?.rows ?? NO_ROWS}
              columns={columns}
              query={ranQuery ?? undefined}
              selected={route.company}
              onSelect={selectCompany}
              sort={sort}
              onSort={toggleSort}
              hrefFor={companyHref}
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
