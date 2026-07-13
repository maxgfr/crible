# 0006. Dataset distribution: demo-data branch + rolling data-latest release + bootstrap

- **Status:** accepted (2026-07-13)

## Context
Self-hosters previously started from an empty `data/` and waited hours for the first crawl to land rows. Meanwhile the nightly `refresh-data` workflow already publishes the full open dataset (raw layer + universe + snapshot + site artifacts) as one orphan commit on the `demo-data` branch, with a never-publish-empty gate and a last-good guarantee. GitHub constraints shape the options: files >100 MiB are blocked from normal git, Git LFS objects are not served by Pages, release assets go up to 2 GB, and committing data to `main` would bloat its history nightly (the Flat Data pattern's cost).

## Decision
The `demo-data` orphan branch stays canonical (atomic publish, Pages source, last-good guarantee). The nightly workflow additionally uploads `crible-data.tar.gz` (raw + universe + snapshot) and the two site parquets as assets on a rolling `data-latest` GitHub Release (`--latest=false` so it never shadows versioned application releases; `--clobber` updates in place). A new `crible bootstrap` command initializes a local `data/` by trying the release asset first, then the codeload tarball of the `demo-data` branch; it refuses a non-empty dataset without `--force` and extracts defensively (only the `data/` layer, no links, no path escapes, staging-then-move).

## Consequences
A fresh install screens within seconds of `crible bootstrap` — zero crawl, zero keys — and the normal ingest loop extends the dataset from there. The dataset gains a stable download URL usable outside crible. Costs: one more nightly workflow step and the standing caveat that scheduled workflows auto-disable after 60 days of repository inactivity (any push resets the clock). The published dataset inherits the documented yfinance redistribution caveat for its small scraped sample; the audited EDGAR/ESEF and universe layers are cleanly redistributable.

## Alternatives considered
Committing `data/` to `main` on a cron (Flat Data / git-scraping) — rejected: permanent history bloat on the code repo for every nightly refresh. One versioned release per night — rejected: hundreds of tag/release entries add noise without value; the branch already provides history. Git LFS — rejected: not served by GitHub Pages and quota-bound. Bootstrap-from-Pages (fetch the site parquets only) — rejected as the primary path: it lacks the raw layer, which is what lets a self-host recompute and extend snapshots.
