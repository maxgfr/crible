// Deterministic synthesis at the top of the drawer — "is it worth a look?"
// computed from the ONE threshold table (format.verdictKind). Never a second
// rule set, never generated prose: family counters, the composite-rank hero
// with the rank bars, and the red/warn attention points with jump buttons.
// Jumps use scrollIntoView — NEVER <a href="#…">: the app hash-routes, and a
// bare fragment would parse as a route and close the drawer.

import { FLAGS, type VerdictKind, formatCell, formatNumber, verdictKind } from "../format";
import { RankBars } from "./RankBars";
import { PiotroskiSparkline } from "./TrendCharts";

interface Family {
  name: string;
  columns: string[];
}

// every column here MUST be decidable by verdictKind — one source of truth
const FAMILIES: Family[] = [
  {
    name: "Solvency & forensics",
    columns: [
      "piotroski_f", "altman_z", "beneish_m", "zmijewski_score",
      "ohlson_o", "montier_c", "dechow_f",
    ],
  },
  { name: "Value", columns: ["graham_margin_of_safety", "ncav_to_market_cap", "peg_ratio"] },
  { name: "Cash", columns: ["fcf_conversion", "dividend_coverage", "rule_of_40"] },
];

// static phrases for the two alarm kinds; good-only columns need none
const ATTENTION_PHRASES: Record<string, Partial<Record<"bad" | "warn", string>> & { sectionId: string }> = {
  piotroski_f: { bad: "Piotroski F at a weak 3 or less", sectionId: "drawer-scores" },
  altman_z: { bad: "Altman Z in the distress zone", sectionId: "drawer-scores" },
  beneish_m: { warn: "Beneish M above the manipulation threshold", sectionId: "drawer-scores" },
  zmijewski_score: { bad: "Zmijewski model flags distress", sectionId: "drawer-scores" },
  ohlson_o: { bad: "Ohlson O flags distress", sectionId: "drawer-scores" },
  montier_c: { warn: "five or more Montier accounting red flags", sectionId: "drawer-scores" },
  dechow_f: { warn: "Dechow F flags substantial misstatement risk", sectionId: "drawer-scores" },
  graham_margin_of_safety: { bad: "price above the Graham number", sectionId: "drawer-value" },
  fcf_conversion: { warn: "earnings not converted into cash", sectionId: "drawer-cash" },
  dividend_coverage: { bad: "dividend not covered by earnings", sectionId: "drawer-cash" },
};

const ATTENTION_CAP = 6;
const THIN_DATA_BELOW = 5;

export interface FamilySummary {
  name: string;
  good: number;
  bad: number;
  warn: number;
  missing: number;
  total: number;
}

export interface AttentionItem {
  column: string;
  kind: "bad" | "warn";
  phrase: string;
  sectionId: string;
}

function numeric(latest: Record<string, unknown>, column: string): number | null {
  const raw = latest[column];
  return typeof raw === "number" && Number.isFinite(raw) ? raw : null;
}

export function synthesize(latest: Record<string, unknown>): {
  families: FamilySummary[];
  attention: AttentionItem[];
  decidable: number;
  total: number;
} {
  const families = FAMILIES.map(({ name, columns }) => {
    const counts = { good: 0, bad: 0, warn: 0, missing: 0 };
    for (const column of columns) {
      const value = numeric(latest, column);
      if (value === null) {
        counts.missing += 1;
        continue;
      }
      const kind = verdictKind(column, value);
      if (kind) counts[kind] += 1; // mid-band counts toward total only
    }
    return { name, ...counts, total: columns.length };
  });

  const attention: AttentionItem[] = [];
  for (const kindWanted of ["bad", "warn"] as const) {
    for (const { columns } of FAMILIES) {
      for (const column of columns) {
        const value = numeric(latest, column);
        if (value === null || verdictKind(column, value) !== kindWanted) continue;
        const entry = ATTENTION_PHRASES[column];
        const phrase = entry?.[kindWanted];
        if (phrase) attention.push({ column, kind: kindWanted, phrase, sectionId: entry.sectionId });
      }
    }
  }

  const total = families.reduce((n, f) => n + f.total, 0);
  const decidable = families.reduce((n, f) => n + (f.total - f.missing), 0);
  return { families, attention: attention.slice(0, ATTENTION_CAP), decidable, total };
}

function kindGlyph(kind: VerdictKind): string {
  return FLAGS[kind].trim();
}

// ---------------------------------------------------------------- invest signal
// One deterministic tier from the SAME verdict table the counters use — no
// second rule set. Display-only synthesis: mechanical thresholds, never advice.

export type InvestSignal = "favorable" | "mixed" | "unfavorable" | "insufficient";

export interface InvestVerdict {
  signal: InvestSignal;
  reason: string;
}

// a distress-model red flag vetoes on its own — solvency first
const CRITICAL_COLUMNS = ["piotroski_f", "altman_z", "zmijewski_score", "ohlson_o"];

const FAVORABLE_GOOD_SHARE = 0.6;
const FAVORABLE_MIN_COMPOSITE = 55;

