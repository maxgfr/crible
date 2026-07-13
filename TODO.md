# crible — TODO

État : v1 zéro clé **construite, testée (140 pytest + 55 vitest), E2E réel validé** ;
open-data hardening 2026-07-13 : provider EDGAR (US audité), fix réconciliation,
`crible bootstrap` + release `data-latest`, query builder complet, catalogue 100 % keyless.
Ce fichier liste ce qui reste. Rien ici n'est bloquant pour utiliser le screener aujourd'hui.

---

## P1 — Complète des fonctionnalités déjà à moitié faites

- [ ] **Automatiser le fichier GLEIF ISIN→LEI** (enrichissement ESEF).
  Le cycle ESEF est câblé mais reste idle tant que `data/isin-lei.csv` n'existe pas
  (~200 Mo, non auto-téléchargé au boot par choix). Ajouter `crible ingest --fetch-gleif`
  (télécharge le fichier de relations GLEIF le plus récent → `data/isin-lei.csv`).

- [ ] **Watchdog anti-hang par requête dans le crawler.**
  L'ADR-0004 promet un watchdog ; aujourd'hui on s'appuie sur les timeouts internes de
  yfinance. Des pulls peuvent pendre (issues documentées). Envelopper `fetch_statements`
  dans un timeout dur (thread + `.join(timeout)` ou signal), traiter comme un échec →
  reschedule.

- [ ] **Refresh périodique de l'univers.**
  FinanceDatabase n'est téléchargé qu'au premier boot ; `delisted` et les nouvelles
  cotations ne bougent jamais. Ajouter un `refresh_universe` hebdo dans `run_loop`
  (re-télécharge, upsert — le upsert idempotent existe déjà, cf. FR-001).

## P2 — Écrans du design system non construits (spéc dans srd/design/SCREENS.md)

- [x] **Écran « Ingest & coverage status »** dans la SPA. _(fait — `StatusView`, hash `#/status` ;
  coverage %, histogramme fraîcheur SVG, jauge req/h, santé providers, ESEF matched/unmatched.)_

- [x] **Écran « Providers & settings »** dans la SPA. _(fait — `ProvidersView`, `#/providers`,
  endpoint `/api/providers` ; inventaire keyless/free-key/paid, pointeur `.env`, upgrade EODHD,
  préférence de thème.)_

- [x] **Toggle dark/light.** _(fait — toggle topbar, persistance `crible-theme`, défaut
  `prefers-color-scheme`, script anti-FOUC dans `index.html` ; light = « paper terminal ».)_

## P3 — Robustesse / passage à l'échelle

- [ ] **Compute incrémental.**
  Chaque cycle reconstruit tout le snapshot. OK à ~500 sociétés, à revisiter vers 20k+ :
  ne recomputer que les symboles dont le raw a changé depuis le dernier snapshot.

- [x] **EDGAR bulk (`companyfacts.zip`, ~1,4 Go nightly)** — _fait (2026-07-13) :
  `run_edgar_bulk` + `demo-refresh --edgar-bulk`, activé dans le nightly ; tout le marché
  US audité (~10k émetteurs, 8 exercices max) en un téléchargement._

- [ ] **Normalisation FX (Frankfurter/ECB, keyless).**
  Les ratios sont currency-neutral donc la valeur immédiate est modeste, mais les
  comparaisons cross-devises de valeurs absolues (market cap, revenue) mériteraient des
  colonnes normalisées (`market_cap_eur`…) : stockage des taux (api.frankfurter.dev ou
  CSV BCE, citer la source), colonnes companion au snapshot, exposition whitelist/UI.

- [ ] **Query builder : round-trip texte → builder** (aujourd'hui volontairement one-way,
  le texte DSL reste le langage unique) et **knob de slimming de l'univers** dans
  `export_site` (filtre régional) si le payload de la démo grossit un jour.

- [ ] **Sortir le sweep Europe complet** (5-7 semaines au débit keyless — c'est le design,
  visible dans `crible status`). Rien à coder ; juste laisser tourner.

## P4 — Dette de test (documentée, assumée)

- [ ] **Test comportemental de `run_loop`** (aujourd'hui `# pragma: no cover`, séquencement
  couvert seulement par l'E2E live) : extraire la logique de séquencement, la tester offline.
- [ ] **Test de rendu du `CompanyDrawer`** (l'API est testée, le JSX ne l'est pas).
- [ ] **Beneish sur un cas réel publié** (type Enron 2000) en plus des vecteurs analytiques.

## P5 — Reporté volontairement (décision explicite requise)

- [ ] **E2E live en nightly CI** — manuel pour l'instant (dépense du vrai budget Yahoo).
      NFR-009 a été aligné là-dessus.
- [ ] **Publication GitHub** (privé → public) + semantic-release façon `feelc`/`andro`.
      *Ne pas faire sans demande explicite de Maxime.*

_Décision 2026-07-13 (open data) : les plugins à clé SimFin/FMP/EODHD et la piste
FinancialReports.eu sont **supprimés** — le catalogue livré est 100 % keyless ;
le seam plugin (`providers/base.py`) reste pour d'éventuels plugins tiers._

## Hors scope v1 (nonGoals du SRD — ne pas faire sans re-spec)

Technique / chartisme · portefeuille · backtesting · exécution d'ordres · temps réel ·
multi-utilisateur / auth · apps mobiles.
