# crible — état d'avancement

_Mise à jour : 2026-07-07 ~02:00. Mode autonome (Maxime dort). **BUILD COMPLET — E2E ZÉRO CLÉ VALIDÉ SUR DONNÉES RÉELLES.**_

## Résultat

**Les 16 tâches du BUILD-PLAN sont done. `construct verify --run-tests --strict` : ✓ (les 14 FRs ont leurs tests ; pytest 78 + vitest 3, tout vert).**

**E2E zéro clé RÉEL validé** (docker compose up sans aucune clé) :
- Services `ingest` + `api` healthy en 25 s (AC ≤ 120 s).
- Bootstrap FinanceDatabase réel → univers ~161k, sample CAC40/DAX/US crawlé en premier.
- Crawl Yahoo réel sous budget (330 req/h, comptage par requête), backoff sur 429, junk symbols (delisted) gérés proprement.
- Compute réel : **482 lignes × 217 colonnes** publiées (46 ratios ftk auto-câblés + scores + growth + provenance).
- **Screen Europe réel : `piotroski_f >= 7 AND country IN ('FR','DE','NL')` → 10 sociétés en 49 ms** (LISI F=9, Streamwide F=8, SAP F=8, lastminute.com F=7…).
- Export CSV complet ✓, SPA servie à `/` ✓ (fix chemin container), API 6 rows après mount ✓.
- Benchmark NFR-008 (161k × ~200 synthétique) : tous les presets + batterie ad-hoc **p95 < 1 s** ✓.

## Gates SRD (tous passés)

- `check` structurel ✓ ; grounding 14/14 FR, 4/4 ADR ; `check --semantic` **PASS** (40/40 paires adjugées, 0 refuted/unsupported).
- 3 rounds de revue adversariale (11 blockers R1 → tous fermés ; découverte R3 : **Stooq derrière un mur anti-bot PoW** → FR-011 redessiné : prix sous budget Yahoo, provenance `price_asof`).
- Revue milestone finale (couverture AC↔test) : lancée, résultat à consigner ici.

## Bugs réels trouvés PAR l'E2E (et fixés + tests de non-régression)

1. Colonnes méta du raw layer cassaient le join canonical (MergeError) → drop `_*` + test round-trip.
2. Premier cycle (50×7 > budget 330) retardait le premier snapshot → cycles 40 + premier cycle = taille sample.
3. `universe.parquet` manquant sur installs antérieurs → self-heal dans run_compute.
4. SPA non servie en container (résolution site-packages) → chemin CWD-relatif `CRIBLE_UI_DIST`.
5. ftk Piotroski ΔROA à l'envers (bug ftk#91 = [E39]) → critère maison conforme à la définition publiée.

## Décisions autonomes à revalider par Maxime

1. **Stooq rétrogradé** (mur anti-bot vérifié au curl) — prix sous budget Yahoo, tiering priorité, plugin stooq optionnel désactivé.
2. `country` = ISO-2 (DSL `country IN ('FR','DE')`), `country_name` = nom complet.
3. Lecteurs 100 % Parquet (jamais le duckdb du crawler) — univers exporté, snapshot auto-suffisant.
4. Beneish : vecteurs analytiques dérivés de la formule publiée 1999 (données exactes du papier non librement vérifiables).
5. PRD EODHD ancré sur payloads réels du token public `demo` (41 exercices AAPL vérifiés) ; €59,99/100k = à revalider à l'achat.
6. Repo PRIVÉ local — pas de push GitHub sans demande explicite.

## Ce qui reste (optionnel / phase 2)

- ~~Brancher l'enrichissement ESEF dans la boucle ingest~~ **FAIT** (`run_esef_cycle` : GLEIF→LEI→filings→raw esef, outage-safe, unmatched compté ; idle tant que `data/isin-lei.csv` n'est pas déposé — fichier GLEIF ~200 Mo, téléchargement volontaire de l'opérateur).
- ~~Refresher prix branché sur la boucle~~ **FAIT** (`run_price_refresh` quotidien sur le sample prioritaire, budget partagé).
- Plugin financialreports (MCP OAuth — à évaluer, cf. risques M3).
- E2E zéro clé en nightly CI (manuel pour l'instant — budget réel).
- Publication GitHub (privé→public) quand Maxime valide.
- 81 tests pytest + 3 vitest au total après câblage.

## Comment vérifier

```bash
cd ~/Downloads/crible
uv run pytest                      # 78 tests
npm --prefix ui run test -- --run  # 3 tests
node ~/.claude/skills/construct/scripts/construct.mjs verify --out srd --run-tests --strict
docker compose up -d               # zéro clé → http://localhost:8000 (SPA + API)
crible screen "piotroski_f >= 7 AND country IN ('FR','DE')"   # via uv run
```
