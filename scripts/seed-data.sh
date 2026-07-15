#!/usr/bin/env bash
# Seed the published dataset from THIS machine — the upfront path for the
# first launch, and the rescue path whenever Yahoo rate-limits the GitHub
# runners. Everything keyless: FinanceDatabase universe, Yahoo fundamentals/
# prices via yfinance, audited ESEF statements via a fresh GLEIF mapping.
#
#   DEADLINE=7200 bash scripts/seed-data.sh
#
# Resumable: re-running skips symbols still inside their freshness window and
# extends coverage instead of starting over.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

DEADLINE="${DEADLINE:-7200}"          # ~47 symbols/h at the default 330 req/h budget
MIN_SYMBOLS="${MIN_SYMBOLS:-50}"
export CRIBLE_DATA_DIR="${CRIBLE_DATA_DIR:-data}"

# 1. start from the published last-good dataset when one exists
if gh release download data-latest --pattern crible-data.tar.gz \
    --output /tmp/crible-data.tar.gz --clobber 2> /dev/null; then
  tar -xzf /tmp/crible-data.tar.gz
  echo "restored last-good data/ from the data-latest release"
fi

# 2. fresh GLEIF ISIN→LEI mapping (best-effort — the ESEF cycle self-skips without it)
mkdir -p "$CRIBLE_DATA_DIR"
curl -fsSL --retry 3 -o "$CRIBLE_DATA_DIR/isin-lei.zip" \
  https://mapping.gleif.org/api/v2/isin-lei/latest/download \
  || echo "GLEIF download failed — ESEF enrichment will be skipped this run"

# 3. bounded keyless refresh: crawl (sample first) → ESEF → prices → prune → compute
uv run crible refresh --deadline "$DEADLINE"

# 4. the never-publish-empty gate
uv run crible export-site --out site-data --min-symbols "$MIN_SYMBOLS"

# 5. publish the data-latest release assets (the only distribution channel)
bash "$(dirname "$0")/publish-data-release.sh"

# 6. a release upload does NOT trigger pages.yml (it only listens to main +
#    refresh-data/import-prices runs) — kick the deploy explicitly
gh workflow run pages.yml \
  || echo "could not trigger the deploy — run: gh workflow run pages.yml"

echo "seeded — watch the deploy with: gh run list --workflow pages.yml"
