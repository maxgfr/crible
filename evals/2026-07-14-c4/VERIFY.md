# Verification worklist

For each pair: read the digest, judge whether it SUPPORTS the finding, write a verdict.
Verdicts: `supported` · `partial` · `refuted` · `unsupported`.

## F1 · src/crible/providers/edinet.py:197
**Finding:** list_documents requests all filings for a day with type=2 and no docTypeCode/ordinanceCode filter (edinet.py:197-200), and _period takes a balance instant from any context whose period resolves (edinet.py:59-63) with no guard that the instant belongs to an annual securities report (有価証券報告書). Income/cashflow are protected by the full-year duration check (edinet.py:64-69), but balance instants are NOT, so a quarterly/semi-annual report's period-end instant can be booked as the annual balance. EDINET is opt-in (requires a Subscription-Key, edinet.py:200) so blast radius is limited, but the values are silently wrong when it is enabled.
```
195:         self._http = http
196: 
197:     def list_documents(self, day: str) -> list[dict]:
198:         response = self._http.get(
199:             f"{API_BASE}/documents.json",
```
**Verdict:** ______  ·  **Note:** ______

## F4 · src/crible/providers/edinet.py:88
**Finding:** The audited enrichment cycles all still live in one module: enrichment.py is 617 LOC holding 7 parallel run_* cycles (ESEF enrichment.py:43, EDGAR :131, EDGAR-bulk :214, FSDS :301, Companies House :396, EDINET :437, ESEF-sweep :513). The per-cycle contracts are already clean, so each could move beside its provider (or an ingest/cycles/ package) to stop one file growing with every new source.
```
86:             continue
87:         info: dict[str, str] = {}
88:         for elem in ctx.iter():
89:             local = _local(elem.tag)
90:             field = {"startdate": "start", "enddate": "end", "instant": "instant"}.get(local)
```
**Verdict:** ______  ·  **Note:** ______

## F1 · src/crible/providers/edinet.py:60
**Finding:** list_documents requests all filings for a day with type=2 and no docTypeCode/ordinanceCode filter (edinet.py:197-200), and _period takes a balance instant from any context whose period resolves (edinet.py:59-63) with no guard that the instant belongs to an annual securities report (有価証券報告書). Income/cashflow are protected by the full-year duration check (edinet.py:64-69), but balance instants are NOT, so a quarterly/semi-annual report's period-end instant can be booked as the annual balance. EDINET is opt-in (requires a Subscription-Key, edinet.py:200) so blast radius is limited, but the values are silently wrong when it is enabled.
```
58:         return None
59:     instant = ctx.get("instant")
60:     if statement == "balance":
61:         if not instant:
62:             return None
```
**Verdict:** ______  ·  **Note:** ______

## F1 · src/crible/providers/edinet.py:90
**Finding:** list_documents requests all filings for a day with type=2 and no docTypeCode/ordinanceCode filter (edinet.py:197-200), and _period takes a balance instant from any context whose period resolves (edinet.py:59-63) with no guard that the instant belongs to an annual securities report (有価証券報告書). Income/cashflow are protected by the full-year duration check (edinet.py:64-69), but balance instants are NOT, so a quarterly/semi-annual report's period-end instant can be booked as the annual balance. EDINET is opt-in (requires a Subscription-Key, edinet.py:200) so blast radius is limited, but the values are silently wrong when it is enabled.
```
88:         for elem in ctx.iter():
89:             local = _local(elem.tag)
90:             field = {"startdate": "start", "enddate": "end", "instant": "instant"}.get(local)
91:             if field and elem.text:
92:                 info[field] = elem.text.strip()
```
**Verdict:** ______  ·  **Note:** ______

## F5 · src/crible/ingest/enrichment.py:513
**Finding:** parse_xbrl_instance records only start/end/instant from each context (edinet.py:88-93) and never the explicit member that marks 連結 (Consolidated) vs 単体 (NonConsolidated). When both a consolidated and a non-consolidated context exist for the same concept and period, the winner is decided purely by concept rank / first-writer (edinet.py:114-119) with no preference for the consolidated member, so a parent-only figure can be booked as the group's audited value. Opt-in (Subscription-Key) so limited blast radius.
```
511: 
512: 
513: def run_esef_sweep(
514:     limit: int = 100, client=None, mapping: dict[str, str] | None = None,
515:     page_size: int = 100, max_pages: int = 300,
```
**Verdict:** ______  ·  **Note:** ______

