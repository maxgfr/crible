# Design tokens

## color

| Token | Value | Notes |
|---|---|---|
| color.bg | oklch(0.13 0 0) | App background — neutral pure black, never tinted. Light « paper terminal »: oklch(1 0 0). |
| color.bg-raised | oklch(0.17 0 0) | Topbar, panels, drawers, sticky header. Light: oklch(0.955 0.004 75). |
| color.fg | oklch(0.93 0.012 75) | Primary text — warm chalk on slate. Light: oklch(0.25 0.015 60). |
| color.muted | oklch(0.65 0.015 75) | Secondary text, borders, disabled (≥4.5:1). Light: oklch(0.47 0.015 60). |
| color.primary | oklch(0.75 0.15 55) | Forge amber — the ONLY interactive signal: actions, links, focus, selection. Light: oklch(0.55 0.13 55). |
| color.on-primary | oklch(0.15 0.03 55) | Text on amber fill. Light: oklch(1 0 0). |
| color.accent | oklch(0.62 0.1 240) | Cooled steel — provenance, info links, neutral badges. Light: oklch(0.45 0.1 240). |
| color.gain | oklch(0.72 0.15 150) | Positive deltas, passing criteria — never colour alone (sign required). Light: oklch(0.52 0.14 150). |
| color.loss | oklch(0.64 0.2 22) | Negative deltas, failing criteria. Light: oklch(0.52 0.19 25). |
| color.danger | oklch(0.64 0.2 22) | Destructive, errors (= loss). Light: oklch(0.52 0.19 25). |
| color.warn | oklch(0.8 0.13 90) | Stale-data badges, Beneish red flags — yellow, distinct from amber. Light: oklch(0.55 0.12 90). |

## typography

| Token | Value | Notes |
|---|---|---|
| font.sans | system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif | Labels, prose. System stack only — nothing fetched or bundled (NFR-013). |
| font.mono | ui-monospace, 'SF Mono', SFMono-Regular, Menlo, 'Cascadia Mono', Consolas, 'Liberation Mono', monospace | The tool's voice: wordmark, numerals (tabular-nums), DSL query bar, provenance. |
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
| radius.sm | 2px | Inputs, badges — instrument, not toy. |
| radius.md | 4px | Buttons, pills. |
| radius.lg | 8px | Drawers, dialogs only. |

## elevation

| Token | Value | Notes |
|---|---|---|
| shadow.sm | 0 1px 2px rgba(0,0,0,0.4) | Dark; light: rgba(0,0,0,0.06). |
| shadow.md | 0 8px 24px rgba(0,0,0,0.5) | Drawer/dialog; light: rgba(0,0,0,0.12). |
| shadow.glow | 0 0 0 1px var(--color-primary), 0 0 12px color-mix(in oklch, var(--color-primary) 25%, transparent) | Phosphor signature — focus/active states only (query bar, active pill). |

## z

| Token | Value | Notes |
|---|---|---|
| z.sticky | 10 |  |
| z.dropdown | 15 |  |
| z.backdrop | 20 |  |
| z.drawer | 30 |  |
| z.toast | 40 |  |
| z.tooltip | 50 |  |

## motion

| Token | Value | Notes |
|---|---|---|
| motion.fast | 120ms ease-out | Hover, focus, sort, glow-in. |
| motion.base | 200ms ease-out | Drawer; 0ms under prefers-reduced-motion. |

> The machine-readable token set is in `design/design-tokens.json`.
