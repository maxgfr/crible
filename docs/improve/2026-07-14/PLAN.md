# PLAN — bulk-first, local-first data plane (cycle 2026-07-14)

Execution checklist. **Discipline** : TDD RED→GREEN, un writer, commit conventionnel par étape verte, **jamais de push**. Zéro clé / zéro CDN (NFR-013) non négociables. Phase 1 doit ramener `ultraeval compare --gate` à EXIT 0 (≥ 80) **avant** merge Phase 2.

Branch : `improve/2026-07-14-bulk-first-data`.

---

## Pilier transverse — local-first + last-good

- **Couche miroir bulk** `data/mirror/<source>/` : chaque archive (companyfacts.zip, FSDS, Companies House, GLEIF ISIN-LEI, taux BCE) fetchée une fois → gardée last-good → re-fetchée seulement si périmée (ETag/If-Modified-Since ⇒ re-fetch inchangé quasi gratuit). Régime permanent = ingestion lit le miroir, jamais l'API live par-enregistrement.
- **Échelle de dégradation par champ** (testée) : `audité-miroir` → `last-good raw audité` → `scrape Yahoo` → `last-good raw Yahoo` → `NULL` (jamais imputé). Source down = un cran plus bas, couverture ne régresse jamais.
- **Mode offline** : `crible refresh --offline` (auto si réseau down) rejoue compute+publish depuis miroir+raw, zéro appel externe. Miroir voyage sur la branche `data`.

---

## Phase 1 — Durcir (gate ≥ 80)

- [ ] **FIX-003 · F1 · P1 — budget partagé dans `run_loop`.** RED `tests/test_service.py` : N cycles → `budget.used_in_window()` cumulé ≤ capacité (pas de reset). GREEN : hisser un `TokenBucket` + `Crawler` long-vécu dans `run_loop`, réutilisé (miroir du pattern `run_refresh`).
- [ ] **FIX-004 · F2 · P1 — watchdog per-fetch.** RED `tests/test_crawler.py` : provider dont `fetch_statements` pend → `crawl_symbol` renvoie False sous timeout + `mark_failed`. GREEN : envelopper `fetch_statements` dans un timeout dur (thread + `join(CRIBLE_FETCH_TIMEOUT` défaut 60s`)`), timeout = échec rescheduled. Corriger docstrings `prices.py:6-7`, `yfinance_provider.py:6`.
- [ ] **FIX-005 · F9 · P1 — garde pleine-année ESEF.** RED `tests/test_fr010_esef.py` : fixture avec durée intérimaire (H1) + annuelle → seul l'annuel retenu ; reconcile n'override le scraped qu'avec l'annuel. GREEN : dans `_fiscal_year`/`facts_to_frames`, n'accepter une **durée** que si pleine-année (fenêtre 320-400 j, comme EDGAR) ; instants (bilan) inchangés.
- [ ] **FIX-010 · F10 · P2 — résolution déterministe des concepts ESEF.** RED : fixture avec `ProfitLoss` + `ProfitLossAttributableToOwnersOfParent` → colonne `NetIncome` déterministe. GREEN : `CONCEPT_MAP` ordonné + map `claimed` (précédence explicite, pattern EDGAR).
- [ ] **FIX-011 · F11 · P2 — ignorer les `.tmp-*` au glob.** RED `tests/test_fr002_ingest.py` : déposer un `.tmp-x.parquet` → prune/compute l'ignorent. GREEN : filtrer `.tmp-*`/dotfiles dans `prune_raw` (raw.py:26) + les lecteurs snapshot.
- [ ] **FIX-012 · F12 · P2 — borner `solve_pow`.** RED `tests/test_captcha.py` : difficulté absurde → abort sous ceiling (itérations/temps). GREEN : cap `max_iterations`/deadline dans `solve_pow`, `StooqError` au-delà.
- [ ] **FIX-013 · F13 · P2 — bootstrap streamé.** RED `tests/test_bootstrap_data.py` : download streamé vers fichier temp (pas de `BytesIO(response.content)`). GREEN : `http.stream` + `iter_bytes` → temp-then-rename, comme `edgar.download_bulk`.
- [ ] **FIX-008 · F3 · P2 — dé-fragmenter `attach_ranks`.** RED `tests/test_fr015_ranks.py` : aucun `PerformanceWarning` (filterwarnings error). GREEN : construire les colonnes de rang en un `concat`.
- [ ] **FIX-009 · F4 · P2 — refactor `service.py` + seam.** GREEN : extraire `ingest/enrichment.py` (cycles audités) + `ingest/refresh.py` (orchestration), poser `providers/audited.py::AuditedBulkProvider` (contrat `resolve/fetch/iter_bulk` + fraîcheur `*_tasks`) et `ingest/mirror.py` (couche miroir/last-good). Tests existants restent verts (caractérisation). Dé-duppliquer le boilerplate GLEIF (223-234 vs 507-518).
- [ ] **GATE Phase 1** : `pytest` + `vitest` verts ; `ultraeval` re-run partiel → `compare --gate` EXIT 0 (≥ 80).

## Phase 2 — Étendre (chaque source sur le seam + miroir)

- [ ] **FIX-002 · GLEIF auto-fetch.** `crible ingest --fetch-gleif` : implémenter `ISIN_LEI_LATEST_URL` (mort, gleif.py:21), stream → `data/mirror/gleif/isin-lei.csv` (timeout + size guard), auto-fetch hebdo dans `run_refresh` si absent/stale. RED `tests/test_gleif.py`. **Allume l'EU audité.**
- [ ] **FIX-007 · FX Frankfurter/BCE.** `providers/fx.py` keyless : taux BCE par date (miroir `data/mirror/fx/`), colonnes companion `market_cap_eur`/`revenue_eur`… (whitelist DSL/UI). RED : ratios currency-neutral inchangés, `market_cap_eur = market_cap × rate`. Nouveau FR via construct.
- [ ] **SEC FSDS** `providers/edgar_fsds.py` + cycle. ZIP trimestriels (SUB/NUM/TAG/PRE), map tags→canonical (discipline CONCEPT_MAP + garde pleine-année), miroir `data/mirror/edgar-fsds/`. Précédence : companyfacts (récent) > FSDS (backfill profondeur). Nouveau FR construct. RED : fixture ZIP subset.
- [ ] **Companies House UK** `providers/companies_house.py` + cycle. Accounts Data Product (ZIP iXBRL), résolution par company number, miroir. Couche **assumed-risk** (DATA-SOURCES.md). Nouveau FR construct. RED : fixture iXBRL.
- [ ] **EDINET JP** `providers/edinet.py` (free-key `CRIBLE_EDINET_KEY`, off défaut, API-only). Attribution PDL1.0. Nouveau FR construct. RED : provider désactivé sans clé ; fixture doc.
- [ ] **FIX-001 · refresh univers dans `run_loop`** (+ marquage delisted). RED `tests/test_service.py`.
- [ ] **FIX-006 · compute incrémental** via seam `build_snapshot(symbols=)` (dirty-set raw). RED `tests/test_fr003_compute.py`.

## Transverse / clôture

- [ ] DATA-SOURCES.md : deux tiers dataset (libre vs assumed-risk) + knob `--redistributable-only` ; attribution EDINET.
- [ ] README + Providers view : nouvelles sources, mode offline, miroir local.
- [ ] construct : FRs des nouvelles sources (`srd/SRD.json` → `render --from-srd --merge` → `check`), tests FR-taggés, `construct verify --strict`.
- [ ] Clôture : pytest + vitest + build verts, `compare --gate` EXIT 0, arbre propre, scorecard.
