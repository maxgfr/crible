// Chart geometry (exact vectors) + the RankBars/TrendCharts rendering
// contracts: null is a gap or a "—", never a fabricated zero; oldest reads
// left; legends appear from 2 series; all-NaN series → no chart.

import { render, screen as rtl } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { RankBars } from "../components/RankBars";
import { PiotroskiSparkline, TrendCharts } from "../components/TrendCharts";
import { barRects, baselineY, chartDomain, linePath } from "../components/charts";

describe("chart geometry", () => {
  it("anchors zero into the domain — the baseline rule", () => {
    expect(chartDomain([[5, 10]])).toEqual({ min: 0, max: 10 });
    expect(chartDomain([[-5, 10]])).toEqual({ min: -5, max: 10 });
    expect(chartDomain([[null, null]])).toBeNull();
    expect(chartDomain([[3, 3]])).toEqual({ min: 0, max: 3 });
    expect(chartDomain([[5]], { min: 0, max: 9 })).toEqual({ min: 0, max: 9 });
  });

  it("linePath maps exact coordinates and splits on null — never interpolates", () => {
    const domain = { min: 0, max: 100 };
    expect(linePath([0, 50, 100], domain)).toBe("M0.00 100.00L50.00 50.00L100.00 0.00");
    const gapped = linePath([0, null, 100], domain);
    expect(gapped.match(/M/g)).toHaveLength(2); // two restarts
    expect(gapped).not.toContain("L"); // no segment crosses the gap
    expect(linePath([42], domain)).toBe(""); // one point draws nothing
    expect(linePath([], domain)).toBe("");
  });

  it("barRects anchors bars to the zero baseline, negatives hang below", () => {
    const domain = { min: -5, max: 10 };
    const zero = baselineY(domain);
    expect(zero).toBeCloseTo(100 - (5 / 15) * 100, 5);
    const [positive, negative, absent] = barRects([10, -5, null], domain);
    expect(positive!.y).toBeCloseTo(0, 5);
    expect(positive!.height).toBeCloseTo(zero, 5);
    expect(negative!.y).toBeCloseTo(zero, 5);
    expect(negative!.height).toBeCloseTo(100 - zero, 5);
    expect(absent).toBeNull(); // never a fabricated zero bar
  });
});

describe("RankBars", () => {
  it("renders the five ranks; a NULL rank is a dash with an empty track", () => {
    const { container } = render(
      <RankBars row={{ composite_rank: 75.7, quality_rank: null, value_rank: 60.5, momentum_rank: 90.9, magic_formula_rank: 60 }} />,
    );
    expect(rtl.getAllByRole("row")).toHaveLength(5);
    expect(rtl.getByText("—")).toBeInTheDocument(); // quality
    expect(container.querySelectorAll("rect.rank-bar")).toHaveLength(4);
    expect(rtl.getByText("75.700")).toBeInTheDocument();
  });
});

const PERIODS_NEWEST_FIRST = [
  { period: "2025", revenue: 400.0, net_income: 40.0, free_cash_flow: 30.0, gross_margin: 0.4, operating_margin: 0.2, net_profit_margin: 0.1, piotroski_f: 8 },
  { period: "2024", revenue: 300.0, net_income: 30.0, free_cash_flow: 25.0, gross_margin: 0.38, operating_margin: 0.19, net_profit_margin: 0.09, piotroski_f: 6 },
  { period: "2023", revenue: 200.0, net_income: 20.0, free_cash_flow: 20.0, gross_margin: 0.36, operating_margin: 0.18, net_profit_margin: 0.08, piotroski_f: 4 },
];

describe("TrendCharts", () => {
  it("reverses newest-first storage so the oldest period reads LEFT", () => {
    const { container } = render(<TrendCharts periods={PERIODS_NEWEST_FIRST} />);
    const revenue = container.querySelector(".trend-chart")!;
    const meta = revenue.querySelectorAll(".trend-meta span");
    expect(meta[0].textContent).toBe("2023");
    expect(meta[1].textContent).toBe("2025");
    // the tallest revenue bar (2025) is the right-most rect
    const bars = [...revenue.querySelectorAll("rect.trend-bar")] as SVGRectElement[];
    const tallest = bars.reduce((a, b) =>
      Number(a.getAttribute("height")) > Number(b.getAttribute("height")) ? a : b,
    );
    const xs = bars.map((b) => Number(b.getAttribute("x")));
    expect(Number(tallest.getAttribute("x"))).toBe(Math.max(...xs));
  });

  it("legends appear from two series on, labels in text tokens", () => {
    const { container } = render(<TrendCharts periods={PERIODS_NEWEST_FIRST} />);
    const legends = container.querySelectorAll(".chart-legend");
    expect(legends).toHaveLength(2); // NI&FCF + Margins; Revenue (1 series) has none
    expect(legends[1].textContent).toContain("Operating");
  });

  it("a chart whose series are all NaN is absent, others still render", () => {
    const noMargins = PERIODS_NEWEST_FIRST.map((p) => ({
      ...p, gross_margin: null, operating_margin: null, net_profit_margin: null,
    }));
    const { container } = render(<TrendCharts periods={noMargins} />);
    const captions = [...container.querySelectorAll("figcaption")].map((c) => c.textContent);
    expect(captions.join(" ")).toContain("Revenue");
    expect(captions.join(" ")).not.toContain("Margins");
  });

  it("hover hit rects carry a per-period multi-series title", () => {
    const { container } = render(<TrendCharts periods={PERIODS_NEWEST_FIRST} />);
    const titles = [...container.querySelectorAll(".chart-hit title")].map((t) => t.textContent);
    expect(titles.some((t) => t?.includes("2024") && t.includes("Net income 30"))).toBe(true);
  });
});

describe("PiotroskiSparkline", () => {
  it("draws on the fixed 0-9 domain, oldest left", () => {
    const { container } = render(<PiotroskiSparkline periods={PERIODS_NEWEST_FIRST} />);
    const d = container.querySelector(".spark-line")!.getAttribute("d")!;
    // oldest (4) → y = 100 - 4/9*100 ≈ 55.56 at x 0; newest (8) → ≈ 11.11 at x 100
    expect(d.startsWith("M0.00 55.56")).toBe(true);
    expect(d.endsWith("L100.00 11.11")).toBe(true);
  });

  it("renders nothing without two usable points", () => {
    const { container } = render(
      <PiotroskiSparkline periods={[{ period: "2025", piotroski_f: 5 }]} />,
    );
    expect(container.firstChild).toBeNull();
  });
});
