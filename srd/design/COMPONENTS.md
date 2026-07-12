# Components

_Seeded from the functional requirements — verify each component and its states during authoring._

## App Shell & Navigation [E75]

Slim top bar (product name, status pill with coverage/freshness, presets menu, theme toggle) framing the full-height screener.

- **States:** default, hover, focus, active, disabled, loading, empty, error
- **Realises:** FR-007

## Query Bar (DSL editor)

Monospaced input for the DSL with syntax-aware validation, inline error (token + position + hint), field autocomplete from the whitelist, and run-on-Enter.

- **States:** default, hover, focus, active, disabled, loading, empty, error
- **Realises:** FR-004, FR-007

## Results Grid [E19][E20]

TanStack Table: virtualised rows, sortable columns, sticky header, tabular-numeral cells with gain/loss coloring, row click → detail drawer.

- **States:** default, hover, focus, active, disabled, loading, empty, error
- **Realises:** FR-004, FR-007

## Column Picker

Searchable multi-select over the ~200 snapshot columns, grouped by family (valuation, profitability, solvency, scores…); persists locally.

- **States:** default, hover, focus, active, disabled, loading, empty, error
- **Realises:** FR-007

## Presets Menu [E67]

Named screens with description and the full DSL visible; one click loads the DSL into the query bar for editing (never hidden logic).

- **States:** default, hover, focus, active, disabled, loading, empty, error
- **Realises:** FR-009, FR-007

## Company Detail Drawer [E58]

Right-side drawer: profile header, statement history table, score cards with component breakdowns (9 Piotroski / 8 Beneish / Altman inputs), provenance + freshness badges, ESEF filing link.

- **States:** default, hover, focus, active, disabled, loading, empty, error
- **Realises:** FR-012, FR-010, FR-007

## Status Dashboard

Coverage %, freshness histogram, rolling req/h vs budget, per-provider health — the operator's window into the rolling crawl.

- **States:** default, hover, focus, active, disabled, loading, empty, error
- **Realises:** FR-002, FR-006, FR-013

## Export Button

Downloads the current result set (rows + visible columns) as CSV via GET /screen.csv; disabled with reason when no results.

- **States:** default, hover, focus, active, disabled, loading, empty, error
- **Realises:** FR-007

## Feedback & Notifications

Inline banners and toasts for API errors (with hint), long-running states and export completion; polite live regions.

- **States:** default, hover, focus, active, disabled, loading, empty, error
- **Realises:** FR-007, FR-006

## Empty & Error States

First-run (universe loading, crawl progress with ETA), no-match (suggest loosening clauses), API-down and not-yet-crawled company states — each teaches the next action.

- **States:** default, hover, focus, active, disabled, loading, empty, error
- **Realises:** FR-007, FR-012, FR-006
