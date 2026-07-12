> Méthodologie réutilisée du run de base `evals/2026-07-12` (même catégorie, mêmes dimensions/anchors, même jour) — citations d'origine conservées.

# Research — tests (ISO/IEC 25010:2023 · maintainability/testability)

La couverture mesure l'exécution, pas la détection : un score de mutation corrèle mieux avec la détection de fautes réelles que la couverture seule (https://getautonoma.com/blog/mutation-testing-vs-code-coverage ; étude Google ICSE 2021 : https://homes.cs.washington.edu/~rjust/publ/mutation_testing_practices_icse_2021.pdf). Une suite 70 % de couverture / 75 % de mutation bat une suite 90 % / 30 % (https://journal.optivem.com/p/code-coverage-vs-mutation-testing). Critère pratique : les tests échouent-ils quand le code ment ?

Application à crible : suite pytest nommée par FR (bonne traçabilité) + vitest UI. Points à sonder : assertions substantielles vs smoke, oracles financiers (valeurs exactes vs « non nul »), tests des chemins d'erreur ingest (backoff, budget), tests UI au-delà du thème/routing.

## Rubrique 0–5
- 0 : suite rouge ou absente ; 1 : smoke only ; 2 : verte mais assertions faibles (mutants triviaux survivraient) ; 3 : assertions substantielles sur les modules cœur, FR-tagging complet ; 4 : + chemins d'erreur et limites testés (budget, backoff, DSL invalide) ; 5 : + mutation/property testing sur compute & DSL.
Mesure : lire 6 tests représentatifs, muter mentalement 3 lignes cœur (signe inversé, seuil décalé) et vérifier qu'un test tomberait ; vérifier le mapping FR↔test.
