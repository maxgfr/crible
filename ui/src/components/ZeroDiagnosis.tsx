// The zero-result funnel: when a screen matches nothing, count the rows
// surviving each top-level AND clause (alone, then cumulatively) so the user
// sees WHICH clause empties the funnel instead of guessing. Counts ride the
// normal screen() path (page size 1, total only) — static and API clients
// alike; nothing here is a second query engine.

import { useEffect, useState } from "react";

import { screen } from "../data";
import { topLevelClauses } from "../dsl/explain";

const CLAUSE_CAP = 20;

interface ClauseCount {
  clause: string;
  alone: number;
  cumulative: number;
}

export function ZeroDiagnosis({ query }: { query: string }) {
  const [counts, setCounts] = useState<ClauseCount[] | null>(null);

  useEffect(() => {
    const clauses = topLevelClauses(query).slice(0, CLAUSE_CAP);
    if (clauses.length < 2) {
      setCounts([]);
      return;
    }
    setCounts(null);
    let cancelled = false;
    (async () => {
      const out: ClauseCount[] = [];
      for (let i = 0; i < clauses.length; i += 1) {
        const alone = (await screen(clauses[i], null, 1, 1)).total;
        const cumulative = (await screen(clauses.slice(0, i + 1).join(" AND "), null, 1, 1)).total;
        if (cancelled) return;
        out.push({ clause: clauses[i], alone, cumulative });
        // the funnel is empty from here on — no need to keep querying
        if (cumulative === 0) break;
      }
      if (!cancelled) setCounts(out);
    })().catch(() => {
      if (!cancelled) setCounts([]);
    });
    return () => {
      cancelled = true;
    };
  }, [query]);

  if (counts === null) return <p className="meta">Working out which clause filters everything…</p>;
  if (counts.length === 0) return null;

  const killer = counts.findIndex((c) => c.cumulative === 0);
  return (
    <div className="zero-diagnosis">
      <p className="meta">Rows surviving each clause — loosen the one that empties the funnel:</p>
      <table>
        <thead>
          <tr>
            <th scope="col">clause</th>
            <th scope="col">alone</th>
            <th scope="col">cumulative</th>
          </tr>
        </thead>
        <tbody>
          {counts.map((count, index) => (
            <tr key={count.clause} className={index === killer ? "zero-diagnosis-killer" : ""}>
              <td>{count.clause}</td>
              <td>{count.alone}</td>
              <td className={count.cumulative === 0 ? "num-bad" : ""}>{count.cumulative}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
