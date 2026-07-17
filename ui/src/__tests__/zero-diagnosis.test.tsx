// Zero-result diagnosis: split the query into top-level AND clauses, count
// survivors per clause (alone + cumulative), point at the killer clause.

import { cleanup, render, screen as rtl, waitFor } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import { topLevelClauses, toDsl } from "../dsl/explain";
import { parse } from "../dsl/parser";

const totals: Record<string, number> = {};
vi.mock("../data", () => ({
  screen: (query: string) => Promise.resolve({ rows: [], total: totals[query] ?? 0 }),
}));

import { ZeroDiagnosis } from "../components/ZeroDiagnosis";

afterEach(cleanup);

test("toDsl round-trips comparisons, IN lists, NOT and nesting", () => {
  for (const q of [
    "piotroski_f >= 7",
    "country IN ('FR', 'DE')",
    "NOT (region = 'us')",
    "piotroski_f >= 7 AND (altman_z > 2.99 OR beneish_m < -1.78)",
  ]) {
    expect(toDsl(parse(q))).toBe(q);
  }
});

test("topLevelClauses splits only top-level ANDs", () => {
  expect(topLevelClauses("piotroski_f >= 7 AND altman_z > 2.99 AND montier_c <= 1")).toEqual([
    "piotroski_f >= 7",
    "altman_z > 2.99",
    "montier_c <= 1",
  ]);
  expect(topLevelClauses("piotroski_f >= 7")).toEqual([]);
  expect(topLevelClauses("a >= 1 OR b >= 2")).toEqual([]);
  expect(topLevelClauses("not a query ((")).toEqual([]);
});

test("ZeroDiagnosis counts survivors and flags the killer clause", async () => {
  totals["piotroski_f >= 7"] = 549;
  totals["altman_z > 2.99"] = 333;
  totals["montier_c <= 1"] = 126;
  totals["piotroski_f >= 7 AND altman_z > 2.99"] = 105;
  totals["piotroski_f >= 7 AND altman_z > 2.99 AND montier_c <= 1"] = 0;

  render(<ZeroDiagnosis query="piotroski_f >= 7 AND altman_z > 2.99 AND montier_c <= 1" />);
  // clause 1's alone and cumulative counts are legitimately the same number
  await waitFor(() => expect(rtl.getAllByText("549")).toHaveLength(2));
  expect(rtl.getByText("105")).toBeInTheDocument();
  const killer = rtl.getByText("montier_c <= 1").closest("tr");
  expect(killer?.className).toContain("zero-diagnosis-killer");
});

test("ZeroDiagnosis renders nothing for a single-clause query", async () => {
  const { container } = render(<ZeroDiagnosis query="piotroski_f >= 9" />);
  await waitFor(() => expect(container.textContent).toBe(""));
});
