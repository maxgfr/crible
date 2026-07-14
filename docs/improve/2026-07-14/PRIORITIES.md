# PRIORITIES — cycle improve 2026-07-14 (« durcir puis étendre », bulk-first local-first)

Sources : `evals/2026-07-14/` (score **76/100, BELOW expectations, barre 80**) × `docs/market/2026-07-14/REPORT.md` (marché + sources bulk-first, `check` vert, 30 sources). Gate inter-cycles : `compare --base evals/2026-07-12-c2 --gate` **EXIT 1** (Δ **−5**, 81 → 76) — première éval du pipeline EDGAR/ESEF/stooq livré le 2026-07-13 : 3 P1 + 6 P2 réels, hotspot `service.py` doublé (370 → 820 LOC).

**Décisions de cadrage (GO utilisateur)** : bulk-first ; **durcir ET étendre** ; **roadmap complète (5 sources)** ; principe directeur **« le plus local possible, jamais perdre de données, fallback partout »** → pilier transverse *local-first + last-good* (couche miroir bulk, échelle de dégradation par champ, mode offline).

## File 1 — Durcir (bugs/robustesse, exécutable sans gate marché)

Restaure le gate ≥ 80 **avant** tout merge de la Phase 2. Cartes TDD RED-first : `evals/2026-07-14/fixes/`.

| Réf | Sév | Fichier:ligne | Défaut | Carte |
|---|---|---|---|---|
| F1 | **P1** | `ingest/service.py:788` | `run_loop` recrée un `TokenBucket` neuf par cycle → budget 330 req/h busté en régime permanent (bans Yahoo). | FIX-003 |
| F2 | **P1** | `ingest/crawler.py:60-70` | Watchdog absent (2 docstrings mentent) — hang yfinance fige la boucle. | FIX-004 |
| F9 | **P1** | `providers/esef.py:87-103` | `_fiscal_year` tague par année de fin sans garde pleine-année → intérimaire stocké comme audité annuel → corruption silencieuse du chiffre auditée. | FIX-005 |
| F10 | P2 | `providers/esef.py:22-39,71` | Collisions de concepts non-déterministes (ordre JSON). | FIX-010 |
| F11 | P2 | `ingest/raw.py:51,26` | `glob("*.parquet")` matche les `.tmp-*` partiels → prune/compute pollués. | FIX-011 |
| F12 | P2 | `ingest/stooq_fetch.py:61-68` | `solve_pow` non borné sur difficulté serveur (DoS CPU). | FIX-012 |
| F13 | P2 | `bootstrap.py:148,153` | Dataset publié bufferisé entier (`BytesIO`) → OOM petit hôte. | FIX-013 |
| F3 | P2 | `compute/ranks.py:96-99` | `attach_ranks` fragmente la frame (PerformanceWarning ×16). | FIX-008 |
| F4 | P2 | `ingest/service.py` (820 LOC) | Hotspot #1 doublé — extraction + **pose du seam `AuditedBulkProvider` + couche miroir/last-good** (point d'extension Phase 2). | FIX-009 |

## File 2 — Étendre (bulk-first, évidence marché [S#])

Chaque source = un `AuditedBulkProvider` + un cycle câblé dans `run_refresh`, symétrique EDGAR/ESEF, lisant **le miroir local** en régime permanent.

1. **GLEIF auto-fetch** `crible ingest --fetch-gleif` (F6/FIX-002, [S12][S53]) — allume toute la couche EU auditée idle out-of-the-box. CC0. **n°1 des deux cycles.**
2. **FX Frankfurter/BCE** (F8/FIX-007, [S26][S71][S72]) — keyless, redistribuable, colonnes `*_eur`. Meilleur ratio gain/risque.
3. **SEC FSDS** `edgar-fsds` ([S23][S24]) — historique « as-filed » trimestriel profond, **domaine public**. Garde companyfacts (récent) + FSDS (profondeur), jamais l'un OU l'autre.
4. **Companies House UK** `companies-house` ([S21][S22]) — Accounts Data Product (ZIP iXBRL), comble le trou UK. **Assumed-risk** (licence non énoncée) → couche dataset isolée.
5. **EDINET JP** `edinet` ([S29]) — free-key **opt-in**, off par défaut (cœur keyless intact), PDL1.0 attribution requise. API-only. *Seule source non-locale — dernière, réversible.*

**Enablers** : refresh univers dans `run_loop` (F5/FIX-001) · compute incrémental via seam `build_snapshot(symbols=)` (F7/FIX-006).

## File 3 — Icebox

Prix (talon d'Achille — aucun OHLCV ouvert redistribuable neuf : Deutsche Börse AWS = rejet non-commercial ; bhavcopy Inde = ToS non établies ; reste Yahoo+dumps assumed-risk) · portfolio tracking · alertes e-mail · historique 15-20 ans.

## Launch checklist (état inchangé)

- [x] LICENSE MIT · README vendeur + comparatif · Guide NAS · Caveat réseau privé
- [ ] **Humain** : awesome-selfhosted (éligible ~2026-11-13) · post r/selfhosted · décision cloud managé optionnel
