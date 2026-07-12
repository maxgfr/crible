# Remediation plan — .

Target: `/Users/maxime/Downloads/crible` · 7 fix task(s), most impactful first.
Each task has a matching TDD card under `fixes/` (RED failing test → GREEN change → VERIFY).

## P1 — Major: materially degrades a scored dimension (fidelity, coverage, robustness); a workaround or secondary path exists (2)

- **FIX-001** README go-to-market : pitch, comparatif honnête, listing awesome-selfhosted — Le README actuel est technique et neutre ; il ne vend pas le seul créneau vide du marché (screener fondamental self-hosted, zéro clé, alternative à un abonnement à €550/an). Le canal de distribution du cœur de cible (awesome-selfhosted, catégorie Money) n'a aucun screener.
  - fix: Réécrire le README : pitch « garde tes €550/an », screenshots dark/light, table comparative honnête (Stockopedia/TIKR/SWS/OpenBB/Ghostfolio), quickstart compose one-liner ; soumettre à awesome-selfhosted.
  - targets: README.md, docs/market/2026-07-12/REPORT.md
- **FIX-002** Rang composite qualité/valeur/momentum (façon StockRanks) — GATÉ marché — Le différenciateur n°1 du leader payant Stockopedia est le StockRank composite (qualité/valeur/momentum), cité par les reviews comme la raison d'abonnement. crible a déjà les scores en base (Piotroski, Altman, ratios) pour le calculer, sans clé.
  - fix: Spécifier via construct (FR + acceptance) un rang composite classant l'univers ; NE PAS développer avant la spec. Évidence marché forte → passe le gate, dev cycle 2.
  - targets: src/crible/compute/scores.py, docs/market/2026-07-12/REPORT.md

## P2 — Minor: polish, consistency, or documentation drift; no scored dimension materially degraded (5)

- **FIX-003** Guide d'install self-host NAS/Synology — Une question explicite « puis-je self-héberger cet outil de recherche actions sur mon Synology ? » reste sans réponse depuis 2023 chez le leader OSS OpenBB. crible peut y répondre par un guide d'install NAS/compose one-liner — friction d'adoption levée pour le cœur de cible.
  - fix: Ajouter une section install NAS/Docker (Synology, compose, volume, port) au README/docs.
  - targets: README.md, docs/market/2026-07-12/REPORT.md
- **FIX-004** Dériver /api/providers du registre (résout F1) — Transformer la duplication F1 en amélioration : l'endpoint consomme le registre au lieu de réénumérer et recalculer, supprimant le risque de dérive UI↔réalité.
  - fix: Refactor de l'endpoint pour itérer les providers enregistrés et appeler enabled(env).
  - targets: src/crible/api/main.py, src/crible/providers/base.py
- **FIX-005** L'inventaire /api/providers réimplémente la règle d'activation du registre — Un provider futur exige deux variables d'env ; activate() gère les deux, l'endpoint continue de tester une seule → l'UI affiche « enabled » alors que le provider est inactif.
  - fix: Dériver l'inventaire depuis le registre (itérer les providers enregistrés, appeler enabled(env)) plutôt que de réénumérer et recalculer côté API.
  - targets: src/crible/api/main.py, src/crible/providers/base.py
- **FIX-006** ingest/service.py concentre trop de responsabilités (hotspot 370 LOC, nesting 14) — Ajouter un provider de prix impose de modifier une fonction profondément imbriquée ; un cas d'erreur non couvert passe entre les branches.
  - fix: Extraire les étapes (bootstrap / crawl / prix / reconcile) en collaborateurs testables ; le SRD décrit déjà ces frontières.
  - targets: src/crible/ingest/service.py
- **FIX-007** compose expose l'API sans auth ni avertissement « réseau privé » — Un utilisateur mappe le port sur 0.0.0.0 d'un VPS sans reverse-proxy → API et données lisibles par quiconque scanne le port.
  - fix: Documenter « réseau privé / reverse-proxy uniquement » dans le README d'install (répond aussi à la demande self-host [S23]) ; envisager un bind loopback par défaut ou une auth optionnelle.
  - targets: docker-compose.yml
