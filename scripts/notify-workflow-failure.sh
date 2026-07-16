#!/usr/bin/env bash
# Failure beacon for the data workflows: raise (or bump) ONE labeled GitHub
# issue instead of failing silently in the Actions tab. Requires GH_TOKEN with
# `issues: write`.
# Usage: notify-workflow-failure.sh <workflow-name> <run-url> [label] [title]
# Distinct label+title pairs keep separate single-issue channels (e.g. the
# top10k-coverage beacon alongside the default data-refresh-failure one).
#
# Caveat: workflow steps guarded by `if: failure()` do not fire on CANCELLED
# runs — the cancellation class was eliminated by giving each data workflow
# its own concurrency group (see import-prices.yml).

set -euo pipefail

workflow="${1:?usage: notify-workflow-failure.sh <workflow-name> <run-url> [label] [title]}"
run_url="${2:?usage: notify-workflow-failure.sh <workflow-name> <run-url> [label] [title]}"
label="${3:-data-refresh-failure}"
title="${4:-Data refresh is failing}"
stamp="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# lazy label creation; --force makes it idempotent
gh label create "$label" --force \
  --description "A data workflow needs attention" --color B60205

existing="$(gh issue list --label "$label" --state open --json number --jq '.[0].number // empty')"

body="The \`${workflow}\` workflow flagged: ${title} (${stamp}).

Run: ${run_url}

The data-latest release keeps its last-good assets (publish only runs after a green export)."

if [ -n "$existing" ]; then
  gh issue comment "$existing" --body "$body"
  echo "commented on issue #$existing"
else
  gh issue create \
    --title "$title" \
    --label "$label" \
    --body "$body"
  echo "opened a new $label issue"
fi
