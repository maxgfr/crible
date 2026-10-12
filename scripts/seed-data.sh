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

# 1. start from the published last-good dataset when one exists. Errors are
#    NOT swallowed: only a confirmed "release not found" means "seed from
#    scratch" — any other failure (auth, network, rate limit) aborts, because
#    a from-scratch seed would later try to publish a thin dataset over the
#    live one (publish-data-release.sh's shrink guard would refuse it anyway).
mkdir -p "$CRIBLE_DATA_DIR"
restore_dir="$(mktemp -d)"
trap 'rm -rf "$restore_dir"' EXIT
if release_out="$(gh release download data-latest --pattern manifest.json \
    --dir "$restore_dir" --clobber 2>&1)"; then
  # manifest BEFORE the tarball: if a publish lands in between, the record is
  # older than the tarball and the publish guard errs on the safe side (abort)
  gh release download data-latest --pattern crible-data.tar.gz \
    --dir "$restore_dir" --clobber
  # a record left by an older local publish must not outlive this restore
  rm -f "$CRIBLE_DATA_DIR/.restored-manifest.json"
  # the tarball stores data/...; strip it so CRIBLE_DATA_DIR can be anywhere
  tar -xzf "$restore_dir/crible-data.tar.gz" --strip-components=1 -C "$CRIBLE_DATA_DIR"
  # tarballs published before the S-032 guard carry no restore record: keep
  # the manifest fetched above as the generation this dataset came from
  if [ ! -f "$CRIBLE_DATA_DIR/.restored-manifest.json" ]; then
    cp "$restore_dir/manifest.json" "$CRIBLE_DATA_DIR/.restored-manifest.json"
  fi
  echo "restored last-good $CRIBLE_DATA_DIR/ from the data-latest release"
elif grep -q "release not found" <<<"$release_out"; then
  echo "no data-latest release yet — seeding from scratch"
else
  echo "$release_out" >&2
  echo "could not download the data-latest release — aborting (fix gh auth/network and re-run)" >&2
  exit 1
fi

# 2. fresh GLEIF ISIN→LEI mapping (best-effort — the ESEF cycle self-skips without it)
curl -fsSL --retry 3 -o "$CRIBLE_DATA_DIR/isin-lei.zip" \
  https://mapping.gleif.org/api/v2/isin-lei/latest/download \
  || echo "GLEIF download failed — ESEF enrichment will be skipped this run"

# 3. bounded keyless refresh: crawl (sample first) → ESEF → prices → prune → compute
uv run crible refresh --deadline "$DEADLINE"

# 4. the never-publish-empty gate
uv run crible export-site --out site-data --min-symbols "$MIN_SYMBOLS"

# 5. publish the data-latest release assets (the only distribution channel)
bash scripts/publish-data-release.sh

# 6. a release upload does NOT trigger pages.yml (it only listens to main +
#    refresh-data/import-prices runs) — kick the deploy explicitly
gh workflow run pages.yml \
  || echo "could not trigger the deploy — run: gh workflow run pages.yml"

echo "seeded — watch the deploy with: gh run list --workflow pages.yml"
