# PRIORITIES — cycle improve 2026-07-12 (croisement marché × éval)

Sources : `docs/market/2026-07-12/REPORT.md` (ultrasearch startup, check ✓) × `evals/2026-07-12/` (ultraeval deep, score 74/100, gate groundé ✓). Règle : on améliore l'existant librement ; **aucune feature sans évidence marché citée**.

## File 1 — Améliorer l'existant (exécutable ce cycle, sans gate)

| Réf | Item | Sévérité | Effort |
|---|---|---|---|
| F4 | README go-to-market : pitch « garde tes €550/an », comparatif honnête, quickstart compose one-liner, screenshots | high | S |
| F5 | Guide d'install self-host NAS/Synology (répond à [S23]) | med | S |
| F6/F1 | Dériver `/api/providers` du registre (supprime la duplication → plus de dérive UI↔réalité) | med | S |
| F3 | Caveat sécurité « réseau privé / reverse-proxy » dans le README (OWASP A05) | P2 | S |
| F2 | Hotspot `ingest/service.py` (370 LOC, nesting 14) — extraction en collaborateurs | P2 | M — reporté (pas de régression fonctionnelle, coût > valeur immédiate) |

## File 2 — Features candidates AVEC évidence marché (spec d'abord, dev cycle 2+)

| Réf | Feature | Évidence marché | Décision |
|---|---|---|---|
| F7 | **Rang composite qualité/valeur/momentum** (façon StockRanks) sur les scores existants | [S21] différenciateur n°1 de Stockopedia (€550/an) ; [S22] cité comme raison d'abonnement | **PASSE le gate** → spec construct ce cycle, dev en attente de ton GO |

## File 3 — Icebox (aucune ligne de code)

- Portfolio tracking / watchlists — territoire Ghostfolio [S4] / OpenMarketView [S7], hors mission screener.
- Historique 15–20 ans de fondamentaux — argument TIKR [S26], incompatible zéro-clé aujourd'hui ; réévaluer si une source gratuite apparaît.
- Alertes/screens programmés par e-mail — aucune évidence marché fetchée ; à sourcer avant toute spec.

## Launch checklist (POC → marché)

- [x] LICENSE MIT (déjà présente)
- [ ] README vendeur + comparatif + screenshots (F4)
- [ ] Guide install NAS/Docker one-liner (F5)
- [ ] Caveat déploiement réseau privé (F3)
- [ ] Soumission awesome-selfhosted, catégorie Money [S24]
- [ ] GitHub topics + social preview + Discussions/Issues templates (canal feedback)
- [ ] Décision pricing : gratuit OSS ; cloud managé optionnel façon Ghostfolio [S14] = cycle 2+
