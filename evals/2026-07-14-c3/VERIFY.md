# Verification worklist

For each pair: read the digest, judge whether it SUPPORTS the finding, write a verdict.
Verdicts: `supported` · `partial` · `refuted` · `unsupported`.

## F1 · src/crible/compute/reconcile.py:63
**Finding:** The c2 F6 fix stopped reconcile from dropping audited-only periods, but it appends them at the END of the frame without re-sorting: reconcile.py:63 does merged.reindex(list(merged.index) + extra_periods). build_canonical guarantees an ascending period index, and build_symbol_snapshot relies on that invariant — it writes the current close to price.iloc[-1] (snapshot.py:79, comment 'the current price applies to the LATEST fiscal period only') and the 6-month momentum to out.iloc[-1] (snapshot.py:96). After the F6 append, iloc[-1] is the newest-appended audited-only period (the OLDEST deep-history year, e.g. 2022 in the repro / 2010s in production), not the latest. So for any scraped symbol that also has deep FSDS/EDGAR history — exactly the US large/mid caps F6 was meant to serve — the current price, return_6m and all price-derived ratios (P/E, P/B, yields) attach to a stale historical period; the true latest period gets NaN price and NaN momentum, and its value/momentum ranks are wrong. The F6 unit test only asserts values by label (test_fr010_esef.py) and never checks period order, so the suite stayed green.
```
61:     extra_periods = [p for p in audited.index if p not in merged.index]
62:     if extra_periods:
63:         merged = merged.reindex(list(merged.index) + extra_periods)
64:     audited_fields: dict[str, list[str]] = {}
65:     discrepancies: list[dict] = []
```
**Verdict:** ______  ·  **Note:** ______

## F1 · src/crible/compute/snapshot.py:79
**Finding:** The c2 F6 fix stopped reconcile from dropping audited-only periods, but it appends them at the END of the frame without re-sorting: reconcile.py:63 does merged.reindex(list(merged.index) + extra_periods). build_canonical guarantees an ascending period index, and build_symbol_snapshot relies on that invariant — it writes the current close to price.iloc[-1] (snapshot.py:79, comment 'the current price applies to the LATEST fiscal period only') and the 6-month momentum to out.iloc[-1] (snapshot.py:96). After the F6 append, iloc[-1] is the newest-appended audited-only period (the OLDEST deep-history year, e.g. 2022 in the repro / 2010s in production), not the latest. So for any scraped symbol that also has deep FSDS/EDGAR history — exactly the US large/mid caps F6 was meant to serve — the current price, return_6m and all price-derived ratios (P/E, P/B, yields) attach to a stale historical period; the true latest period gets NaN price and NaN momentum, and its value/momentum ranks are wrong. The F6 unit test only asserts values by label (test_fr010_esef.py) and never checks period order, so the suite stayed green.
```
77:             # older periods keep NaN rather than pretending historical prices
78:             price = pd.Series(float("nan"), index=canonical.index)
79:             price.iloc[-1] = value
80: 
81:     ratios = compute_ratios(canonical, price)
```
**Verdict:** ______  ·  **Note:** ______

## F1 · src/crible/compute/snapshot.py:96
**Finding:** The c2 F6 fix stopped reconcile from dropping audited-only periods, but it appends them at the END of the frame without re-sorting: reconcile.py:63 does merged.reindex(list(merged.index) + extra_periods). build_canonical guarantees an ascending period index, and build_symbol_snapshot relies on that invariant — it writes the current close to price.iloc[-1] (snapshot.py:79, comment 'the current price applies to the LATEST fiscal period only') and the 6-month momentum to out.iloc[-1] (snapshot.py:96). After the F6 append, iloc[-1] is the newest-appended audited-only period (the OLDEST deep-history year, e.g. 2022 in the repro / 2010s in production), not the latest. So for any scraped symbol that also has deep FSDS/EDGAR history — exactly the US large/mid caps F6 was meant to serve — the current price, return_6m and all price-derived ratios (P/E, P/B, yields) attach to a stale historical period; the true latest period gets NaN price and NaN momentum, and its value/momentum ranks are wrong. The F6 unit test only asserts values by label (test_fr010_esef.py) and never checks period order, so the suite stayed green.
```
94:         if pd.isna(momentum) and momentum_6m is not None:
95:             momentum = momentum_6m  # distilled from the imported dump
96:         out.iloc[-1, out.columns.get_loc("return_6m")] = momentum
97:     out.insert(0, "symbol", symbol)
98:     out.insert(1, "period", out.index.astype(str))
```
**Verdict:** ______  ·  **Note:** ______

