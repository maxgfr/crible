# Data model

Three storage layers (ADR-0003): an immutable **raw layer** (versioned Parquet per provider fetch), the wide **snapshot layer** (one Parquet published by atomic swap), and small **operational state** (DuckDB owned by the ingest process). Entities below describe the logical model across those layers.

## Company

| Attribute | Type |
|---|---|
| symbol | identifier (Yahoo-suffixed ticker, PK) |
| name | string |
| isin | string (nullable) |
| country | string (ISO-3166 alpha-2 — the DSL filter code) |
| country_name | string (original FinanceDatabase name) |
| region | string (europe | us | world — drives crawl priority) |
| sector | string |
| industry | string |
| exchange | string |
| currency | string |
| marketCapClass | string (Large/Mid/Small — categorical from FinanceDatabase) |
| delisted | boolean |
| updatedAt | timestamp |

_Referenced by: FR-001, FR-006, FR-007, FR-010, FR-012_

## RawStatement

| Attribute | Type |
|---|---|
| symbol | ref Company |
| provider | string (yfinance | esef | simfin | financialreports | …) |
| statementType | enum (income | balance | cashflow) |
| freq | enum (annual | quarterly) |
| period | string (fiscal period end) |
| payload | json (as-fetched fields) |
| fetchedAt | timestamp |
| parquetPath | string (versioned raw layer file) |

_Referenced by: FR-002, FR-010, FR-012, FR-013_

## PriceBar

| Attribute | Type |
|---|---|
| symbol | ref Company |
| date | date |
| open/high/low/close | number |
| volume | number |
| provider | string (yfinance | stooq) |

_Referenced by: FR-002, FR-011_

## SnapshotRow

| Attribute | Type |
|---|---|
| symbol | ref Company |
| period | string (fiscal period) |
| ratios | ~200 numeric columns (financetoolkit + derived) |
| piotroskiF | int 0–9 (+ 9 criterion booleans) |
| altmanZ | number (+ inputs) |
| beneishM | number (+ 8 components) |
| provenance | json (per-field provider + fetchedAt) |
| computedAt | timestamp |

_Referenced by: FR-003, FR-004, FR-005, FR-006, FR-007, FR-012_

## CrawlTask

| Attribute | Type |
|---|---|
| symbol | ref Company |
| priority | int (0 = europe, 1 = us large caps, 2 = world) |
| nextDue | timestamp (freshness-driven) |
| lastCrawledAt | timestamp |
| consecutiveFailures | int |
| status | enum (pending | inflight | done | parked) |

_Referenced by: FR-002_

## Preset

| Attribute | Type |
|---|---|
| id | identifier (slug) |
| name | string |
| description | string |
| dsl | string (the full, visible query) |

_Referenced by: FR-004, FR-006, FR-009_

## Provider

| Attribute | Type |
|---|---|
| id | identifier (yfinance | esef | stooq | simfin | financialreports | fmp_free | eodhd_free | eodhd) |
| kind | enum (keyless | free-key | paid) |
| enabled | boolean (derived: keyless → true; keyed → key present & valid) |
| keyEnvVar | string (nullable) |
| health | json (last success, error counts, budget usage) |

_Referenced by: FR-002, FR-008, FR-011, FR-013, FR-014_
