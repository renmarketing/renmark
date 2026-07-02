# Finish Lanes — Reference (single source of truth)

**Shared by `/renmark:finish`.** This is the one place the four finish lanes and their per-lane contracts live: what each lane commits to, who should use it, and the default lane by lifecycle stage. Operationalizes cost control (REQ-19) and finish-pipeline discipline. The deterministic source of truth is `renmark/finish_lanes.py` (LANES dict, `recommend_lane`, `lane_table`, `is_renmark_repo`).

---

## The four lanes

| Lane | Merges? | Releases? | Packages? | WSL Install | Verification | Cost | Use case |
|---|---|---|---|---|---|---|---|
| **quick** | No | No | No | No | Confirm existing artifacts | Low | Fast feedback on docs/config changes. No git impact. |
| **release** | Yes* | Yes | No | No | Re-verify + validate release artifacts | Medium | Feature complete, ready to tag. Merge (when approved) + version/changelog/release. |
| **self-update** | Yes* | Yes | Yes | Yes | Re-verify + release QA + CLI/plugin check | High | renmark project ONLY. Full workflow: merge + release + zip package + update WSL install. |
| **full** | Yes* | Yes | Yes | Yes | Full + cross-session validation | High | Explicit-only. Deepest verification tier. |

\* Merge only when approved via `/renmark:approve` gate.

---

## Default lane by lifecycle stage

The `/renmark:finish` skill recommends the cheapest safe lane based on current lifecycle:

| Stage | Recommended lane | Rationale |
|---|---|---|
| `created` (code complete, not yet reviewed) | **quick** | No merge/release yet. Re-verify artifact quality. |
| `reviewed` (code review passed) | **release** (if ready) or **quick** (if more work pending) | Ready to merge/release if approved. |
| `documented` (changelog + docs done) | **release** | Default for shipping a feature. |
| `ready-to-release` | **release** | Ready to merge + tag (WSL install is manual for most projects). |
| renmark project, `ready-to-release` | **self-update** (Recommended) | Renmark on renmark: merge + release + package + WSL. Preserves full workflow. |

---

## Lane details

### quick lane
- **Goal:** Fast feedback on docs/config/small changes.
- **What it does:** Re-verifies existing artifacts, confirms no regressions.
- **What it does NOT do:** No merge, release, packaging, WSL install.
- **Cost:** Low (verification run only).
- **When to use:** Changelog-only, doc updates, typo fixes, config tweaks. No git impact; user merges separately if desired.

### release lane
- **Goal:** Ship a feature or bug fix.
- **What it does:** Merge (when `/renmark:approve` clears it), bump version, update CHANGELOG.md, create GitHub release.
- **What it does NOT do:** Package or WSL install (user can do manually; renmark does not assume bash/zip installed everywhere).
- **Cost:** Medium (re-verify + merge gate + release artifact generation).
- **When to use:** Feature ready to ship, lifecycle at `documented` or `ready-to-release`.

### self-update lane
- **Goal:** Update renmark itself — merge + release + package + install in WSL.
- **What it does:** Everything in `release` lane, PLUS: zip the project (`ai-system-renmark-v<VERSION>-<YYYY-MM-DD>.zip` at `/home/renmark/projects/`), update the WSL Claude Code plugin install (symlink refresh + reload), verify installed CLI/plugin work, clean old worktrees.
- **What it does NOT do:** Update Windows app (separate `~/ai-system` clone; manual `git fetch` + `installed_plugins.json` edit).
- **Cost:** High (release QA + install verification + cleanup).
- **When to use:** ONLY when the project IS renmark. Recommended default for renmark when lifecycle is `ready-to-release`.
- **Preserves full workflow:** The self-update lane does **not** weaken renmark-on-renmark. It automates post-release steps only; it does not skip verification, review, or merge gates.

### full lane
- **Goal:** Deepest verification and cross-session validation (explicit-only).
- **What it does:** Everything in `self-update` lane, PLUS: cross-session smoke tests, artifact deep-inspection, comprehensive changelog audit.
- **Cost:** High (full QA tier).
- **When to use:** Only when explicitly requested. Reserved for major releases or high-risk changes.

---

## Deterministic source of truth

All lane logic lives in `renmark/finish_lanes.py`:

- `LANES` dict: lane name → contract (merges, releases, packages, wsl_install, verifier, cost_band).
- `recommend_lane(lifecycle_stage, is_renmark)` → recommended lane name.
- `lane_table()` → the matrix above (programmatically generated).
- `is_renmark_repo(repo_root)` → boolean (checks for renmark project markers).

When updating lane logic (new lane, changed contract, new stage rules), edit `finish_lanes.py` FIRST, then cite it here.

---

## Examples

**Scenario 1: Doc-only fix (changelog typo).**
- Lifecycle: `documented`
- Recommended lane: `quick` (no merge needed)
- Cost: Low (artifact re-verify only)
- User action: Approve → finish runs quick lane → confirms no regressions → done.

**Scenario 2: Feature ready to ship.**
- Lifecycle: `ready-to-release`
- Project: Normal (not renmark)
- Recommended lane: `release` (merge + tag + release)
- Cost: Medium
- User action: Approve → finish merges + creates release → done.

**Scenario 3: Renmark project, ready to release.**
- Lifecycle: `ready-to-release`
- Project: renmark (detected by `is_renmark_repo`)
- Recommended lane: `self-update` (merge + release + package + WSL install)
- Cost: High
- User action: Approve → finish runs full workflow + verifies CLI/plugin install in WSL → done.

---

## Why a shared file

Finish-lane logic was originally inline in `/renmark:finish` skill, then copied into `/renmark:verify`. Lane contracts drifted: one thought `quick` meant "skip all verification," another added an undocumented `hotfix` lane. Centralizing here means:

- One edit point. Lane contracts are defined once; both finish and verify cite this reference.
- Programmatic source. `renmark/finish_lanes.py` is the canonical truth; this file explains the intent.
- Clear defaults. Users know which lane is recommended before they ask questions.

When citing in a SKILL.md or skill prompt, write:

> *Use the finish lanes in `${CLAUDE_PLUGIN_ROOT}/skills/_shared/finish-lanes.md`: quick (verify only), release (merge+tag), self-update (renmark only: merge+release+package+WSL), full (explicit-only). Consult `renmark.finish_lanes.recommend_lane` for the default by lifecycle stage. Do not invent new lanes.*

Do not paste the lane table into the calling SKILL.md — cite this file.
