# Screens & flows

## Screens

- **Screener** — The home screen: query bar + presets + results grid + export. Where 95% of time is spent; everything else is a drawer or a pill away. _(FRs: FR-004, FR-007, FR-009)_
- **Company detail** — Drawer (deep-linkable route) over the screener: statements, score breakdowns, provenance, ESEF filing link. _(FRs: FR-012, FR-010)_
- **Ingest & coverage status** — The crawl observatory: universe coverage, freshness histogram, rate-budget gauge, provider health, recent failures. _(FRs: FR-002, FR-006, FR-013)_
- **Providers & settings** — Read-only provider inventory (keyless / keyed-off / keyed-on with health), pointer to .env configuration and the EODHD upgrade path; theme preference. _(FRs: FR-013, FR-014)_

## Shell & navigation

One-window shell, no sidebar (the width belongs to the table). Topbar, left to right: wordmark (sieve glyph + « crible » in mono) · view switcher pills **Screener / Status / Providers** (hash-routed `#/`, `#/status`, `#/providers` so views are linkable) · ingest status pill · theme toggle (dark ⇄ light « paper terminal », persisted in localStorage, initial default from `prefers-color-scheme`). The company drawer stays an overlay over whichever view is active and keeps its deep-linkable route. Keyboard: `/` focuses the DSL query bar, `Esc` closes the drawer, view pills are tabbable.

## User flows

### First run (zero-key) _(FRs: FR-001, FR-002, FR-008, FR-009, FR-007)_

1. docker compose up with no keys
2. The screener never shows a blank grid: its first-run empty state teaches — bootstrap/crawl progress inline (coverage %, ETA) with a link to the Status view
3. Status shows universe bootstrap then Europe-first crawl progress with ETA
4. First preset screen returns rows on the ingested sample
5. Grid renders; the operator saves a first custom DSL screen

### Screen & export _(FRs: FR-004, FR-007)_

1. Type or edit DSL in the query bar (autocomplete from whitelist)
2. Run: results in < 1 s, sortable, column picker adjusts the view
3. Export CSV of exactly what is displayed

### Investigate a company _(FRs: FR-012, FR-010)_

1. Click a result row — the detail drawer opens without losing the result set
2. Read score component breakdowns and per-field provenance
3. Follow the ESEF filing link for the audited source

### Enable a phase-2 provider _(FRs: FR-013, FR-008)_

1. Add the provider key to .env and restart the stack
2. Provider flips to enabled in the status view with live health
3. New facts appear with their provider provenance

### Watch the rolling crawl _(FRs: FR-002, FR-006)_

1. Open the status screen
2. Check coverage %, freshness histogram and req/h vs budget
3. Drill into recent failures and parked symbols
