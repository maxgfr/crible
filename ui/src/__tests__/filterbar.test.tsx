// Structured filters that COMPOSE the DSL — no hidden logic: applying the
// filters writes a plain, editable query into the query bar and runs it.

import { fireEvent, render, screen as rtl } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { FilterBar } from "../components/FilterBar";

describe("FilterBar", () => {
  it("composes a DSL query from the selected filters", () => {
    const onApply = vi.fn();
    render(<FilterBar onApply={onApply} />);

    fireEvent.change(rtl.getByLabelText("Region"), { target: { value: "europe" } });
    fireEvent.change(rtl.getByLabelText("Sector"), { target: { value: "Industrials" } });
    fireEvent.change(rtl.getByLabelText("Country (ISO)"), { target: { value: "fr" } });
    fireEvent.change(rtl.getByLabelText("Piotroski min"), { target: { value: "7" } });
    fireEvent.change(rtl.getByLabelText("Composite rank min"), { target: { value: "60" } });
    fireEvent.change(rtl.getByLabelText("P/E max"), { target: { value: "15" } });
    fireEvent.click(rtl.getByText("Apply filters"));

    expect(onApply).toHaveBeenCalledWith(
      "region = 'europe' AND sector = 'Industrials' AND country = 'FR'" +
        " AND piotroski_f >= 7 AND composite_rank >= 60 AND price_to_earnings_ratio <= 15",
    );
  });

  it("omits empty filters and applies nothing when all are empty", () => {
    const onApply = vi.fn();
    render(<FilterBar onApply={onApply} />);

    fireEvent.change(rtl.getByLabelText("Piotroski min"), { target: { value: "8" } });
    fireEvent.click(rtl.getByText("Apply filters"));
    expect(onApply).toHaveBeenCalledWith("piotroski_f >= 8");

    fireEvent.change(rtl.getByLabelText("Piotroski min"), { target: { value: "" } });
    fireEvent.click(rtl.getByText("Apply filters"));
    // nothing selected → no query applied
    expect(onApply).toHaveBeenCalledTimes(1);
  });

  it("quotes string values safely (no DSL injection through inputs)", () => {
    const onApply = vi.fn();
    render(<FilterBar onApply={onApply} />);
    fireEvent.change(rtl.getByLabelText("Country (ISO)"), { target: { value: "F' OR 1=1" } });
    fireEvent.click(rtl.getByText("Apply filters"));
    const query = onApply.mock.calls[0][0] as string;
    expect(query).toBe("country = 'F\\' OR 1=1'"); // quote escaped, stays one literal
  });
});
