# PRD (summary) — FMP Ultimate: evaluated and REJECTED

_Status: documented alternative, not planned. FR-014. Last reviewed: 2026-07-07._

## What it is

Financial Modeling Prep's top tier. Planning research (2026-06): worldwide
coverage arrives **only at the Ultimate tier ($149/mo annual)** — lower tiers are
US-only (free: 250 req/day, 5-year history) or add just UK/Canada (Premium).
Prices **to revalidate** if this decision is ever reopened.

## Why rejected (vs EODHD Fundamentals)

- **~2.5× the price** for the same role in crible's architecture (replace the
  fragile keyless fundamentals link with a reliable worldwide feed).
- crible needs statements + ratios inputs, not FMP's extras (13F, transcripts,
  1-min intraday) that justify Ultimate's price.
- financetoolkit is FMP-native, but crible deliberately computes from its own
  raw layer through ftk's pure functions — provider lock-in buys nothing.

## If ever reconsidered

The free key (already held) validates schemas the same way the EODHD stub does:
`/api/v3/income-statement/{symbol}?apikey=…` etc. — the `fmp_free` plugin
(`src/crible/providers/fmp_free.py`) already exists for exactly that, and lands
facts as `provider='fmp_free'` raw statements behind the same Provider seam.
Activation would mirror docs/prds/eodhd.md step-for-step.
