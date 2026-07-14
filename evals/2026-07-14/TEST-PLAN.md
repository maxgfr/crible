# TEST-PLAN — crible cycle 2026-07-14 (data-pipeline / self-hosting lens)

Mode: improve. Bar: 80. Base: evals/2026-07-12-c2 (81). Focus: the ingest → enrich → compute →
publish pipeline and its self-hosting / bulk-first readiness (next work targets data sources).

## Method
1. Deterministic: run the target's own suites (`uv run pytest`, `vitest`) — record exit codes → runs/core.md.
2. Grounding probes: grep the wiring (refresh_universe, GLEIF download, watchdog/timeout, FX,
   docker entrypoint) — every claim resolves to a real file:line.
3. Read the pipeline modules end-to-end (providers/*, ingest/*, compute/reconcile+snapshot+ranks,
   universe, bootstrap, site_export) and confirm/refute each documented TODO gap AGAINST the code.
4. Brainstorm bulk-first opportunities anchored to code + the data-sources research doc.

## Dimensions (weights unchanged from base)
correctness .30 · tests .20 · security .20 · maintainability .20 · performance .10

## TODO gaps to adjudicate (confirm/refute in code, don't trust the doc)
- Crawler per-request watchdog anti-hang (ADR-0004) — F2.
- Periodic universe refresh in run_loop — opportunity (refresh_universe exists; loop path frozen).
- GLEIF ISIN→LEI auto-fetch — opportunity (URL constant dead; ESEF layer idle).
- Incremental compute — opportunity (build_snapshot symbols= seam unused).
- FX normalization (Frankfurter/ECB) — opportunity (absent).

## Pass criteria
Suites green; every finding grounded (check PASS) and adversarially verified (verify, 3 honeypots);
no new P0 vs base; score gated by `compare --base evals/2026-07-12-c2 --gate`.
