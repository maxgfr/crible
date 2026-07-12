# Design

Identité « terminal phosphore » : un instrument financier souverain. Fond noir pur (pas de teinte — la chaleur vit dans les couleurs de marque, pas dans la surface), encre craie chaude, un seul accent interactif : l'ambre forge. Le thème clair est le « paper terminal » : même instrument, imprimé sur papier.

## Theme

- Dark = thème primaire (`:root[data-theme="dark"]`, défaut) ; light = variante complète (`[data-theme="light"]`), persistée en localStorage, défaut initial via `prefers-color-scheme`.
- Stratégie couleur : **Restrained** — neutres purs + ambre ≤ 10 % de la surface. Les couleurs sémantiques n'apparaissent que sur les données.

## Color (OKLCH, source de vérité : srd/design/design-tokens.json)

| Rôle | Dark | Light | Usage |
|---|---|---|---|
| bg | `oklch(0.13 0 0)` | `oklch(1 0 0)` | Fond app — neutre pur, jamais teinté |
| bg-raised | `oklch(0.17 0 0)` | `oklch(0.955 0.004 75)` | Topbar, panneaux, drawer, header sticky |
| fg | `oklch(0.93 0.012 75)` | `oklch(0.25 0.015 60)` | Texte — craie chaude sur ardoise / encre sur papier |
| muted | `oklch(0.65 0.015 75)` | `oklch(0.47 0.015 60)` | Texte secondaire, bordures (≥ 4.5:1 au corps 13px) |
| primary | `oklch(0.75 0.15 55)` | `oklch(0.55 0.13 55)` | Ambre forge : liens, actions, focus, sélection — le SEUL signal « interactif » |
| on-primary | `oklch(0.15 0.03 55)` | `oklch(1 0 0)` | Texte sur aplat primary (ambre clair→encre sombre ; ambre foncé→blanc) |
| accent | `oklch(0.62 0.10 240)` | `oklch(0.45 0.10 240)` | Acier refroidi : provenance, liens info, badges neutres |
| gain | `oklch(0.72 0.15 150)` | `oklch(0.52 0.14 150)` | Deltas positifs, critères passés |
| loss / danger | `oklch(0.64 0.20 22)` | `oklch(0.52 0.19 25)` | Deltas négatifs, erreurs, destructif |
| warn | `oklch(0.80 0.13 90)` | `oklch(0.55 0.12 90)` | Données périmées, red flags Beneish (jaune, distinct de l'ambre) |

Règles : gain/perte toujours accompagnés du signe (jamais couleur seule). Ambre = interaction ; s'il apparaît sur une donnée, c'est un bug de design.

## Typography

- **La mono système est la voix de l'outil** : wordmark, chiffres (`tabular-nums`, alignés droite), query bar DSL, badges de provenance. `--font-mono: ui-monospace, "SF Mono", SFMono-Regular, Menlo, "Cascadia Mono", Consolas, monospace`.
- Sans système pour labels et prose : `--font-sans: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif`. **Aucune font fetchée** (NFR-013) — la contrainte EST l'identité.
- Échelle fixe dense : body 13px/1.45 · h1 20px/1.3 · small 11px/1.35. Pas de fluid type.

## Components

- **Wordmark** : « crible » en mono, poids 650, précédé d'un glyphe tamis (SVG inline : cercle + hachures diagonales interrompues — les lignes qui passent au travers). Ambre sur dark, encre sur light.
- **Boutons** : rectangles nets (radius 4px), bordure 1px ; primaire = aplat ambre + on-primary. Jamais bordure + ombre large combinées.
- **Query bar** : mono, focus = anneau ambre + `--shadow-glow` (halo phosphore discret) — signature de l'identité, uniquement sur focus/état actif.
- **Table** : header sticky sur bg-raised, lignes hover `color-mix(primary 8%)`, sélection bordure ambre 1px pleine (pas de side-stripe).
- **Drawer** : bg-raised, shadow-md, radius 8px côté exposé seulement.
- **Vides/chargement** : skeletons alignés sur la grille ; l'empty state du premier run enseigne (progression du crawl inline + lien Statut).
- **Toggle thème** : icône topbar (soleil/lune), cycle dark→light, persisté.

## Layout

- Shell une fenêtre : topbar (wordmark · switch de vue Screener/Statut/Fournisseurs · pill statut · toggle thème) au-dessus de la vue active. Pas de sidebar — la largeur appartient à la table.
- Densité assumée : tables > 120ch légitimes ; prose (descriptions provider) capée à 72ch.
- z-index sémantique : sticky 10 · drawer-backdrop 20 · drawer 30 · toast 40 · tooltip 50.

## Motion

- 120ms ease-out (hover, focus, tri) · 200ms ease-out (drawer). Rien d'orchestré au chargement.
- Le glow de focus apparaît en 120ms, disparaît instantanément. `prefers-reduced-motion` : tout à 0ms (déjà en tokens).

## Radius & elevation

- radius : sm 2px · md 4px · lg 8px — instrument, pas jouet.
- shadow-sm/md conservées ; `--shadow-glow: 0 0 0 1px <primary>, 0 0 12px color-mix(in oklch, <primary> 25%, transparent)` réservée aux états focus/actif.
