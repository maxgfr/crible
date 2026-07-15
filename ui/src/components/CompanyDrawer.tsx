// FR-012 — company detail drawer: profile, period history, score component
// breakdowns (9 Piotroski criteria, 8 Beneish components, Altman inputs),
// provenance (provider + computed_at). Deep enough to explain every number.

import { Fragment, useEffect, useState } from "react";
import { company, type CompanyDetail } from "../data";
import { PriceChart } from "./PriceChart";

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

function num(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "number") {
    if (Math.abs(value) >= 1e9) return `${(value / 1e9).toFixed(2)}B`;
    if (Math.abs(value) >= 1e6) return `${(value / 1e6).toFixed(1)}M`;
    return Number.isInteger(value) ? String(value) : value.toFixed(3);
  }
  if (typeof value === "boolean") return value ? "✓" : "✗";
  return String(value);
}

export function CompanyDrawer({ symbol, onClose }: Props) {
  const [detail, setDetail] = useState<CompanyDetail | null | "loading">("loading");

  useEffect(() => {
    setDetail("loading");
    company(symbol).then(setDetail);
  }, [symbol]);

  return (
    <aside className="drawer" aria-label={`${symbol} details`}>
      <button onClick={onClose} style={{ float: "right" }}>
        Close
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
            <p className="meta">
              Not crawled yet — universe metadata only. It is queued by region priority; check the
              status bar for coverage progress.
            </p>
          ) : (
            <>
              <h3>Statements</h3>
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
              <h3>Scores — full breakdown</h3>
              <table>
                <tbody>
                  <tr>
                    <td>Piotroski F</td>
                    {detail.periods.map((p) => (
                      <td key={String(p.period)}>{num(p.piotroski_f)}</td>
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
                      <td key={String(p.period)}>{num(p.altman_z)}</td>
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
                      <td key={String(p.period)}>{num(p.beneish_m)}</td>
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
                      <td key={String(p.period)}>{num(p.zmijewski_score)}</td>
                    ))}
                  </tr>
                  <tr>
                    <td>Ohlson O</td>
                    {detail.periods.map((p) => (
                      <td key={String(p.period)}>{num(p.ohlson_o)}</td>
                    ))}
                  </tr>
                  <tr>
                    <td>Montier C</td>
                    {detail.periods.map((p) => (
                      <td key={String(p.period)}>{num(p.montier_c)}</td>
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
                </tbody>
              </table>
              {detail.periods[0].composite_rank !== null &&
                detail.periods[0].composite_rank !== undefined && (
                  <>
                    <h3>Rank — how it is built (FR-015)</h3>
                    <table>
                      <tbody>
                        <tr>
                          <td>Composite</td>
                          <td>{num(detail.periods[0].composite_rank)}</td>
                        </tr>
                        {RANK_PILLARS.map(([label, column, components]) => (
                          <Fragment key={column}>
                            <tr>
                              <td>{label}</td>
                              <td>{num(detail.periods[0][column])}</td>
                            </tr>
                            {components.map((component) => (
                              <tr key={component}>
                                <td className="meta">· {component}</td>
                                <td>{num(detail.periods[0][component])}</td>
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
                  <h3>Value — Greenblatt & Graham</h3>
                  <table>
                    <tbody>
                      {VALUE_ROWS.map(([label, column]) => (
                        <tr key={column}>
                          <td className={label.startsWith("·") ? "meta" : undefined}>{label}</td>
                          <td>{num(detail.periods[0][column])}</td>
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
              </p>
            </>
          )}
        </>
      )}
    </aside>
  );
}
