#!/usr/bin/env bash
set -euo pipefail

# One-time (and re-runnable) label bootstrap.
# Requires: gh CLI authenticated with repo admin scope, jq.
# Usage: .github/labels.sh [owner/repo]

REPO="${1:-$(gh repo view --json nameWithOwner -q .nameWithOwner)}"
MANIFEST="$(dirname "$0")/labels.json"

jq -c '.[]' "$MANIFEST" | while read -r label; do
  name="$(jq -r '.name' <<<"$label")"
  color="$(jq -r '.color' <<<"$label")"
  description="$(jq -r '.description' <<<"$label")"
  gh label create "$name" --repo "$REPO" --color "$color" --description "$description" --force
  echo "synced: $name"
done
