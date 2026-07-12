# REPORT — self-hosted / zero-key fundamental stock screeners (mode startup)

## Executive summary

crible occupe un créneau qu'aucun acteur identifié ne sert : le screening fondamental full-univers, self-hosted, sans clé API ni abonnement. Le marché se partage entre SaaS fondamentaux payants — Stockopedia à €550/an (Europe) ou €725/an (US+Europe) [S21], TIKR (données S&P CapitalIQ, 100 000+ actions, ~20 ans d'historique) [S26], Simply Wall St (freemium, 6 M d'utilisateurs revendiqués) [S25][S11], Portfolio123 (backtesting/gestion de stratégies) [S12] — et un écosystème open-source qui fait du *tracking* (Ghostfolio [S4][S8]) ou du *terminal* (OpenBB, 70.5k★/7.1k forks [S23][S9]), pas du screening fondamental packagé. La demande self-host est réelle et non répondue [S23] ; le canal de distribution naturel (awesome-selfhosted) n'a aucun screener dans sa catégorie Money [S24].

## Problem & customer

- Client : l'investisseur particulier « self-hoster » — il fait tourner Actual/Firefly III sur son NAS [S24], veut posséder ses données et refuse les abonnements.
- Douleurs documentées : les APIs financières « gratuites » plafonnent vite (quotas, clés, churn des free tiers) [S2] ; les screeners sérieux coûtent €550/an et plus [S21][S22] ; la question « puis-je self-héberger un outil de recherche actions sur mon Synology ? » reste sans réponse chez le leader OSS [S23].
- Job-to-be-done : filtrer un univers mondial sur des critères fondamentaux transparents (Piotroski, Altman, Beneish, 350+ ratios chez le leader payant [S21]) sans dépendre d'un fournisseur.

## Market sizing (TAM / SAM / SOM)

Aucune source fetchée ne publie un TAM du screening self-hosted ; ordres de grandeur par proxys cités : Simply Wall St revendique 6 M d'investisseurs individuels [S25] ; OpenBB agrège 70.5k stars / 7.1k forks [S23] ; Actual (budgeting self-hosted) 27474★ [S24]. Le SOM réaliste de crible est la fraction « self-host + fondamental » de ces bases — de l'ordre de quelques dizaines de milliers d'installations potentielles [M]. À affiner en cycle 2 (tier deep) si une décision de pricing en dépend.

## Competitive landscape

### Competitor table (name · positioning · pricing)

| Acteur | Positionnement | Pricing | Self-host | Screening fondamental |
|---|---|---|---|---|
| Stockopedia | Recherche fondamentale + StockRanks, UK/EU-first [S19][S21] | €550/an EU, €725/an US+EU [S21] ; $200–600/an selon régions [S22] | Non | Oui — 350+ ratios, StockRanks [S21] |
| TIKR | « Bloomberg du particulier », données CapitalIQ [S26] | Plus/Pro par abonnement mensuel [S26] | Non | Oui (global, 20 ans d'historique) [S26] |
| Simply Wall St | Analyse visuelle guidée, freemium [S3][S25] | Free (5 rapports/mois) / Premium / Unlimited ; screeners limités à 3 puis 10 [S25] | Non | Partiel (guidé, pas raw-data) [S3] |
| Portfolio123 | Stratégies + backtesting pour investisseurs avancés [S12][S20] | Abonnement (non publié dans nos sources) [S12] | Non | Oui (orienté stratégie) |
| OpenBB | Plateforme/terminal de recherche open source [S9][S17] | OSS + offres workspace [S13][S17] | Desktop/plateforme — demande serveur/NAS sans réponse [S23] | Terminal, pas un screener packagé [S9] |
| Ghostfolio | Wealth management OSS self-hosted [S4][S8][S16] | OSS (+ cloud optionnel) [S14] | Oui (Docker) [S4] | Non — tracking, pas screening [S5] |
| OpenMarketView | Viewer watchlists self-hosted [S7] | OSS | Oui | Non (listes/quotes, pas fondamental) [S7] |
| **crible** | Screener fondamental full-univers, zéro clé, Europe-depth | OSS gratuit | **Oui — c'est le produit** | **Oui — DSL + Piotroski/Altman/Beneish** [M] |

## Pricing & business models observed

- SaaS fondamental : €550–725/an (Stockopedia [S21]), abonnements TIKR Plus/Pro [S26], freemium à paliers avec limites de screeners (SWS : 3 → 10 screeners [S25]).
- OSS : gratuit self-host + cloud managé optionnel (Ghostfolio [S14]) — le modèle éprouvé du secteur, applicable à crible plus tard ; hors scope tant que le POC n'a pas d'utilisateurs.
- Implication positionnement : le README peut chiffrer l'alternative — « l'équivalent self-hosted d'un abonnement à €550/an [S21], gratuit, chez toi ».

## Go-to-market channels

1. **awesome-selfhosted** — catégorie Money sans aucun screener : listing = visibilité immédiate auprès du cœur de cible [S24].
2. **GitHub** (topics, README soigné, releases) — le canal qui a fait OpenBB (70.5k★) [S23] et Ghostfolio [S4].
3. r/selfhosted / Hacker News (Show HN) — récits de lancement OSS finance déjà rodés (threads HN non fetchés, à sourcer avant de s'en prévaloir) [M].
4. Comparateurs d'alternatives (findmymoat, slashdot/sourceforge) qui indexent déjà la catégorie [S1][S3][S5].

## Trends & timing

- La fatigue des clés API gratuites est documentée (quotas, churn) [S2] — l'argument « zéro clé » est différenciant maintenant.
- Le self-host finance est mainstream côté budgeting (Actual 27474★, Firefly III) [S24] ; le screening est la case vide adjacente.
- Les données réglementaires européennes gratuites (ESEF/xBRL) sont l'avantage structurel Europe-first de crible — aucun concurrent listé ne s'en prévaut (constat interne au produit, pas sourcé marché) [M].

## Risks & moats

- **Risque données** : dépendance au crawl Yahoo budgeté — le même vent contraire que les APIs gratuites documentées [S2]. Mitigé par ESEF + provenance.
- **Risque géant** : OpenBB pourrait packager un screener serveur — la demande existe chez eux [S23] et reste vide depuis 2023 : fenêtre ouverte mais pas éternelle.
- **Moat** : intégration verticale zéro-clé (univers complet + ESEF audité + scores transparents) et la transparence provenance — les SaaS vendent l'inverse (boîte noire premium [S21][S26]).

## Candidate features (gate marché — évidence requise)

| Feature candidate | Évidence | Verdict |
|---|---|---|
| Rang composite qualité/valeur/momentum (à la StockRanks) sur les scores existants | Différenciateur n°1 du leader payant [S21], mis en avant par les reviews [S22] | **PASSE le gate** — spec en Temps 4, dev cycle 2 |
| Guide d'install NAS/Synology + one-liner compose | Demande explicite non servie [S23] | Existant (install story) — file 1, pas une feature |
| Portfolio tracking / watchlists | Territoire couvert par Ghostfolio [S4] et OpenMarketView [S7] | **Icebox** — hors mission screener |
| Historique 15–20 ans de fondamentaux | Argument TIKR [S26] | **Icebox** — incompatible zéro-clé à ce jour, réévaluer si source gratuite apparaît |
| Alertes/screens programmés par e-mail | Aucune évidence dans les sources fetchées [M] | **Icebox** — à sourcer avant toute spec |

## Launch checklist (POC → marché)

- README vendeur : pitch « garde tes €550/an [S21] », screenshots dark/light, comparatif honnête vs Stockopedia/TIKR/SWS/OpenBB/Ghostfolio (table ci-dessus), quickstart compose one-liner.
- Guide self-host NAS (Synology/Docker) répondant exactement à [S23].
- Soumission awesome-selfhosted (catégorie Money) [S24] + GitHub topics/social preview.
- LICENSE (MIT — déjà), CHANGELOG/releases propres, canal feedback (GitHub Discussions/Issues templates). [M]
- Positionnement pricing : gratuit OSS ; cloud managé optionnel façon Ghostfolio [S14] = décision cycle 2+.

## Open questions / contradictions

- Taille réelle du segment « self-host + investissement actif » : aucun chiffre direct fetché — proxys seulement [S25][S23][S24]. À creuser en tier deep si le pricing en dépend.
- Threads HN sur OpenBB non fetchés (fetch bloqué) — les récits de lancement HN restent à sourcer avant d'en faire un canal chiffré. [M]
- Pricing Portfolio123 non publié dans nos extraits [S12][S20].

## Sources

Voir `sources.json` / `DOSSIER.md` — S1–S26 (S21–S26 ingérées manuellement : pricing Stockopedia/SWS, review TIKR, discussion self-host OpenBB, awesome-selfhosted). [M]
