# Design tokens

crible's brand: dense, data-first, terminal-inspired; dark mode is the primary theme (light values noted per token). Numerals are always monospaced/tabular.

## color

| Token | Value | Notes |
|---|---|---|
| color.bg | #0D1117 | App background (dark-first). Light theme: #FFFFFF. |
| color.bg-raised | #161B22 | Panels, drawers, sticky header. Light: #F6F8FA. |
| color.fg | #E6EDF3 | Primary text. Light: #1F2328. |
| color.muted | #8B949E | Secondary text, borders, disabled. Light: #59636E. |
| color.primary | #4DA3FF | Actions, links, focused query bar. Light: #0969DA. AA on both bgs. |
| color.gain | #3FB950 | Positive deltas, passing criteria. Light: #1A7F37. |
| color.loss | #F85149 | Negative deltas, failing criteria. Light: #CF222E. |
| color.danger | #F85149 | Destructive actions, errors. Light: #CF222E. |
| color.warn | #D29922 | Stale-data badges, Beneish red flags. Light: #9A6700. |

## typography

| Token | Value | Notes |
|---|---|---|
| font.sans | 'Inter', system-ui, -apple-system, 'Segoe UI', sans-serif | UI chrome, labels. Bundled with the SPA (@font-face, no CDN — NFR-013 egress test). |
| font.mono | 'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, monospace | All numerals (tabular-nums), DSL query bar, code. Bundled with the SPA (no CDN). |
| scale.body | 13px / 1.45 | Dense default; grid cells. |
| scale.h1 | 20px / 1.3 | Screen titles — chrome stays small. |
| scale.small | 11px / 1.35 | Badges, provenance, freshness. |

## spacing

| Token | Value | Notes |
|---|---|---|
| space.1 | 4px |  |
| space.2 | 8px |  |
| space.3 | 12px |  |
| space.4 | 16px |  |
| space.6 | 24px |  |
| space.8 | 32px |  |

## radius

| Token | Value | Notes |
|---|---|---|
| radius.sm | 3px |  |
| radius.md | 6px |  |
| radius.lg | 10px | Drawers, dialogs only. |

## elevation

| Token | Value | Notes |
|---|---|---|
| shadow.sm | 0 1px 2px rgba(0,0,0,0.4) | Dark-theme value; light: rgba(0,0,0,0.06). |
| shadow.md | 0 8px 24px rgba(0,0,0,0.5) | Drawer/dialog; light: rgba(0,0,0,0.12). |

## motion

| Token | Value | Notes |
|---|---|---|
| motion.fast | 120ms ease-out | Hover, focus, sort-arrow. |
| motion.base | 200ms ease-out | Drawer slide; disabled under prefers-reduced-motion. |
