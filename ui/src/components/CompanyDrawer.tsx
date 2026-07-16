// FR-012 — company detail drawer: profile, period history, score component
// breakdowns (9 Piotroski criteria, 8 Beneish components, Altman inputs),
// provenance (provider + computed_at). Deep enough to explain every number.

import {
  Fragment,
  useEffect,
  useRef,
  useState,
  type CSSProperties,
  type KeyboardEvent as ReactKeyboardEvent,
  type PointerEvent as ReactPointerEvent,
} from "react";
import { company, requestFetch, STATIC_MODE, type CompanyDetail } from "../data";
import { fieldLabel } from "../data/field-catalog";
import { formatCell, formatNumber } from "../format";
import { PriceChart } from "./PriceChart";
import { SynthesisBlock } from "./SynthesisBlock";
import { TrendCharts } from "./TrendCharts";

interface Props {
  symbol: string;
  onClose: () => void;
}

const PIOTROSKI = [
  "piotroski_roa_positive", "piotroski_ocf_positive", "piotroski_roa_improving",
  "piotroski_accruals", "piotroski_leverage_decreasing", "piotroski_current_ratio_improving",
  "piotroski_no_dilution", "piotroski_gross_margin_improving", "piotroski_asset_turnover_improving",
];
const BENEISH = [
  "beneish_dsri", "beneish_gmi", "beneish_aqi", "beneish_sgi",
  "beneish_depi", "beneish_sgai", "beneish_tata", "beneish_lvgi",
];
const ALTMAN = ["altman_x1_wc_ta", "altman_x2_re_ta", "altman_x3_ebit_ta", "altman_x4_mve_tl", "altman_x5_s_ta"];
// Montier C: six red flags (0/1); unlike Piotroski, a raised flag is BAD
const MONTIER = [
  "montier_ni_cfo_diverging", "montier_dso_rising", "montier_dsi_rising",
  "montier_oca_to_rev_rising", "montier_depr_declining", "montier_asset_growth_high",
];
// Mohanram G (partial 6/8): peer-relative 0/1 signals, latest period only
const MOHANRAM = [
  "mohanram_g1_roa", "mohanram_g2_cfo_roa", "mohanram_g3_accruals",
  "mohanram_g4_roa_stability", "mohanram_g5_growth_stability", "mohanram_g6_capex_intensity",
];
// Dechow F (Model 1, accounting core): 7 components behind the logit
const DECHOW = [
  "dechow_rsst", "dechow_ch_rec", "dechow_ch_inv", "dechow_soft_assets",
  "dechow_ch_cs", "dechow_ch_roa", "dechow_issuance",
];
// value toolkit — each metric links back to the components it is built from
const VALUE_ROWS: [string, string][] = [
  ["Magic Formula rank", "magic_formula_rank"],
  ["· earnings yield (EBIT/EV)", "greenblatt_earnings_yield"],
  ["· return on capital", "greenblatt_roc"],
  ["Graham number", "graham_number"],
  ["· margin of safety", "graham_margin_of_safety"],
  ["NCAV (net-net)", "ncav"],
  ["· NCAV / market cap", "ncav_to_market_cap"],
];
// FR-015 — each pillar rank links back to the component values it ranks
const RANK_PILLARS: [string, string, string[]][] = [
  ["Quality", "quality_rank", ["piotroski_f", "altman_z"]],
  ["Value", "value_rank", ["earnings_yield", "price_to_book_ratio"]],
  ["Momentum", "momentum_rank", ["return_6m"]],
];
const STATEMENT_FIELDS = [
  "revenue", "gross_profit", "operating_income", "net_income",
  "total_assets", "total_equity", "total_debt", "operating_cashflow", "free_cash_flow",
];
// earnings backed by cash — the cash-quality preset's inputs + quality checks
const CASH_QUALITY = [
  "ebitda_margin", "fcf_margin", "fcf_conversion", "income_quality_ratio",
  "sloan_accruals", "rule_of_40", "capex_coverage_ratio", "dividend_coverage",
  "dividend_payout_ratio",
];
// the classic ratio families, grouped the way an analyst scans them
const KEY_RATIOS: [string, string[]][] = [
  ["Valuation", [
    "market_cap", "price_to_earnings_ratio", "peg_ratio", "price_to_book_ratio",
    "ev_to_ebitda_ratio", "ev_to_sales_ratio", "earnings_yield", "free_cash_flow_yield",
    "weighted_dividend_yield", "shareholder_yield",
  ]],
  ["Profitability", [
    "gross_margin", "operating_margin", "net_profit_margin", "return_on_assets",
    "return_on_equity", "return_on_capital_employed", "return_on_invested_capital",
  ]],
  ["Balance", [
    "current_ratio", "quick_ratio", "cash_ratio", "debt_to_equity_ratio",
    "net_debt_to_ebitda_ratio", "interest_coverage_ratio",
  ]],
  ["Efficiency", [
    "asset_turnover_ratio", "inventory_turnover_ratio", "days_of_sales_outstanding",
    "days_of_inventory_outstanding", "days_of_accounts_payable_outstanding",
    "cash_conversion_cycle", "sga_to_revenue_ratio",
  ]],
];
// year-over-year trajectory (signed + colored; debt growth reads inverted)
const GROWTH_FIELDS = [
  "revenue_growth", "net_income_growth", "operating_cashflow_growth",
  "free_cash_flow_growth", "total_debt_growth",
  "revenue_cagr_3y", "net_income_cagr_3y",
];
// price-derived, latest period only (never back-dated) — one shared rule
const MOMENTUM_FIELDS = ["return_6m", "return_12_1", "high_52w_proximity", "volatility_1y"];
// trailing 12 months — quarterly sums + price ratios, crawled tier only
const TTM_FIELDS = [
  "ttm_revenue", "ttm_net_income", "ttm_operating_cashflow", "ttm_free_cash_flow",
  "price_to_earnings_ttm", "price_to_sales_ttm", "ttm_fcf_yield",
];

