# Design tokens

Identité « terminal phosphore » (voir `/DESIGN.md`) : noir pur, encre craie chaude, un seul accent interactif — l'ambre forge ; acier refroidi pour la provenance. Dark est le thème primaire ; light est le « paper terminal », variante complète. Numéraux toujours mono/tabulaires. Valeurs en OKLCH.

## color

| Token | Dark | Light | Notes |
|---|---|---|---|
| color.bg | oklch(0.13 0 0) | oklch(1 0 0) | Fond app — neutre pur, jamais teinté. |
| color.bg-raised | oklch(0.17 0 0) | oklch(0.955 0.004 75) | Topbar, panneaux, drawers, header sticky. |
| color.fg | oklch(0.93 0.012 75) | oklch(0.25 0.015 60) | Texte primaire (≥ 7:1 sur bg). |
| color.muted | oklch(0.65 0.015 75) | oklch(0.47 0.015 60) | Texte secondaire, bordures, disabled (≥ 4.5:1). |
| color.primary | oklch(0.75 0.15 55) | oklch(0.55 0.13 55) | Ambre forge — le SEUL signal interactif : actions, liens, focus, sélection. |
| color.on-primary | oklch(0.15 0.03 55) | oklch(1 0 0) | Texte sur aplat primary. |
| color.accent | oklch(0.62 0.1 240) | oklch(0.45 0.1 240) | Acier refroidi — provenance, liens info, badges neutres. |
| color.gain | oklch(0.72 0.15 150) | oklch(0.52 0.14 150) | Deltas positifs, critères passés. Jamais couleur seule (signe requis). |
| color.loss | oklch(0.64 0.2 22) | oklch(0.52 0.19 25) | Deltas négatifs, critères échoués. |
| color.danger | oklch(0.64 0.2 22) | oklch(0.52 0.19 25) | Destructif, erreurs (= loss). |
| color.warn | oklch(0.8 0.13 90) | oklch(0.55 0.12 90) | Badges stale, red flags Beneish — jaune, distinct de l'ambre. |

## typography

| Token | Value | Notes |
|---|---|---|
| font.sans | system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif | Labels, prose. Stack système pur — rien n'est fetché ni bundlé (NFR-013). |
| font.mono | ui-monospace, 'SF Mono', SFMono-Regular, Menlo, 'Cascadia Mono', Consolas, 'Liberation Mono', monospace | La voix de l'outil : wordmark, numéraux (tabular-nums), query bar DSL, provenance. |
| scale.body | 13px / 1.45 | Dense par défaut ; cellules de grille. |
| scale.h1 | 20px / 1.3 | Titres d'écran — le chrome reste petit. |
| scale.small | 11px / 1.35 | Badges, provenance, fraîcheur. |

## spacing

| Token | Value |
|---|---|
| space.1 | 4px |
| space.2 | 8px |
| space.3 | 12px |
| space.4 | 16px |
| space.6 | 24px |
| space.8 | 32px |

## radius

| Token | Value | Notes |
|---|---|---|
| radius.sm | 2px | Inputs, badges. |
| radius.md | 4px | Boutons, pills. |
| radius.lg | 8px | Drawers, dialogs uniquement. |

## elevation

| Token | Value | Notes |
|---|---|---|
| shadow.sm | 0 1px 2px rgba(0,0,0,0.4) | Dark ; light : rgba(0,0,0,0.06). |
| shadow.md | 0 8px 24px rgba(0,0,0,0.5) | Drawer/dialog ; light : rgba(0,0,0,0.12). |
| shadow.glow | anneau primary 1px + halo 12px à 25 % | Signature phosphore — états focus/actif uniquement (query bar, pill active). |

## z-index (échelle sémantique)

| Token | Value |
|---|---|
| z.sticky | 10 |
| z.backdrop | 20 |
| z.drawer | 30 |
| z.toast | 40 |
| z.tooltip | 50 |

## motion

| Token | Value | Notes |
|---|---|---|
| motion.fast | 120ms ease-out | Hover, focus, tri, glow-in. |
| motion.base | 200ms ease-out | Drawer ; 0ms sous prefers-reduced-motion. |
