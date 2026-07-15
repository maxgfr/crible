// FR-012 — drawer sizing: Expand toggles a persisted wide mode, the left
// separator resizes with the arrow keys (the keyboard path to the drag
// handle), and both survive a close/reopen. Pointer-capture drags are not
// exercised here — jsdom has no layout.

import { fireEvent, render, screen as rtl, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { CompanyDrawer } from "../components/CompanyDrawer";

vi.mock("../data", () => ({
  company: async () => ({
    profile: { name: "Acme", country: "FR", sector: "Tech" },
    periods: [],
  }),
}));
vi.mock("../components/PriceChart", () => ({ PriceChart: () => null }));

beforeEach(() => {
  window.localStorage.clear();
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
