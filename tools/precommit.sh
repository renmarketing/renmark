#!/usr/bin/env bash
# Renmark pre-commit guard — Layer 1 guardrails.
#
# Runs seven fast checks in order. Any failure aborts the commit:
#   1. Unit tests (pytest)         — catches regressions
#   2. Shadow regression net       — G3/G11/G12 drift guard
#   3. Drift check                 — VERSION files in sync
#   4. Plugin lint                 — plugin contracts well-formed
#   5. Skillgen consistency lint   — SKILL.md frontmatter + doc-slimming guard
#   6. Ruff (lint + format)        — Python style + obvious bugs
#   7. Mypy (type check)           — strict mode, catches type errors
#
# Total budget: ~30s on a warm checkout. Skip with --no-verify in genuine
# emergencies (then run `bash tools/precommit.sh` manually before pushing).
#
# Steps 6-7 require `pip install -e .[dev]`; if ruff or mypy is missing the
# step is skipped with a one-line note (graceful degradation for contributors
# who haven't installed dev deps yet).
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$REPO_ROOT"

start=$(date +%s)
fail=0

say() { printf '  %s\n' "$*"; }
hdr() { printf '\n→ %s\n' "$*"; }

hdr "1/7  pytest (unit tests)"
if python -m pytest -q --no-header 2>&1 | tail -3; then
    say "OK"
else
    say "FAIL — unit tests broke"
    fail=1
fi

hdr "2/7  shadow regression net (G3/G11/G12)"
if python -m renmark.shadow run 2>&1 | tail -5; then
    say "OK"
else
    say "FAIL — shadow baselines drifted; run: python -m renmark.shadow accept --subsystem <sub> -m 'reason'"
    fail=1
fi

hdr "3/7  version drift check"
if out=$(python -m renmark.release check 2>&1); then
    say "$out"
else
    say "FAIL — version files drifted:"
    echo "$out" | sed 's/^/  /'
    fail=1
fi

hdr "4/7  plugin lint"
if out=$(python -m renmark.lint --strict-frontmatter 2>&1); then
    say "$out"
else
    say "FAIL — plugin contract issues:"
    echo "$out" | sed 's/^/  /'
    fail=1
fi

hdr "5/7  skillgen consistency lint (SKILL.md)"
if out=$(python3 -m renmark.skillgen --check 2>&1); then
    say "$out"
else
    say "FAIL — SKILL.md consistency issues:"
    echo "$out" | sed 's/^/  /'
    fail=1
fi

hdr "6/7  ruff (lint + format)"
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

hdr "7/7  mypy (strict type check)"
if command -v mypy >/dev/null 2>&1; then
    if mypy renmark/ 2>&1 | tail -5; then
        say "OK"
    else
        say "FAIL — fix type errors above"
        fail=1
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