## F6 · src/crible/ingest/enrichment.py:513
**Finding:** list_documents requests all filings for a day with type=2 and no docTypeCode/ordinanceCode filter (edinet.py:197-200), and _period takes a balance instant from any context whose period resolves (edinet.py:59-63) with no guard that the instant belongs to an annual securities report (有価証券報告書). Income/cashflow are protected by the full-year duration check (edinet.py:64-69), but balance instants are NOT, so a quarterly/semi-annual report's period-end instant can be booked as the annual balance. EDINET is opt-in (requires a Subscription-Key, edinet.py:200) so blast radius is limited, but the values are silently wrong when it is enabled.
```
511: 
512: 
513: def run_esef_sweep(
514:     limit: int = 100, client=None, mapping: dict[str, str] | None = None,
515:     page_size: int = 100, max_pages: int = 300,
```
**Verdict:** ______  ·  **Note:** ______

## F2 · src/crible/providers/edinet.py:88
**Finding:** parse_xbrl_instance records only start/end/instant from each context (edinet.py:88-93) and never the explicit member that marks 連結 (Consolidated) vs 単体 (NonConsolidated). When both a consolidated and a non-consolidated context exist for the same concept and period, the winner is decided purely by concept rank / first-writer (edinet.py:114-119) with no preference for the consolidated member, so a parent-only figure can be booked as the group's audited value. Opt-in (Subscription-Key) so limited blast radius.
```
86:             continue
87:         info: dict[str, str] = {}
88:         for elem in ctx.iter():
89:             local = _local(elem.tag)
90:             field = {"startdate": "start", "enddate": "end", "instant": "instant"}.get(local)
```
**Verdict:** ______  ·  **Note:** ______

## F2 · src/crible/providers/edinet.py:116
**Finding:** parse_xbrl_instance records only start/end/instant from each context (edinet.py:88-93) and never the explicit member that marks 連結 (Consolidated) vs 単体 (NonConsolidated). When both a consolidated and a non-consolidated context exist for the same concept and period, the winner is decided purely by concept rank / first-writer (edinet.py:114-119) with no preference for the consolidated member, so a parent-only figure can be booked as the group's audited value. Opt-in (Subscription-Key) so limited blast radius.
```
114:         rank = CONCEPT_RANK[_local(elem.tag)]
115:         key = (period, column)
116:         if key in claimed and claimed[key] <= rank:
117:             continue
118:         values.setdefault(period, {})[column] = value
```
**Verdict:** ______  ·  **Note:** ______

## F3 · src/crible/ingest/enrichment.py:43
**Finding:** The audited enrichment cycles all still live in one module: enrichment.py is 617 LOC holding 7 parallel run_* cycles (ESEF enrichment.py:43, EDGAR :131, EDGAR-bulk :214, FSDS :301, Companies House :396, EDINET :437, ESEF-sweep :513). The per-cycle contracts are already clean, so each could move beside its provider (or an ingest/cycles/ package) to stop one file growing with every new source.
```
41: 
42: 
43: def run_esef_cycle(limit: int = 5, client=None, mapping: dict[str, str] | None = None) -> dict:
44:     """FR-010 — the ESEF enrichment cycle: EU companies whose ISIN resolves to
45:     an LEI (GLEIF file at data/isin-lei.csv, operator-provided) get audited
```
**Verdict:** ______  ·  **Note:** ______

## F3 · src/crible/ingest/enrichment.py:513
**Finding:** The audited enrichment cycles all still live in one module: enrichment.py is 617 LOC holding 7 parallel run_* cycles (ESEF enrichment.py:43, EDGAR :131, EDGAR-bulk :214, FSDS :301, Companies House :396, EDINET :437, ESEF-sweep :513). The per-cycle contracts are already clean, so each could move beside its provider (or an ingest/cycles/ package) to stop one file growing with every new source.
```
511: 
512: 
513: def run_esef_sweep(
514:     limit: int = 100, client=None, mapping: dict[str, str] | None = None,
515:     page_size: int = 100, max_pages: int = 300,
```
**Verdict:** ______  ·  **Note:** ______

