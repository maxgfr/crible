// T-016 — minimal hash router (no lib): #/ · #/status ·
// #/company/:symbol (deep-linkable drawer over the screener). The screener's
// state travels in the hash query string (#/?q=…&sort=…) so every screen is
// a permalink; #/company/:symbol carries it too, so refreshing or closing
// the drawer restores the screen that found the company.

import { useCallback, useEffect, useState } from "react";

export type View = "screener" | "status";

export interface Route {
  view: View;
  company: string | null;
  q: string | null;
  sort: string | null;
}

// a malformed escape (#/company/%E0) must never crash the app: keep it raw
function safeDecode(text: string): string {
  try {
    return decodeURIComponent(text);
  } catch {
    return text;
  }
}

export function parseHash(hash: string): Route {
  const raw = hash.replace(/^#/, "");
  const [path, search = ""] = raw.split("?", 2) as [string, string?];
  const params = new URLSearchParams(search);
  const q = params.get("q");
  const sort = params.get("sort");
  // /providers merged into /status — old permalinks keep landing somewhere
  if (path === "/status" || path === "/providers") return { view: "status", company: null, q, sort };
  const company = path.match(/^\/company\/(.+)$/);
  if (company) {
    return { view: "screener", company: safeDecode(company[1]), q, sort };
  }
  return { view: "screener", company: null, q, sort };
}

export function hashFor(route: Route): string {
  const params = new URLSearchParams();
  // q="" is meaningful (blank query = the full snapshot), so only null skips
  if (route.q !== null) params.set("q", route.q);
  if (route.sort) params.set("sort", route.sort);
  // toString(), not .size — URLSearchParams.size is missing before Safari 17
  const query = params.toString();
  const search = query ? `?${query}` : "";
  if (route.company) return `#/company/${encodeURIComponent(route.company)}${search}`;
  if (route.view === "status") return "#/status";
  return `#/${search}`;
}

export function useHashRoute(): [Route, (route: Route, opts?: { replace?: boolean }) => void] {
  const [route, setRoute] = useState<Route>(() => parseHash(window.location.hash));
  useEffect(() => {
    const onHashChange = () => setRoute(parseHash(window.location.hash));
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);
  // stable identity: callers memoise on it (the grid's link builder)
  const navigate = useCallback((next: Route, opts?: { replace?: boolean }) => {
    const target = hashFor(next);
    if (opts?.replace) {
      // replaceState fires no hashchange event — sync the state ourselves
      window.history.replaceState(null, "", `${window.location.pathname}${window.location.search}${target}`);
      setRoute(parseHash(target));
    } else {
      window.location.hash = target;
    }
  }, []);
  return [route, navigate];
}
