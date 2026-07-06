# Components

## App Shell & Navigation

Slim top bar (product name, status pill with coverage/freshness, presets menu, theme toggle) framing the full-height screener. [E75]

_States: default, hover, focus, active, disabled, loading, empty, error · FRs: FR-007_

## Query Bar (DSL editor)

Monospaced input for the DSL with syntax-aware validation, inline error (token + position + hint), field autocomplete from the whitelist, and run-on-Enter.

_States: default, hover, focus, active, disabled, loading, empty, error · FRs: FR-004, FR-007_

## Results Grid

TanStack Table: virtualised rows, sortable columns, sticky header, tabular-numeral cells with gain/loss coloring, row click → detail drawer. [E19][E20]

_States: default, hover, focus, active, disabled, loading, empty, error · FRs: FR-004, FR-007_

## Column Picker

Searchable multi-select over the ~200 snapshot columns, grouped by family (valuation, profitability, solvency, scores…); persists locally.

_States: default, hover, focus, active, disabled, loading, empty, error · FRs: FR-007_

## Presets Menu

Named screens with description and the full DSL visible; one click loads the DSL into the query bar for editing (never hidden logic). [E67]

_States: default, hover, focus, active, disabled, loading, empty, error · FRs: FR-009, FR-007_

## Company Detail Drawer

Right-side drawer: profile header, statement history table, score cards with component breakdowns (9 Piotroski / 8 Beneish / Altman inputs), provenance + freshness badges, ESEF filing link. [E58]

_States: default, hover, focus, active, disabled, loading, empty, error · FRs: FR-012, FR-010, FR-007_

## Status Dashboard

Coverage %, freshness histogram, rolling req/h vs budget, per-provider health — the operator's window into the rolling crawl.

_States: default, hover, focus, active, disabled, loading, empty, error · FRs: FR-002, FR-006, FR-013_

## Export Button

Downloads the current result set (rows + visible columns) as CSV via GET /screen.csv; disabled with reason when no results.

_States: default, hover, focus, active, disabled, loading, empty, error · FRs: FR-007_

## Feedback & Notifications

Inline banners and toasts for API errors (with hint), long-running states and export completion; polite live regions.

_States: default, hover, focus, active, disabled, loading, empty, error · FRs: FR-007, FR-006_

## Empty & Error States

First-run (universe loading, crawl progress with ETA), no-match (suggest loosening clauses), API-down and not-yet-crawled company states — each teaches the next action.

_States: default, hover, focus, active, disabled, loading, empty, error · FRs: FR-007, FR-012, FR-006_
