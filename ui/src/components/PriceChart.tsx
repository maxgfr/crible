// Company drawer price chart — a hand-rolled SVG close-price line (no chart
// lib, same token-driven style as StatusView). The viewBox is normalized to
// 0..100 × 0..100 with a non-scaling stroke; the line stretches to fit. Renders
// nothing when the symbol has no series (EDGAR-only issuers only carry the
// distilled quote), so its absence is silent.

import { useEffect, useState } from "react";
import { prices, type PriceBar } from "../data";

const W = 100;
const H = 100;

function path(bars: PriceBar[]): string {
  const closes = bars.map((b) => b.close).filter((c): c is number => c !== null);
  if (closes.length < 2) return "";
  const min = Math.min(...closes);
  const max = Math.max(...closes);
  const span = max - min || 1;
  const n = closes.length - 1;
  return closes
    .map((c, i) => {
      const x = (i / n) * W;
      const y = H - ((c - min) / span) * H;
      return `${i === 0 ? "M" : "L"}${x.toFixed(2)},${y.toFixed(2)}`;
    })
    .join(" ");
}

export function PriceChart({ symbol }: { symbol: string }) {
  const [bars, setBars] = useState<PriceBar[] | null>(null);

  useEffect(() => {
    let live = true;
    prices(symbol)
      .then((b) => live && setBars(b))
      .catch(() => live && setBars([]));
    return () => {
      live = false;
    };
  }, [symbol]);

  const d = bars ? path(bars) : "";
  if (!bars || !d) return null;

  const closes = bars.map((b) => b.close).filter((c): c is number => c !== null);
  const last = closes[closes.length - 1];
  const asof = bars[bars.length - 1]?.date ?? "";
  const fmt = (v: number) => (Math.abs(v) >= 1000 ? v.toFixed(0) : v.toFixed(2));

  return (
    <div className="price-chart">
      <h3>Price — {bars.length} sessions</h3>
      <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" aria-hidden="true">
        <path className="price-chart-line" d={d} />
      </svg>
      <div className="price-chart-meta">
        <span>lo {fmt(Math.min(...closes))} · hi {fmt(Math.max(...closes))}</span>
        <span>
          {fmt(last)} · {asof}
        </span>
      </div>
    </div>
  );
}
