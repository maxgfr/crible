// Static-mode coverage line: built from the published manifest, which the app
// does not control — a manifest missing a field must cost the line, not the app.

import { render, screen as rtl } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

const manifestMock = vi.fn();
vi.mock("../data", () => ({ manifest: () => manifestMock() }));

import { CoverageBanner } from "../components/CoverageBanner";

const FULL = {
  schema: 3,
  generated_at: 1_794_331_713,
  universe_rows: 95_615,
  snapshot_rows: 175_566,
  snapshot_symbols: 31_666,
  snapshot_by_region: { europe: 12_000, us: 9_000 },
  prices: { symbols: 20_000, bars: 1, window_days: 400, max_date: "2026-11-09", shards: [] },
  sample: [],
  commit: "abc",
};

describe("CoverageBanner", () => {
  it("states what the published dataset covers", async () => {
    manifestMock.mockResolvedValue(FULL);
    render(<CoverageBanner />);
    expect(await rtl.findByRole("note")).toHaveTextContent("31,666");
    expect(rtl.getByRole("note")).toHaveTextContent("2026-11-");
  });

  it("a manifest missing its date or counts still renders, never throws", async () => {
    // new Date(undefined * 1000).toISOString() threw a RangeError, and the
    // banner sits at the top of the app: the whole screener went down
    manifestMock.mockResolvedValue({ ...FULL, generated_at: undefined, universe_rows: undefined });
    render(<CoverageBanner />);
    const note = await rtl.findByRole("note");
    expect(note).toHaveTextContent("31,666");
    expect(note).not.toHaveTextContent("NaN");
    expect(note).not.toHaveTextContent("undefined");
  });
});
