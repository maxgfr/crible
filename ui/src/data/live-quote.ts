// Best-effort real-time quote for stale published data. The dataset ships
// nightly EOD closes; when the latest close is not from today (UTC), the
// drawer tops it up from Yahoo's public chart endpoint — direct first, then
// public CORS mirrors (Yahoo sends no CORS headers itself). The mirrors are
// third parties that see every ticker looked up: they are ON for the hosted
// static site (no server of its own) and OFF for a self-hosted API build
// unless VITE_LIVE_QUOTE_PROXY=1. Failures are silent: the chip simply
// doesn't render and the published as-of stays the honest truth. The quote
// is display-only — it never feeds a score, a rank or the invest signal.

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

interface Route {
  /** how the quote reached the browser — shown on the chip */
  via: string;
  url: (target: string) => string;
  proxy: boolean;
}

const ROUTES: Route[] = [
  { via: "(direct)", url: (target) => target, proxy: false },
  {
    via: "via corsproxy.io",
    url: (target) => `https://corsproxy.io/?url=${encodeURIComponent(target)}`,
    proxy: true,
  },
  {
    via: "via allorigins.win",
    url: (target) => `https://api.allorigins.win/raw?url=${encodeURIComponent(target)}`,
    proxy: true,
  },
];

// read at call time (not module load) so a build flag or a test can flip it
function proxiesAllowed(): boolean {
  return (
    import.meta.env.VITE_DATA_MODE === "static" ||
    import.meta.env.VITE_LIVE_QUOTE_PROXY === "1"
  );
}

// The direct browser → Yahoo call. On the hosted static site it is the point
// of the chip; a self-hosted API build makes no call to a third party unless
// its operator opts in at build time (VITE_LIVE_QUOTE=1, or the proxies'
// VITE_LIVE_QUOTE_PROXY=1): the ticker a user opens stays on their server.
function directAllowed(): boolean {
  return (
    import.meta.env.VITE_DATA_MODE === "static" ||
    import.meta.env.VITE_LIVE_QUOTE === "1" ||
    import.meta.env.VITE_LIVE_QUOTE_PROXY === "1"
  );
}

const TIMEOUT_MS = 6_000;
const TTL_MS = 60_000;
const cache = new Map<string, { at: number; quote: LiveQuote | null }>();

/** Published closes are EOD — anything not dated today (UTC) is stale. */
export function isStale(asof: string | null | undefined, today = new Date()): boolean {
  if (!asof) return true;
  return String(asof).slice(0, 10) < today.toISOString().slice(0, 10);
}

function parse(payload: unknown, via: string): LiveQuote | null {
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
    source: `Yahoo Finance ${via}`,
  };
}

// one request per symbol at a time: concurrent callers share it
const inFlight = new Map<string, Promise<LiveQuote | null>>();

export function fetchLiveQuote(
  symbol: string,
  { proxies = proxiesAllowed(), direct = directAllowed() || proxies }: { proxies?: boolean; direct?: boolean } = {},
): Promise<LiveQuote | null> {
  const hit = cache.get(symbol);
  if (hit && Date.now() - hit.at < TTL_MS) return Promise.resolve(hit.quote);
  const pending = inFlight.get(symbol);
  if (pending) return pending;
  const request = resolveQuote(symbol, proxies, direct).finally(() => inFlight.delete(symbol));
  inFlight.set(symbol, request);
  return request;
}

async function resolveQuote(symbol: string, proxies: boolean, direct: boolean): Promise<LiveQuote | null> {
  let quote: LiveQuote | null = null;
  for (const route of ROUTES) {
    if (route.proxy ? !proxies : !direct) continue;
    try {
      const signal =
        typeof AbortSignal.timeout === "function" ? AbortSignal.timeout(TIMEOUT_MS) : undefined;
      const res = await fetch(route.url(QUOTE_URL(symbol)), { signal });
      if (!res.ok) continue;
      quote = parse(await res.json(), route.via);
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
  inFlight.clear();
}
