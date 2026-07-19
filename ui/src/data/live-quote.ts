// Best-effort real-time quote for stale published data. The dataset ships
// nightly EOD closes; when the latest close is not from today (UTC), the
// drawer tops it up from Yahoo's public chart endpoint — direct first, then
// public CORS mirrors (Yahoo sends no CORS headers itself). Failures are
// silent: the chip simply doesn't render and the published as-of stays the
// honest truth. The quote is display-only — it never feeds a score, a rank
// or the invest signal.

export interface LiveQuote {
  price: number;
  previousClose: number | null;
  currency: string | null;
  /** epoch seconds of the quote */
  time: number;
  source: string;
}

const QUOTE_URL = (symbol: string) =>
  `https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(symbol)}?range=1d&interval=1d`;

const ROUTES: ((url: string) => string)[] = [
  (url) => url,
  (url) => `https://corsproxy.io/?url=${encodeURIComponent(url)}`,
  (url) => `https://api.allorigins.win/raw?url=${encodeURIComponent(url)}`,
];

const TIMEOUT_MS = 6_000;
const TTL_MS = 60_000;
const cache = new Map<string, { at: number; quote: LiveQuote | null }>();

/** Published closes are EOD — anything not dated today (UTC) is stale. */
export function isStale(asof: string | null | undefined, today = new Date()): boolean {
  if (!asof) return true;
  return String(asof).slice(0, 10) < today.toISOString().slice(0, 10);
}

function parse(payload: unknown): LiveQuote | null {
  const meta = (payload as { chart?: { result?: { meta?: Record<string, unknown> }[] } })?.chart
    ?.result?.[0]?.meta;
  const price = meta?.regularMarketPrice;
  if (typeof price !== "number" || !Number.isFinite(price)) return null;
  const prev = meta?.chartPreviousClose ?? meta?.previousClose;
  return {
    price,
    previousClose: typeof prev === "number" && Number.isFinite(prev) ? prev : null,
    currency: typeof meta?.currency === "string" ? meta.currency : null,
    time:
      typeof meta?.regularMarketTime === "number"
        ? meta.regularMarketTime
        : Math.floor(Date.now() / 1000),
    source: "Yahoo Finance",
  };
}

export async function fetchLiveQuote(symbol: string): Promise<LiveQuote | null> {
  const hit = cache.get(symbol);
  if (hit && Date.now() - hit.at < TTL_MS) return hit.quote;
  let quote: LiveQuote | null = null;
  for (const route of ROUTES) {
    try {
      const signal =
        typeof AbortSignal.timeout === "function" ? AbortSignal.timeout(TIMEOUT_MS) : undefined;
      const res = await fetch(route(QUOTE_URL(symbol)), { signal });
      if (!res.ok) continue;
      quote = parse(await res.json());
      if (quote) break;
    } catch {
      /* unreachable route — try the next one */
    }
  }
  cache.set(symbol, { at: Date.now(), quote });
  return quote;
}

export function clearLiveQuoteCache(): void {
  cache.clear();
}
