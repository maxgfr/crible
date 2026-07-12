# Research — performance (ISO/IEC 25010:2023 · time behaviour, resource utilization, capacity)

ISO 25010 « performance efficiency » = comportement temporel, utilisation des ressources, capacité (https://blog.pacificcert.com/iso-25010-software-product-quality-model/ ; https://www.perforce.com/blog/qac/what-is-iso-25010). Pour un moteur analytique local, les métriques utiles sont p95 de latence de requête à univers complet, empreinte mémoire du snapshot, et le coût du chemin chaud UI (re-render de la grille).

Application à crible : contrat NFR-008 existant — screen full-univers (161k×200) p95 < 1 s, benchmark déjà en CI ; run réel mesuré à 49 ms sur 10 sociétés et 8,09 ms affiché en topbar sur le seed. À sonder : chemin chaud UI (TanStack re-renders sur tri/résultats larges), démarrage API (chargement snapshot), mémoire du crawl long.

## Rubrique 0–5
- 0 : requête nominale > 5 s ; 1 : p95 > 1 s (NFR-008 violé) ; 2 : NFR-008 tenu mais non re-mesuré après changements UI ; 3 : NFR-008 en CI + UI fluide sur 1k lignes ; 4 : + profil mémoire crawl documenté ; 5 : + budgets perf par couche et alerte de régression.
Mesure : lancer le benchmark NFR-008, charger 1k lignes dans la grille, chronométrer le cold-start API.
