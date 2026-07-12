# PRIORITIES — cycle improve #2 (2026-07-12, après GO « continue en boucle sur tout »)

Sources : `evals/2026-07-12-c2/` (score **81/100, meets-expectations ✓, barre 80**) × `docs/market/2026-07-12/REPORT.md` (inchangé ce cycle). Gate inter-cycles : `compare --base evals/2026-07-12 --gate` **EXIT 0** (Δ +7, 6 résolus, 3 introduits tous P2 et soldés/differés ci-dessous).

## Livré ce cycle

- **FR-015 rang composite** (GO utilisateur) : moteur percentiles par peer group région×secteur (fallback global), `return_6m` momentum, sémantique NULL jamais imputée, preset « Top ranked », décomposition complète dans le drawer, colonnes par défaut + README « How the rank is built » (F9), garde-fou de coût de build < 5 s sur 161k (F10). 9 tests FR-015 pytest + 2 UI.
- **F8** (défaut trouvé par l'éval c2, corrigé in-cycle) : preset « Top ranked » sur snapshot pré-upgrade → hint « recompute (`crible compute`) » au lieu d'une erreur sans remède.

## File 1 — restant (différé, décision documentée)

| Réf | Item | Décision |
|---|---|---|
| F2 | Hotspot `ingest/service.py` (370 LOC, nesting 14) | Différé — extraction des collaborateurs à faire à la prochaine évolution du module (coût > valeur tant qu'aucune feature ne le touche). |

## File 2 — features candidates

Vide : FR-015 était la seule feature passée au gate marché ; aucune nouvelle évidence ce cycle.

## File 3 — icebox (inchangé)

Portfolio tracking · historique 15-20 ans · alertes e-mail (à sourcer avant toute spec).

## Launch checklist (état)

- [x] LICENSE MIT · [x] README vendeur + comparatif + rank doc · [x] Guide NAS · [x] Caveat réseau privé
- [ ] **Humain** : soumission awesome-selfhosted (catégorie Money) · GitHub topics/social preview/Discussions · décision cloud managé optionnel
