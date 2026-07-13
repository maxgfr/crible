#!/usr/bin/env bash
# Publish the demo dataset as GitHub Release assets on the rolling
# `data-latest` release — the stable download URL `crible bootstrap` prefers
# over the demo-data branch. Called by refresh-data.yml right after
# publish-demo-data.sh and shares its never-publish-empty gate
# (site-data/manifest.json). Requires the gh CLI (GH_TOKEN in CI).
#
# Assets:
#   crible-data.tar.gz   data/raw + data/universe.parquet + data/snapshot (+ status.json)
#   universe.parquet     the site-data copies, individually downloadable
#   snapshot.parquet
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
tar -czf "$tarball" "${paths[@]}"

# a rolling release: created once, assets clobbered nightly; --latest=false so
# it never shadows the versioned application releases
gh release view data-latest > /dev/null 2>&1 || gh release create data-latest \
  --latest=false --title "Rolling open dataset (nightly)" \
  --notes "Nightly keyless open-data refresh. Bootstrap a self-hosted crible from it with \`crible bootstrap\` — no crawl needed."
gh release upload data-latest "$tarball" site-data/universe.parquet site-data/snapshot.parquet --clobber
echo "released data-latest assets ($(du -h "$tarball" | cut -f1 | tr -d ' ') tarball)"
