---
name: finish
description: Use when implementation is complete — re-runs verifiers, shows commit summary, then offers PR / merge / release / nothing. Release builds a version-anchored distribution zip into .renmark/baks/ (always, offline) and a matching git tag, plus a GitHub release when a remote + gh are available. Thin branch-close wrapper around gh and git.
---

# finish

## Overview

Three steps: verify everything still passes → show what was built → offer next action.

## When to Use

- After `/renmark:orchestrate` (and optionally `/renmark:verify`) completes cleanly
- When the user says "ship it", "create a PR", "we're done"

**Do NOT use if verifiers are failing** — fix with `/renmark:debug` first.

## Steps

**Step 0 — Context check.** Call `lifecycle.skill_preamble(repo, 'finish')`. If it returns a non-None hint, surface as a one-line note.

**Final step — Lifecycle update.** After all verifiers pass, call `lifecycle.write_lifecycle(repo, stage='ready-to-release')`. The recommended next command becomes `/renmark:release` (per `NEXT_BY_STAGE`). In v0.4.0+, finish becomes a stage-marker only — PR/merge logic moves to `/renmark:release`.

**Decision log entry.** Immediately after the lifecycle write, finish appends a single ADR to `.renmark/memory/decisions.md` via `memory.log_decision()` — capturing the feature name (`state.feature`), branch, stage transition (e.g. `documented → ready-to-release`), and the list of completed stages. The call is idempotent on `(title.strip(), date)`, so re-running finish on the same day short-circuits and never duplicates ADRs. Canonical snippet finish runs:

```python
from renmark import memory, lifecycle
from pathlib import Path
s = lifecycle.read_lifecycle(Path('.'))
if s:
    memory.log_decision(Path('.'),
        title=f"Finished feature {s.feature}",
        decision=f"Branch {s.branch} reached stage {s.stage}",
        context=f"Completed stages: {', '.join(s.stages_completed)}")
```

### 1. Re-run verifiers

Run each task's verifier from the plan, or `npm test` / `pytest -q` if a test suite exists. If any fail: **stop**, report which ones, route to `/renmark:debug`.

### 1.5 Refresh the project map

Now that verifiers pass and the branch is in its final shape, refresh the codebase map:

```bash
python -m renmark.init
```

The script byte-equality-skips: if shape didn't change (e.g. this feature only fixed bugs), no files are written — zero cache bust, zero churn. The stdout line tells you exactly what happened: `stub=unchanged map=unchanged` vs `stub=refreshed map=refreshed`.

**If the script wrote anything** (stdout shows `refreshed` or `created` for any of stub/agents/map), commit it as part of this branch:

```bash
# Stage only files the script actually touches
git add CLAUDE.md AGENTS.md .renmark/memory/project-map.md 2>/dev/null
# Only commit if there's something to commit
git diff --cached --quiet || git commit -m "docs: refresh project map"
```

This puts the map refresh on the feature branch — the PR's diff includes the doc updates, and merging the feature merges the refreshed map.

Add the script's stdout line to the eventual report (step 3 / [p] PR body / etc.) as `Project map: <stdout>`.

### 2. Show branch summary

```bash
git log --oneline <base>..HEAD   # base = main or master
git diff --stat <base>..HEAD
```

Present: N commits, M files changed, brief note on each commit.

### 3. Offer next steps

> *"All verifiers pass. N commits, M files changed.*
> *What's next?*
> *  1. [p] Pull request — open a PR with gh, using the CHANGELOG summary as the body*
> *  2. [m] Merge — merge the branch into main locally and push*
> *  3. [r] Release — package this version to .renmark/baks/ + tag it (+ GitHub release if available)*
> *  4. [n] Nothing — stop here; leave the branch as-is to PR or merge later"*

A choice is required to continue — wait for the user to pick a number (or its bracket letter); never auto-proceed.

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

**[r] Release:** see § Release below.

**[n]:** Stop. Confirm branch name so user can run any of the above manually later.

### 4. Release (package + version parity)

Produce a versioned distribution that matches the committed/tagged version, with
a **local copy always** in `.renmark/baks/` and a GitHub release **when available**.
The local bak is the offline fallback — "if I don't want to pull from GitHub, it's
in `.renmark/baks/`."

> **Maintainer note (packaging renmark itself, not a managed project):** the
> default writes inside the project's `.renmark/baks/`. To package a release to a
> sibling/parent directory with a custom name (e.g. renmark's own repo, whose
> releases live in `~/projects/ai-system-renmark-vX-DATE.zip`), use the override:
> `python -m renmark.release package --dest ~/projects --name ai-system-renmark-v<VERSION>-<DATE>`.
> `--dest` is an explicit opt-out of the project-write-boundary for maintainer
> release builds only — managed-project releases always default to `.renmark/baks/`.

**4a. Drift gate (free).** `python -m renmark.release check` — refuse to release
if the 7 version locations disagree. Fix drift first.

**4b. Build the local package (always, offline, no deps).**
```bash
python -m renmark.release package
# → .renmark/baks/<plugin-name>-v<VERSION>.zip   (gitignored; pure-Python zip)
```
This is the same artifact a GitHub release would attach. `build_package` writes
**only inside the project** (`project-write-boundary-rule`) and excludes
`.git`, `.venv`, `__pycache__`, `.env`, `.renmark/`, `PLAN.md`, etc.

**4c. Tag the version (local; the parity anchor).** The tag name MUST equal
`v<VERSION>` so the local bak, the tag, and any GitHub release all carry the
same version.
```bash
git tag -a "v$(cat VERSION)" -m "renmark v$(cat VERSION)"
```
Confirm with the user before tagging — tags are cheap but shared once pushed.

**4d. GitHub release — only if a remote + `gh` both exist.** Detect first:
```bash
git remote -v        # is there an 'origin'?
command -v gh        # is the GitHub CLI installed + authed?
```
- **Both present** → offer to push the tag and create the release with the bak attached:
  ```bash
  git push origin "v$(cat VERSION)"
  gh release create "v$(cat VERSION)" ".renmark/baks/$(python -m renmark.release current | sed 's/^/<name>-v/').zip" \
      --title "v$(cat VERSION)" --notes-from-tag
  ```
  (Pushing + publishing a release are shared/remote actions — get explicit user
  approval before running, per the careful-action rule.)
- **No remote or no `gh`** → do NOT fail. Report: *"No GitHub remote/gh detected —
  built local release at `.renmark/baks/<name>-v<VERSION>.zip` and tagged
  `v<VERSION>` locally. Add a remote + gh later and re-run [r] to publish."* The
  local bak + local tag are a complete release on their own.

**Versioning rule:** bak filename, git tag, and GitHub release tag are all
`v<VERSION>` — one version string, three places, never drifting. The same
discipline `renmark.release check` already enforces for the in-repo version files.