## F7 · src/crible/providers/edinet.py:107
**Finding:** The audited enrichment cycles all still live in one module: enrichment.py is 617 LOC holding 7 parallel run_* cycles (ESEF, EDGAR, EDGAR-bulk, FSDS, Companies House, EDINET, ESEF-sweep) at reconcile.py:43-513. The per-cycle contracts are already clean, so each could move beside its provider (or an ingest/cycles/ package) to stop one file growing with every new source.
```
105:             continue  # monetary facts only
106:         column, statement = mapped
107:         period = _period(contexts.get(ctxref), statement)
108:         if period is None:
109:             continue
```
**Verdict:** ______  ·  **Note:** ______

## F1 · src/crible/compute/canonical.py:104
**Finding:** The c2 F6 fix stopped reconcile from dropping audited-only periods, but it appends them at the END of the frame without re-sorting: reconcile.py:63 does merged.reindex(list(merged.index) + extra_periods). build_canonical guarantees an ascending period index, and build_symbol_snapshot relies on that invariant — it writes the current close to price.iloc[-1] (snapshot.py:79, comment 'the current price applies to the LATEST fiscal period only') and the 6-month momentum to out.iloc[-1] (snapshot.py:96). After the F6 append, iloc[-1] is the newest-appended audited-only period (the OLDEST deep-history year, e.g. 2022 in the repro / 2010s in production), not the latest. So for any scraped symbol that also has deep FSDS/EDGAR history — exactly the US large/mid caps F6 was meant to serve — the current price, return_6m and all price-derived ratios (P/E, P/B, yields) attach to a stale historical period; the true latest period gets NaN price and NaN momentum, and its value/momentum ranks are wrong. The F6 unit test only asserts values by label (test_fr010_esef.py) and never checks period order, so the suite stayed green.
```
102:         # yfinance capital_expenditure is negative
103:         out["free_cash_flow"] = out["operating_cashflow"] + out["capital_expenditure"]
104:     if out["earnings_before_interest_and_taxes"].isna().all():
105:         out["earnings_before_interest_and_taxes"] = (
106:             out["income_before_tax"] + out["interest_expense"]
```
**Verdict:** ______  ·  **Note:** ______

## F1 · run:runs/regression-price-period.txt#L1
**Finding:** The c2 F6 fix stopped reconcile from dropping audited-only periods, but it appends them at the END of the frame without re-sorting: reconcile.py:63 does merged.reindex(list(merged.index) + extra_periods). build_canonical guarantees an ascending period index, and build_symbol_snapshot relies on that invariant — it writes the current close to price.iloc[-1] (snapshot.py:79, comment 'the current price applies to the LATEST fiscal period only') and the 6-month momentum to out.iloc[-1] (snapshot.py:96). After the F6 append, iloc[-1] is the newest-appended audited-only period (the OLDEST deep-history year, e.g. 2022 in the repro / 2010s in production), not the latest. So for any scraped symbol that also has deep FSDS/EDGAR history — exactly the US large/mid caps F6 was meant to serve — the current price, return_6m and all price-derived ratios (P/E, P/B, yields) attach to a stale historical period; the true latest period gets NaN price and NaN momentum, and its value/momentum ranks are wrong. The F6 unit test only asserts values by label (test_fr010_esef.py) and never checks period order, so the suite stayed green.
```
1: merged period order: ['2023', '2024', '2019', '2020', '2021', '2022']
2: return_6m landed on period: ['2022'] (expected ['2024'])
3: latest period 2024 return_6m: nan
```
**Verdict:** ______  ·  **Note:** ______

