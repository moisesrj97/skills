#!/usr/bin/env bash
# Lists the comment lines a change added or modified, as <file>:<line>: <text>.
# Usage: find_comments.sh [<git diff args>]   default: --merge-base <default branch>
set -euo pipefail

if [ $# -eq 0 ]; then
  base=$(git symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null) \
    || base="origin/$(gh repo view --json defaultBranchRef -q .defaultBranchRef.name)"
  set -- --merge-base "$base"
fi

git diff "$@" -U0 -- . ':!*.md' ':!*.lock' ':!*-lock.*' | awk '
/^\+\+\+ b\// { file=substr($0,7) }
/^@@/ { match($0, /\+[0-9]+/); n=substr($0, RSTART+1, RLENGTH-1) }
/^\+/ && !/^\+\+\+/ { l=$0; sub(/^\+/,"",l); if (l ~ /^[ \t]*(\/\/|\/\*|\*|#|--|<!--)/) print file":"n": "l; n++ }'
