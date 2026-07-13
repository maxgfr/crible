#!/usr/bin/env bash
# Publish the dataset (data/ last-good layer + site-data/ artifacts) as
# ONE orphan commit force-pushed to the data branch. Shared by
# .github/workflows/refresh-data.yml and scripts/seed-data.sh — the
# single source of truth for what the published dataset contains.
#
# Pure git plumbing (temp index + commit-tree): never switches branches and
# never touches the working tree, so it is safe to run from a dirty local
# checkout.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

if [ ! -f site-data/manifest.json ]; then
  echo "refusing to publish: site-data/manifest.json missing — run \`crible export-site\` first" >&2
  exit 1
fi

# CI runners have no git identity configured
if ! git config user.email > /dev/null; then
  export GIT_AUTHOR_NAME="github-actions[bot]"
  export GIT_AUTHOR_EMAIL="41898282+github-actions[bot]@users.noreply.github.com"
  export GIT_COMMITTER_NAME="$GIT_AUTHOR_NAME"
  export GIT_COMMITTER_EMAIL="$GIT_AUTHOR_EMAIL"
fi

tmp_index="$(mktemp)"
trap 'rm -f "$tmp_index"' EXIT
export GIT_INDEX_FILE="$tmp_index"
git read-tree --empty
# -f: these paths are gitignored on main by design; status.json only exists
# once a refresh has written its heartbeat (mid-crawl publishes lack it)
paths=(data/raw data/universe.parquet data/snapshot site-data)
[ -f data/status.json ] && paths+=(data/status.json)
# imported price artifacts (ADR-0007): the windowed OHLCV series stores and
# the per-symbol distillate the snapshot consumes
[ -d data/prices ] && paths+=(data/prices)
[ -f data/prices-latest.parquet ] && paths+=(data/prices-latest.parquet)
git add -f "${paths[@]}"
tree="$(git write-tree)"
unset GIT_INDEX_FILE

commit="$(git commit-tree "$tree" -m "data: refresh $(date -u +%FT%H:%MZ)")"
git push --force origin "$commit:refs/heads/data"
echo "published data ($(git ls-tree -r --name-only "$commit" | wc -l | tr -d ' ') files) as $commit"
