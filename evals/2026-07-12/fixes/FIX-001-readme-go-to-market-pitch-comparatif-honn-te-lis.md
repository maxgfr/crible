# FIX-001 — README go-to-market : pitch, comparatif honnête, listing awesome-selfhosted  (P1 · OPPORTUNITY · impact high · effort S)

**Opportunity F4:** Le README actuel est technique et neutre ; il ne vend pas le seul créneau vide du marché (screener fondamental self-hosted, zéro clé, alternative à un abonnement à €550/an). Le canal de distribution du cœur de cible (awesome-selfhosted, catégorie Money) n'a aucun screener.
**Evidence:** `README.md:1`, `docs/market/2026-07-12/REPORT.md:1`
**Why it matters:** Le README actuel est technique et neutre ; il ne vend pas le seul créneau vide du marché (screener fondamental self-hosted, zéro clé, alternative à un abonnement à €550/an). Le canal de distribution du cœur de cible (awesome-selfhosted, catégorie Money) n'a aucun screener.

## RED — write this test first
Write a spec/characterization test that pins the desired behavior: Réécrire le README : pitch « garde tes €550/an », screenshots dark/light, table comparative honnête (Stockopedia/TIKR/SWS/OpenBB/Ghostfolio), quickstart compose one-liner ; soumettre à awesome-selfhosted.

Suggested test file: `tests/readme-go-to-market-pitch-comparatif-honn-te-lis.test.ts`
Run it and watch it FAIL before you touch the implementation.

## GREEN — make it pass
Réécrire le README : pitch « garde tes €550/an », screenshots dark/light, table comparative honnête (Stockopedia/TIKR/SWS/OpenBB/Ghostfolio), quickstart compose one-liner ; soumettre à awesome-selfhosted.

Touch only: `README.md`, `docs/market/2026-07-12/REPORT.md`

## VERIFY
`pytest`
The RED test now passes and no existing test regresses.
