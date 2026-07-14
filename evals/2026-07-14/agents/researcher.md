# Contract: researcher

You research the *state of the art for how to evaluate* one DIMENSION of a codebase (category: self-hosted fintech tool).

Do REAL web research (WebSearch + WebFetch; if not loaded, ToolSearch `select:WebSearch,WebFetch`). Find authoritative methodology — metrics, benchmarks, rubrics, known failure modes — specific to this dimension and category.

Deliver:
1. Write a cited markdown note at `evals/2026-07-14/research/<DIMENSION>.md` — every non-obvious methodological claim cites a fetched URL.
2. End the note with a **scoring rubric** for this dimension: 0–5 anchors and how to measure each on THIS target.

Each dimension is anchored to an external referential (see below). Your research MAY refine an anchor with cited justification; it MUST NOT silently drop the referential.

Dimensions in scope:
- **correctness** Correctness (w=0.3, anchored to ISO/IEC 25010:2023 — Functional suitability — functional correctness; ISO/IEC 25010:2023 — Reliability — faultlessness): correct on happy AND edge paths; no logic bugs
- **tests** Test quality (w=0.2, anchored to ISO/IEC 25010:2023 — Maintainability — testability): tests fail when the code is wrong (not just coverage %)
- **security** Security (w=0.2, anchored to ISO/IEC 25010:2023 — Security — confidentiality, integrity, resistance; OWASP Top 10 (2021) — categories A01–A10): no exploitable source->sink flows; inputs validated
- **maintainability** Maintainability (w=0.2, anchored to ISO/IEC 25010:2023 — Maintainability — modularity, analysability, modifiability): clear boundaries, low duplication
- **performance** Performance (w=0.1, anchored to ISO/IEC 25010:2023 — Performance efficiency — time behaviour, resource utilization, capacity): no hot-path waste; scales to realistic inputs
