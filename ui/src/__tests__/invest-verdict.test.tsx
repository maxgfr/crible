// The invest signal — ONE deterministic tier derived from the same verdict
// table as the family counters: a distress-model red flag vetoes alone, two
// soft fails veto together, favorable needs a clean sheet + pass share +
// composite gate, and thin data never gets a call.

import { render, screen as rtl } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { investVerdict, SynthesisBlock } from "../components/SynthesisBlock";

// clean sheet: 11 goods, 1 mid-band (fcf_conversion), 1 missing (ncav)
const STRONG = {
  piotroski_f: 8, altman_z: 4.1, beneish_m: -2.6, zmijewski_score: -1.5,
  ohlson_o: -2.0, montier_c: 1, dechow_f: 0.4,
  graham_margin_of_safety: 0.25, ncav_to_market_cap: null, peg_ratio: 0.8,
  fcf_conversion: 1.2, dividend_coverage: 2.5, rule_of_40: 0.5,
  composite_rank: 82,
};

describe("investVerdict", () => {
  it("a clean sheet with a strong composite is favorable", () => {
    const verdict = investVerdict(STRONG);
    expect(verdict.signal).toBe("favorable");
    expect(verdict.reason).toBe("11/12 checks pass, no red flag, composite 82");
  });

  it("stays favorable when the composite rank is missing — never imputed", () => {
    expect(investVerdict({ ...STRONG, composite_rank: null }).signal).toBe("favorable");
  });

  it("one distress-model red flag vetoes alone", () => {
    const verdict = investVerdict({ ...STRONG, altman_z: 1.2 });
    expect(verdict.signal).toBe("unfavorable");
    expect(verdict.reason).toContain("altman_z");
  });

  it("two soft fails veto together", () => {
    const verdict = investVerdict({
      ...STRONG,
      dividend_coverage: 0.5,
      graham_margin_of_safety: -0.2,
    });
    expect(verdict.signal).toBe("unfavorable");
    expect(verdict.reason).toBe("2 failed checks of 12");
  });

  it("one soft fail is mixed, not unfavorable", () => {
    expect(investVerdict({ ...STRONG, dividend_coverage: 0.5 }).signal).toBe("mixed");
  });

  it("two warnings break the clean sheet — mixed", () => {
    expect(investVerdict({ ...STRONG, beneish_m: -1.0, dechow_f: 2.0 }).signal).toBe("mixed");
  });

  it("a weak composite blocks favorable even with a clean sheet", () => {
    expect(investVerdict({ ...STRONG, composite_rank: 30 }).signal).toBe("mixed");
  });

  it("thin data is never called — insufficient below five decidable checks", () => {
    const verdict = investVerdict({ piotroski_f: 8 });
    expect(verdict.signal).toBe("insufficient");
    expect(verdict.reason).toContain("only 1 checks decidable");
  });
});

describe("SynthesisBlock invest badge", () => {
  it("renders the tier badge with its reason and the advice disclaimer", () => {
    const { container } = render(<SynthesisBlock latest={STRONG} periods={[STRONG]} />);
    expect(rtl.getByText(/Invest signal: Favorable/)).toBeInTheDocument();
    expect(container.querySelector(".invest-signal")?.className).toContain("invest-favorable");
    expect(rtl.getByText(/not investment advice/)).toBeInTheDocument();
  });

  it("flips to unfavorable when a distress model fires", () => {
    render(<SynthesisBlock latest={{ ...STRONG, altman_z: 1.2 }} periods={[STRONG]} />);
    expect(rtl.getByText(/Invest signal: Unfavorable/)).toBeInTheDocument();
  });
});
