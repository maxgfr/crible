// Structured quick-filters that COMPOSE the DSL. No hidden logic (FR-009
// spirit): applying writes a plain, editable query into the query bar — the
// DSL stays the single screening language in both api and static modes.

import { useState } from "react";

interface Props {
  onApply: (dsl: string) => void;
}

const REGIONS = ["europe", "us", "world"];
// FinanceDatabase sector vocabulary (GICS-like)
const SECTORS = [
  "Communication Services", "Consumer Discretionary", "Consumer Staples",
  "Energy", "Financials", "Health Care", "Industrials",
  "Information Technology", "Materials", "Real Estate", "Utilities",
];

/** Escape a value into one single-quoted DSL string literal. */
function quote(value: string): string {
  return `'${value.replaceAll("\\", "\\\\").replaceAll("'", "\\'")}'`;
}

export function FilterBar({ onApply }: Props) {
  const [region, setRegion] = useState("");
  const [sector, setSector] = useState("");
  const [country, setCountry] = useState("");
  const [piotroskiMin, setPiotroskiMin] = useState("");
  const [rankMin, setRankMin] = useState("");
  const [peMax, setPeMax] = useState("");

  const build = (): string => {
    const clauses: string[] = [];
    if (region) clauses.push(`region = ${quote(region)}`);
    if (sector) clauses.push(`sector = ${quote(sector)}`);
    if (country.trim()) clauses.push(`country = ${quote(country.trim().toUpperCase())}`);
    if (piotroskiMin !== "") clauses.push(`piotroski_f >= ${Number(piotroskiMin)}`);
    if (rankMin !== "") clauses.push(`composite_rank >= ${Number(rankMin)}`);
    if (peMax !== "") clauses.push(`price_to_earnings_ratio <= ${Number(peMax)}`);
    return clauses.join(" AND ");
  };

  return (
    <div className="filterbar">
      <select aria-label="Region" value={region} onChange={(e) => setRegion(e.target.value)}>
        <option value="">region…</option>
        {REGIONS.map((r) => (
          <option key={r} value={r}>{r}</option>
        ))}
      </select>
      <select aria-label="Sector" value={sector} onChange={(e) => setSector(e.target.value)}>
        <option value="">sector…</option>
        {SECTORS.map((s) => (
          <option key={s} value={s}>{s}</option>
        ))}
      </select>
      <input
        aria-label="Country (ISO)"
        placeholder="country (FR…)"
        size={8}
        value={country}
        onChange={(e) => setCountry(e.target.value)}
      />
      <input
        aria-label="Piotroski min"
        placeholder="piotroski ≥"
        type="number" min={0} max={9} size={6}
        value={piotroskiMin}
        onChange={(e) => setPiotroskiMin(e.target.value)}
      />
      <input
        aria-label="Composite rank min"
        placeholder="rank ≥"
        type="number" min={0} max={100} size={6}
        value={rankMin}
        onChange={(e) => setRankMin(e.target.value)}
      />
      <input
        aria-label="P/E max"
        placeholder="P/E ≤"
        type="number" min={0} size={6}
        value={peMax}
        onChange={(e) => setPeMax(e.target.value)}
      />
      <button
        onClick={() => {
          const dsl = build();
          if (dsl) onApply(dsl);
        }}
      >
        Apply filters
      </button>
    </div>
  );
}
