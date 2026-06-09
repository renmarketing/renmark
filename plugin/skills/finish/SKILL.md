---
name: finish
description: Use when implementation is complete — re-runs verifiers, shows commit summary, then offers PR / merge / release / nothing. Release builds a version-anchored distribution zip into .renmark/version/ (always, offline) and a matching git tag, plus a GitHub release when a remote + gh are available. Thin branch-close wrapper around gh and git.
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

**Final step — Lifecycle update.** After all verifiers pass, call `lifecycle.write_lifecycle(repo, stage='ready-to-release')` — but **only when the feature is not already at a later stage** (`released`). Never downgrade `released → ready-to-release` on a re-run; if the stage is already `released`, leave it and report that the feature is already shipped. There is **no `/renmark:release` skill** — it is unimplemented (see `lifecycle.NEXT_BY_STAGE`, which routes `ready-to-release` to the manual fallback *"tag the release and build the zip; see README § Release"*; the `/renmark:release` target lives only in the aspirational `NEXT_BY_STAGE_PLANNED`). PR, merge, branch cleanup, and release packaging/tagging all live in **this skill** (steps 3–4 below), not in a separate release command.

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

### 2.5 Build and record the feature report

After the branch summary and before presenting the next-steps menu, build the feature report and record the analytics run. This step is **non-blocking** — if any call fails, log the error and continue to step 3 without aborting finish.

```python
import subprocess, glob
from renmark import reports, analytics, state, lifecycle, summary
from pathlib import Path

repo = Path('.')
s = lifecycle.read_lifecycle(repo)

# Gather what finish already knows
feature_name = s.feature if s else ""
branch = s.branch if s else ""
sha = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip()
# Files changed against base (main/master)
diff_stat = subprocess.check_output(
    ["git", "diff", "--stat", "main..HEAD"]).decode()
files_changed = sum(1 for line in diff_stat.splitlines()
                    if "|" in line)  # each changed file has a "|" in --stat output
# Verification result comes from the verify artifact pointer (LifecycleState has
# NO `verification_result` attr) — read the artifact's bounded metadata, never its body.
verification = ""
vpath = s.artifacts.get("verification") if s and s.artifacts else None
if vpath:
    meta = summary.read_metadata(vpath)  # frontmatter only — no body read
    # summary_lines live in the BODY's '## Summary' section, never the frontmatter:
    sl = summary.read_summary_lines(vpath)  # bounded bullets, G3-capped
    verification = sl[0] if sl else (meta or {}).get("completion_state", "")
# Codereview artifact — check for most recent review file
review_files = sorted(glob.glob(".renmark/reviews/*.review.md"))
codereview = review_files[-1] if review_files else ""
# Version path — check for a release snapshot matching current stage
version_dirs = sorted(glob.glob(".renmark/version/v*/"))
version_path = version_dirs[-1] if version_dirs else ""
branch_disposition = "merged" if s and s.stage == "released" else "open"
# Map the lifecycle STAGE to an analytics status vocab term — analytics classifies
# success/blocked on SUCCESS_STATUSES/BLOCKED_STATUSES, NOT on raw stage names.
stage = s.stage if s else ""
if stage == "released":
    feature_status = "shipped"
elif stage in {"verified", "reviewed", "documented", "ready-to-release"}:
    feature_status = "completed"
else:
    feature_status = "blocked"
now = state.now_iso()

# 1. Build + write the feature report
report = reports.build_feature_report(
    repo,
    feature=feature_name,
    branch=branch,
    sha=sha,
    version_path=version_path,
    verification=verification,
    codereview=codereview,
    files_changed=files_changed,
    branch_disposition=branch_disposition,
    now=now,
)
md_path, json_path = reports.write_feature_report(repo, feature_name, report)

# 2. Record the analytics run
analytics.record_feature_run(
    repo,
    ts=now,
    feature=feature_name,
    branch=branch,
    status=feature_status,  # mapped to analytics vocab (shipped/completed/blocked), NOT raw stage
    sha=sha,
    files_changed=files_changed,
    verification=verification,
    branch_disposition=branch_disposition,
)
```

