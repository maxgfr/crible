# crible — TODO

État : v1 zéro clé **construite, testée (87 pytest + 4 vitest), E2E réel validé**.
Ce fichier liste ce qui reste. Rien ici n'est bloquant pour utiliser le screener aujourd'hui.

---

## P1 — Complète des fonctionnalités déjà à moitié faites

- [ ] **Brancher les plugins à clé dans la boucle d'ingestion.**
  SimFin / FMP-free / EODHD-stub existent et sont testés unitairement (gating, self-disable,
  détection de tier), mais `run_loop` n'appelle que `yfinance` : même avec `SIMFIN_KEY` dans
  `.env`, aucun fetch n'est déclenché. Ajouter une passe multi-provider dans le service
  (`ProviderRegistry.activate` → itérer les providers actifs par symbole, écrire chaque
  `provider=<id>` dans le raw layer, la réconciliation existe déjà). ~1 fonction + tests.

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

- [ ] **Écran « Ingest & coverage status »** dans la SPA.
  Données déjà servies par `/api/status` (coverage %, histogramme fraîcheur, req/h vs budget,
  santé par provider, `esef_unmatched`). Manque le composant React (`StatusDashboard` est
  listé dans le design system mais pas implémenté).

- [ ] **Écran « Providers & settings »** dans la SPA.
  Inventaire read-only des providers (keyless / keyed-off / keyed-on) + pointeur `.env` +
  chemin d'upgrade EODHD. Toggle de thème.

- [ ] **Toggle dark/light.**
  Les tokens light existent (`tokens.css`), `data-theme` est figé sur `dark`. Ajouter un
  bouton qui bascule `data-theme` sur `<html>` (+ persistance localStorage).

## P3 — Robustesse / passage à l'échelle

- [ ] **Compute incrémental.**
  Chaque cycle reconstruit tout le snapshot. OK à ~500 sociétés, à revisiter vers 20k+ :
  ne recomputer que les symboles dont le raw a changé depuis le dernier snapshot.

- [ ] **Sortir le sweep Europe complet** (5-7 semaines au débit keyless — c'est le design,
  visible dans `crible status`). Rien à coder ; juste laisser tourner, ou brancher EODHD.

## P4 — Dette de test (documentée, assumée)

- [ ] **Test comportemental de `run_loop`** (aujourd'hui `# pragma: no cover`, séquencement
  couvert seulement par l'E2E live) : extraire la logique de séquencement, la tester offline.
- [ ] **Test de rendu du `CompanyDrawer`** (l'API est testée, le JSX ne l'est pas).
- [ ] **Beneish sur un cas réel publié** (type Enron 2000) en plus des vecteurs analytiques.

## P5 — Reporté volontairement (décision explicite requise)

- [ ] **Plugin FinancialReports.eu** (MCP OAuth) — spike à faire avant de s'engager
  (risque M3 du build plan : l'OAuth peut mal convenir à une ingestion headless).
- [ ] **E2E live en nightly CI** — manuel pour l'instant (dépense du vrai budget Yahoo).
      NFR-009 a été aligné là-dessus.
- [ ] **Publication GitHub** (privé → public) + semantic-release façon `feelc`/`andro`.
      *Ne pas faire sans demande explicite de Maxime.*
- [ ] **Achat EODHD Fundamentals €59,99/mois** — tout est prêt (PRD `docs/prds/eodhd.md`
      + stub validé sur le token demo) ; seul switch payant prévu.

## Hors scope v1 (nonGoals du SRD — ne pas faire sans re-spec)

Technique / chartisme · portefeuille · backtesting · exécution d'ordres · temps réel ·
multi-utilisateur / auth · apps mobiles.
