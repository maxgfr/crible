// The zero-result funnel: when a screen matches nothing, count the rows
// surviving each top-level AND clause (alone, then cumulatively) so the user
// sees WHICH clause empties the funnel instead of guessing. Counts come from
// the data client's funnel(): ONE aggregate query in static mode (a count_if
// per clause), total-only screens against the API — nothing here is a
// second query engine.

import { useEffect, useState } from "react";

import { funnel, type FunnelCount } from "../data";
import { topLevelClauses } from "../dsl/explain";

const CLAUSE_CAP = 20;

type ClauseCount = FunnelCount;

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
    funnel(clauses).then(
      (out) => {
        if (!cancelled) setCounts(out);
      },
      () => {
        if (!cancelled) setCounts([]);
      },
    );
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
