#!/usr/bin/env bash
# Renmark pre-commit guard — Layer 1 guardrails.
#
# Runs three fast checks in order. Any failure aborts the commit:
#   1. Unit tests (pytest)         — catches regressions
#   2. Drift check                 — VERSION files in sync
#   3. Lint                        — plugin contracts well-formed
#
# Total budget: ~30s on a warm checkout. Skip with --no-verify in genuine
# emergencies (then run `bash tools/precommit.sh` manually before pushing).
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$REPO_ROOT"

start=$(date +%s)
fail=0

say() { printf '  %s\n' "$*"; }
hdr() { printf '\n→ %s\n' "$*"; }

hdr "1/3  pytest (unit tests)"
if python -m pytest -q --no-header 2>&1 | tail -3; then
    say "OK"
else
    say "FAIL — unit tests broke"
    fail=1
fi

hdr "2/3  version drift check"
if out=$(python -m renmark.release check 2>&1); then
    say "$out"
else
    say "FAIL — version files drifted:"
    echo "$out" | sed 's/^/  /'
    fail=1
fi

hdr "3/3  plugin lint"
if out=$(python -m renmark.lint 2>&1); then
    say "$out"
else
    say "FAIL — plugin contract issues:"
    echo "$out" | sed 's/^/  /'
    fail=1
fi

elapsed=$(( $(date +%s) - start ))
echo
if [[ $fail -eq 0 ]]; then
    printf '✓ pre-commit OK  (%ss)\n' "$elapsed"
    exit 0
else
    printf '✗ pre-commit FAILED  (%ss)\n' "$elapsed"
    printf '  fix the issues above, or bypass with --no-verify (not recommended)\n'
    exit 1
fi