## F2 · src/crible/compute/snapshot.py:199
**Finding:** build_symbol_rows passes audited_frames=audited only when a yfinance scrape exists, else None (snapshot.py:199), while feeding the audited data in as the primary frames (scraped or audited, snapshot.py:197). In build_symbol_snapshot the audited_fields provenance is only populated inside the `if audited_frames:` block (snapshot.py:54, 60) and via reconcile (snapshot.py:65), so an audited-only symbol takes neither branch: every field is audited yet the audited_fields output column (snapshot.py:101-102) is empty. Row-level provider still records the source, so this is a provenance-completeness gap, not a data error — but it is exactly the case (a listing with no yfinance scrape) the audited layers exist to serve.
```
197:             scraped or audited,
198:             provider="yfinance" if scraped else _frames_provider(audited, "esef"),
199:             audited_frames=audited if scraped else None,
200:             price_quote=(quote[0], quote[1]) if quote else None,
201:             momentum_6m=quote[2] if quote else None,
```
**Verdict:** ______  ·  **Note:** ______

## F2 · src/crible/compute/snapshot.py:54
**Finding:** build_symbol_rows passes audited_frames=audited only when a yfinance scrape exists, else None (snapshot.py:199), while feeding the audited data in as the primary frames (scraped or audited, snapshot.py:197). In build_symbol_snapshot the audited_fields provenance is only populated inside the `if audited_frames:` block (snapshot.py:54, 60) and via reconcile (snapshot.py:65), so an audited-only symbol takes neither branch: every field is audited yet the audited_fields output column (snapshot.py:101-102) is empty. Row-level provider still records the source, so this is a provenance-completeness gap, not a data error — but it is exactly the case (a listing with no yfinance scrape) the audited layers exist to serve.
```
52:     canonical = build_canonical(frames)
53:     audited_fields: dict[str, list[str]] = {}
54:     if audited_frames:
55:         from crible.compute.reconcile import align_periods, reconcile
56: 
```
**Verdict:** ______  ·  **Note:** ______

## F2 · src/crible/compute/snapshot.py:101
**Finding:** build_symbol_rows passes audited_frames=audited only when a yfinance scrape exists, else None (snapshot.py:199), while feeding the audited data in as the primary frames (scraped or audited, snapshot.py:197). In build_symbol_snapshot the audited_fields provenance is only populated inside the `if audited_frames:` block (snapshot.py:54, 60) and via reconcile (snapshot.py:65), so an audited-only symbol takes neither branch: every field is audited yet the audited_fields output column (snapshot.py:101-102) is empty. Row-level provider still records the source, so this is a provenance-completeness gap, not a data error — but it is exactly the case (a listing with no yfinance scrape) the audited layers exist to serve.
```
99:     out["provider"] = provider
100:     out["price_asof"] = price_asof
101:     out["audited_fields"] = [
102:         ",".join(audited_fields.get(str(p), [])) or None for p in out["period"]
103:     ]
```
**Verdict:** ______  ·  **Note:** ______

## F8 · src/crible/ingest/enrichment.py:513
**Finding:** build_symbol_rows passes audited_frames=audited only when a yfinance scrape exists, else None (snapshot.py:199), while feeding the audited data in as the primary frames (scraped or audited, snapshot.py:197). In build_symbol_snapshot the audited_fields provenance is only populated inside the `if audited_frames:` block (snapshot.py:54, 60) and via reconcile (snapshot.py:65), so an audited-only symbol takes neither branch: every field is audited yet the audited_fields output column (snapshot.py:101-102) is empty. Row-level provider still records the source, so this is a provenance-completeness gap, not a data error — but it is exactly the case (a listing with no yfinance scrape) the audited layers exist to serve.
```
511: 
512: 
513: def run_esef_sweep(
514:     limit: int = 100, client=None, mapping: dict[str, str] | None = None,
515:     page_size: int = 100, max_pages: int = 300,
```
**Verdict:** ______  ·  **Note:** ______

