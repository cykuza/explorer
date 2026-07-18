#!/usr/bin/env bash
# Build a clean orphan history for a fresh GitHub repo.
# Does NOT push, force-push, or delete the remote — you do those steps.
#
# Usage (from repo root):
#   ./scripts/prepare-public-rewrite.sh
#
# Result: local branch `public-clean` with a single root commit of the current tree.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

BRANCH="${PUBLIC_BRANCH:-public-clean}"
MSG="${PUBLIC_COMMIT_MSG:-feat: Cyberyen explorer public tree (history rewritten)}"

if [[ -n "$(git status --porcelain)" ]]; then
  echo "warning: working tree is not clean; uncommitted changes will be included in the orphan snapshot." >&2
  git status -sb >&2
fi

# Private planning drafts must never be tracked.
if git ls-files --error-unmatch docs/CONCEPT.md >/dev/null 2>&1; then
  echo "error: docs/CONCEPT.md is still tracked. Run: git rm --cached docs/CONCEPT.md" >&2
  exit 1
fi

if git show-ref --verify --quiet "refs/heads/${BRANCH}"; then
  echo "error: branch ${BRANCH} already exists. Delete it or set PUBLIC_BRANCH." >&2
  exit 1
fi

CURRENT="$(git branch --show-current)"
echo "Creating orphan branch ${BRANCH} from worktree (current branch: ${CURRENT})..."

git checkout --orphan "${BRANCH}"
git reset
git add -A

# Never publish agent/editor config or private concept drafts.
git rm -r --cached --ignore-unmatch .cursor >/dev/null 2>&1 || true
git rm --cached --ignore-unmatch docs/CONCEPT.md >/dev/null 2>&1 || true
git rm --cached --ignore-unmatch CONCEPT.md >/dev/null 2>&1 || true

git add -A
if git diff --cached --name-only | grep -E '(^|/)\.cursor/|(^|/)CONCEPT\.md$' >/dev/null; then
  echo "error: refusing to commit; .cursor/ or CONCEPT.md still staged:" >&2
  git diff --cached --name-only | grep -E '(^|/)\.cursor/|(^|/)CONCEPT\.md$' >&2 || true
  exit 1
fi

git commit -m "${MSG}"

echo
echo "Ready: branch ${BRANCH} @ $(git rev-parse --short HEAD)"
echo
echo "After you delete/recreate github.com/cykuza/explorer as empty:"
echo "  git remote add origin git@github.com:cykuza/explorer.git"
echo "  git push -u origin ${BRANCH}:master"
echo
echo "Then (optional) drop the old local branch:"
echo "  git branch -D ${CURRENT}"
echo
echo "Do not force-push old history; push only this new root commit."