// provenance ends at the SOURCE, not at a provider string: link the place
// the numbers actually come from (the audited filings when the layer is
// audited, the quote page for the scraped fallback)
const PROVENANCE_LINKS: Record<string, (symbol: string) => { href: string; label: string }> = {
  yfinance: (symbol) => ({
    href: `https://finance.yahoo.com/quote/${encodeURIComponent(symbol)}`,
    label: "view on Yahoo Finance",
  }),
  edgar: (symbol) => ({
    href: `https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=${encodeURIComponent(symbol.split(".")[0])}&type=10-K`,
    label: "view the SEC filings",
  }),
  fsds: (symbol) => ({
    href: `https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=${encodeURIComponent(symbol.split(".")[0])}&type=10-K`,
    label: "view the SEC filings",
  }),
  esef: () => ({
    href: "https://filings.xbrl.org/",
    label: "browse the ESEF filings repository",
  }),
};

// drawer size: a width the user dragged + an expanded toggle, both
// persisted (same try/catch contract as theme.ts — storage may not exist)
const DRAWER_KEY = "crible-drawer";
const DEFAULT_WIDTH = 560;
const MIN_WIDTH = 420;
const EXPANDED_WIDTH = "min(1100px, 96vw)";

interface DrawerPrefs {
  width: number;
  expanded: boolean;
}

function loadDrawerPrefs(): DrawerPrefs {
  try {
    const parsed = JSON.parse(window.localStorage.getItem(DRAWER_KEY) ?? "{}") as Partial<DrawerPrefs>;
    return {
      width: typeof parsed.width === "number" && Number.isFinite(parsed.width) ? parsed.width : DEFAULT_WIDTH,
      expanded: parsed.expanded === true,
    };
  } catch {
    /* storage unavailable or garbage — defaults */
    return { width: DEFAULT_WIDTH, expanded: false };
  }
}

