// FR-012 — drawer sizing: Expand toggles a persisted wide mode, the left
// separator resizes with the arrow keys (the keyboard path to the drag
// handle), and both survive a close/reopen. Pointer-capture drags are not
// exercised here — jsdom has no layout.

import { act, fireEvent, render, screen as rtl, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { CompanyDrawer } from "../components/CompanyDrawer";
import type { CompanyDetail } from "../data/types";

const ACME = { profile: { name: "Acme", country: "FR", sector: "Tech" }, periods: [] };
const requestFetchMock = vi.fn(async (_symbol: string) => ({ queued: true }));
const companyMock = vi.fn(async (_symbol: string): Promise<CompanyDetail | null> => ACME);
vi.mock("../data", () => ({
  company: (symbol: string) => companyMock(symbol),
  requestFetch: (symbol: string) => requestFetchMock(symbol),
  STATIC_MODE: false,
}));
vi.mock("../components/PriceChart", () => ({ PriceChart: () => null }));
vi.mock("../components/LiveQuote", () => ({ LiveQuote: () => null }));

beforeEach(() => {
  window.localStorage.clear();
  companyMock.mockReset();
  companyMock.mockImplementation(async () => ACME);
});

describe("drawer loading", () => {
  it("shows B, never A's late response, once B is selected", async () => {
    const pending = new Map<string, (detail: CompanyDetail) => void>();
    companyMock.mockImplementation(
      (symbol) => new Promise((resolve) => pending.set(symbol, resolve)),
    );
    const { rerender } = render(<CompanyDrawer symbol="AAA" onClose={() => {}} />);
    rerender(<CompanyDrawer symbol="BBB" onClose={() => {}} />);
    await act(async () =>
      pending.get("BBB")!({ profile: { name: "Bravo" }, periods: [] }));
    await act(async () =>
      pending.get("AAA")!({ profile: { name: "Alpha" }, periods: [] }));
    expect(rtl.getByText("Bravo")).toBeInTheDocument();
    expect(rtl.queryByText("Alpha")).not.toBeInTheDocument();
  });

  it("a failed load shows an error, never an endless Loading…", async () => {
    companyMock.mockImplementation(async () => {
      throw new Error("API error 500");
    });
    render(<CompanyDrawer symbol="ACME" onClose={() => {}} />);
    await waitFor(() => expect(rtl.getByRole("alert")).toHaveTextContent(/API error 500/));
    expect(rtl.queryByText(/Loading/)).not.toBeInTheDocument();
  });
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

// jsdom has no PointerEvent — without one, fireEvent drops clientX
if (typeof window.PointerEvent === "undefined") {
  class PointerEventShim extends MouseEvent {
    pointerId: number;
    constructor(type: string, init: PointerEventInit = {}) {
      super(type, init);
      this.pointerId = init.pointerId ?? 0;
    }
  }
  window.PointerEvent = PointerEventShim as unknown as typeof PointerEvent;
}

describe("drawer resize drag", () => {
  it("drags through a CSS variable and writes storage once, on pointerup", async () => {
    render(<CompanyDrawer symbol="ACME" onClose={() => {}} />);
    await waitFor(() => expect(rtl.getByText("Acme")).toBeInTheDocument());
    const dialog = rtl.getByRole("dialog");
    const handle = rtl.getByRole("separator", { name: /resize/i });
    const writes = vi.spyOn(Storage.prototype, "setItem");

    fireEvent.pointerDown(handle, { pointerId: 1, clientX: 464 });
    for (const clientX of [450, 420, 400]) fireEvent.pointerMove(handle, { pointerId: 1, clientX });
    // the width follows the pointer live…
    expect(dialog.style.getPropertyValue("--drawer-w")).toBe(`${window.innerWidth - 400}px`);
    // …without a storage write per move
    expect(writes).not.toHaveBeenCalled();

    fireEvent.pointerUp(handle, { pointerId: 1, clientX: 400 });
    expect(writes).toHaveBeenCalledTimes(1);
    expect(JSON.parse(window.localStorage.getItem("crible-drawer") ?? "{}")).toMatchObject({
      width: window.innerWidth - 400,
      expanded: false,
    });
    writes.mockRestore();
  });
});

describe("drawer accessibility", () => {
  it("the resize separator exposes its value range", async () => {
    render(<CompanyDrawer symbol="ACME" onClose={() => {}} />);
    await waitFor(() => expect(rtl.getByText("Acme")).toBeInTheDocument());
    const handle = rtl.getByRole("separator", { name: /resize/i });
    expect(handle).toHaveAttribute("aria-valuenow", "560");
    expect(handle).toHaveAttribute("aria-valuemin", "420");
    expect(handle).toHaveAttribute("aria-valuemax", String(Math.round(window.innerWidth * 0.96)));
    fireEvent.keyDown(handle, { key: "ArrowLeft" });
    expect(handle).toHaveAttribute("aria-valuenow", "592");
  });

  it("Tab and Shift+Tab wrap inside the dialog (focus trap)", async () => {
    render(<CompanyDrawer symbol="ACME" onClose={() => {}} />);
    await waitFor(() => expect(rtl.getByText("Acme")).toBeInTheDocument());
    const dialog = rtl.getByRole("dialog");
    const focusables = Array.from(
      dialog.querySelectorAll<HTMLElement>('a[href], button:not([disabled]), [tabindex="0"]'),
    );
    const first = focusables[0];
    const last = focusables[focusables.length - 1];

    last.focus();
    fireEvent.keyDown(last, { key: "Tab" });
    expect(first).toHaveFocus();

    first.focus();
    fireEvent.keyDown(first, { key: "Tab", shiftKey: true });
    expect(last).toHaveFocus();
  });

  it("the background is inert while the drawer is open", async () => {
    const { rerender } = render(
      <>
        <main data-testid="background">grid</main>
        <CompanyDrawer symbol="ACME" onClose={() => {}} />
      </>,
    );
    await waitFor(() => expect(rtl.getByText("Acme")).toBeInTheDocument());
    expect(rtl.getByTestId("background")).toHaveAttribute("inert");
    expect(rtl.getByRole("dialog")).not.toHaveAttribute("inert");

    rerender(<main data-testid="background">grid</main>);
    expect(rtl.getByTestId("background")).not.toHaveAttribute("inert");
  });
});

describe("figures currency", () => {
  it("labels money rows with the reporting currency the engine priced them in", async () => {
    const { figuresCurrency } = await import("../components/CompanyDrawer");
    const detail = (reporting: string | null, listing: string) => ({
      profile: { symbol: "X", currency: listing },
      periods: [{ period: "2025", reporting_currency: reporting }],
    }) as never;
    expect(figuresCurrency(detail("USD", "EUR"))).toBe("USD"); // MT.AS
    expect(figuresCurrency(detail(null, "GBp"))).toBe("GBP"); // pence quote → pounds
    expect(figuresCurrency(detail(null, "EUR"))).toBe("EUR");
  });
});
