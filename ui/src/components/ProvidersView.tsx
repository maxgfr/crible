// T-020 — providers & settings: read-only inventory (keyless built-ins +
// any plugin providers), and the theme preference. The table is the hero
// here too. The shipped catalog is keyless-only (open-data cleanup).

import { useEffect, useState } from "react";
import { providers, type ProviderInfo } from "../data";
import type { ThemePref } from "../theme";

interface Props {
  pref: ThemePref;
  onPref: (pref: ThemePref) => void;
}

const BUILT_INS = [
  { id: "esef", note: "audited EU statements — filings.xbrl.org" },
  { id: "edgar", note: "audited US statements — SEC EDGAR companyfacts" },
];

const NOTES: Record<string, string> = {
  yfinance: "primary keyless source — rolling, rate-budgeted crawl",
};

function StatePill({ provider }: { provider: ProviderInfo }) {
  if (provider.enabled) return <span className="pill pill-ok">on</span>;
  return <span className="pill pill-muted">off — no key</span>;
}

export function ProvidersView({ pref, onPref }: Props) {
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
          Every bundled source is keyless open data — there is nothing to configure in{" "}
          <code>.env</code>. Third-party keyed plugins remain possible through the provider
          seam (one without its key simply stays off), but zero-key operation is the
          contract: nothing here is ever required.
        </p>

        <h3>Appearance</h3>
        <fieldset className="theme-pref">
          <legend className="meta">theme</legend>
          <label>
            <input
              type="radio"
              name="theme"
              checked={pref === "auto"}
              onChange={() => onPref("auto")}
            />{" "}
            Auto (follow the system)
          </label>
          <label>
            <input
              type="radio"
              name="theme"
              checked={pref === "dark"}
              onChange={() => onPref("dark")}
            />{" "}
            Dark (phosphore)
          </label>
          <label>
            <input
              type="radio"
              name="theme"
              checked={pref === "light"}
              onChange={() => onPref("light")}
            />{" "}
            Light (paper terminal)
          </label>
        </fieldset>
      </div>
    </section>
  );
}
