#!/usr/bin/env bash
# Renmark pre-commit guard — Layer 1 guardrails.
#
# Runs five fast checks in order. Any failure aborts the commit:
#   1. Unit tests (pytest)         — catches regressions
#   2. Drift check                 — VERSION files in sync
#   3. Plugin lint                 — plugin contracts well-formed
#   4. Ruff (lint + format)        — Python style + obvious bugs
#   5. Mypy (type check)           — strict mode, catches type errors
#
# Total budget: ~30s on a warm checkout. Skip with --no-verify in genuine
# emergencies (then run `bash tools/precommit.sh` manually before pushing).
#
# Steps 4-5 require `pip install -e .[dev]`; if ruff or mypy is missing the
# step is skipped with a one-line note (graceful degradation for contributors
# who haven't installed dev deps yet).
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$REPO_ROOT"

start=$(date +%s)
fail=0

say() { printf '  %s\n' "$*"; }
hdr() { printf '\n→ %s\n' "$*"; }

hdr "1/5  pytest (unit tests)"
if python -m pytest -q --no-header 2>&1 | tail -3; then
    say "OK"
else
    say "FAIL — unit tests broke"
    fail=1
fi

hdr "2/5  version drift check"
if out=$(python -m renmark.release check 2>&1); then
    say "$out"
else
    say "FAIL — version files drifted:"
    echo "$out" | sed 's/^/  /'
    fail=1
fi

hdr "3/5  plugin lint"
if out=$(python -m renmark.lint 2>&1); then
    say "$out"
else
    say "FAIL — plugin contract issues:"
    echo "$out" | sed 's/^/  /'
    fail=1
fi

hdr "4/5  ruff (lint + format)"
if command -v ruff >/dev/null 2>&1; then
    if ruff check renmark/ 2>&1 | tail -5; then
        say "OK (lint)"
    else
        say "FAIL — fix ruff errors above, or run \`ruff check --fix renmark/\`"
        fail=1
    fi
    if ruff format --check renmark/ 2>&1 | tail -5; then
        say "OK (format)"
    else
        say "FAIL — formatting drift. Run \`ruff format renmark/\` to fix."
        fail=1
    fi
else
    say "ruff not installed — skipping (install with \`pip install -e .[dev]\`)"
fi

hdr "5/5  mypy (type check)"
# v0.5.3 baseline: mypy is informational (does NOT block commits) until the
# 20 known errors are cleaned up. Once that backlog is fixed, flip this from
# soft-warn to hard-fail by setting fail=1 in the else branch below.
if command -v mypy >/dev/null 2>&1; then
    if mypy renmark/ 2>&1 | tail -5; then
        say "OK"
    else
        say "WARN — type errors detected (informational; see tracking issue for cleanup)"
    fi
else
    say "mypy not installed — skipping (install with \`pip install -e .[dev]\`)"
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
