# PRD — EODHD Fundamentals Data Feed (the single planned paid switch)

_Status: specced, stubbed, NOT purchased. FR-014 · ADR-0002/0004. Last validated: 2026-07-07._

## Why this provider, why later

crible's keyless mode is a permanent contract, but its fundamentals link (yfinance)
is fragile and shallow, and worldwide coverage refreshes only best-effort under the
rate budget (ADR-0004). The one paid switch that fixes exactly that link — without
touching universe, compute, DSL, API or UI — is EODHD's **Fundamentals Data Feed**.

## Grounded facts vs to-revalidate

| Fact | Status |
|---|---|
| Free tier = **20 API calls/day**, more data requires a paid plan | **Grounded** — pricing page, SRD [E111] |
| Pricing is tier-based with a yearly discount | **Grounded** — [E112] |
| One fundamentals request costs **10 API calls** of quota | Planning research — **revalidate at purchase** |
| Fundamentals Data Feed ≈ **€59.99/mo**, **100,000 API calls/day** | Planning research (2026-06 pricing page) — **REVALIDATE AT PURCHASE** |
| Worldwide fundamentals, 30+ years US / non-US from ~2000 | Demo payload shows **41 yearly periods** for AAPL.US (verified 2026-07-07); non-US depth **revalidate at purchase** |

## Verified endpoint schemas (captured 2026-07-07 with the public `demo` token, AAPL.US)

### `GET /api/fundamentals/{SYMBOL}?api_token=…&fmt=json`

Top-level keys (verified): `General`, `Highlights`, `Valuation`, `SharesStats`,
`Technicals`, `SplitsDividends`, `AnalystRatings`, `Holders`, `InsiderTransactions`,
`ESGScores`, `outstandingShares`, `Earnings`, `Financials`.

```jsonc
// General (verified subset)
{ "Code": "AAPL", "Type": "Common Stock", "Name": "Apple Inc.",
  "Exchange": "NASDAQ", "CurrencyCode": "USD", "CountryISO": "US",
  "ISIN": "US0378331005" }

// Financials = { Balance_Sheet | Cash_Flow | Income_Statement }
//   each = { currency_symbol, quarterly: {date: {...}}, yearly: {date: {...}} }
// AAPL.US yearly Balance_Sheet: 41 periods (verified) — fields incl.:
//   date, filing_date, currency_symbol, totalAssets, intangibleAssets,
//   otherCurrentAssets, totalLiab, totalStockholderEquity, commonStock, …
```

### `GET /api/eod/{SYMBOL}?api_token=…&fmt=json&period=d`

Verified: 11,481 daily bars for AAPL.US, e.g.
`{"date": "2026-07-06", "open": 307.68, "high": 314.2, "low": 307.01, "close": 312.66, "adjusted_close": 312.66, "volume": 49130304}`.

## Field mapping → crible raw schema

EODHD payloads land as `provider='eodhd'` raw statements, then flow through the
same canonical extraction as every provider (`src/crible/compute/canonical.py`).
Mapping (EODHD → canonical candidates to add to `FIELD_CANDIDATES` at activation):

| EODHD (Financials.*.yearly) | canonical |
|---|---|
| totalRevenue | revenue |
| costOfRevenue | cost_of_goods_sold |
| grossProfit | gross_profit |
| operatingIncome | operating_income |
| sellingGeneralAdministrative | sga_expenses |
| netIncome | net_income |
| incomeBeforeTax | income_before_tax |
| interestExpense | interest_expense |
| totalAssets | total_assets |
| totalCurrentAssets | current_assets |
| totalCurrentLiabilities | current_liabilities |
| cash / cashAndEquivalents | cash_and_equivalents |
| netReceivables | accounts_receivable |
| inventory | inventory |
| propertyPlantEquipment | net_ppe |
| totalLiab | total_liabilities |
| totalStockholderEquity | total_equity |
| retainedEarnings | retained_earnings |
| longTermDebt | long_term_debt |
| shortLongTermDebtTotal | total_debt |
| totalCashFromOperatingActivities | operating_cashflow |
| capitalExpenditures | capital_expenditure |
| depreciation | depreciation_and_amortization |
| commonStockSharesOutstanding (SharesStats) | shares_outstanding |

`General.ISIN` also upgrades FR-010: direct ISIN (denser than FinanceDatabase's)
improves the GLEIF→ESEF match rate.

## Activation plan (one switch)

1. Purchase the Fundamentals Data Feed; **revalidate price/quota** on the invoice.
2. `EODHD_KEY=<paid key>` in `.env` → restart. The stub
   (`src/crible/providers/eodhd.py`) validates the key with ONE `/api/user` call
   and activates only when the detected tier includes fundamentals — a free key
   logs `insufficient tier for fundamentals` and stays disabled (tested:
   `tests/test_fr013_plugins.py::test_fr014_eodhd_*`).
3. Implement `fetch_statements` against the schemas above (raise
   `requests_per_fetch=10` is already set to match EODHD's quota accounting).
4. Scheduler: EODHD replaces yfinance as the fundamentals source for all tiers
   (100k calls/day ÷ 10 = 10,000 symbols/day → full universe sweep ≈ 16 days,
   quarterly worldwide freshness with huge headroom); yfinance stays as fallback.
5. Zero-key mode remains intact and CI-enforced — removing the key returns to
   keyless operation (FR-008 AC-3).

## Rollback

Unset `EODHD_KEY` → plugin disables at next start; raw eodhd facts remain in the
append-only raw layer; the crawler resumes keyless.
