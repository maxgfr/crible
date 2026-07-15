// Pure chart geometry for the drawer's hand-rolled SVGs (no chart lib —
// NFR-013). Everything projects into the normalized 0..100 viewBox that the
// CSS box stretches (preserveAspectRatio="none" + non-scaling strokes — the
// PriceChart idiom). Pure functions: unit-tested with exact vectors.

export const CHART_W = 100;
export const CHART_H = 100;

export interface ChartDomain {
  min: number;
  max: number;
}

function scaleY(value: number, domain: ChartDomain): number {
  const span = domain.max - domain.min || 1;
  return CHART_H - ((value - domain.min) / span) * CHART_H;
}

/** Domain across all series, zero ALWAYS anchored in (the baseline rule —
 *  negative net income keeps a visible zero line). Fixed bounds (e.g. the
 *  0–9 Piotroski sparkline) override. null when nothing is plottable. */
export function chartDomain(
  series: (number | null)[][],
  fixed?: Partial<ChartDomain>,
): ChartDomain | null {
  const values = series.flat().filter((v): v is number => v !== null && Number.isFinite(v));
  if (!values.length) return null;
  const min = fixed?.min ?? Math.min(0, ...values);
  const max = fixed?.max ?? Math.max(0, ...values);
  return max === min ? { min, max: min + 1 } : { min, max };
}

/** Polyline over the viewBox, SPLIT on null — gaps are honest, never
 *  interpolated. "" when fewer than 2 points exist at all. */
export function linePath(values: (number | null)[], domain: ChartDomain): string {
  const n = values.length;
  if (n === 0) return "";
  const step = n > 1 ? CHART_W / (n - 1) : 0;
  let d = "";
  let pen = false;
  let points = 0;
  values.forEach((value, i) => {
    if (value === null || !Number.isFinite(value)) {
      pen = false;
      return;
    }
    d += `${pen ? "L" : "M"}${(i * step).toFixed(2)} ${scaleY(value, domain).toFixed(2)}`;
    pen = true;
    points += 1;
  });
  return points >= 2 ? d : "";
}

export interface BarRect {
  x: number;
  y: number;
  width: number;
  height: number;
}

/** One rect per finite value, anchored to the y(0) baseline; null → null
 *  (never a zero-height bar pretending zero). */
export function barRects(values: (number | null)[], domain: ChartDomain): (BarRect | null)[] {
  const n = values.length || 1;
  const slot = CHART_W / n;
  const width = Math.max(1, slot * 0.6);
  const zero = scaleY(0, domain);
  return values.map((value, i) => {
    if (value === null || !Number.isFinite(value)) return null;
    const y = scaleY(value, domain);
    return {
      x: i * slot + (slot - width) / 2,
      y: Math.min(y, zero),
      width,
      height: Math.abs(zero - y),
    };
  });
}

export function baselineY(domain: ChartDomain): number {
  return scaleY(0, domain);
}
