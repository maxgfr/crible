// T-016 — minimal hash router (no lib): #/ · #/status · #/providers ·
// #/company/:symbol (deep-linkable drawer over the screener).

import { useEffect, useState } from "react";

export type View = "screener" | "status" | "providers";

export interface Route {
  view: View;
  company: string | null;
}

export function parseHash(hash: string): Route {
  const path = hash.replace(/^#/, "");
  if (path === "/status") return { view: "status", company: null };
  if (path === "/providers") return { view: "providers", company: null };
  const company = path.match(/^\/company\/(.+)$/);
  if (company) return { view: "screener", company: decodeURIComponent(company[1]) };
  return { view: "screener", company: null };
}

export function hashFor(route: Route): string {
  if (route.company) return `#/company/${encodeURIComponent(route.company)}`;
  if (route.view === "status") return "#/status";
  if (route.view === "providers") return "#/providers";
  return "#/";
}

export function useHashRoute(): [Route, (route: Route) => void] {
  const [route, setRoute] = useState<Route>(() => parseHash(window.location.hash));
  useEffect(() => {
    const onHashChange = () => setRoute(parseHash(window.location.hash));
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);
  const navigate = (next: Route) => {
    window.location.hash = hashFor(next);
  };
  return [route, navigate];
}
