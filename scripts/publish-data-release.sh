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
# The upload is NOT atomic (assets go up one by one): a crash mid-upload, or
# two publishers overlapping, can leave a mixed-generation release — observed
# live on 2026-07-15 (site-data.tar.gz 8h newer than crible-data.tar.gz). The
# post-upload verification below fails the run loudly when any expected asset
# is missing or predates this publish, and prunes orphan prices-NN.parquet
# shards that --clobber (replace-only, never delete) would leave behind.
# The existence check distinguishes a confirmed 404 from transient API errors
# — a flaky `gh release view` once read as "missing" and the blind create
# died on HTTP 422 tag_name-already-exists (2026-07-17 incident).
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

# retry <attempts> <cmd...>: linear backoff for transient gh/network failures.
# stdout passes through (usable in command substitution); diagnostics on stderr.
retry() {
  local attempts="$1" attempt
  shift
  for attempt in $(seq 1 "$attempts"); do
    if "$@"; then return 0; fi
    if [ "$attempt" -lt "$attempts" ]; then
      echo "attempt $attempt/$attempts failed: $1 — retrying in $((attempt * 10))s" >&2
      sleep $((attempt * 10))
    fi
  done
  echo "failed after $attempts attempts: $*" >&2
  return 1
}

# release_exists: 0 = data-latest exists, 1 = confirmed missing (HTTP 404).
# Anything else (5xx / network / API rate limit) is retried, then ABORTS the
# whole script (exit, not return — also under seed-data.sh's set -e) rather
# than risk a duplicate create. The {owner}/{repo} placeholders resolve from
# the git remote in CWD, so no GITHUB_REPOSITORY needed for local runs.
release_exists() {
  local attempt out
  for attempt in 1 2 3 4; do
    if out="$(gh api "repos/{owner}/{repo}/releases/tags/data-latest" --silent 2>&1)"; then
      return 0
    fi
    if grep -q "HTTP 404" <<<"$out"; then
      return 1
    fi
    echo "transient error checking data-latest existence (attempt $attempt/4): $out" >&2
    [ "$attempt" -lt 4 ] && sleep $((attempt * 5))
  done
  echo "could not confirm whether data-latest exists — aborting instead of risking a 422 duplicate create" >&2
  exit 1
}

# 60 s of slack absorbs GitHub-side clock skew on updatedAt
started_epoch="$(( $(date -u +%s) - 60 ))"

if [ ! -f site-data/manifest.json ]; then
  echo "refusing to release: site-data/manifest.json missing — run \`crible export-site\` first" >&2
  exit 1
fi

workdir="$(mktemp -d)"
trap 'rm -rf "$workdir"' EXIT
tarball="$workdir/crible-data.tar.gz"
paths=(data/raw data/universe.parquet data/snapshot)
[ -f data/status.json ] && paths+=(data/status.json)
# the rolling budget window rides along so chained CI crawls resume it
# instead of double-spending the hour (NFR-007)
[ -f data/budget-state.json ] && paths+=(data/budget-state.json)
[ -f data/prices-latest.parquet ] && paths+=(data/prices-latest.parquet)
[ -d data/prices ] && paths+=(data/prices)
[ -d data/events ] && paths+=(data/events)
[ -d data/caps ] && paths+=(data/caps)
tar -czf "$tarball" "${paths[@]}"

site_tarball="$workdir/site-data.tar.gz"
tar -czf "$site_tarball" site-data

# manifest.json rides along as a loose asset: a cheap generation stamp
# (generated_at + commit) inspectable without untarring anything
assets=("$tarball" "$site_tarball" site-data/manifest.json
        site-data/universe.parquet site-data/snapshot.parquet)
for shard in site-data/prices-*.parquet; do
  [ -f "$shard" ] && assets+=("$shard")
done

# a rolling release: created once, assets clobbered nightly; --latest=false so
# it never shadows the versioned application releases. Only create after a
# CONFIRMED 404; a create that loses a race to a concurrent publisher is fine.
if ! release_exists; then
  if ! create_out="$(gh release create data-latest \
      --latest=false --title "Rolling open dataset (nightly)" \
      --notes "Nightly keyless open-data refresh. Bootstrap a self-hosted crible from it with \`crible bootstrap\` — no crawl needed." 2>&1)"; then
    if grep -qi "already exists" <<<"$create_out"; then
      echo "data-latest already exists (lost a create race) — proceeding to upload"
    else
      echo "$create_out" >&2
      exit 1
    fi
  fi
fi
retry 3 gh release upload data-latest "${assets[@]}" --clobber

# ---- post-publish consistency check + orphan-shard prune -------------------
expected=()
for asset in "${assets[@]}"; do expected+=("$(basename "$asset")"); done

assets_json="$(retry 3 gh release view data-latest --json assets)"
verify_output="$(ASSETS_JSON="$assets_json" python3 - "$started_epoch" "${expected[@]}" <<'PY'
import datetime as dt
import json
import os
import sys

cutoff = int(sys.argv[1])
expected = set(sys.argv[2:])
assets = {
    a["name"]: dt.datetime.fromisoformat(a["updatedAt"].replace("Z", "+00:00")).timestamp()
    for a in json.loads(os.environ["ASSETS_JSON"])["assets"]
}
stale = sorted(n for n in expected if assets.get(n, 0) < cutoff)
orphans = sorted(
    n for n in assets
    if n.startswith("prices-") and n.endswith(".parquet") and n not in expected
)
print("STALE=" + ",".join(stale))
print("ORPHANS=" + ",".join(orphans))
PY
)"
stale="$(sed -n 's/^STALE=//p' <<<"$verify_output")"
orphans="$(sed -n 's/^ORPHANS=//p' <<<"$verify_output")"

if [ -n "$stale" ]; then
  echo "release verification FAILED — assets missing or from an older generation: $stale" >&2
  echo "the release may be mixed-generation; re-run the publish" >&2
  exit 1
fi

for orphan in ${orphans//,/ }; do
  gh release delete-asset data-latest "$orphan" --yes
  echo "pruned orphan shard $orphan"
done

echo "released data-latest assets ($(du -h "$tarball" | cut -f1 | tr -d ' ') tarball) — verified single-generation"