function saveDrawerPrefs(prefs: DrawerPrefs): void {
  try {
    window.localStorage.setItem(DRAWER_KEY, JSON.stringify(prefs));
  } catch {
    /* non-persistent is fine */
  }
}

function clampWidth(width: number): number {
  return Math.min(Math.max(width, MIN_WIDTH), Math.round(window.innerWidth * 0.96));
}

function num(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "number") return formatNumber(value);
  if (typeof value === "boolean") return value ? "✓" : "✗";
  return String(value);
}

// a value with its verdict color + glyph (shared thresholds with the grid);
// booleans keep the plain ✓/✗ path
function Val({ column, value }: { column: string; value: unknown }) {
  if (typeof value === "boolean") return <>{value ? "✓" : "✗"}</>;
  const { text, className, flag } = formatCell(column, value);
  return (
    <span className={className || undefined}>
      {text}
      {flag && <span className="cell-flag">{flag}</span>}
    </span>
  );
}

export function CompanyDrawer({ symbol, onClose }: Props) {
  const [detail, setDetail] = useState<CompanyDetail | null | "loading">("loading");
  const [prefs, setPrefs] = useState<DrawerPrefs>(() => loadDrawerPrefs());
  const [dragging, setDragging] = useState(false);
  const closeRef = useRef<HTMLButtonElement>(null);

  // FR-012 — after an on-demand fetch is queued, poll until the ingest
  // service has crawled + computed (one loop cycle, ~1-3 min), then swap the
  // drawer content in place. Gives up after ~6 min (rate-limit, bad symbol).
  const [fetchState, setFetchState] = useState<"idle" | "queued" | "failed">("idle");

  useEffect(() => {
    setDetail("loading");
    setFetchState("idle");
    company(symbol).then(setDetail);
  }, [symbol]);

  useEffect(() => {
    if (fetchState !== "queued") return;
    const poll = setInterval(async () => {
      const fresh = await company(symbol);
      if (fresh && fresh.periods.length > 0) {
        setDetail(fresh);
        setFetchState("idle");
      }
    }, 20_000);
    const giveUp = setTimeout(() => setFetchState("failed"), 6 * 60_000);
    return () => {
      clearInterval(poll);
      clearTimeout(giveUp);
    };
  }, [fetchState, symbol]);

  // dialog semantics: focus moves in on open and back out on close
  useEffect(() => {
    const opener = document.activeElement as HTMLElement | null;
    closeRef.current?.focus();
    return () => opener?.focus?.();
  }, []);

  useEffect(() => {
    saveDrawerPrefs(prefs);
  }, [prefs]);

  // dragging the left edge resizes; a drag always leaves expanded mode so
  // the width under the pointer is the width you get
  const onResizeMove = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (!dragging) return;
    const width = clampWidth(window.innerWidth - event.clientX);
    setPrefs({ width, expanded: false });
  };

  const onResizeKey = (event: ReactKeyboardEvent<HTMLDivElement>) => {
    if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
    event.preventDefault();
    const delta = event.key === "ArrowLeft" ? 32 : -32; // the drawer grows leftward
    setPrefs((p) => ({ width: clampWidth(p.width + delta), expanded: false }));
  };

  return (
    <aside
      className={`drawer${prefs.expanded ? " expanded" : ""}${dragging ? " dragging" : ""}`}
      style={{ "--drawer-w": prefs.expanded ? EXPANDED_WIDTH : `${prefs.width}px` } as CSSProperties}
      role="dialog"
      aria-modal="true"
      aria-label={`${symbol} details`}
    >
      <div
        className="drawer-resize"
        role="separator"
        aria-orientation="vertical"
        aria-label="Resize drawer (arrow keys)"
        tabIndex={0}
        onPointerDown={(event) => {
          event.preventDefault();
          event.currentTarget.setPointerCapture?.(event.pointerId);
          setDragging(true);
        }}
        onPointerMove={onResizeMove}
        onPointerUp={() => setDragging(false)}
        onPointerCancel={() => setDragging(false)}
        onKeyDown={onResizeKey}
      />
      <button ref={closeRef} className="drawer-close" onClick={onClose}>
        Close
      </button>
      <button
        className="drawer-expand"
        aria-pressed={prefs.expanded}
        onClick={() => setPrefs((p) => ({ ...p, expanded: !p.expanded }))}
      >
        {prefs.expanded ? "Shrink" : "Expand"}
      </button>
      {detail === "loading" && <p className="meta">Loading {symbol}…</p>}
      {detail === null && <p className="meta">{symbol}: not in the universe.</p>}
      {detail && detail !== "loading" && (
        <>
          <h2>
            {String(detail.profile.name ?? symbol)}
            <span className="badge">{String(detail.profile.country ?? "?")}</span>
            <span className="badge">{String(detail.profile.sector ?? "?")}</span>
          </h2>
          <PriceChart symbol={symbol} />
          {detail.periods.length === 0 ? (
            <div className="teach">
              <p className="meta">
                Not crawled yet — universe metadata only. It is queued by region priority; watch
                coverage progress in the <a href="#/status">Status view</a>.
              </p>
              {!STATIC_MODE && fetchState === "idle" && (
                <button
                  className="fetch-now"
                  onClick={async () => {
                    try {
                      await requestFetch(symbol);
                      setFetchState("queued");
                    } catch {
                      setFetchState("failed");
                    }
                  }}
                >
                  Fetch this company now
                </button>
              )}
              {fetchState === "queued" && (
                <p className="meta" role="status">
                  Queued — the ingest service is fetching it (budget-charged). This drawer
                  refreshes by itself in a minute or two…
                </p>
              )}
              {fetchState === "failed" && (
                <p className="meta" role="status">
                  Nothing landed — the crawl may be rate-limited or the source empty. Try again
                  later.
                </p>
              )}
            </div>
          ) : (
            <>
              <SynthesisBlock latest={detail.periods[0]} periods={detail.periods} />
              <h3 id="drawer-statements" tabIndex={-1}>Statements</h3>
              <table>
                <thead>
                  <tr>
                    <th>field</th>
                    {detail.periods.map((p) => (
                      <th key={String(p.period)}>{String(p.period)}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {STATEMENT_FIELDS.map((field) => (
                    <tr key={field}>
                      <td>{field}</td>
                      {detail.periods.map((p) => (
                        <td key={String(p.period)}>{num(p[field])}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
              <h3 id="drawer-trends" tabIndex={-1}>Trends</h3>
              <TrendCharts periods={detail.periods} />
              <h3 id="drawer-cash" tabIndex={-1}>Cash quality</h3>
              <table>
                <tbody>
                  {CASH_QUALITY.map((field) => (
                    <tr key={field}>
                      <td>{fieldLabel(field)}</td>
                      {detail.periods.map((p) => (
                        <td key={String(p.period)}>
                          <Val column={field} value={p[field]} />
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
              <h3 id="drawer-ratios" tabIndex={-1}>Key ratios</h3>
              <table>
                <tbody>
                  {KEY_RATIOS.map(([group, fields]) => (
                    <Fragment key={group}>
                      <tr>
                        <td className="meta" colSpan={detail.periods.length + 1}>
                          {group}
                        </td>
                      </tr>
                      {fields.map((field) => (
                        <tr key={field}>
                          <td>{fieldLabel(field)}</td>
                          {detail.periods.map((p) => (
                            <td key={String(p.period)}>
                              <Val column={field} value={p[field]} />
                            </td>
                          ))}
                        </tr>
                      ))}
                    </Fragment>
                  ))}
                </tbody>
              </table>
              <h3 id="drawer-growth" tabIndex={-1}>Growth (YoY)</h3>
              <table>
                <tbody>
                  {GROWTH_FIELDS.map((field) => (
                    <tr key={field}>
                      <td>{fieldLabel(field)}</td>
                      {detail.periods.map((p) => (
                        <td key={String(p.period)}>
                          <Val column={field} value={p[field]} />
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
              <h3 id="drawer-momentum" tabIndex={-1}>Momentum</h3>
              <table>
                <tbody>
                  {MOMENTUM_FIELDS.map((field) => (
                    <tr key={field}>
                      <td>{fieldLabel(field)}</td>
                      <td>
                        <Val column={field} value={detail.periods[0][field]} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {detail.periods[0].ttm_revenue != null && (
                <>
                  <h3 id="drawer-ttm" tabIndex={-1}>TTM — trailing 12 months</h3>
                  <table>
                    <tbody>
                      {TTM_FIELDS.map((field) => (
                        <tr key={field}>
                          <td>{fieldLabel(field)}</td>
                          <td>
                            <Val column={field} value={detail.periods[0][field]} />
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  <p className="meta">
                    Last four reported quarters — fresher than the fiscal-year rows above;
                    crawled symbols plus audited US issuers reporting discrete quarters.
                  </p>
                </>
              )}
              <h3 id="drawer-scores" tabIndex={-1}>Scores — full breakdown</h3>
              <table>
                <tbody>
                  <tr>
                    <td>Piotroski F</td>
                    {detail.periods.map((p) => (
                      <td key={String(p.period)}>
                        <Val column="piotroski_f" value={p.piotroski_f} />
                      </td>
                    ))}
                  </tr>
                  {PIOTROSKI.map((criterion) => (
                    <tr key={criterion}>
                      <td className="meta">{criterion.replace("piotroski_", "· ")}</td>
                      {detail.periods.map((p) => (
                        <td key={String(p.period)}>{num(p[criterion])}</td>
                      ))}
                    </tr>
                  ))}
                  <tr>
                    <td>Altman Z</td>
                    {detail.periods.map((p) => (
                      <td key={String(p.period)}>
                        <Val column="altman_z" value={p.altman_z} />
                      </td>
                    ))}
                  </tr>
                  {ALTMAN.map((input) => (
                    <tr key={input}>
                      <td className="meta">{input.replace("altman_", "· ")}</td>
                      {detail.periods.map((p) => (
                        <td key={String(p.period)}>{num(p[input])}</td>
                      ))}
                    </tr>
                  ))}
                  <tr>
                    <td>Beneish M</td>
                    {detail.periods.map((p) => (
                      <td key={String(p.period)}>
                        <Val column="beneish_m" value={p.beneish_m} />
                      </td>
                    ))}
                  </tr>
                  {BENEISH.map((component) => (
                    <tr key={component}>
                      <td className="meta">{component.replace("beneish_", "· ")}</td>
                      {detail.periods.map((p) => (
                        <td key={String(p.period)}>{num(p[component])}</td>
                      ))}
                    </tr>
                  ))}
                  <tr>
                    <td>Zmijewski</td>
                    {detail.periods.map((p) => (
                      <td key={String(p.period)}>
                        <Val column="zmijewski_score" value={p.zmijewski_score} />
                      </td>
                    ))}
                  </tr>
                  <tr>
                    <td>Ohlson O</td>
                    {detail.periods.map((p) => (
                      <td key={String(p.period)}>
                        <Val column="ohlson_o" value={p.ohlson_o} />
                      </td>
                    ))}
                  </tr>
                  <tr>
                    <td>Montier C</td>
                    {detail.periods.map((p) => (
                      <td key={String(p.period)}>
                        <Val column="montier_c" value={p.montier_c} />
                      </td>
                    ))}
                  </tr>
                  {MONTIER.map((flag) => (
                    <tr key={flag}>
                      <td className="meta">{flag.replace("montier_", "· ")}</td>
                      {detail.periods.map((p) => (
                        <td key={String(p.period)}>{num(p[flag])}</td>
                      ))}
                    </tr>
                  ))}
                  <tr>
                    <td>Dechow F</td>
                    {detail.periods.map((p) => (
                      <td key={String(p.period)}>
                        <Val column="dechow_f" value={p.dechow_f} />
                      </td>
                    ))}
                  </tr>
                  {DECHOW.map((component) => (
                    <tr key={component}>
                      <td className="meta">{component.replace("dechow_", "· ")}</td>
                      {detail.periods.map((p) => (
                        <td key={String(p.period)}>{num(p[component])}</td>
                      ))}
                    </tr>
                  ))}
                  <tr>
                    <td>Mohanram G (6/8)</td>
                    {detail.periods.map((p) => (
                      <td key={String(p.period)}>
                        <Val column="mohanram_g" value={p.mohanram_g} />
                      </td>
                    ))}
                  </tr>
                  {MOHANRAM.map((signal) => (
                    <tr key={signal}>
                      <td className="meta">{signal.replace("mohanram_", "· ")}</td>
                      {detail.periods.map((p) => (
                        <td key={String(p.period)}>{num(p[signal])}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
              {detail.periods[0].composite_rank !== null &&
                detail.periods[0].composite_rank !== undefined && (
                  <>
                    <h3 id="drawer-rank" tabIndex={-1}>Rank — how it is built</h3>
                    <table>
                      <tbody>
                        <tr>
                          <td>Composite</td>
                          <td>
                            <Val column="composite_rank" value={detail.periods[0].composite_rank} />
                          </td>
                        </tr>
                        {RANK_PILLARS.map(([label, column, components]) => (
                          <Fragment key={column}>
                            <tr>
                              <td>{label}</td>
                              <td>
                                <Val column={column} value={detail.periods[0][column]} />
                              </td>
                            </tr>
                            {components.map((component) => (
                              <tr key={component}>
                                <td className="meta">· {component}</td>
                                <td>
                                  <Val column={component} value={detail.periods[0][component]} />
                                </td>
                              </tr>
                            ))}
                          </Fragment>
                        ))}
                      </tbody>
                    </table>
                    <p className="meta">
                      Percentiles 0–100 · peer group: {String(detail.periods[0].rank_peer_group ?? "global")}
                      {detail.periods[0].rank_missing_pillars
                        ? ` · ${String(detail.periods[0].rank_missing_pillars)} pillar omitted (missing input — never imputed)`
                        : ""}
                    </p>
                  </>
                )}
              {(detail.periods[0].graham_number != null ||
                detail.periods[0].magic_formula_rank != null) && (
                <>
                  <h3 id="drawer-value" tabIndex={-1}>Value — Greenblatt & Graham</h3>
                  <table>
                    <tbody>
                      {VALUE_ROWS.map(([label, column]) => (
                        <tr key={column}>
                          <td className={label.startsWith("·") ? "meta" : undefined}>{label}</td>
                          <td>
                            <Val column={column} value={detail.periods[0][column]} />
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  <p className="meta">
                    Latest fiscal period only — price-based metrics are never back-dated (missing price → —).
                  </p>
                </>
              )}
              <h3>Provenance</h3>
              <p className="meta">
                provider: {String(detail.periods[0].provider ?? "yfinance")} · computed at:{" "}
                {detail.periods[0].computed_at
                  ? new Date(Number(detail.periods[0].computed_at) * 1000).toISOString()
                  : "—"}
                {(() => {
                  const provider = String(detail.periods[0].provider ?? "yfinance");
                  const link = PROVENANCE_LINKS[provider]?.(symbol);
                  return link ? (
                    <>
                      {" · "}
                      <a href={link.href} target="_blank" rel="noreferrer">
                        {link.label}
                      </a>
                    </>
                  ) : null;
                })()}
              </p>
            </>
          )}
        </>
      )}
    </aside>
  );
}
