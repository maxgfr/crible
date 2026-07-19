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
import { LiveQuote } from "./LiveQuote";
import { PeriodRow, PeriodTable, sparsePeriodFlags, STATEMENT_FIELDS } from "./PeriodTable";
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
// each headline score unfolds into its component rows (· prefix strips the
// score's own column prefix, e.g. piotroski_roa_positive → · roa_positive)
const SCORES: [string, string, string[]][] = [
  ["Piotroski F", "piotroski_f", PIOTROSKI],
  ["Altman Z", "altman_z", ALTMAN],
  ["Beneish M", "beneish_m", BENEISH],
  ["Zmijewski", "zmijewski_score", []],
  ["Ohlson O", "ohlson_o", []],
  ["Montier C", "montier_c", MONTIER],
  ["Dechow F", "dechow_f", DECHOW],
  ["Mohanram G (6/8)", "mohanram_g", MOHANRAM],
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

// listing currency (universe metadata, merged onto every period row) — the
// currency every price-denominated figure is quoted in; never converted here
function listingCurrency(detail: CompanyDetail): string | undefined {
  for (const candidate of [detail.profile.currency, detail.periods[0]?.currency]) {
    if (typeof candidate === "string" && candidate) return candidate;
  }
  return undefined;
}

// the published close's as-of date on the latest period — the live-quote
// chip's staleness input; null when the snapshot carries no price
function priceAsof(detail: CompanyDetail): string | null {
  const raw = detail.periods[0]?.price_asof;
  return typeof raw === "string" && raw ? raw : null;
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
          <LiveQuote symbol={symbol} asof={priceAsof(detail)} />
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
            <DrawerSections symbol={symbol} detail={detail} />
          )}
          {detail.periods.length === 0 && (
            <PriceChart symbol={symbol} currency={listingCurrency(detail)} />
          )}
        </>
      )}
    </aside>
  );
}

