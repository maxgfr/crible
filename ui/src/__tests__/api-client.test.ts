// The FastAPI client never reads an error body as data: a non-2xx answer
// throws a meaningful error (status + the server's detail), a 422 keeps its
// DslApiError detail, and a 404 company stays the "not in the universe" null.

import { afterEach, describe, expect, it, vi } from "vitest";
import { apiClient } from "../data/api-client";
import { DslApiError } from "../data/types";

function stub(status: number, body: unknown) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => ({ ok: status < 400, status, json: async () => body })),
  );
}

afterEach(() => vi.unstubAllGlobals());

describe("api client — non-2xx answers", () => {
  it("company() throws on a 500 instead of returning the error body", async () => {
    stub(500, { detail: "snapshot unreadable" });
    await expect(apiClient.company("AIR.PA")).rejects.toThrow(/500.*snapshot unreadable/);
  });

  it("company() keeps null for a 404", async () => {
    stub(404, { detail: "not found" });
    expect(await apiClient.company("NOPE")).toBeNull();
  });

  it("status/presets/providers throw on a 5xx", async () => {
    stub(503, {});
    await expect(apiClient.status()).rejects.toThrow(/503/);
    await expect(apiClient.presets()).rejects.toThrow(/503/);
    await expect(apiClient.providers()).rejects.toThrow(/503/);
  });

  it("screen() keeps the DslApiError detail on a 422", async () => {
    stub(422, { detail: { error: "unknown field 'x' at position 0", position: 0, hint: null } });
    const err = await apiClient.screen("x > 1", null, 1, 10).catch((e) => e);
    expect(err).toBeInstanceOf(DslApiError);
    expect(err.detail.position).toBe(0);
  });

  it("screen() surfaces the server detail of a 500", async () => {
    stub(500, { detail: "Binder Error: cannot compare" });
    await expect(apiClient.screen("country > 5", null, 1, 10)).rejects.toThrow(
      /API error 500.*Binder Error/,
    );
  });
});

describe("api client — funnel", () => {
  it("counts each clause alone and cumulatively, stopping at the first empty funnel", async () => {
    const totals: Record<string, number> = {
      "a >= 1": 10, "b >= 2": 5, "a >= 1 AND b >= 2": 0, "c >= 3": 7,
    };
    vi.stubGlobal(
      "fetch",
      vi.fn(async (_url: string, init?: RequestInit) => {
        const { query } = JSON.parse(String(init?.body));
        return { ok: true, status: 200, json: async () => ({ rows: [], total: totals[query] ?? 0, page: 1, tookMs: 0 }) };
      }),
    );
    expect(await apiClient.funnel(["a >= 1", "b >= 2", "c >= 3"])).toEqual([
      { clause: "a >= 1", alone: 10, cumulative: 10 },
      { clause: "b >= 2", alone: 5, cumulative: 0 },
    ]);
  });
});
