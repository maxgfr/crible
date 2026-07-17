#!/usr/bin/env bash
# Green-run resolver for the failure beacons: close the open labeled issue
# (if any) with a comment linking the green run — the counterpart of
# notify-workflow-failure.sh, same argument contract. Requires GH_TOKEN with
# `issues: write`.
# Usage: resolve-workflow-beacon.sh <workflow-name> <run-url> [label]
#
# The default data-refresh-failure label is SHARED by the three publish
# workflows, so a green sibling can close an issue a still-broken workflow
# opened. Accepted: its next failure re-opens a fresh issue via the notify
# script — worst case is issue churn, never silence.

set -euo pipefail

workflow="${1:?usage: resolve-workflow-beacon.sh <workflow-name> <run-url> [label]}"
run_url="${2:?usage: resolve-workflow-beacon.sh <workflow-name> <run-url> [label]}"
label="${3:-data-refresh-failure}"
stamp="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

existing="$(gh issue list --label "$label" --state open --json number --jq '.[0].number // empty')"
if [ -z "$existing" ]; then
  echo "no open $label issue — nothing to resolve"
  exit 0
fi

gh issue close "$existing" \
  --comment "Resolved: \`${workflow}\` went green (${stamp}). Run: ${run_url}"
echo "closed issue #$existing"
