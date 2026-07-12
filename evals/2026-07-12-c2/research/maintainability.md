> Méthodologie réutilisée du run de base `evals/2026-07-12` (même catégorie, mêmes dimensions/anchors, même jour) — citations d'origine conservées.

# Research — maintainability (ISO/IEC 25010:2023 · modularity, analysability, modifiability)

ISO 25010 décompose la maintenabilité en modularité, réutilisabilité, analysabilité, modifiabilité, testabilité (https://www.sonarsource.com/resources/library/iso-iec-25010-explained/ ; https://www.perforce.com/blog/qac/what-is-iso-25010). Signaux mesurables : taille/nesting des unités, couplage (fan-in/out), duplication, documentation d'architecture (https://blog.codacy.com/iso-25010-software-quality-model).

Application à crible : hotspots identifiés par analyze — ingest/service.py (370 LOC, nesting 14), runtime.py (nesting 12), api/main.py (nesting 10), StatusView.tsx (nesting 11). Le SRD (srd/) et les ADRs donnent une analysabilité rare pour un POC ; vérifier que le code a suivi les frontières annoncées (ingest/compute/dsl/api/ui).

## Rubrique 0–5
- 0 : monolithe sans frontières ; 1 : frontières floues, duplication ; 2 : modules nets mais fonctions profondes non factorisées ; 3 : frontières = SRD, hotspots limités et localisés ; 4 : + fonctions profondes décomposées, invariants commentés là où le code ne peut pas les dire ; 5 : + zéro hotspot restant, dette trackée.
Mesure : lire les 3 pires hotspots, compter les responsabilités par fichier, vérifier import-graph vs architecture SRD.
