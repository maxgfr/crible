# Product

## Register

product

## Platform

web

## Users

Un investisseur particulier exigeant (ou un petit family office) qui self-héberge ses outils : à l'aise avec Docker et un DSL de filtrage, allergique aux abonnements de données et aux boîtes noires. Il travaille le soir ou le week-end, sessions longues, souvent en pièce sombre, sur grand écran. Le poste de travail secondaire est l'opérateur du crawl : la même personne, casquette admin, qui surveille couverture et fraîcheur des données.

## Product Purpose

crible filtre un univers mondial de ~161 000 actions (profondeur Europe d'abord) sur des critères fondamentaux — ratios, Piotroski, Altman, Beneish — sans aucune clé API, pour toujours. Le succès : un screen full-univers rend en moins d'une seconde, chaque chiffre est traçable jusqu'à sa source (provenance, dépôt ESEF audité), et la stack tourne chez l'utilisateur en `docker compose up`.

## Positioning

Le seul screener fondamental self-hosted, zéro clé, Europe-first — chaque nombre explicable jusqu'au dépôt audité.

## Brand Personality

Précis, souverain, incandescent. L'ambiance d'une salle des marchés après la clôture : écrans denses dans une pièce sombre, chiffres qui brûlent calmement en ambre sur acier noir. La chaleur vient des données qui travaillent, jamais de la décoration.

## Anti-references

- Le clone GitHub-dark : la palette actuelle est empruntée à Primer ; l'outil doit avoir sa propre lumière.
- Le kitsch « Bloomberg cosplay » : scanlines décoratives, faux CRT, vert Matrix, curseurs clignotants.
- Le dashboard SaaS générique : hero-metrics, cartes identiques, dégradés, coins sur-arrondis.
- Robinhood et consorts : le confetti, la gamification — crible est un instrument, pas un jeu.

## Design Principles

- La table est le héros : chaque pixel de chrome doit se justifier contre une ligne visible de plus.
- Une seule couleur veut dire « interactif » (l'ambre forge) ; les couleurs sémantiques (gain/perte/alerte) encodent le sens, jamais l'humeur.
- Les chiffres d'abord : mono à chasse tabulaire, alignés à droite ; la voix typographique de l'outil est la mono système.
- Transparence dans l'UI même : chaque score se déplie vers ses composantes, chaque valeur vers sa provenance.
- Souverain jusqu'au réseau : aucune ressource externe (fonts système uniquement, NFR-013) ; le thème clair « paper terminal » est un citoyen de plein droit.

## Accessibility & Inclusion

WCAG 2.2 AA : contraste ≥ 4.5:1 y compris texte secondaire à 13px, densité ≠ inaccessible (navigation clavier complète, focus visible ambre), `prefers-reduced-motion` neutralise les transitions, gain/perte jamais encodés par la couleur seule (signe et icône de tendance accompagnent).