## F3 · src/crible/providers/edinet.py:198
**Finding:** list_documents requests all filings for a day with type=2 and no docTypeCode/ordinanceCode filter (edinet.py:198-201), and parse_xbrl_instance takes a balance instant from any context whose period resolves (edinet.py:56-63, 107) with no guard that the instant belongs to an annual securities report (有価証券報告書). Income/cashflow are protected by the full-year duration check, but balance instants are not, so a quarterly/semi-annual report's period-end instant can be booked as the annual balance. EDINET is opt-in (requires a Subscription-Key) so blast radius is limited, but the values are silently wrong when it is enabled.
```
196: 
197:     def list_documents(self, day: str) -> list[dict]:
198:         response = self._http.get(
199:             f"{API_BASE}/documents.json",
200:             params={"date": day, "type": 2, "Subscription-Key": self._key},
```
**Verdict:** ______  ·  **Note:** ______

## F9 · src/crible/ingest/enrichment.py:43
**Finding:** build_symbol_rows passes audited_frames=audited only when a yfinance scrape exists, else None (snapshot.py:199), while feeding the audited data in as the primary frames (scraped or audited, snapshot.py:197). In build_symbol_snapshot the audited_fields provenance is only populated inside the `if audited_frames:` block (snapshot.py:54, 60) and via reconcile (snapshot.py:65), so an audited-only symbol takes neither branch: every field is audited yet the audited_fields output column (snapshot.py:101-102) is empty. Row-level provider still records the source, so this is a provenance-completeness gap, not a data error — but it is exactly the case (a listing with no yfinance scrape) the audited layers exist to serve.
```
41: 
42: 
43: def run_esef_cycle(limit: int = 5, client=None, mapping: dict[str, str] | None = None) -> dict:
44:     """FR-010 — the ESEF enrichment cycle: EU companies whose ISIN resolves to
45:     an LEI (GLEIF file at data/isin-lei.csv, operator-provided) get audited
```
**Verdict:** ______  ·  **Note:** ______

## F3 · src/crible/providers/edinet.py:61
**Finding:** list_documents requests all filings for a day with type=2 and no docTypeCode/ordinanceCode filter (edinet.py:198-201), and parse_xbrl_instance takes a balance instant from any context whose period resolves (edinet.py:56-63, 107) with no guard that the instant belongs to an annual securities report (有価証券報告書). Income/cashflow are protected by the full-year duration check, but balance instants are not, so a quarterly/semi-annual report's period-end instant can be booked as the annual balance. EDINET is opt-in (requires a Subscription-Key) so blast radius is limited, but the values are silently wrong when it is enabled.
```
59:     instant = ctx.get("instant")
60:     if statement == "balance":
61:         if not instant:
62:             return None
63:         end = instant
```
**Verdict:** ______  ·  **Note:** ______

## F3 · src/crible/providers/edinet.py:107
**Finding:** list_documents requests all filings for a day with type=2 and no docTypeCode/ordinanceCode filter (edinet.py:198-201), and parse_xbrl_instance takes a balance instant from any context whose period resolves (edinet.py:56-63, 107) with no guard that the instant belongs to an annual securities report (有価証券報告書). Income/cashflow are protected by the full-year duration check, but balance instants are not, so a quarterly/semi-annual report's period-end instant can be booked as the annual balance. EDINET is opt-in (requires a Subscription-Key) so blast radius is limited, but the values are silently wrong when it is enabled.
```
105:             continue  # monetary facts only
106:         column, statement = mapped
107:         period = _period(contexts.get(ctxref), statement)
108:         if period is None:
109:             continue
```
**Verdict:** ______  ·  **Note:** ______

## F4 · src/crible/providers/edinet.py:88
**Finding:** parse_xbrl_instance records only start/end/instant from each context (edinet.py:87-93) and never the explicit member that marks 連結 (Consolidated) vs 単体 (NonConsolidated). When both a consolidated and a non-consolidated context exist for the same concept and period, the winner is decided purely by concept rank / first-writer (edinet.py:114-119) with no preference for the consolidated member, so a parent-only figure can be booked as the group's audited value. Opt-in (Subscription-Key) so limited blast radius.
```
86:             continue
87:         info: dict[str, str] = {}
88:         for elem in ctx.iter():
89:             local = _local(elem.tag)
90:             field = {"startdate": "start", "enddate": "end", "instant": "instant"}.get(local)
```
**Verdict:** ______  ·  **Note:** ______