**CRITICAL context hygiene:** surface ONLY the report path and a ≤5-line summary to the orchestrator — **never read or paste the report body** into the conversation.

Report written to: `<md_path>` (JSON: `<json_path>`)

### 3. Offer next steps

> *"All verifiers pass. N commits, M files changed.*
> *What's next?*
> *  1. [p] Pull request — open a PR with gh, using the CHANGELOG summary as the body*
> *  2. [m] Merge — merge the branch into main locally and push*
> *  3. [r] Release — package this version to .renmark/version/ (zip + unpacked snapshot) + tag it (+ GitHub release if available)*
> *  4. [a] Analytics — open the feature analytics dashboard with `/renmark:analytics`*
> *  5. [n] Nothing — stop here; leave the branch as-is to PR or merge later"*

**Present this as an interactive `AskUserQuestion` choice when available** (PRIMARY): arrow-selectable choices `Pull request [p]`, `Merge [m]`, `Release [r]`, `Analytics [a]`, `Nothing [n]`. **Fallback** (tool unavailable / non-interactive / headless, OR the picker is declined, errors, returns no valid selection, or would show no visible options): print the numbered list above and accept a number or bracket letter — pass options as real `AskUserQuestion` choices (never embedded in the question text), and never end on the question with no visible choices. A choice is required either way — never auto-proceed. (Merge / release are outward, irreversible actions — only run on the user's explicit selection.)

**[a] Analytics:** Run `/renmark:analytics` to open the feature analytics dashboard for this run.

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
git checkout main && git merge --no-ff <branch>
git push                                 # only if an 'origin' remote exists; skip when none
# Clean up the branch finish/feature created — once merged it's redundant.
git branch -d <branch>                   # safe delete: refuses if NOT fully merged, so it can never lose work
git push origin --delete <branch>        # only if a remote exists AND the branch was pushed there
```
**Always delete the merged feature branch after a clean merge** — `/renmark:feature`
created it, so closing the feature is what removes it. Use `git branch -d` (lowercase,
the *safe* form: it refuses to delete an unmerged branch); never `-D` unless the user
explicitly discards unmerged work. Omit both `git push` lines when there's no `origin`.

**[r] Release:** see § Release below. A release is cut from `main` *after* the merge,
so by release time the feature branch is already gone (deleted by the merge step above).
If a stray merged feature branch still exists at release time, delete it with
`git branch -d <branch>` as part of closing out.

**[n]:** Stop. Confirm branch name so user can run any of the above manually later.

**Picking the next feature (post-merge / post-release hand-off).** Once the
branch is closed (merged, released, or parked), do NOT dead-end on a generic
"start a new one." The recommended way to choose what to build next is
**`/renmark:roadmap` in gap mode** (advisory): it runs gap discovery —
PRD-vs-shipped — comparing `PRD.md` against `CHANGELOG.md` + `.renmark/memory/features.md`
to surface unbuilt promises and drift, then ranks the next candidate feature.
That feeds straight into `/renmark:feature` for the one you pick. `/renmark:start`
remains available for a free-form, blank-slate idea that isn't already implied by
the PRD.

### 4. Release (package + version parity)

Produce a versioned distribution that matches the committed/tagged version, with
a **local copy always** in `.renmark/version/` and a GitHub release **when available**.
`.renmark/baks/` remains readable for old artifacts but **new releases write ONLY
to `.renmark/version/`**.

> **Maintainer note (packaging renmark itself, not a managed project):** by
> default, `python -m renmark.release snapshot` writes both the zip
> (`<name>-v<VERSION>.zip`) and the unpacked snapshot directory (`v<VERSION>/`)
> inside the project's `.renmark/version/`. To write those same two outputs to a
> sibling/parent directory with a custom name stem — e.g. renmark's own releases,
> which land at `~/projects/ai-system-renmark-v<VERSION>-<DATE>.zip` and
> `~/projects/ai-system-renmark-v<VERSION>-<DATE>/` — use the override flags:
> `python -m renmark.release snapshot --dest ~/projects --name ai-system-renmark-v<VERSION>-<DATE>`.
> Both `--dest` and `--name` apply to the zip AND the unpacked directory. `--dest`
> is an explicit opt-out of the project-write-boundary for maintainer release builds
> only — managed-project releases always default to `.renmark/version/`.

**Timing contract — preconditions (in order). The snapshot is the last LOCAL
artifact-generation step (it runs before any remote publish in 4d). It MUST NOT
run until ALL of the following are true:**

1. Human merge approval has been given explicitly.
2. The branch has been merged into `main`.
3. Final verifiers pass on `main` (not the feature branch).
4. The version string and tag name are known and confirmed.

Never snapshot a pre-merge or unverified tree.

**4a. Drift gate (free).** `python -m renmark.release check` — refuse to release
if the 7 version locations disagree. Fix drift first.

**4b. Tag the version (local; the parity anchor).** The tag name MUST equal
`v<VERSION>` so the snapshot, the tag, and any GitHub release all carry the
same version.
```bash
git tag -a "v$(cat VERSION)" -m "renmark v$(cat VERSION)"
```
Confirm with the user before tagging — tags are cheap but shared once pushed.

**4c. Snapshot (always, offline, no deps — runs AFTER merge + verification).**
```bash
python -m renmark.release snapshot
```
This single command writes **both**:
- `.renmark/version/<basename>-v<VERSION>.zip` — portable zip (the distributable artifact)
- `.renmark/version/v<VERSION>/` — unpacked, browsable snapshot directory containing:
  - `manifest.json` — version metadata, file inventory, timestamps
  - `release.md` — human-readable release notes
  - `verification.md` — verifier pass/fail record from step 4 precondition check
  - `files-changed.txt` — diff stat vs previous release tag

Both outputs write **only inside the project** (`project-write-boundary-rule`) and
exclude `.git`, `.venv`, `__pycache__`, `.env`, `.renmark/`, `PLAN.md`, etc.
This is the same zip a GitHub release would attach.

**4d. GitHub release — only if a remote + `gh` both exist.** Detect first:
```bash
git remote -v        # is there an 'origin'?
command -v gh        # is the GitHub CLI installed + authed?
```
- **Both present** → offer to push the tag and create the release with the zip attached:
  ```bash
  git push origin "v$(cat VERSION)"
  gh release create "v$(cat VERSION)" ".renmark/version/$(python -m renmark.release current | sed 's/^/<name>-v/').zip" \
      --title "v$(cat VERSION)" --notes-from-tag
  ```
  (Pushing + publishing a release are shared/remote actions — get explicit user
  approval before running, per the careful-action rule.)
- **No remote or no `gh`** → do NOT fail. Report: *"No GitHub remote/gh detected —
  built local release at `.renmark/version/<name>-v<VERSION>.zip` and tagged
  `v<VERSION>` locally. Add a remote + gh later and re-run [r] to publish."* The
  local snapshot + local tag are a complete release on their own.

**Versioning rule:** snapshot filename, git tag, and GitHub release tag are all
`v<VERSION>` — one version string, three places, never drifting. The same
discipline `renmark.release check` already enforces for the in-repo version files.

## What's next

finish is a **pipeline skill** (class 1). After the chosen branch-close action
(PR / merge / release / nothing) completes:

> *End by calling `renmark.lifecycle.next_steps(repo, "finish")` and render the
> result per `${CLAUDE_PLUGIN_ROOT}/skills/_shared/next-steps.md` (class 1 —
> Tier-0 stage routing). Present via `AskUserQuestion` (handoff-menu.md rules
> 6–9); the state-derived next command is the `(Recommended)` option. Require an
> explicit choice — never auto-proceed.*

For **choosing the next feature to build** (the post-merge / post-release
hand-off), the recommended option is **`/renmark:roadmap` in gap mode** — gap
discovery (PRD-vs-shipped) per the next-step contract's Tiered cost gating, not a
generic "start a new one." `/renmark:start` stays available for blank-slate ideas.
Do not paste the rendering rules — cite the file.

*Mirror any rule changes in `AGENTS.md` in the same commit.*
