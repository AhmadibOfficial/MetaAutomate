#!/usr/bin/env bash
# Never stage, commit or merge automatically; request confirmation before push.
set -euo pipefail
cd "$(dirname "$0")/.."

BRANCH="$(git branch --show-current)"
if [[ -z "$BRANCH" || "$BRANCH" == "main" ]]; then
  echo 'ERROR: Switch to a feature branch before make pr.' >&2
  exit 1
fi
if [[ -n "$(git status --porcelain)" ]]; then
  echo 'ERROR: Review and commit all local changes before make pr:' >&2
  git status --short >&2
  exit 1
fi
command -v gh >/dev/null || { echo 'ERROR: GitHub CLI (gh) is not installed.' >&2; exit 1; }

if gh pr view "$BRANCH" --json url --jq .url 2>/dev/null; then
  echo 'An existing PR was found; no changes made.'
  exit 0
fi

make validate
printf 'Push %s and open a PR against main? [y/N] ' "$BRANCH"
read -r REPLY
if [[ "$REPLY" != y && "$REPLY" != Y ]]; then
  echo 'Cancelled without changing GitHub.'
  exit 0
fi

git push -u origin "$BRANCH"
gh pr create --base main --head "$BRANCH" --fill
