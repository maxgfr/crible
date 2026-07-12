# Research — correctness (ISO/IEC 25010:2023 · functional correctness + reliability/faultlessness)

ISO/IEC 25010 définit la « functional correctness » comme la capacité du produit à fournir des résultats corrects avec le degré de précision requis, sous-caractéristique de la functional suitability (https://www.sonarsource.com/resources/library/iso-iec-25010-explained/ ; https://blog.pacificcert.com/iso-25010-software-product-quality-model/). L'évaluation combine analyse statique, tests, revue de code et vérification (https://blog.codacy.com/iso-25010-software-quality-model).

Application à crible (screener fondamental) : la correction porte sur (1) l'exactitude des scores financiers (Piotroski/Altman/Beneish) vs leurs définitions publiées, (2) la fidélité DSL→SQL (le filtre exécuté est celui écrit), (3) la cohérence des agrégats full-univers (pas de lignes perdues/dupliquées), (4) les chemins d'erreur (symbole manquant, exercice incomplet, devise). Les vecteurs analytiques publiés (Beneish 1999) servent d'oracle — le repo les utilise déjà en tests.

## Rubrique 0–5
- 0 : scores faux sur cas nominal ; 1 : happy path OK mais erreurs silencieuses sur données manquantes ; 2 : nominal exact, edge non testés (devise, exercices partiels) ; 3 : nominal + edge principaux corrects et testés FR-taggés ; 4 : + oracles externes (vecteurs publiés) et invariants (row-count, provenance) vérifiés ; 5 : + tests de propriété sur DSL/compute et zéro divergence connue.
Mesure : exécuter la suite pytest FR-taggée, tracer 3 valeurs de bout en bout (parquet→ratio→UI), tenter 5 requêtes DSL adversariales.