## F4 · src/crible/providers/edinet.py:116
**Finding:** parse_xbrl_instance records only start/end/instant from each context (edinet.py:87-93) and never the explicit member that marks 連結 (Consolidated) vs 単体 (NonConsolidated). When both a consolidated and a non-consolidated context exist for the same concept and period, the winner is decided purely by concept rank / first-writer (edinet.py:114-119) with no preference for the consolidated member, so a parent-only figure can be booked as the group's audited value. Opt-in (Subscription-Key) so limited blast radius.
```
114:         rank = CONCEPT_RANK[_local(elem.tag)]
115:         key = (period, column)
116:         if key in claimed and claimed[key] <= rank:
117:             continue
118:         values.setdefault(period, {})[column] = value
```
**Verdict:** ______  ·  **Note:** ______

## F5 · src/crible/ingest/enrichment.py:43
**Finding:** The audited enrichment cycles all still live in one module: enrichment.py is 617 LOC holding 7 parallel run_* cycles (ESEF, EDGAR, EDGAR-bulk, FSDS, Companies House, EDINET, ESEF-sweep) at reconcile.py:43-513. The per-cycle contracts are already clean, so each could move beside its provider (or an ingest/cycles/ package) to stop one file growing with every new source.
```
41: 
42: 
43: def run_esef_cycle(limit: int = 5, client=None, mapping: dict[str, str] | None = None) -> dict:
44:     """FR-010 — the ESEF enrichment cycle: EU companies whose ISIN resolves to
45:     an LEI (GLEIF file at data/isin-lei.csv, operator-provided) get audited
```
**Verdict:** ______  ·  **Note:** ______

## F5 · src/crible/ingest/enrichment.py:513
**Finding:** The audited enrichment cycles all still live in one module: enrichment.py is 617 LOC holding 7 parallel run_* cycles (ESEF, EDGAR, EDGAR-bulk, FSDS, Companies House, EDINET, ESEF-sweep) at reconcile.py:43-513. The per-cycle contracts are already clean, so each could move beside its provider (or an ingest/cycles/ package) to stop one file growing with every new source.
```
511: 
512: 
513: def run_esef_sweep(
514:     limit: int = 100, client=None, mapping: dict[str, str] | None = None,
515:     page_size: int = 100, max_pages: int = 300,
```
**Verdict:** ______  ·  **Note:** ______

## F6 · src/crible/ingest/mirror.py:102
**Finding:** fetch_if_stale streams response.iter_bytes to disk with no byte ceiling (mirror.py:102) under an httpx timeout that is per-operation, not total (mirror.py:88). URLs are hardcoded/trusted (no SSRF), but a misbehaving or hostile mirror could fill the disk or keep a slow ~200MB GLEIF download alive indefinitely on the auto-heal path.
```
100:             tmp = path.with_name(path.name + ".tmp")
101:             with open(tmp, "wb") as out:
102:                 for block in response.iter_bytes(chunk):
103:                     out.write(block)
104:             tmp.rename(path)
```
**Verdict:** ______  ·  **Note:** ______

## F6 · src/crible/ingest/mirror.py:88
**Finding:** fetch_if_stale streams response.iter_bytes to disk with no byte ceiling (mirror.py:102) under an httpx timeout that is per-operation, not total (mirror.py:88). URLs are hardcoded/trusted (no SSRF), but a misbehaving or hostile mirror could fill the disk or keep a slow ~200MB GLEIF download alive indefinitely on the auto-heal path.
```
86:         import httpx
87: 
88:         http = httpx.Client(timeout=120, follow_redirects=True)
89: 
90:     request_headers = dict(headers or {})
```
**Verdict:** ______  ·  **Note:** ______

