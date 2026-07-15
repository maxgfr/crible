// T-016 — minimal hash router (no lib): #/ · #/status · #/providers ·
// #/company/:symbol (deep-linkable drawer over the screener). The screener's
// state travels in the hash query string (#/?q=…&sort=…) so every screen is
// a permalink; #/company/:symbol carries it too, so refreshing or closing
// the drawer restores the screen that found the company.

import { useEffect, useState } from "react";

export type View = "screener" | "status" | "providers";

export interface Route {
  view: View;
  company: string | null;
  q: string | null;
  sort: string | null;
}

export function parseHash(hash: string): Route {
  const raw = hash.replace(/^#/, "");
  const [path, search = ""] = raw.split("?", 2) as [string, string?];
  const params = new URLSearchParams(search);
  const q = params.get("q");
  const sort = params.get("sort");
  if (path === "/status") return { view: "status", company: null, q, sort };
  if (path === "/providers") return { view: "providers", company: null, q, sort };
  const company = path.match(/^\/company\/(.+)$/);
  if (company) {
    return { view: "screener", company: decodeURIComponent(company[1]), q, sort };
  }
  return { view: "screener", company: null, q, sort };
}

export function hashFor(route: Route): string {
  const params = new URLSearchParams();
  // q="" is meaningful (blank query = the full snapshot), so only null skips
  if (route.q !== null) params.set("q", route.q);
  if (route.sort) params.set("sort", route.sort);
  const search = params.size ? `?${params.toString()}` : "";
  if (route.company) return `#/company/${encodeURIComponent(route.company)}${search}`;
  if (route.view === "status") return "#/status";
  if (route.view === "providers") return "#/providers";
  return `#/${search}`;
}

export function useHashRoute(): [Route, (route: Route, opts?: { replace?: boolean }) => void] {
  const [route, setRoute] = useState<Route>(() => parseHash(window.location.hash));
  useEffect(() => {
    const onHashChange = () => setRoute(parseHash(window.location.hash));
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);
  const navigate = (next: Route, opts?: { replace?: boolean }) => {
    const target = hashFor(next);
    if (opts?.replace) {
      // replaceState fires no hashchange event — sync the state ourselves
      window.history.replaceState(null, "", `${window.location.pathname}${window.location.search}${target}`);
      setRoute(parseHash(target));
    } else {
      window.location.hash = target;
    }
  };
  return [route, navigate];
}
