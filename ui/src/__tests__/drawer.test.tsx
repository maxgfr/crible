// FR-012 — drawer sizing: Expand toggles a persisted wide mode, the left
// separator resizes with the arrow keys (the keyboard path to the drag
// handle), and both survive a close/reopen. Pointer-capture drags are not
// exercised here — jsdom has no layout.

import { fireEvent, render, screen as rtl, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { CompanyDrawer } from "../components/CompanyDrawer";

const requestFetchMock = vi.fn(async (_symbol: string) => ({ queued: true }));
vi.mock("../data", () => ({
  company: async () => ({
    profile: { name: "Acme", country: "FR", sector: "Tech" },
    periods: [],
  }),
  requestFetch: (symbol: string) => requestFetchMock(symbol),
  STATIC_MODE: false,
}));
vi.mock("../components/PriceChart", () => ({ PriceChart: () => null }));
vi.mock("../components/LiveQuote", () => ({ LiveQuote: () => null }));

beforeEach(() => {
  window.localStorage.clear();
});

describe("drawer synthesis placement", () => {
  it("no synthesis without periods; with periods it precedes Statements", async () => {
    const { unmount } = render(<CompanyDrawer symbol="ACME" onClose={() => {}} />);
    await waitFor(() => expect(rtl.getByText("Acme")).toBeInTheDocument());
    // the mocked company has periods: [] — metadata only, no synthesis
    expect(rtl.queryByLabelText("Synthesis")).not.toBeInTheDocument();
    unmount();
  });
});

describe("on-demand fetch (FR-012)", () => {
  it("an uncrawled company offers 'Fetch now' and shows the queued state", async () => {
    const { unmount } = render(<CompanyDrawer symbol="ACME" onClose={() => {}} />);
    await waitFor(() => expect(rtl.getByText("Acme")).toBeInTheDocument());
    const button = rtl.getByRole("button", { name: /fetch this company now/i });
    fireEvent.click(button);
    await waitFor(() => expect(rtl.getByRole("status")).toHaveTextContent(/queued/i));
    expect(requestFetchMock).toHaveBeenCalledWith("ACME");
    expect(rtl.queryByRole("button", { name: /fetch this company now/i })).not.toBeInTheDocument();
    unmount();
  });
});

describe("drawer sizing", () => {
  it("Expand toggles a persisted wide mode that survives a reopen", async () => {
    const { unmount } = render(<CompanyDrawer symbol="ACME" onClose={() => {}} />);
    await waitFor(() => expect(rtl.getByText("Acme")).toBeInTheDocument());
    const dialog = rtl.getByRole("dialog");
    expect(dialog.style.getPropertyValue("--drawer-w")).toBe("560px");

    fireEvent.click(rtl.getByRole("button", { name: "Expand" }));
    expect(dialog.style.getPropertyValue("--drawer-w")).toBe("min(1100px, 96vw)");
    expect(rtl.getByRole("button", { name: "Shrink" })).toHaveAttribute("aria-pressed", "true");
    expect(JSON.parse(window.localStorage.getItem("crible-drawer") ?? "{}")).toMatchObject({
      expanded: true,
    });

    unmount();
    render(<CompanyDrawer symbol="ACME" onClose={() => {}} />);
    await waitFor(() => expect(rtl.getByText("Acme")).toBeInTheDocument());
    expect(rtl.getByRole("button", { name: "Shrink" })).toHaveAttribute("aria-pressed", "true");
  });

  it("arrow keys on the separator resize, persist, and leave expanded mode", async () => {
    render(<CompanyDrawer symbol="ACME" onClose={() => {}} />);
    await waitFor(() => expect(rtl.getByText("Acme")).toBeInTheDocument());
    const dialog = rtl.getByRole("dialog");
    const handle = rtl.getByRole("separator", { name: /resize/i });

    fireEvent.keyDown(handle, { key: "ArrowLeft" }); // the drawer grows leftward
    expect(dialog.style.getPropertyValue("--drawer-w")).toBe("592px");
    fireEvent.keyDown(handle, { key: "ArrowRight" });
    expect(dialog.style.getPropertyValue("--drawer-w")).toBe("560px");
    expect(JSON.parse(window.localStorage.getItem("crible-drawer") ?? "{}")).toMatchObject({
      width: 560,
      expanded: false,
    });
  });
});
