// Live-quote chip under the drawer title — renders ONLY when the published
// close is stale (not today's) AND the best-effort fetch actually landed.
// Clearly labeled unofficial, with the dataset as-of alongside so the two
// vintages are never confused.

import { useEffect, useState } from "react";
import { fetchLiveQuote, isStale, type LiveQuote as Quote } from "../data/live-quote";

function fmt(value: number): string {
  return Math.abs(value) >= 1000 ? value.toFixed(0) : value.toFixed(2);
}

export function LiveQuote({ symbol, asof }: { symbol: string; asof: string | null }) {
  const [quote, setQuote] = useState<Quote | null>(null);

  useEffect(() => {
    setQuote(null);
    if (!isStale(asof)) return;
    let live = true;
    fetchLiveQuote(symbol).then((q) => {
      if (live) setQuote(q);
    });
    return () => {
      live = false;
    };
  }, [symbol, asof]);

  if (!quote) return null;
  const change =
    quote.previousClose !== null && quote.previousClose !== 0
      ? (quote.price - quote.previousClose) / quote.previousClose
      : null;
  const when = new Date(quote.time * 1000).toISOString().slice(0, 16).replace("T", " ");
  return (
    <p className="live-quote" role="status">
      <span className="live-quote-dot" aria-hidden="true" />
      live {fmt(quote.price)}
      {quote.currency ? ` ${quote.currency}` : ""}
      {change !== null && (
        <span className={change < 0 ? "num-bad" : "num-good"}>
          {" "}
          {change >= 0 ? "+" : ""}
          {(change * 100).toFixed(1)}% vs last close
        </span>
      )}
      <span className="meta">
        {" "}
        · {when} UTC · {quote.source}, unofficial · dataset close {asof ?? "missing"}
      </span>
    </p>
  );
}
