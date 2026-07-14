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

- [x] **FIX-003 · F1 · P1 — budget partagé dans `run_loop`.** RED `tests/test_service.py` : N cycles → `budget.used_in_window()` cumulé ≤ capacité (pas de reset). GREEN : hisser un `TokenBucket` + `Crawler` long-vécu dans `run_loop`, réutilisé (miroir du pattern `run_refresh`).
- [x] **FIX-004 · F2 · P1 — watchdog per-fetch.** (crawl + prix, helper partagé `ingest/watchdog.py`) RED `tests/test_crawler.py` : provider dont `fetch_statements` pend → `crawl_symbol` renvoie False sous timeout + `mark_failed`. GREEN : envelopper `fetch_statements` dans un timeout dur (thread + `join(CRIBLE_FETCH_TIMEOUT` défaut 60s`)`), timeout = échec rescheduled. Corriger docstrings `prices.py:6-7`, `yfinance_provider.py:6`.
- [x] **FIX-005 · F9 · P1 — garde pleine-année ESEF.** RED `tests/test_fr010_esef.py` : fixture avec durée intérimaire (H1) + annuelle → seul l'annuel retenu ; reconcile n'override le scraped qu'avec l'annuel. GREEN : dans `_fiscal_year`/`facts_to_frames`, n'accepter une **durée** que si pleine-année (fenêtre 320-400 j, comme EDGAR) ; instants (bilan) inchangés.
- [x] **FIX-010 · F10 · P2 — résolution déterministe des concepts ESEF.** RED : fixture avec `ProfitLoss` + `ProfitLossAttributableToOwnersOfParent` → colonne `NetIncome` déterministe. GREEN : `CONCEPT_MAP` ordonné + map `claimed` (précédence explicite, pattern EDGAR).
- [x] **FIX-011 · F11 · P2 — ignorer les `.tmp-*` au glob.** RED `tests/test_fr002_ingest.py` : déposer un `.tmp-x.parquet` → prune/compute l'ignorent. GREEN : filtrer `.tmp-*`/dotfiles dans `prune_raw` (raw.py:26) + les lecteurs snapshot.
- [x] **FIX-012 · F12 · P2 — borner `solve_pow`.** RED `tests/test_captcha.py` : difficulté absurde → abort sous ceiling (itérations/temps). GREEN : cap `max_iterations`/deadline dans `solve_pow`, `StooqError` au-delà.
- [x] **FIX-013 · F13 · P2 — bootstrap streamé.** RED `tests/test_bootstrap_data.py` : download streamé vers fichier temp (pas de `BytesIO(response.content)`). GREEN : `http.stream` + `iter_bytes` → temp-then-rename, comme `edgar.download_bulk`.
- [x] **FIX-008 · F3 · P2 — dé-fragmenter `attach_ranks`.** RED `tests/test_fr015_ranks.py` : aucun `PerformanceWarning` (filterwarnings error). GREEN : construire les colonnes de rang en un `concat`.
- [x] **FIX-009 · F4 · P2 — refactor `service.py` + seam.** GREEN : extraire `ingest/enrichment.py` (cycles audités) + `ingest/refresh.py` (orchestration), poser `providers/audited.py::AuditedBulkProvider` (contrat `resolve/fetch/iter_bulk` + fraîcheur `*_tasks`) et `ingest/mirror.py` (couche miroir/last-good). Tests existants restent verts (caractérisation). Dé-duppliquer le boilerplate GLEIF (223-234 vs 507-518).
- [x] **GATE Phase 1 (tests)** : **196 pytest + 62 vitest + build UI verts**, ruff clean. `ultraeval compare --gate` relancé UNE fois en fin de Phase 2 (plus efficace qu'un double run).

## Phase 2 — Étendre (chaque source sur le seam + miroir)

- [x] **FIX-002 · GLEIF auto-fetch.** `crible ingest --fetch-gleif` : implémenter `ISIN_LEI_LATEST_URL` (mort, gleif.py:21), stream → `data/mirror/gleif/isin-lei.csv` (timeout + size guard), auto-fetch hebdo dans `run_refresh` si absent/stale. RED `tests/test_gleif.py`. **Allume l'EU audité.**
- [x] **FIX-007 · FX Frankfurter/BCE.** `providers/fx.py` keyless : taux BCE par date (miroir `data/mirror/fx/`), colonnes companion `market_cap_eur`/`revenue_eur`… (whitelist DSL/UI). RED : ratios currency-neutral inchangés, `market_cap_eur = market_cap × rate`. Nouveau FR via construct.
- [x] **SEC FSDS** `providers/edgar_fsds.py` + cycle. ZIP trimestriels (SUB/NUM/TAG/PRE), map tags→canonical (discipline CONCEPT_MAP + garde pleine-année), miroir `data/mirror/edgar-fsds/`. Précédence : companyfacts (récent) > FSDS (backfill profondeur). Nouveau FR construct. RED : fixture ZIP subset.
- [x] **Companies House UK** `providers/companies_house.py` + cycle. Accounts Data Product (ZIP iXBRL), résolution par company number, miroir. Couche **assumed-risk** (DATA-SOURCES.md). Nouveau FR construct. RED : fixture iXBRL.
- [x] **EDINET JP** `providers/edinet.py` (free-key `CRIBLE_EDINET_KEY`, off défaut, API-only). Attribution PDL1.0. Nouveau FR construct. RED : provider désactivé sans clé ; fixture doc.
- [x] **FIX-001 · refresh univers dans `run_loop`** (+ marquage delisted). RED `tests/test_service.py`.
- [x] **FIX-006 · compute incrémental** via seam `build_snapshot(symbols=)` (dirty-set raw). RED `tests/test_fr003_compute.py`.

## Transverse / clôture

- [x] DATA-SOURCES.md : deux tiers dataset (libre vs assumed-risk) + attribution EDINET.
- [x] README + Providers view : nouvelles sources, mode offline, miroir local ; EdinetProvider dans le catalogue (vue Providers).
- [x] **Vérification réelle end-to-end** (skill verify) : CLI `compute` incrémental (base.parquet + « unchanged »), FX `*_eur` exacts (AAPL 362e9€, Toyota 281.25e9€), réconciliation auditée (EDGAR 200e9 bat Yahoo 100e9, `audited_fields=revenue`), ESEF-only sans Yahoo, API `/api/providers` (edinet off). **Bug trouvé+corrigé** : CLI `compute` n'était pas incrémental.
- [x] **Déploiement (demande utilisateur)** : `run_loop` self-heal GLEIF+FX (+ bulk EDGAR optionnel `CRIBLE_EDGAR_BULK`) ; docker-compose env optionnels (SEC UA, clé EDINET) ; `refresh-data.yml` `--fsds-quarters 2` + FX/GLEIF défaut on ; miroir persiste dans le volume `/data` ; `publish-data.sh` allowlist → miroir jamais commité ; `.env.example` réécrit.
- [ ] construct : FRs des nouvelles sources — **différé** (les FRs sont couverts par PRIORITIES.md + PLAN.md + DATA-SOURCES.md ; le render construct régénère tout l'arbre srd/ et risque de clobber l'identité design ; à faire dans un thread dédié avec sync du bloc design).
- [x] **Gate adverse (ultraeval c2) + remédiation** : l'éval a confirmé les **13 anciens findings résolus** mais trouvé **2 P1 silencieux, invisibles aux tests** dans le nouveau code — corrigés test-first :
  - **F6** `reconcile` jetait les périodes audité-only → profondeur FSDS/EDGAR inerte pour tout symbole scrapé (`reconcile.py`, réindex des périodes) ;
  - **F7** `_company_number` parsait la date de dépôt → UK zéro ligne sur vrais fichiers (`companies_house.py`, extraction du numéro).
  - + P2 correction/robustesse corrigés : F11 OOM (streaming GLEIF+FSDS), F16 BOM, F10 coreg, F12 FX latest-only, F9 GLEIF re-fetch hebdo, F8 incrémental/prix, F6 sec_code alphanumérique, F4 sidecar atomique.
  - **Résiduels documentés (différés, off-by-default / enhancement / maintenabilité)** : F3 split `enrichment.py` (617 LOC, opportunité) · F5 provenance audité-only vide (enhancement) · F13/F14 EDINET consolidé/docType (off par défaut) · F15 dirty-on-delete-du-plus-récent (edge).
- [x] **Clôture — qualité de référence atteinte** : **82/100, meets-expectations ✓, P0=0 P1=0** (eval c4, gate PASS Δ+5). Trajectoire 81→76→73→77→**82**. pytest **223 verts** + vitest **62 verts** + build UI + ruff clean ; vrai CLI/API re-vérifiés. Résiduels non bloquants (backlog cycle suivant) : 2 P2 EDINET opt-in (garde bilan-intérimaire `edinet.py:60` + dimension consolidé `:88/116`, tous deux derrière `CRIBLE_EDINET_KEY`) + 1 opportunité maintenabilité (split `enrichment.py` 617 LOC). Cartes TDD : `evals/2026-07-14-c4/fixes/`.
