// The shared period-table machinery: sparse-column detection for period
// columns that carry NO statement fundamentals (structural — the source
// publishes ~4-5 fiscal years and YoY/average metrics need the prior year).

import { describe, expect, it } from "vitest";
import { STATEMENT_FIELDS, sparsePeriodFlags } from "../components/PeriodTable";

describe("sparsePeriodFlags", () => {
  it("returns an empty list for no periods", () => {
    expect(sparsePeriodFlags([])).toEqual([]);
  });

  it("flags a period where every statement field is missing", () => {
    const full = { period: "2025-12-31", revenue: 84e9, net_income: 385e6 };
    const empty = { period: "2021-12-31" };
    expect(sparsePeriodFlags([full, empty])).toEqual([false, true]);
  });

  it("treats null like missing but zero as a real value", () => {
    const nulls = Object.fromEntries(STATEMENT_FIELDS.map((f) => [f, null]));
    expect(sparsePeriodFlags([{ period: "2022-12-31", ...nulls }])).toEqual([true]);
    expect(sparsePeriodFlags([{ period: "2022-12-31", ...nulls, revenue: 0 }])).toEqual([false]);
  });

  it("respects a custom field list", () => {
    const period = { period: "2024-12-31", revenue: 1 };
    expect(sparsePeriodFlags([period], ["net_income"])).toEqual([true]);
    expect(sparsePeriodFlags([period], ["revenue"])).toEqual([false]);
  });
});
