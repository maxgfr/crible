// The deterministic synthesis: family counters and attention points come
// from the ONE threshold table (verdictKind); jumps are buttons scrolling
// within the drawer — never fragment links (hash-router conflict).

import { fireEvent, render, screen as rtl } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { SynthesisBlock, synthesize } from "../components/SynthesisBlock";

const CRAFTED = {
  // Solvency & forensics: good=2 (piotroski, beneish), bad=2 (altman, ohlson),
  // warn=2 (montier, dechow), missing=1 (zmijewski)
  piotroski_f: 8,
  altman_z: 1.2,
  beneish_m: -2.5,
  zmijewski_score: null,
  ohlson_o: 0.5,
  montier_c: 5,
  dechow_f: 2.0,
  // Value: bad=1 (graham), good=1 (peg), neutral=1 (ncav mid-band)
  graham_margin_of_safety: -0.2,
  ncav_to_market_cap: 0.3,
  peg_ratio: 0.8,
  // Cash: warn=1 (fcf_conversion), bad=1 (dividend), missing=1 (rule_of_40)
  fcf_conversion: 0.7,
  dividend_coverage: 0.5,
  rule_of_40: null,
  composite_rank: 75.7,
  rank_peer_group: "europe×Consumer Staples",
};

describe("synthesize", () => {
  it("counts each family from the shared verdict table", () => {
    const { families, attention, decidable, total } = synthesize(CRAFTED);
    expect(families).toEqual([
      { name: "Solvency & forensics", good: 2, bad: 2, warn: 2, missing: 1, total: 7 },
      { name: "Value", good: 1, bad: 1, warn: 0, missing: 0, total: 3 },
      { name: "Cash", good: 0, bad: 1, warn: 1, missing: 1, total: 3 },
    ]);
    expect(decidable).toBe(11);
    expect(total).toBe(13);
    // bads first, then warns; every item carries a phrase and a section
    expect(attention.map((a) => a.kind)).toEqual(["bad", "bad", "bad", "bad", "warn", "warn"]);
    expect(attention.map((a) => a.column)).toEqual([
      "altman_z", "ohlson_o", "graham_margin_of_safety", "dividend_coverage",
      "montier_c", "dechow_f",
    ]);
    expect(attention.every((a) => a.phrase && a.sectionId.startsWith("drawer-"))).toBe(true);
  });

  it("caps the attention list at six", () => {
    const everythingBad = {
      ...CRAFTED,
      piotroski_f: 2, zmijewski_score: 1.0, beneish_m: -1.0, fcf_conversion: 0.5,
    };
    expect(synthesize(everythingBad).attention).toHaveLength(6);
  });

  it("an all-null row is all-missing with a thin-data verdict", () => {
    const { families, attention, decidable } = synthesize({});
    expect(families.every((f) => f.missing === f.total)).toBe(true);
    expect(attention).toEqual([]);
    expect(decidable).toBe(0);
  });
});

describe("SynthesisBlock", () => {
  it("renders the hero, the counters, and scrolls on jump — no fragment links", () => {
    const scrolled = vi.fn();
    const target = document.createElement("h3");
    target.id = "drawer-scores";
    target.scrollIntoView = scrolled;
    document.body.appendChild(target);

    const { container } = render(<SynthesisBlock latest={CRAFTED} periods={[CRAFTED]} />);
    expect(container.querySelector(".synthesis-rank")?.textContent).toBe("75.700");
    expect(rtl.getByText(/composite percentile/)).toHaveTextContent(
      "peers: europe×Consumer Staples",
    );
    expect(rtl.getByText("Solvency & forensics")).toBeInTheDocument();
    expect(rtl.getByText(/Altman Z in the distress zone/)).toBeInTheDocument();

    fireEvent.click(rtl.getAllByRole("button", { name: "view" })[0]);
    expect(scrolled).toHaveBeenCalled();
    // hash-router guard: a fragment href would close the drawer
    expect(container.querySelector('a[href^="#"]')).toBeNull();
    target.remove();
  });

  it("says so when the composite rank is missing and data is thin", () => {
    render(
      <SynthesisBlock
        latest={{ missing_inputs: "total_assets,net_income,inventory" }}
        periods={[]}
      />,
    );
    expect(rtl.getByText(/not ranked — missing pillar inputs/)).toBeInTheDocument();
    expect(rtl.getByText(/Only 0 of 13 checks decidable/)).toBeInTheDocument();
    expect(rtl.getByText(/total_assets, net_income, inventory/)).toBeInTheDocument();
  });
});
