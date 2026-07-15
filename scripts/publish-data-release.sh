#!/usr/bin/env bash
# Publish the dataset as GitHub Release assets on the rolling `data-latest`
# release — the ONLY distribution channel (no data ever travels in git; main
# stays code-only). Called by refresh-data.yml, import-prices.yml and
# seed-data.sh; the never-publish-empty gate is site-data/manifest.json.
# Requires the gh CLI (GH_TOKEN in CI).
#
# Assets:
#   crible-data.tar.gz   data/raw + data/universe.parquet + data/snapshot
#                        (+ status.json, prices-latest.parquet, data/prices)
#                        — what `crible bootstrap` and the CI restore steps pull
#   site-data.tar.gz     the full site-data/ export (parquet + JSON manifest)
#                        — what the Pages deploy attaches to the SPA
#   universe.parquet     the site-data copies, individually downloadable
#   snapshot.parquet
#   prices-*.parquet     the OHLCV series shards (when series exist)
#
# --clobber replaces same-named assets but never deletes: if the shard count
# shrinks, a stale prices-NN.parquet can linger — the tarball and
# site-data/manifest.json stay authoritative.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

if [ ! -f site-data/manifest.json ]; then
  echo "refusing to release: site-data/manifest.json missing — run \`crible export-site\` first" >&2
  exit 1
fi

workdir="$(mktemp -d)"
trap 'rm -rf "$workdir"' EXIT
tarball="$workdir/crible-data.tar.gz"
paths=(data/raw data/universe.parquet data/snapshot)
[ -f data/status.json ] && paths+=(data/status.json)
[ -f data/prices-latest.parquet ] && paths+=(data/prices-latest.parquet)
[ -d data/prices ] && paths+=(data/prices)
tar -czf "$tarball" "${paths[@]}"

site_tarball="$workdir/site-data.tar.gz"
tar -czf "$site_tarball" site-data

assets=("$tarball" "$site_tarball" site-data/universe.parquet site-data/snapshot.parquet)
for shard in site-data/prices-*.parquet; do
  [ -f "$shard" ] && assets+=("$shard")
done

# a rolling release: created once, assets clobbered nightly; --latest=false so
# it never shadows the versioned application releases
gh release view data-latest > /dev/null 2>&1 || gh release create data-latest \
  --latest=false --title "Rolling open dataset (nightly)" \
  --notes "Nightly keyless open-data refresh. Bootstrap a self-hosted crible from it with \`crible bootstrap\` — no crawl needed."
gh release upload data-latest "${assets[@]}" --clobber
echo "released data-latest assets ($(du -h "$tarball" | cut -f1 | tr -d ' ') tarball)"
