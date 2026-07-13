// T-020 — providers & settings: read-only inventory (keyless built-ins +
// plugin providers keyed off/on), the .env pointer, the EODHD upgrade
// path, and the theme preference. The table is the hero here too.

import { useEffect, useState } from "react";
import { providers, type ProviderInfo } from "../data";
import type { Theme } from "../theme";

interface Props {
  theme: Theme;
  onTheme: (theme: Theme) => void;
}

const BUILT_INS = [
  { id: "esef", note: "audited EU statements — filings.xbrl.org" },
  { id: "stooq", note: "price fallback (budget-free)" },
];

const NOTES: Record<string, string> = {
  yfinance: "primary keyless source — rolling, rate-budgeted crawl",
  simfin: "annual EU/US statements (free tier)",
  fmp_free: "annual statements (free tier)",
  eodhd: "€59.99/mo — deepest EU fundamentals; the one paid upgrade path (see srd/prds)",
};

function StatePill({ provider }: { provider: ProviderInfo }) {
  if (provider.enabled) return <span className="pill pill-ok">on</span>;
  return <span className="pill pill-muted">off — no key</span>;
}

export function ProvidersView({ theme, onTheme }: Props) {
  const [plugins, setPlugins] = useState<ProviderInfo[] | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    providers().then(setPlugins).catch(() => setFailed(true));
  }, []);

  return (
    <section className="view">
      <h2>Providers</h2>
      <div className="view-body">
        <table className="inventory">
          <thead>
            <tr>
              <th>provider</th>
              <th>kind</th>
              <th>key</th>
              <th>state</th>
              <th>notes</th>
            </tr>
          </thead>
          <tbody>
            {plugins?.map((p) => (
              <tr key={p.id}>
                <th scope="row">{p.id}</th>
                <td>{p.kind}</td>
                <td>{p.key_env_var ?? "—"}</td>
                <td>
                  <StatePill provider={p} />
                </td>
                <td className="note">{NOTES[p.id] ?? ""}</td>
              </tr>
            ))}
            {BUILT_INS.map((b) => (
              <tr key={b.id}>
                <th scope="row">{b.id}</th>
                <td>keyless</td>
                <td>—</td>
                <td>
                  <span className="pill pill-ok">always on</span>
                </td>
                <td className="note">{b.note}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {failed && (
          <div className="error-banner" role="alert">
            API unreachable — plugin states unknown (built-ins shown).
          </div>
        )}
        {plugins === null && !failed && <div className="skeleton-block" aria-hidden="true" />}

        <p className="teach">
          Keys live in <code>.env</code> next to <code>docker-compose.yml</code> — add{" "}
          <code>SIMFIN_KEY=…</code> and restart the stack; a provider without a key simply
          stays off. Zero-key operation is the contract: nothing here is ever required.
        </p>

        <h3>Appearance</h3>
        <fieldset className="theme-pref">
          <legend className="meta">theme</legend>
          <label>
            <input
              type="radio"
              name="theme"
              checked={theme === "dark"}
              onChange={() => onTheme("dark")}
            />{" "}
            Dark (phosphore)
          </label>
          <label>
            <input
              type="radio"
              name="theme"
              checked={theme === "light"}
              onChange={() => onTheme("light")}
            />{" "}
            Light (paper terminal)
          </label>
        </fieldset>
      </div>
    </section>
  );
}
