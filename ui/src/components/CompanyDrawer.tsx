// FR-012 — company detail drawer: profile, period history, score component
// breakdowns (9 Piotroski criteria, 8 Beneish components, Altman inputs),
// provenance (provider + computed_at). Deep enough to explain every number.

import { useEffect, useState } from "react";
import { company, type CompanyDetail } from "../api";

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
                </tbody>
              </table>
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
