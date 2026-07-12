# FIX-003 — Guide d'install self-host NAS/Synology  (P2 · OPPORTUNITY · impact med · effort S)

**Opportunity F5:** Une question explicite « puis-je self-héberger cet outil de recherche actions sur mon Synology ? » reste sans réponse depuis 2023 chez le leader OSS OpenBB. crible peut y répondre par un guide d'install NAS/compose one-liner — friction d'adoption levée pour le cœur de cible.
**Evidence:** `README.md:20`, `docs/market/2026-07-12/REPORT.md:1`
**Why it matters:** Une question explicite « puis-je self-héberger cet outil de recherche actions sur mon Synology ? » reste sans réponse depuis 2023 chez le leader OSS OpenBB. crible peut y répondre par un guide d'install NAS/compose one-liner — friction d'adoption levée pour le cœur de cible.

## RED — write this test first
Write a spec/characterization test that pins the desired behavior: Ajouter une section install NAS/Docker (Synology, compose, volume, port) au README/docs.

Suggested test file: `tests/guide-d-install-self-host-nas-synology.test.ts`
Run it and watch it FAIL before you touch the implementation.

## GREEN — make it pass
Ajouter une section install NAS/Docker (Synology, compose, volume, port) au README/docs.

Touch only: `README.md`, `docs/market/2026-07-12/REPORT.md`

## VERIFY
`pytest`
The RED test now passes and no existing test regresses.
