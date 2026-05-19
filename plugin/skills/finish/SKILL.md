---
name: finish
description: Use when implementation is complete — re-runs verifiers, shows commit summary, then offers PR / merge to main / nothing. Thin branch-close wrapper around gh and git.
---

# finish

## Overview

Three steps: verify everything still passes → show what was built → offer next action.

## When to Use

- After `/renmark:orchestrate` (and optionally `/renmark:verify`) completes cleanly
- When the user says "ship it", "create a PR", "we're done"

**Do NOT use if verifiers are failing** — fix with `/renmark:debug` first.

## Steps

### 1. Re-run verifiers

Run each task's verifier from the plan, or `npm test` / `pytest -q` if a test suite exists. If any fail: **stop**, report which ones, route to `/renmark:debug`.

### 2. Show branch summary

```bash
git log --oneline <base>..HEAD   # base = main or master
git diff --stat <base>..HEAD
```

Present: N commits, M files changed, brief note on each commit.

### 3. Offer next steps

> *"All verifiers pass. N commits, M files changed.*
> *What's next?*
> *  [p] Pull request — gh pr create with CHANGELOG summary as body*
> *  [m] Merge to main — local merge + push*
> *  [n] Nothing — done, leave as-is"*

**[p] PR:**
Pull the `**Built:**` lines from CHANGELOG.md entries written during this run and use them as bullet points in the PR body.
```bash
gh pr create --title "<feature name>" --body "$(cat <<'EOF'
## Summary
- [bullets from CHANGELOG Built entries]

## Verified
- All task verifiers pass

🤖 Built with renmark
EOF
)"
```

**[m] Merge:**
```bash
git checkout main && git merge --no-ff <branch> && git push
```

**[n]:** Stop. Confirm branch name so user can run any of the above manually later.
