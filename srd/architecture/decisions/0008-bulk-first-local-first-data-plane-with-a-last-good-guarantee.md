# 0008. Bulk-first, local-first data plane with a last-good guarantee and two licence tiers

- **Status:** accepted

## Context
The 2026-07-14 improve cycle (docs/improve/2026-07-14/, market dossier docs/market/2026-07-14/) targeted the fragile per-symbol Yahoo scrape and the US-only ceiling of free feeds. SEC EDGAR/FSDS are public domain and redistributable; Companies House and the price dumps carry no explicit reuse licence; EDINET is PDL1.0 (attribution) behind a free key. Live per-record APIs are also a self-hosting liability.

## Decision
Shrink Yahoo to a resilient fallback and grow an audited, redistributable BULK layer behind one AuditedBulkProvider seam (providers/audited.py). Every bulk archive is fetched once into a local mirror (ingest/mirror.py, data/mirror/<source>/) kept as last-good, re-fetched only when stale (ETag), size-capped; ingestion reads the mirror so a refresh can run offline and coverage never regresses. The published dataset is split into a FULLY-FREE tier (EDGAR+FSDS, ESEF, GLEIF, ECB/Frankfurter FX, FinanceDatabase) and an ASSUMED-RISK tier (Yahoo prices, Stooq/HuggingFace dumps, Companies House); EDINET stays off by default so the core and CI contract remain keyless (NFR-009/013).

## Consequences
US audited coverage deepens (FSDS backfills pre-8-year history; segmented rows excluded), EU audited is on out-of-the-box (GLEIF auto-fetch), UK/JP are reachable, and cross-currency size screens work (*_eur, latest period only — only the spot rate is mirrored). The mirror persists in the Docker volume. Prices remain the one non-redistributable, non-open gap.

## Alternatives considered
Keep Yahoo primary — rejected: fragile, rate-limited, non-redistributable. Mirror upstream files into the published dataset — rejected: the 1.4 GB companyfacts bulk must never be committed (publish-data.sh allowlist). Ship EDINET on by default — rejected: it needs a key and would break the keyless contract.