export function investVerdict(latest: Record<string, unknown>): InvestVerdict {
  const { families, decidable } = synthesize(latest);
  if (decidable < THIN_DATA_BELOW) {
    return {
      signal: "insufficient",
      reason: `only ${decidable} checks decidable — too thin to call`,
    };
  }
  const good = families.reduce((n, f) => n + f.good, 0);
  const bad = families.reduce((n, f) => n + f.bad, 0);
  const warn = families.reduce((n, f) => n + f.warn, 0);
  const critical = CRITICAL_COLUMNS.filter((column) => {
    const value = numeric(latest, column);
    return value !== null && verdictKind(column, value) === "bad";
  });
  if (critical.length > 0) {
    return { signal: "unfavorable", reason: `distress red flag: ${critical.join(", ")}` };
  }
  if (bad >= 2) {
    return { signal: "unfavorable", reason: `${bad} failed checks of ${decidable}` };
  }
  const composite = numeric(latest, "composite_rank");
  if (
    bad === 0 &&
    warn <= 1 &&
    good >= Math.ceil(decidable * FAVORABLE_GOOD_SHARE) &&
    (composite === null || composite >= FAVORABLE_MIN_COMPOSITE)
  ) {
    return {
      signal: "favorable",
      reason:
        `${good}/${decidable} checks pass, no red flag` +
        (composite !== null ? `, composite ${formatNumber(composite)}` : ""),
    };
  }
  return {
    signal: "mixed",
    reason: `${good} pass · ${bad} fail · ${warn} warn of ${decidable} checks`,
  };
}

const SIGNAL_BADGES: Record<InvestSignal, { glyph: string; label: string }> = {
  favorable: { glyph: "✓", label: "Favorable" },
  mixed: { glyph: "!", label: "Mixed" },
  unfavorable: { glyph: "✗", label: "Unfavorable" },
  insufficient: { glyph: "—", label: "Not enough data" },
};

export function SynthesisBlock({
  latest,
  periods,
}: {
  latest: Record<string, unknown>;
  periods: Record<string, unknown>[];
}) {
  const { families, attention, decidable, total } = synthesize(latest);
  const composite = numeric(latest, "composite_rank");
  const thin = decidable < THIN_DATA_BELOW;
  const audited = String(latest.audited_fields ?? "").length > 0;
  const crawled = String(latest.provider ?? "").includes("yfinance");
  const missingInputs = String(latest.missing_inputs ?? "")
    .split(",")
    .filter(Boolean)
    .slice(0, 4);
  const jump = (sectionId: string) => {
    const target = document.getElementById(sectionId);
    target?.scrollIntoView({ block: "start" });
    target?.focus?.();
  };

  const verdict = investVerdict(latest);
  const badge = SIGNAL_BADGES[verdict.signal];

  return (
    <section className="synthesis" aria-label="Synthesis">
      <div className={`invest-signal invest-${verdict.signal}`} role="status">
        <span className="invest-signal-badge">
          {badge.glyph} Invest signal: {badge.label}
        </span>
        <span className="meta">{verdict.reason} · mechanical thresholds, not investment advice</span>
      </div>
      <div className="synthesis-hero">
        <div>
          <div className="synthesis-rank">{composite !== null ? formatNumber(composite) : "—"}</div>
          <div className="meta">
            composite percentile · peers: {String(latest.rank_peer_group ?? "global")}
            {composite === null ? " · not ranked — missing pillar inputs" : ""}
          </div>
        </div>
        <RankBars row={latest} />
      </div>
      {thin && (
        <div className="coverage-note" role="status">
          <p>
            Partial data — {decidable} of {total} checks decidable.
          </p>
          <p className="meta">
            {audited
              ? "Audited filing ingested; the keyless crawl hasn't reached this listing yet — fields fill as it advances."
              : crawled
                ? "Crawled quotes only; no audited filing matched yet."
                : "Awaiting the first data pass for this listing."}
          </p>
        </div>
      )}
      <div className="synthesis-families">
        {families.map((family) =>
          family.missing === family.total ? (
            <div key={family.name} className="synthesis-family">
              <span className="synthesis-family-name">{family.name}</span>
              <span className="meta">no data yet</span>
            </div>
          ) : (
            <div key={family.name} className="synthesis-family">
              <span className="synthesis-family-name">{family.name}</span>
              <span className="num-good">{family.good} ✓</span>
              <span className="num-bad">{family.bad} ✗</span>
              <span className="num-warn">{family.warn} !</span>
              <span className="meta">
                {family.missing} — · of {family.total}
              </span>
              {family.name === "Solvency & forensics" && <PiotroskiSparkline periods={periods} />}
            </div>
          ),
        )}
      </div>
      {attention.length > 0 && (
        <ul className="attention-list">
          {attention.map((item) => (
            <li key={item.column}>
              <span className={`num-${item.kind}`}>
                {kindGlyph(item.kind)} {formatCell(item.column, latest[item.column]).text}
              </span>{" "}
              {item.phrase}{" "}
              <button className="jump-link" onClick={() => jump(item.sectionId)}>
                view
              </button>
            </li>
          ))}
        </ul>
      )}
      {thin && missingInputs.length > 0 && (
        <p className="meta">Missing inputs: {missingInputs.join(", ")}…</p>
      )}
    </section>
  );
}
