# FIX-011 — Bulk archives are read whole into memory (GLEIF ~1GB decompressed, FSDS num.txt hundreds of MB) — OOM risk on the self-hosted target, defeating the mirror's streaming design  (P2 · DEFECT)

**Finding F11:** Two bulk parsers materialize an entire archive member in RAM. load_isin_lei_map reads the whole zip to bytes (gleif.py:43), decompresses the whole CSV to bytes (gleif.py:47), then decodes it to a str for StringIO (gleif.py:49) — triple-buffered for a file the docstring calls ~200MB (decompressed ~1GB). parse_fsds_quarter does the same archive.read(...).decode(...) on num.txt (edgar_fsds.py:131-132), hundreds of MB uncompressed per quarter. Both run on auto-heal / opt-in ingest paths that the memory-safe mirror streaming was meant to protect — the same OOM class as the prior-cycle F13 bootstrap fix.
**Evidence:** `src/crible/providers/gleif.py:43`, `src/crible/providers/gleif.py:47`, `src/crible/providers/edgar_fsds.py:131`
**Why it matters:** A 1GB-RAM VPS runs the GLEIF auto-fetch on first refresh; loading the ISIN-LEI file peaks several GB of RSS and the process is OOM-killed, leaving the audited-EU layer idle.

## RED — write this test first
Write a failing test that reproduces: A 1GB-RAM VPS runs the GLEIF auto-fetch on first refresh; loading the ISIN-LEI file peaks several GB of RSS and the process is OOM-killed, leaving the audited-EU layer idle.

Suggested test file: `tests/test_gleif.FIX-011.py`
Run it and watch it FAIL before you touch the implementation.

## GREEN — make it pass
Stream both: zipfile.open(inner)+io.TextIOWrapper -> csv.reader for GLEIF, and archive.open('num.txt')+TextIOWrapper for FSDS, capping peak memory to the resulting structures.

Touch only: `src/crible/providers/gleif.py`, `src/crible/providers/edgar_fsds.py`

## VERIFY
`pytest`
The RED test now passes and no existing test regresses.
