# FIX-006 — EDINET sec_code rejects the new 4-char alphanumeric Tokyo codes (e.g. 130A.T)  (P2 · OPPORTUNITY · impact low · effort S)

**Opportunity F4:** sec_code returns None when the ticker base is not all digits (edinet.py:155), silently skipping the alphanumeric TSE codes the Tokyo exchange began issuing in 2024 (e.g. 130A.T). Those JP listings never resolve to an EDINET securities code. EDINET is opt-in (off without a key) so the blast radius is small.
**Evidence:** `src/crible/providers/edinet.py:155`
**Why it matters:** sec_code returns None when the ticker base is not all digits (edinet.py:155), silently skipping the alphanumeric TSE codes the Tokyo exchange began issuing in 2024 (e.g. 130A.T). Those JP listings never resolve to an EDINET securities code. EDINET is opt-in (off without a key) so the blast radius is small.

## RED — write this test first
Write a spec/characterization test that pins the desired behavior: Accept a 4-char alphanumeric base and pad to the 5-char EDINET securities code.

Suggested test file: `tests/test_edinet.FIX-006.py`
Run it and watch it FAIL before you touch the implementation.

## GREEN — make it pass
Accept a 4-char alphanumeric base and pad to the 5-char EDINET securities code.

Touch only: `src/crible/providers/edinet.py`

## VERIFY
`pytest`
The RED test now passes and no existing test regresses.
