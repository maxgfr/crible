#!/usr/bin/env bash
# Publish the dataset as GitHub Release assets on the rolling `data-latest`
# release — the ONLY distribution channel (no data ever travels in git; main
# stays code-only). Called by refresh-data.yml, import-prices.yml,
# crawl-marathon.yml and seed-data.sh; the never-publish-empty gate is
# site-data/manifest.json.
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
#
# Pre-publish guards (S-032) — against the live release, before any upload:
#   - DIVERGED: the live manifest's generation (generated_at + commit) must be
#     the one this dataset was restored from. The data tarball carries that
#     record as data/.restored-manifest.json (written below, restored with the
#     tarball by every CI restore step and by seed-data.sh); a mismatch means
#     another publisher released while this one was working, and uploading
#     would silently revert its work. Override: CRIBLE_ALLOW_DIVERGED=1.
#   - SHRINK: snapshot_symbols may not fall below 90% of the live value — a
#     run that restored nothing (or crawled into a wall) would otherwise
#     replace a big dataset with a thin one. Override: CRIBLE_ALLOW_SHRINK=1.
#   No live release (or a legacy one without manifest.json) = first publish:
#   nothing to protect, both guards are skipped. A dataset without a restore
#   record (first run after this guard shipped, or a from-scratch local data
#   dir) only gets a warning on DIVERGED; SHRINK still applies.
#
# CRIBLE_DATA_DIR (default: data, relative to the repo root) is honoured; the
# tarball layout stays data/... whatever the local directory is called, since
# the CI restore steps and `crible bootstrap` expect it.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

data_dir="${CRIBLE_DATA_DIR:-data}"
restored_record="$data_dir/.restored-manifest.json"

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

if [ ! -d "$data_dir" ]; then
  echo "refusing to release: data dir $data_dir missing (CRIBLE_DATA_DIR)" >&2
  exit 1
fi

workdir="$(mktemp -d)"
trap 'rm -rf "$workdir"' EXIT

# ---- pre-publish guards (see header) ----------------------------------------
live_exists=0
if release_exists; then live_exists=1; fi

if [ "$live_exists" = 1 ]; then
  live_assets="$(retry 3 gh release view data-latest --json assets --jq '.assets[].name')"
  if grep -qx "manifest.json" <<<"$live_assets"; then
    mkdir -p "$workdir/live"
    retry 3 gh release download data-latest --pattern manifest.json \
      --dir "$workdir/live" --clobber
    python3 - "$workdir/live/manifest.json" site-data/manifest.json "$restored_record" <<'PY'
import json
import os
import sys
from pathlib import Path

live = json.loads(Path(sys.argv[1]).read_text())
new = json.loads(Path(sys.argv[2]).read_text())
record_path = Path(sys.argv[3])
failed = False


def generation(m):
    return {"generated_at": m.get("generated_at"), "commit": m.get("commit")}


if record_path.is_file():
    restored = json.loads(record_path.read_text())
    if generation(restored) != generation(live):
        msg = (
            f"live data-latest changed since this dataset was restored: "
            f"restored {generation(restored)}, live now {generation(live)}"
        )
        if os.environ.get("CRIBLE_ALLOW_DIVERGED") == "1":
            print(f"WARNING (CRIBLE_ALLOW_DIVERGED=1): {msg}", file=sys.stderr)
        else:
            print(f"refusing to release: {msg} — publishing would revert the newer "
                  "release; re-run from a fresh restore (override: "
                  "CRIBLE_ALLOW_DIVERGED=1)", file=sys.stderr)
            failed = True
else:
    print(f"WARNING: no restore record ({record_path}) — cannot tell whether the live "
          "release changed since this dataset was built", file=sys.stderr)

live_n = int(live.get("snapshot_symbols") or 0)
new_n = int(new.get("snapshot_symbols") or 0)
if live_n and new_n < 0.9 * live_n:
    msg = f"snapshot_symbols would shrink {live_n} -> {new_n} (< 90% of the live release)"
    if os.environ.get("CRIBLE_ALLOW_SHRINK") == "1":
        print(f"WARNING (CRIBLE_ALLOW_SHRINK=1): {msg}", file=sys.stderr)
    else:
        print(f"refusing to release: {msg} (override: CRIBLE_ALLOW_SHRINK=1)",
              file=sys.stderr)
        failed = True
print(f"guards: live snapshot_symbols={live_n}, new={new_n}")
sys.exit(1 if failed else 0)
PY
  else
    echo "WARNING: live data-latest has no manifest.json — skipping the pre-publish guards" >&2
  fi
else
  echo "no live data-latest release — first publish, nothing to guard"
fi

# ---- build the assets -------------------------------------------------------
# The tarball keeps the data/... layout whatever CRIBLE_DATA_DIR is: a staging
# symlink named data points at the real dir (intermediate path components are
# resolved by the OS, so members are stored as data/raw/..., not as a link).
stage="$workdir/stage"
mkdir -p "$stage/record/data"
ln -s "$(cd "$data_dir" && pwd)" "$stage/data"
# the restore record for the NEXT publisher = this publish's manifest. Taken
# from a staged copy: the local record is only updated once the release is
# verified, so a failed upload never makes the local data dir lie.
cp site-data/manifest.json "$stage/record/data/.restored-manifest.json"

tarball="$workdir/crible-data.tar.gz"
paths=(data/raw data/universe.parquet data/snapshot)
[ -f "$data_dir/status.json" ] && paths+=(data/status.json)
# the rolling budget window rides along so chained CI crawls resume it
# instead of double-spending the hour (NFR-007)
[ -f "$data_dir/budget-state.json" ] && paths+=(data/budget-state.json)
[ -f "$data_dir/prices-latest.parquet" ] && paths+=(data/prices-latest.parquet)
[ -d "$data_dir/prices" ] && paths+=(data/prices)
[ -d "$data_dir/events" ] && paths+=(data/events)
[ -d "$data_dir/caps" ] && paths+=(data/caps)
tar -czf "$tarball" -C "$stage" "${paths[@]}" \
  -C "$stage/record" data/.restored-manifest.json

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
# CONFIRMED 404 (checked once, above); a create that loses a race to a
# concurrent publisher is fine.
if [ "$live_exists" = 0 ]; then
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

# verified single-generation: the local data dir now matches the live release
cp site-data/manifest.json "$restored_record"

echo "released data-latest assets ($(du -h "$tarball" | cut -f1 | tr -d ' ') tarball) — verified single-generation"
