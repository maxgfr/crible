#!/usr/bin/env bash
# Graft locally-imported price artifacts (data/prices-latest.parquet + the
# data/prices/ series stores) onto the CURRENT data branch — surgical:
# nothing else from the local data/ is published. The Stooq flow (bulk zips
# are CAPTCHA-gated, so the download is manual by design):
#
#   1. download a zip from https://stooq.com/db/h/   (browser, CAPTCHA)
#   2. crible import-prices path/to/d_de_txt.zip
#   3. bash scripts/publish-prices.sh
#
# The next nightly refresh recomputes the snapshot with these quotes and
# re-exports the series shards.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

if [ ! -f data/prices-latest.parquet ]; then
  echo "nothing to publish: data/prices-latest.parquet missing — run \`crible import-prices …\` first" >&2
  exit 1
fi

if ! git fetch origin data; then
  echo "no data branch yet — run the refresh-data workflow once first" >&2
  exit 1
fi

if ! git config user.email > /dev/null; then
  export GIT_AUTHOR_NAME="github-actions[bot]"
  export GIT_AUTHOR_EMAIL="41898282+github-actions[bot]@users.noreply.github.com"
  export GIT_COMMITTER_NAME="$GIT_AUTHOR_NAME"
  export GIT_COMMITTER_EMAIL="$GIT_AUTHOR_EMAIL"
fi

tmp_index="$(mktemp)"
trap 'rm -f "$tmp_index"' EXIT
export GIT_INDEX_FILE="$tmp_index"
git read-tree FETCH_HEAD
blob="$(git hash-object -w data/prices-latest.parquet)"
git update-index --add --cacheinfo 100644 "$blob" data/prices-latest.parquet
for store in data/prices/*.parquet; do
  [ -f "$store" ] || continue
  blob="$(git hash-object -w "$store")"
  git update-index --add --cacheinfo 100644 "$blob" "$store"
done
tree="$(git write-tree)"
unset GIT_INDEX_FILE

commit="$(git commit-tree "$tree" -p FETCH_HEAD -m "prices: import update $(date -u +%FT%H:%MZ)")"
git push origin "$commit:refs/heads/data"
echo "grafted price artifacts onto data as $commit — the next nightly folds them into the snapshot"
