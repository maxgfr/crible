# Build plan

## M1 — Walking skeleton (must-haves)

A usable end-to-end slice covering every must-have requirement.

- **Requirements:** FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-007, FR-008
- **Risks:**
  - Yahoo rate-limiting/blocking is the dominant hazard: 429s and YFRateLimitError are endemic [E105][E107]; mitigated by the hard token-bucket budget, capped backoff and the degradation path (serve last snapshot).
  - Snapshot atomicity under concurrent reader/writer processes (ADR-0003 write-then-swap) must be proven by tests before the API ships.
  - Keyless throughput arithmetic caps first-boot experience — the bootstrap sample (~100 symbols) is what makes M1 demoable within hours.

## M2 — Rounded product (should-haves)

The product is complete enough for real users.

- **Requirements:** FR-009, FR-010, FR-011, FR-012
- **Risks:**
  - ESEF repository coverage is partial (e.g. German/Irish filings unavailable [E15]) and ISINs are sparse in FinanceDatabase [E35] — ESEF enrichment lands on a subset; the unmatched-EU metric keeps it honest.
  - Stooq has no formal API contract; its CSV endpoints may change without notice — provider isolation keeps the blast radius to one plugin.

## M3 — Enhancements (could-haves)

Nice-to-have capabilities that differentiate the product.

- **Requirements:** FR-013, FR-014
- **Risks:**
  - EODHD paid quotas/pricing recorded at planning time must be re-validated with the free key before any purchase decision [E111][E112].
  - FinancialReports.eu MCP OAuth flow may not suit headless ingestion — evaluate during the plugin spike before committing.

## M4 — Bulk-first / local-first data plane (2026-07-14/15)

Audited redistributable bulk (US deep + EU/UK/JP), keyless FX, a local-first mirror with last-good, and incremental compute — Yahoo demoted to a resilient fallback.

- **Requirements:** FR-016, FR-017, FR-018, FR-019, FR-020, FR-021, FR-022
- **Risks:**
  - No open redistributable OHLCV source exists — prices stay Yahoo/dumps (assumed-risk).
  - Real-corpus parser edge cases (FSDS segments, iXBRL taxonomy variety, EDINET consolidation) — mitigated by real-data validation, not just fixtures.
