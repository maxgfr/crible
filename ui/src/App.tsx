// FR-007 — the screener shell: query bar + presets + grid + export + drawer.
// Errors keep the previous results visible; export downloads the FULL result
// set of the current query (all pages) via /api/screen.csv.

import { useEffect, useMemo, useState } from "react";
import {
  DslApiError,
  exportCsvUrl,
  screen,
  status,
  type DslErrorDetail,
  type ScreenResponse,
} from "./api";
import { ColumnPicker } from "./components/ColumnPicker";
import { CompanyDrawer } from "./components/CompanyDrawer";
import { PresetsMenu } from "./components/PresetsMenu";
import { QueryBar } from "./components/QueryBar";
import { ResultsGrid } from "./components/ResultsGrid";

const DEFAULT_COLUMNS = [
  "symbol", "name", "country", "sector",
  "piotroski_f", "altman_z", "beneish_m",
  "return_on_equity", "net_profit_margin", "debt_to_equity_ratio",
];
const DEFAULT_QUERY = "piotroski_f >= 7";

export default function App() {
  const [query, setQuery] = useState(DEFAULT_QUERY);
  const [ranQuery, setRanQuery] = useState<string | null>(null);
  const [result, setResult] = useState<ScreenResponse | null>(null);
  const [error, setError] = useState<DslErrorDetail | null>(null);
  const [running, setRunning] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);
  const [visibleColumns, setVisibleColumns] = useState<string[]>(DEFAULT_COLUMNS);
  const [statusLine, setStatusLine] = useState("");

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
        const universe = s.universe ?? "?";
        const snapshot = s.snapshot ? "snapshot ✓" : "no snapshot yet";
        setStatusLine(`universe ${universe} · ${snapshot}`);
      })
      .catch(() => setStatusLine("api unreachable"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const availableColumns = useMemo(
    () => (result?.rows.length ? Object.keys(result.rows[0]) : DEFAULT_COLUMNS),
    [result],
  );
  const columns = visibleColumns.filter((c) => availableColumns.includes(c));

  return (
    <div className="app">
      <header className="topbar">
        <h1>crible</h1>
        <span className="status-pill">{statusLine}</span>
      </header>
      <QueryBar
        value={query}
        onChange={setQuery}
        onRun={() => run()}
        running={running}
        error={error}
      />
      <div className="toolbar">
        <PresetsMenu
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
        {result && (
          <span className="meta">
            {result.rows.length} of {result.total} rows · {result.tookMs} ms
            {result.hint ? ` · ${result.hint}` : ""}
          </span>
        )}
        <a href={ranQuery ? exportCsvUrl(ranQuery, null) : "#"}>
          <button disabled={!ranQuery || !result?.total}>Export all results (CSV)</button>
        </a>
      </div>
      <ResultsGrid
        rows={result?.rows ?? []}
        columns={columns.length ? columns : ["symbol"]}
        onSelect={setSelected}
      />
      {selected && <CompanyDrawer symbol={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}