// every section below the price chart — the period tables. Extracted so the
// shared column context (sparse flags, listing currency, the latest-period
// header label) is computed once for all of them.
function DrawerSections({ symbol, detail }: { symbol: string; detail: CompanyDetail }) {
  const periods = detail.periods;
  const latest = periods[0];
  const sparse = sparsePeriodFlags(periods);
  const currency = listingCurrency(detail);
  // money rows carry the listing currency on the LABEL — one mention per row,
  // never per cell
  const money = (label: string) => (currency ? `${label} (${currency})` : label);
  const latestOnly = [latest];
  const latestLabels = [`latest — ${String(latest.period)}`];

  return (
            <>
              <SynthesisBlock latest={latest} periods={periods} />
              <h3 id="drawer-statements" tabIndex={-1}>Statements</h3>
              <PeriodTable periods={periods} sparse={sparse}>
                {STATEMENT_FIELDS.map((field) => (
                  <PeriodRow
                    key={field}
                    label={field}
                    periods={periods}
                    sparse={sparse}
                    cell={(p) => num(p[field])}
                  />
                ))}
              </PeriodTable>
              {sparse.some(Boolean) && (
                <p className="meta table-note">
                  Greyed columns: the sources publish ~4–5 fiscal years, and YoY/average
                  metrics need the prior year — the oldest (rightmost) columns carry no
                  fundamentals.
                </p>
              )}
              <h3 id="drawer-cash" tabIndex={-1}>Cash quality</h3>
              <PeriodTable periods={periods} sparse={sparse}>
                {CASH_QUALITY.map((field) => (
                  <PeriodRow
                    key={field}
                    label={fieldLabel(field)}
                    periods={periods}
                    sparse={sparse}
                    cell={(p) => <Val column={field} value={p[field]} />}
                  />
                ))}
              </PeriodTable>
              <h3 id="drawer-ratios" tabIndex={-1}>Key ratios</h3>
              <PeriodTable periods={periods} sparse={sparse}>
                {KEY_RATIOS.map(([group, fields]) => (
                  <Fragment key={group}>
                    <tr>
                      <td className="meta" colSpan={periods.length + 1}>
                        {group}
                      </td>
                    </tr>
                    {fields.map((field) => (
                      <PeriodRow
                        key={field}
                        label={field === "market_cap" ? money(fieldLabel(field)) : fieldLabel(field)}
                        periods={periods}
                        sparse={sparse}
                        cell={(p) => <Val column={field} value={p[field]} />}
                      />
                    ))}
                  </Fragment>
                ))}
              </PeriodTable>
              <h3 id="drawer-growth" tabIndex={-1}>Growth (YoY)</h3>
              <PeriodTable periods={periods} sparse={sparse}>
                {GROWTH_FIELDS.map((field) => (
                  <PeriodRow
                    key={field}
                    label={fieldLabel(field)}
                    periods={periods}
                    sparse={sparse}
                    cell={(p) => <Val column={field} value={p[field]} />}
                  />
                ))}
              </PeriodTable>
              <h3 id="drawer-momentum" tabIndex={-1}>Momentum</h3>
              <PeriodTable periods={latestOnly} labels={latestLabels}>
                {MOMENTUM_FIELDS.map((field) => (
                  <PeriodRow
                    key={field}
                    label={fieldLabel(field)}
                    periods={latestOnly}
                    cell={(p) => <Val column={field} value={p[field]} />}
                  />
                ))}
              </PeriodTable>
              {latest.ttm_revenue != null && (
                <>
                  <h3 id="drawer-ttm" tabIndex={-1}>TTM — trailing 12 months</h3>
                  <PeriodTable periods={latestOnly} labels={latestLabels}>
                    {TTM_FIELDS.map((field) => (
                      <PeriodRow
                        key={field}
                        label={fieldLabel(field)}
                        periods={latestOnly}
                        cell={(p) => <Val column={field} value={p[field]} />}
                      />
                    ))}
                  </PeriodTable>
                  <p className="meta">
                    Last four reported quarters — fresher than the fiscal-year rows above;
                    crawled symbols plus audited US issuers reporting discrete quarters.
                  </p>
                </>
              )}
              <h3 id="drawer-scores" tabIndex={-1}>Scores — full breakdown</h3>
              <PeriodTable periods={periods} sparse={sparse}>
                {SCORES.map(([label, column, components]) => (
                  <Fragment key={column}>
                    <PeriodRow
                      label={label}
                      periods={periods}
                      sparse={sparse}
                      cell={(p) => <Val column={column} value={p[column]} />}
                    />
                    {components.map((component) => (
                      <PeriodRow
                        key={component}
                        labelClass="meta"
                        label={component.replace(`${column.split("_")[0]}_`, "· ")}
                        periods={periods}
                        sparse={sparse}
                        cell={(p) => num(p[component])}
                      />
                    ))}
                  </Fragment>
                ))}
              </PeriodTable>
              {latest.composite_rank !== null &&
                latest.composite_rank !== undefined && (
                  <>
                    <h3 id="drawer-rank" tabIndex={-1}>Rank — how it is built</h3>
                    <PeriodTable periods={latestOnly} labels={latestLabels}>
                      <PeriodRow
                        label="Composite"
                        periods={latestOnly}
                        cell={(p) => <Val column="composite_rank" value={p.composite_rank} />}
                      />
                      {RANK_PILLARS.map(([label, column, components]) => (
                        <Fragment key={column}>
                          <PeriodRow
                            label={label}
                            periods={latestOnly}
                            cell={(p) => <Val column={column} value={p[column]} />}
                          />
                          {components.map((component) => (
                            <PeriodRow
                              key={component}
                              labelClass="meta"
                              label={`· ${component}`}
                              periods={latestOnly}
                              cell={(p) => <Val column={component} value={p[component]} />}
                            />
                          ))}
                        </Fragment>
                      ))}
                    </PeriodTable>
                    <p className="meta">
                      Percentiles 0–100 · peer group: {String(latest.rank_peer_group ?? "global")}
                      {latest.rank_missing_pillars
                        ? ` · ${String(latest.rank_missing_pillars)} pillar omitted (missing input — never imputed)`
                        : ""}
                    </p>
                  </>
                )}
              {(latest.graham_number != null ||
                latest.magic_formula_rank != null) && (
                <>
                  <h3 id="drawer-value" tabIndex={-1}>Value — Greenblatt & Graham</h3>
                  <PeriodTable periods={latestOnly} labels={latestLabels}>
                    {VALUE_ROWS.map(([label, column]) => (
                      <PeriodRow
                        key={column}
                        labelClass={label.startsWith("·") ? "meta" : undefined}
                        label={
                          column === "graham_number" || column === "ncav" ? money(label) : label
                        }
                        periods={latestOnly}
                        cell={(p) => <Val column={column} value={p[column]} />}
                      />
                    ))}
                  </PeriodTable>
                  <p className="meta">
                    Latest fiscal period only — price-based metrics are never back-dated (missing price → —).
                  </p>
                </>
              )}
              {/* charts LAST — number tables first, every curve after them */}
              <PriceChart symbol={symbol} currency={currency} />
              <h3 id="drawer-trends" tabIndex={-1}>Trends</h3>
              <TrendCharts periods={periods} />
              <h3>Provenance</h3>
              <p className="meta">
                provider: {String(latest.provider ?? "yfinance")} · computed at:{" "}
                {latest.computed_at
                  ? new Date(Number(latest.computed_at) * 1000).toISOString()
                  : "—"}
                {(() => {
                  const provider = String(latest.provider ?? "yfinance");
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
  );
}
