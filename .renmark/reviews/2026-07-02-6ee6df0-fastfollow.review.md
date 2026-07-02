OpenAI Codex v0.117.0 (research preview)
--------
[1mworkdir:[0m /home/renmark/projects/ai-system/.claude/worktrees/agency-fastfollow
[1mmodel:[0m gpt-5.4
[1mprovider:[0m openai
[1mapproval:[0m never
[1msandbox:[0m read-only
[1mreasoning effort:[0m none
[1mreasoning summaries:[0m none
[1msession id:[0m 019f24f2-c29f-7912-b4ee-c1d9bcce8017
--------
[36muser[0m
You are reviewing the diff main..HEAD — the Agency Mode "fast-follow" that extends agency-awareness to 5 more pipelines. Emit TWO verdicts.

━━ VERDICT 1 — Spec-compliance ━━
Goal: Extend Agency Mode awareness (already shipped for the spine start/prd/roadmap/finish/resume in v0.30.0) to feature/plan/orchestrate/verify/codereview. Changes: (a) renmark/lifecycle.py renames _AGENCY_SPINE_SKILLS -> _AGENCY_AWARE_SKILLS covering all 10 pipeline skills (back-compat alias kept), so _with_agency_note now surfaces the agency hint for these 5 too when agency is active; (b) a "When Agency Mode is active" block added to each of the 5 SKILL.md (pointer to _shared/agency-delivery.md via ${CLAUDE_PLUGIN_ROOT}, never inline); (c) behavior test updated to assert all 10 gain the hint when active and non-aware skills (debug/audit) stay clean.
Emit exactly one: Spec: compliant | Spec: under-built — <what> | Spec: over-built — <what>

━━ VERDICT 2 — Code-quality ━━
Invariants: (1) agency INACTIVE still leaves skill_preamble byte-identical (no behavior change when off); (2) the back-compat alias _AGENCY_SPINE_SKILLS still resolves; (3) non-agency-aware skills (debug/audit/help/init/etc.) never get the hint even when active; (4) SKILL.md pointers use ${CLAUDE_PLUGIN_ROOT} (portable — NOT absolute /home/... paths that break on Windows). Find any bug, regression, or missed reference (e.g. other code/tests that referenced the old _AGENCY_SPINE_SKILLS name and would break).
For each finding: file:line | severity Critical|Major|Minor|Nit | one-sentence desc | one-sentence fix. Summary counts per severity at top.
Present BOTH verdicts at TOP. Do not modify files. Do not exit until complete.

[1m[33mwarning:[0m[0m Codex could not find system bubblewrap at /usr/bin/bwrap. Please install bubblewrap with your package manager. Codex will use the vendored bubblewrap in the meantime.
[35m[3mcodex[0m[0m
Reviewing `main..HEAD` for the Agency Mode fast-follow. I’m checking the diff, the affected lifecycle/test/skill files, and any remaining references to the old constant name before I issue the two verdicts.
[35m[3mexec[0m[0m
[1m/bin/bash -lc 'git status --short'[0m in /home/renmark/projects/ai-system/.claude/worktrees/agency-fastfollow
[32m succeeded in 0ms:[0m
?? .renmark/reviews/2026-07-02-6ee6df0-fastfollow.review.md

[35m[3mexec[0m[0m
[1m/bin/bash -lc "bash -lc 'if [ -f CHANGELOG.md ]; then tail -n 80 CHANGELOG.md; fi'"[0m in /home/renmark/projects/ai-system/.claude/worktrees/agency-fastfollow
[32m succeeded in 0ms:[0m
- `renmark-execute --roadmap` — prints the status table and writes `roadmap.md` snapshot.
- `renmark-execute --no-commit` — flag added (currently a no-op; v0.1.1 will wire it into the per-task commit code so the skill can batch commits per wave).
- argparse prog name corrected from `nim-execute` to `renmark-execute`.

**Memory templates:**

The eight `.renmark/memory/` files now have proper documentation-grade templates:
- `features.md`, `bugs.md`, `decisions.md` (ADR format), `stack.md`, `architecture.md`, `conventions.md`, `routing.md`, `learnings.md`, plus an auto-maintained `INDEX.md`.

**Plugin manifest now declares 7 skills** (brainstorm, plan, orchestrate, debug, codereview, roadmap, help).

**Tests:** 85 passing (up from 52 in v0.0.3).

**Still pending (v0.1.1+):**
- CLI `execute_plan` actually using `dispatch.group_tasks_by_wave` + `dispatch_wave` (currently the loop still runs single-task serial via the v0.0.x path)
- `--no-commit` wired through per-task commit code
- Cost preview in `--dry-run`
- Routing memory auto-updates from run outcomes
- `/renmark:debug` per-step routing (NIM grep / codex trace / opus reasoning)
- `/renmark:codereview` Sonnet + Opus passes
- Additional native providers (Ollama, OpenRouter, OpenAI-compat) — Phase 4
- ~~LiteLLM plug-in slot — Phase 5~~ (dropped — native providers cover the realistic use cases) (optional)

## v0.0.3 — 2026-05-12 (Phase 1, +memory + help)

**Persistent memory module + `/renmark:help` skill.**

- `renmark/memory.py` — read/write helpers for `.renmark/memory/`. Functions: `ensure_memory(repo)`, `read_index(repo)`, `read_file(repo, name)`, `log_feature(...)`, `log_bug(...)`, `log_decision(...)`, `append_routing(...)`, `append_learning(...)`. Section-aware appends (newest-first per CHANGELOG convention). Lessons in `log_bug` auto-cross-post to `learnings.md`. 8 new tests.
- Memory templates rewritten so the files act as **living documentation**:
  - `features.md` — shipped / in-progress / planned (CHANGELOG style)
  - `bugs.md` — open / fixed with severity, symptom, root cause, fix, lesson
  - `decisions.md` — ADR format (context, decision, alternatives, consequences) with auto-numbered IDs
  - `stack.md` — languages, libs, runtime env, external APIs
  - `architecture.md` — components, data flow, module boundaries, invariants
  - `conventions.md`, `routing.md`, `learnings.md` — auto-tuned + hand-edited
  - `INDEX.md` is a cheap top-of-file index loaded first by every skill
- `/renmark:help` skill (new) — prints all six commands with one-sentence descriptions and the typical workflow order. Pure documentation, no API calls.
- `plugin.json` updated to declare 6 skills.

52 tests total (44 from baseline + 8 memory tests).

## v0.0.2 — 2026-05-12 (Phase 1, partial — skills visible)

**Plugin manifest + all five `/renmark:*` SKILL.md files** so the commands appear in Claude Code's skill list after install. Template files for empty-folder bootstrap. install.sh hardened.

Added:
- `plugin/plugin.json` declaring the 5 skills
- `plugin/skills/{brainstorm,plan,orchestrate,debug,codereview}/SKILL.md` — workflow docs for each
- `plugin/templates/{CLAUDE.md,AGENTS.md,renmark-readme.md,memory/*.md}.template` — what `/renmark:brainstorm` writes when bootstrapping an empty project
- `install.sh` ran successfully — symlinks live at `~/.claude/plugins/renmark` and `~/.local/bin/renmark-execute`

Fixed:
- `install.sh` v0.0.1 stored the /orchestrator backup at `~/.claude/skills/.orchestrator.bak/` — Claude Code's skill discovery picked it up as a phantom skill named `.orchestrator.bak`. **Backup removed entirely**: the orchestrator source still lives in `/home/renmark/projects/ai-inference/` (and in its git history), so a separate copy under `~/.claude/` was just paranoia and bug surface. install.sh now `rm -rf`s the old skill outright; manual revert is `cd ~/projects/ai-inference && bash install.sh` against the v0.2.0 baseline.

Not yet wired (still Phase 1):
- `renmark/dispatch.py` — wave-based parallel dispatcher (so orchestrate can't yet run opus/sonnet tasks or parallel groups)
- `renmark/memory.py` — `.renmark/memory/` reader/writer
- `renmark/providers/claude_agent.py` — Opus/Sonnet via Agent tool from skill side
- Parser extensions for `complexity`, `parallel_group`, `est_tokens`, `est_cost_usd`
- CLI `--no-commit` mode for batched wave commits
- Cost preview in `--dry-run`
- Empty-folder bootstrap code (skill docs reference it but the brainstorm skill currently does it by hand)

The skills are visible and `/renmark:brainstorm` + `/renmark:plan` are workable today (they're Opus-driven conversations). `/renmark:orchestrate` runs the same single-task path the v0.0.1 baseline supports.

## v0.0.1 — 2026-05-12 (Phase 0)

**Bootstrap of the new `ai-system` repo.** Copies the working v0.2.0 baseline from `/home/renmark/projects/ai-inference/` and retargets the Python package from `nim_execute` to `renmark`.

Changes vs. ai-inference v0.2.0:

- Package renamed `nim_execute` → `renmark`
- `nim_client.py` → `renmark/providers/nim.py`
- `codex_exec.py` → `renmark/providers/codex.py`
- New `renmark/providers/__init__.py` with `PROVIDERS` registry stub
- Runtime state dir renamed `.nim-state/` → `.renmark/state/` (with `RENMARK_DIR_NAME`, `STATE_SUBDIR`, `MEMORY_SUBDIR`, `DEBUG_SUBDIR` constants; legacy `STATE_DIR_NAME` aliased for back-compat)
- All test imports updated, 41 tests still passing
- CLI references `renmark-execute` / `.renmark/state/` in user-facing strings

Phase 1 (next): the five `/renmark:*` skills, `plugin/plugin.json`, dispatch layer, memory module, empty-folder bootstrap. See `PLAN.md`.

[35m[3mexec[0m[0m
[1m/bin/bash -lc 'git diff --stat main..HEAD'[0m in /home/renmark/projects/ai-system/.claude/worktrees/agency-fastfollow
[32m succeeded in 0ms:[0m
 CHANGELOG.md                       |  9 +++++++++
 plugin/skills/codereview/SKILL.md  |  2 ++
 plugin/skills/feature/SKILL.md     |  4 ++++
 plugin/skills/orchestrate/SKILL.md |  4 ++++
 plugin/skills/plan/SKILL.md        |  4 ++++
 plugin/skills/verify/SKILL.md      |  4 ++++
 renmark/lifecycle.py               | 22 ++++++++++++++++------
 tests/test_agency_behavior.py      | 38 ++++++++++++++++++++++++++++----------
 8 files changed, 71 insertions(+), 16 deletions(-)

[35m[3mexec[0m[0m
[1m/bin/bash -lc 'git diff --name-only main..HEAD'[0m in /home/renmark/projects/ai-system/.claude/worktrees/agency-fastfollow
[32m succeeded in 0ms:[0m
CHANGELOG.md
plugin/skills/codereview/SKILL.md
plugin/skills/feature/SKILL.md
plugin/skills/orchestrate/SKILL.md
plugin/skills/plan/SKILL.md
plugin/skills/verify/SKILL.md
renmark/lifecycle.py
tests/test_agency_behavior.py

[35m[3mcodex[0m[0m
The diff is small and localized. Next I’m reading the changed hunks and grepping for any stale `_AGENCY_SPINE_SKILLS` references or hard-coded skill-path strings that would violate the portability invariant.
[35m[3mexec[0m[0m
[1m/bin/bash -lc 'git diff main..HEAD -- renmark/lifecycle.py tests/test_agency_behavior.py plugin/skills/feature/SKILL.md plugin/skills/plan/SKILL.md plugin/skills/orchestrate/SKILL.md plugin/skills/verify/SKILL.md plugin/skills/codereview/SKILL.md CHANGELOG.md'[0m in /home/renmark/projects/ai-system/.claude/worktrees/agency-fastfollow
[32m succeeded in 0ms:[0m
diff --git a/CHANGELOG.md b/CHANGELOG.md
index 21a4ef1..a419b14 100644
--- a/CHANGELOG.md
+++ b/CHANGELOG.md
@@ -1,5 +1,14 @@
 # Changelog
 
+## [2026-07-02] — Agency Mode fast-follow (full pipeline coverage)
+**Request:** Extend Agency Mode awareness to the 5 pipelines the v0.30.0 walking-skeleton MVP deferred (feature, plan, orchestrate, verify, codereview) so the whole delivery loop is agency-aware.
+**Built:**
+- `renmark/lifecycle.py` — `_AGENCY_SPINE_SKILLS` → `_AGENCY_AWARE_SKILLS` (now all 10 pipeline skills; back-compat alias kept). `_with_agency_note` surfaces the agency hint for the newly-covered pipelines when agency is active.
+- Agency blocks added to `plugin/skills/{feature,plan,orchestrate,verify,codereview}/SKILL.md` — each referencing `_shared/agency-delivery.md` by pointer (never inline): feature=select-next-milestone + PRD-alignment + no drift; plan=atomic tasks + milestone acceptance criteria + cost preview; orchestrate=background agents + continue-until-checkpoint + progress summaries; verify=tests/browser + demo-readiness + unverified; codereview=full review before signoff + merge readiness.
+- `tests/test_agency_behavior.py` — asserts all 10 pipeline skills gain the hint when active; non-aware skills (debug/audit) stay clean; inactive path still byte-identical.
+**Files changed:** renmark/lifecycle.py, 5 SKILL.md, tests/test_agency_behavior.py, CHANGELOG.md.
+**Do not change:** agency hint only for `_AGENCY_AWARE_SKILLS`; inactive path byte-identical; bodies load on demand (pointer only); reuses cost-control/finish-lanes/deterministic-first infra.
+
 ## [2026-07-02] — v0.30.0 — Agency Mode (walking-skeleton MVP)
 **Release.** Bumps v0.29.0 → v0.30.0. Ships **Agency Mode** (REQ-22) — an OPTIONAL
 higher-level project-delivery workflow ABOVE Conductor/Orchestrator (does not replace
diff --git a/plugin/skills/codereview/SKILL.md b/plugin/skills/codereview/SKILL.md
index 8572b3d..679bc43 100644
--- a/plugin/skills/codereview/SKILL.md
+++ b/plugin/skills/codereview/SKILL.md
@@ -75,6 +75,8 @@ tier-override flag:
 - **`standard` / `full` tier, OR `--full` on any tier** → run the full codex pass
   below.
 
+**When Agency Mode is active:** codereview runs a full review before each milestone signoff, reports both merge-readiness and risk findings, and gates the owner signoff on review verdict. The review blocks premature "done" declarations until findings are addressed. See the Agency Mode contract at `${CLAUDE_PLUGIN_ROOT}/skills/_shared/agency-delivery.md` for gating rules and escalation conditions. When Agency Mode is off, existing codereview behavior is unchanged.
+
 **Adversarial escalation (REQ-2 — highest-stakes diffs only).** For release-gating,
 security-sensitive, or engine/state code, adversarial verification subagents MAY be
 dispatched on `fable` (Agent tool, `model: "fable"`) to attempt to refute the review's
diff --git a/plugin/skills/feature/SKILL.md b/plugin/skills/feature/SKILL.md
index 48f785b..a584f6e 100644
--- a/plugin/skills/feature/SKILL.md
+++ b/plugin/skills/feature/SKILL.md
@@ -29,6 +29,10 @@ full signals (lite must never skip the full review on a risky change).
 
 `feature` defaults to **Orchestrator** mode: execute at the goal level, dispatching narrow scoped subagents where useful. In **Conductor** mode, keep each change single-file/tight and explain the next move before editing. The mode is selected once (ask-once) and persisted; override it durably via `renmark-execute --set-mode`.
 
+## When Agency Mode is active
+
+In Agency Mode, **feature selects the next milestone/feature from the roadmap** rather than treating each feature request as an isolated change. The PRD-alignment check (Step 2) runs against the selected milestone, and scope drift is surfaced immediately — feedback that changes scope updates the roadmap and PRD rather than silently expanding the feature. See `${CLAUDE_PLUGIN_ROOT}/skills/_shared/agency-delivery.md` for the full delivery contract.
+
 ## When to Use
 
 - New functionality that warrants isolation before merging
diff --git a/plugin/skills/orchestrate/SKILL.md b/plugin/skills/orchestrate/SKILL.md
index 4275653..5c244fa 100644
--- a/plugin/skills/orchestrate/SKILL.md
+++ b/plugin/skills/orchestrate/SKILL.md
@@ -28,6 +28,10 @@ After each wave, the skill writes `.renmark/state/wave-summaries/wave-N.json` (t
 
 **Orchestrator** is orchestrate's default: dispatch parallel scoped subagents, offload bulk/single-file emissions to Codex, and advance on reviewed PASS/FAIL outcomes. In **Conductor** mode, prefer serial single-task execution with tighter user checkpoints between tasks. Either mode keeps the G11 isolation/aggregation contract above unchanged.
 
+## When Agency Mode is active
+
+In Agency Mode, orchestrate runs tasks via scoped background agents and advances to the next milestone **checkpoint** rather than halting after each task. The owner agent continues coordination while background agents execute in parallel; progress emits compact summaries only. See `${CLAUDE_PLUGIN_ROOT}/skills/_shared/agency-delivery.md` for the delivery contract. When Agency is off, orchestrate behaves as above — no changes to isolation or task dispatch.
+
 ## When to Use
 
 - User has a `.renmark/plans/*.plan.md` file ready and wants it executed
diff --git a/plugin/skills/plan/SKILL.md b/plugin/skills/plan/SKILL.md
index 523d190..039e61a 100644
--- a/plugin/skills/plan/SKILL.md
+++ b/plugin/skills/plan/SKILL.md
@@ -31,6 +31,10 @@ The plan is consumed by `/renmark:orchestrate`.
 - Without a spec or clear feature description — route to `/renmark:brainstorm` first
 - For executing — that's `/renmark:orchestrate`
 
+## When Agency Mode is active
+
+In Agency Mode, `plan` decomposes the assigned **milestone** (not the full PRD) into atomic tasks, attaches the milestone's **acceptance criteria** as the verifier success target (what "done + demo-ready" means for the owner), and **always displays a cost preview before dispatch**. Reference the full agency delivery contract by pointer only — `${CLAUDE_PLUGIN_ROOT}/skills/_shared/agency-delivery.md`. This behavior is additive; existing plan behavior is unchanged when agency is off.
+
 ## Steps
 
 **Step 0a — Context check.** Call `lifecycle.skill_preamble(repo, 'plan')`. If it returns a non-None hint, surface as a one-line note.
diff --git a/plugin/skills/verify/SKILL.md b/plugin/skills/verify/SKILL.md
index 137b089..f8bbad2 100644
--- a/plugin/skills/verify/SKILL.md
+++ b/plugin/skills/verify/SKILL.md
@@ -52,6 +52,10 @@ In projects where `capabilities.top_tier == "fable"` (per `renmark.capabilities.
 
 State it plainly: **deterministic smoke remains the always-run default** — the fable pass is additive and never replaces verifiers (REQ-7).
 
+## When Agency Mode is active
+
+In Agency Mode, verify escalates from feature-level smoke to milestone-readiness assessment. Runs smoke tests plus browser QA (`--qa`) / edge-case checks (`--deep-qa`) when the milestone surfaces user-visible behavior. Reports DEMO-readiness against the milestone acceptance criteria (what passed, what remains unverified, confidence level) and feeds the owner's signoff checkpoint. See contract pointer: `${CLAUDE_PLUGIN_ROOT}/skills/_shared/agency-delivery.md`. Additive — existing verify behavior unchanged when agency is off.
+
 ## When to Use
 
 - **Automatically by `/renmark:orchestrate`** after a fully clean run (v0.3.3+) — orchestrate clears pipeline state, sets stage `created`, then invokes this. You rarely run it by hand.
diff --git a/renmark/lifecycle.py b/renmark/lifecycle.py
index a08b59f..03afc6f 100644
--- a/renmark/lifecycle.py
+++ b/renmark/lifecycle.py
@@ -727,11 +727,20 @@ def _with_mode_note(repo: Path | str, skill: str, hint: str | None) -> str | Non
     return line if hint is None else f"{hint} | {line}"
 
 
-# Spine skills that receive an Agency Mode hint when agency is active.
-_AGENCY_SPINE_SKILLS: frozenset[str] = frozenset(
-    {"start", "prd", "roadmap", "finish", "resume"}
+# Pipeline skills that receive an Agency Mode hint when agency is active.
+# v0.30.0 shipped the spine (start/prd/roadmap/finish/resume); the fast-follow
+# extends coverage to the remaining pipelines (feature/plan/orchestrate/verify/
+# codereview) so the whole delivery loop is agency-aware.
+_AGENCY_AWARE_SKILLS: frozenset[str] = frozenset(
+    {
+        "start", "prd", "roadmap", "finish", "resume",
+        "feature", "plan", "orchestrate", "verify", "codereview",
+    }
 )
 
+# Back-compat alias: the original spine-only name still resolves.
+_AGENCY_SPINE_SKILLS: frozenset[str] = _AGENCY_AWARE_SKILLS
+
 # Marker string used to identify the agency hint line — load-bearing for
 # behavior tests (T15): assert active preamble contains this prefix and
 # inactive preamble does NOT.
@@ -741,8 +750,9 @@ _AGENCY_HINT_MARKER: str = "Agency Mode active"
 def _with_agency_note(repo: Path | str, skill: str, hint: str | None) -> str | None:
     """ADDITIVE: append an Agency Mode hint to ``hint`` when agency is active.
 
-    Only surfaces the hint for SPINE skills (start, prd, roadmap, finish,
-    resume) — all other skills are passed through unchanged regardless of
+    Only surfaces the hint for AGENCY-AWARE pipeline skills (the spine —
+    start/prd/roadmap/finish/resume — plus feature/plan/orchestrate/verify/
+    codereview) — all other skills are passed through unchanged regardless of
     agency state.
 
     When agency is INACTIVE the return value is byte-identical to ``hint``
@@ -753,7 +763,7 @@ def _with_agency_note(repo: Path | str, skill: str, hint: str | None) -> str | N
     Follows the same additive pattern as :func:`_with_mode_note` and
     :func:`_with_headless_note`.
     """
-    if skill not in _AGENCY_SPINE_SKILLS:
+    if skill not in _AGENCY_AWARE_SKILLS:
         return hint
     try:
         from . import agency as _agency
diff --git a/tests/test_agency_behavior.py b/tests/test_agency_behavior.py
index dc58fc3..a5185ed 100644
--- a/tests/test_agency_behavior.py
+++ b/tests/test_agency_behavior.py
@@ -62,13 +62,31 @@ def test_inactive_agency_note_is_byte_identical_passthrough(tmp_path: Path) -> N
         assert lifecycle._with_agency_note(tmp_path, skill, None) is None
 
 
-def test_agency_note_noop_for_nonspine_even_when_active(tmp_path: Path) -> None:
-    """Non-spine skills are passed through unchanged even when agency is ACTIVE."""
+def test_agency_note_noop_for_nonaware_even_when_active(tmp_path: Path) -> None:
+    """Skills NOT in the agency-aware set pass through unchanged even when active.
+
+    (debug/audit are non-pipeline skills — they never get an agency hint.)"""
     _init_state_dir(tmp_path)
     agency.activate(tmp_path, current_phase="alpha", current_milestone="M1")
     sentinel = "SENTINEL-preamble-xyz"
-    assert lifecycle._with_agency_note(tmp_path, "orchestrate", sentinel) == sentinel
-    assert lifecycle._with_agency_note(tmp_path, "debug", None) is None
+    assert "debug" not in lifecycle._AGENCY_AWARE_SKILLS
+    assert lifecycle._with_agency_note(tmp_path, "debug", sentinel) == sentinel
+    assert lifecycle._with_agency_note(tmp_path, "audit", None) is None
+
+
+def test_all_pipeline_skills_gain_hint_when_active(tmp_path: Path) -> None:
+    """Fast-follow: every agency-aware pipeline skill — the spine PLUS
+    feature/plan/orchestrate/verify/codereview — surfaces the agency hint +
+    fragment pointer when agency is active."""
+    _init_state_dir(tmp_path)
+    agency.activate(tmp_path, current_phase="alpha", current_milestone="M1")
+    pointer = context.fragment_pointer("agency-delivery")
+    for skill in ("feature", "plan", "orchestrate", "verify", "codereview"):
+        note = lifecycle._with_agency_note(tmp_path, skill, None)
+        assert note is not None and lifecycle._AGENCY_HINT_MARKER in note, (
+            f"{skill} did not gain the agency hint when active: {note!r}"
+        )
+        assert pointer in note, f"{skill} note missing fragment pointer: {note!r}"
 
 
 # ── 2. Active spine preamble gains the hint ────────────────────────────────────
@@ -97,19 +115,19 @@ def test_active_spine_preamble_gains_hint(tmp_path: Path) -> None:
 # ── 3. Active non-spine preamble stays clean ──────────────────────────────────
 
 
-def test_active_nonspine_preamble_stays_clean(tmp_path: Path) -> None:
-    """With agency active, a NON-spine skill ('orchestrate') preamble must NOT
+def test_active_nonaware_preamble_stays_clean(tmp_path: Path) -> None:
+    """With agency active, a NON-agency-aware skill ('debug') preamble must NOT
     contain the agency hint marker."""
     _init_state_dir(tmp_path)
     agency.activate(tmp_path, current_phase="beta", current_milestone="M2")
 
-    # 'orchestrate' is NOT in _AGENCY_SPINE_SKILLS
-    assert "orchestrate" not in lifecycle._AGENCY_SPINE_SKILLS
+    # 'debug' is NOT in the agency-aware pipeline set
+    assert "debug" not in lifecycle._AGENCY_AWARE_SKILLS
 
-    result = lifecycle.skill_preamble(tmp_path, "orchestrate")
+    result = lifecycle.skill_preamble(tmp_path, "debug")
     if result is not None:
         assert lifecycle._AGENCY_HINT_MARKER not in result, (
-            f"Agency hint leaked into non-spine skill 'orchestrate': {result!r}"
+            f"Agency hint leaked into non-aware skill 'debug': {result!r}"
         )
 
 

[35m[3mexec[0m[0m
[1m/bin/bash -lc "rg -n \"_AGENCY_SPINE_SKILLS|_AGENCY_AWARE_SKILLS|agency-delivery\\.md|CLAUDE_PLUGIN_ROOT|skill_preamble\\(\" -S"[0m in /home/renmark/projects/ai-system/.claude/worktrees/agency-fastfollow
[32m succeeded in 0ms:[0m
CLAUDE.md:33:Agency Mode is an OPTIONAL higher-level project-delivery workflow that sits ABOVE Conductor and Orchestrator and does NOT replace them — it drives Orchestrator internally. Explicit opt-in via `/renmark:start` (never auto-detected). It runs the owner-facing delivery loop: discovery → PRD agreement → tech-stack recommendation → roadmap/milestones → build → demo/feedback → verification → signoff → release, pausing at milestone checkpoints for owner signoff. Lightweight resumable state lives in `.renmark/state/agency.json` (`renmark/agency.py`); the agency contract loads on demand from `${CLAUDE_PLUGIN_ROOT}/skills/_shared/agency-delivery.md` (never eager). Reuses — never re-implements — cost-control / finish-lanes / deterministic-first infra.
CLAUDE.md:65:renmark separates working context into four kinds: **static** (always-present `CLAUDE.md`/`AGENTS.md` rules), **dynamic** (skill bodies + `_shared/*.md` fragments — metadata upfront, full bodies loaded ONLY on demand), **memory** (`.renmark/memory/*`, durable across `/clear`), and **task-local** (the per-subagent dispatch packet, ephemeral). Skill/fragment metadata is exposed cheaply upfront via the `skillmeta` registry; bodies load on demand via `renmark/context.py` (`load_skill_body` / `load_fragment`) — dynamic bodies are never pre-loaded into the orchestrator. The production dispatch packet (`renmark.dispatch.build_subagent_input`) carries required-skill **metadata only** (name + pointer), never full skill bodies, guarded by `assert_metadata_only` in `renmark/context.py`. See `${CLAUDE_PLUGIN_ROOT}/skills/_shared/context-taxonomy.md`. Operationalizes REQ-5 context hygiene (REQ-20).
CLAUDE.md:102:(`~/.claude/plugins/...`, `${CLAUDE_PLUGIN_ROOT}`), `$HOME`, and anything above
CLAUDE.md:156:- **Cross-domain transition:** recommend `/clear` (memory survives). The %-side is enforced by orchestrator self-monitoring; the cross-domain side is automated via `renmark.lifecycle.skill_preamble(repo, skill)` (resolves domain from `DOMAIN_BY_SKILL`, runs `context_budget_check`, returns the hint).
AGENTS.md:29:renmark separates working context into four kinds: **static** (always-present `CLAUDE.md`/`AGENTS.md` rules), **dynamic** (skill bodies + `_shared/*.md` fragments — metadata upfront, full bodies loaded ONLY on demand), **memory** (`.renmark/memory/*`, durable across `/clear`), and **task-local** (the per-subagent dispatch packet, ephemeral). Skill/fragment metadata is exposed cheaply upfront via the `skillmeta` registry; bodies load on demand via `renmark/context.py` (`load_skill_body` / `load_fragment`) — dynamic bodies are never pre-loaded into the orchestrator. The production dispatch packet (`renmark.dispatch.build_subagent_input`) carries required-skill **metadata only** (name + pointer), never full skill bodies, guarded by `assert_metadata_only` in `renmark/context.py`. See `${CLAUDE_PLUGIN_ROOT}/skills/_shared/context-taxonomy.md`. Operationalizes REQ-5 context hygiene (REQ-20).
AGENTS.md:45:**All renmark output stays inside the project.** Every file renmark generates MUST be written inside this project, under `.renmark/` or a project-root doc. Canonical homes: specs→`.renmark/specs/`, plans→`.renmark/plans/`, reviews/verification→`.renmark/reviews/`, research→`.renmark/research/`, runtime→`.renmark/state/`, memory→`.renmark/memory/`, logs→`.renmark/logs/`, debug→`.renmark/debug/<session-id>/`, audits→`.renmark/audits/`. **Never write outside the project** — the global plugin install (`~/.claude/plugins/...`, `${CLAUDE_PLUGIN_ROOT}`), `$HOME`, and anything above the project root are read-only. Reading FROM the plugin dir is fine. See `CLAUDE.md` § `project-write-boundary-rule`.
AGENTS.md:93:Agency Mode is an OPTIONAL higher-level project-delivery workflow that sits ABOVE Conductor and Orchestrator and does NOT replace them — it drives Orchestrator internally. Explicit opt-in via `/renmark:start` (never auto-detected). It runs the owner-facing delivery loop: discovery → PRD agreement → tech-stack recommendation → roadmap/milestones → build → demo/feedback → verification → signoff → release, pausing at milestone checkpoints for owner signoff. Lightweight resumable state lives in `.renmark/state/agency.json` (`renmark/agency.py`); the agency contract loads on demand from `${CLAUDE_PLUGIN_ROOT}/skills/_shared/agency-delivery.md` (never eager). Reuses — never re-implements — cost-control / finish-lanes / deterministic-first infra.
plugin/templates/CLAUDE.md.template:86:(`~/.claude/plugins/...`, `${CLAUDE_PLUGIN_ROOT}`), `$HOME`, and anything above
plugin/templates/CLAUDE.md.template:140:- **Cross-domain transition:** recommend `/clear` (memory survives). The %-side is enforced by orchestrator self-monitoring; the cross-domain side is automated via `renmark.lifecycle.skill_preamble(repo, skill)` (resolves domain from `DOMAIN_BY_SKILL`, runs `context_budget_check`, returns the hint).
plugin/templates/AGENTS.md.template:42:**All renmark output stays inside the project.** Specs, plans, reviews, research, logs, memory — everything goes under this project's `.renmark/` subtree or a project-root doc. Never write to the global plugin install (`${CLAUDE_PLUGIN_ROOT}`, `~/.claude/...`), `$HOME`, or above the project root. Reading templates/reference files from the plugin is fine; the install is read-only. See `CLAUDE.md` § `project-write-boundary-rule`.
renmark/behavior.py:433:def _render_skill_preamble(repo: Path, case: Case) -> str:
renmark/behavior.py:434:    """Render ``lifecycle.skill_preamble(repo, skill)`` to text (empty if None)."""
renmark/behavior.py:437:    hint = lifecycle.skill_preamble(repo, case.skill)
renmark/lifecycle.py:602:def skill_preamble(repo: Path | str, skill: str) -> str | None:
renmark/lifecycle.py:734:_AGENCY_AWARE_SKILLS: frozenset[str] = frozenset(
renmark/lifecycle.py:742:_AGENCY_SPINE_SKILLS: frozenset[str] = _AGENCY_AWARE_SKILLS
renmark/lifecycle.py:766:    if skill not in _AGENCY_AWARE_SKILLS:
renmark/skillgen.py:5:(``${CLAUDE_PLUGIN_ROOT}/skills/_shared/<name>.md``). There is therefore no
tests/test_context.py:112:        == "${CLAUDE_PLUGIN_ROOT}/skills/plan/SKILL.md"
tests/test_context.py:172:    assert skill_refs[0]["pointer"] == "${CLAUDE_PLUGIN_ROOT}/skills/plan/SKILL.md"
tests/test_lint.py:73:        f"## What's next\nSee `${{CLAUDE_PLUGIN_ROOT}}/skills/_shared/next-steps.md`.\n"
tests/test_lint.py:80:        f"Read ${{CLAUDE_PLUGIN_ROOT}}/skills/{name}/SKILL.md and follow its instructions.\n"
tests/test_lint.py:157:        "---\ndescription: wrong\n---\n\nRead ${CLAUDE_PLUGIN_ROOT}/skills/elsewhere/SKILL.md — wrong target.\n"
tests/test_lifecycle.py:281:    hint = lifecycle.skill_preamble(tmp_path, "brainstorm")
tests/test_lifecycle.py:291:    hint = lifecycle.skill_preamble(tmp_path, "verify")
tests/test_lifecycle.py:301:    hint = lifecycle.skill_preamble(tmp_path, "brainstorm")
tests/test_lifecycle.py:314:    hint = lifecycle.skill_preamble(tmp_path, "brainstorm")
tests/test_lifecycle.py:323:    lifecycle.skill_preamble(tmp_path, "debug")
tests/test_lifecycle.py:325:    hint = lifecycle.skill_preamble(tmp_path, "brainstorm")
tests/test_lifecycle.py:538:    lifecycle.skill_preamble(tmp_path, "debug")
tests/test_lifecycle.py:540:    assert lifecycle.skill_preamble(tmp_path, "resume") is None
tests/test_lifecycle.py:549:    lifecycle.skill_preamble(tmp_path, "debug")
tests/test_lifecycle.py:550:    lifecycle.skill_preamble(tmp_path, "resume")
tests/test_lifecycle.py:560:    lifecycle.skill_preamble(tmp_path, "debug")
tests/test_lifecycle.py:562:    hint = lifecycle.skill_preamble(tmp_path, "audit")
tests/test_lifecycle.py:590:    lifecycle.skill_preamble(tmp_path, "orchestrate")  # A: records build
tests/test_lifecycle.py:591:    assert lifecycle.skill_preamble(tmp_path, "resume") is None  # B: minimal, records meta
tests/test_lifecycle.py:592:    hint = lifecycle.skill_preamble(tmp_path, "feature")  # C: must see B (meta)
tests/test_lifecycle.py:652:    hint = lifecycle.skill_preamble(tmp_path, "feature")
tests/test_lifecycle.py:670:    conductor_hint = lifecycle.skill_preamble(tmp_path, "feature")
tests/test_lifecycle.py:673:    orchestrator_hint = lifecycle.skill_preamble(tmp_path, "feature")
tests/test_lifecycle.py:688:    hint = lifecycle.skill_preamble(tmp_path, "feature")
tests/test_lifecycle.py:702:    hint = lifecycle.skill_preamble(tmp_path, "help")
tests/test_lifecycle.py:723:    hint = lifecycle.skill_preamble(tmp_path, "feature")
tests/test_lifecycle.py:736:    hint = lifecycle.skill_preamble(tmp_path, "orchestrate")
tests/test_lifecycle.py:747:    hint = lifecycle.skill_preamble(tmp_path, "orchestrate")
renmark/dispatch.py:225:    metadata references (name + ``${CLAUDE_PLUGIN_ROOT}`` pointer + non-body
renmark/context.py:273:    The literal ``${CLAUDE_PLUGIN_ROOT}/skills/<name>/SKILL.md`` — the reference
renmark/context.py:276:    return f"${{CLAUDE_PLUGIN_ROOT}}/skills/{name}/SKILL.md"
renmark/context.py:281:    return f"${{CLAUDE_PLUGIN_ROOT}}/skills/_shared/{name}.md"
tests/test_agency_behavior.py:5:- Spine vs non-spine routing (_AGENCY_SPINE_SKILLS)
tests/test_agency_behavior.py:37:    """With agency inactive (fresh tmp repo), skill_preamble('start') must NOT
tests/test_agency_behavior.py:43:    result = lifecycle.skill_preamble(tmp_path, "start")
tests/test_agency_behavior.py:59:    for skill in sorted(lifecycle._AGENCY_SPINE_SKILLS):
tests/test_agency_behavior.py:72:    assert "debug" not in lifecycle._AGENCY_AWARE_SKILLS
tests/test_agency_behavior.py:97:    skill_preamble(repo, 'start') must contain the marker AND the fragment pointer."""
tests/test_agency_behavior.py:101:    result = lifecycle.skill_preamble(tmp_path, "start")
tests/test_agency_behavior.py:125:    assert "debug" not in lifecycle._AGENCY_AWARE_SKILLS
tests/test_agency_behavior.py:127:    result = lifecycle.skill_preamble(tmp_path, "debug")
tests/test_agency_behavior.py:141:    Loads the real agency-delivery.md body from the live plugin dir to pick a
tests/test_agency_behavior.py:148:    result = lifecycle.skill_preamble(tmp_path, "start")
plugin/skills/loop/SKILL.md:53:**Step 0 — Context check.** Call `lifecycle.skill_preamble(repo, 'loop')`. If it returns a
plugin/skills/loop/SKILL.md:268:result per `${CLAUDE_PLUGIN_ROOT}/skills/_shared/next-steps.md` (class 1 —
CHANGELOG.md:6:- `renmark/lifecycle.py` — `_AGENCY_SPINE_SKILLS` → `_AGENCY_AWARE_SKILLS` (now all 10 pipeline skills; back-compat alias kept). `_with_agency_note` surfaces the agency hint for the newly-covered pipelines when agency is active.
CHANGELOG.md:7:- Agency blocks added to `plugin/skills/{feature,plan,orchestrate,verify,codereview}/SKILL.md` — each referencing `_shared/agency-delivery.md` by pointer (never inline): feature=select-next-milestone + PRD-alignment + no drift; plan=atomic tasks + milestone acceptance criteria + cost preview; orchestrate=background agents + continue-until-checkpoint + progress summaries; verify=tests/browser + demo-readiness + unverified; codereview=full review before signoff + merge readiness.
CHANGELOG.md:10:**Do not change:** agency hint only for `_AGENCY_AWARE_SKILLS`; inactive path byte-identical; bodies load on demand (pointer only); reuses cost-control/finish-lanes/deterministic-first infra.
CHANGELOG.md:22:- `plugin/skills/_shared/agency-delivery.md` — shared agency delivery contract, loaded ON
CHANGELOG.md:26:  inactive (`_with_agency_note`, `_AGENCY_SPINE_SKILLS`, `_AGENCY_HINT_MARKER`).
CHANGELOG.md:32:**Files changed:** renmark/agency.py (new), plugin/skills/_shared/agency-delivery.md (new),
CHANGELOG.md:38:`lifecycle._AGENCY_SPINE_SKILLS`. Reuses cost-control/finish-lanes/deterministic-first infra.
CHANGELOG.md:53:**MVP boundary (walking skeleton):** agency state (`renmark/agency.py` + `.renmark/state/agency.json`) + shared `agency-delivery.md` fragment (loaded on demand) + mode-conditioned preamble + agency-aware CORE SPINE only (start → prd → roadmap → finish → resume) + behavior tests + help/docs.
CHANGELOG.md:231:- Reference-dir fragment: skills cite it via `${CLAUDE_PLUGIN_ROOT}/skills/_shared/context-taxonomy.md`, never re-inline it (skillgen doc-slimming guard).
CHANGELOG.md:2693:- **renmark must never write outside the project.** All specs, plans, reviews, research, logs, and memory go under the project's `.renmark/` subtree (or project-root docs). The global plugin install (`${CLAUDE_PLUGIN_ROOT}`, `~/.claude/...`) is read-only — reading templates/reference files from it is fine, writing to it is forbidden. Codified as `project-write-boundary-rule` in `CLAUDE.md.template` and mirrored in `AGENTS.md.template`.
CHANGELOG.md:2707:- **Step-0 boilerplate consolidated** — new `lifecycle.skill_preamble(repo, skill)` replaces the duplicated `context_budget_check` + `record_skill_invocation` block across all 14 SKILL.md files. Domain resolves centrally from `DOMAIN_BY_SKILL`, so per-skill drift is impossible.
renmark/hygiene.py:310:        hint = lifecycle.skill_preamble(repo, "hygiene")
tests/test_audit.py:47:        f"See `${{CLAUDE_PLUGIN_ROOT}}/skills/_shared/next-steps.md`.\n"
plugin/skills/hygiene/SKILL.md:27:**Step 0 — Context check.** Call `lifecycle.skill_preamble(repo, 'hygiene')`. Hygiene is `meta` domain; cross-domain prompts only fire on transitions FROM `build` / `debug` / `audit`. Surface the returned hint if non-None.
plugin/skills/hygiene/SKILL.md:67:> `${CLAUDE_PLUGIN_ROOT}/skills/_shared/next-steps.md` (class 3 — resume-pipeline
plugin/skills/plan/SKILL.md:36:In Agency Mode, `plan` decomposes the assigned **milestone** (not the full PRD) into atomic tasks, attaches the milestone's **acceptance criteria** as the verifier success target (what "done + demo-ready" means for the owner), and **always displays a cost preview before dispatch**. Reference the full agency delivery contract by pointer only — `${CLAUDE_PLUGIN_ROOT}/skills/_shared/agency-delivery.md`. This behavior is additive; existing plan behavior is unchanged when agency is off.
plugin/skills/plan/SKILL.md:40:**Step 0a — Context check.** Call `lifecycle.skill_preamble(repo, 'plan')`. If it returns a non-None hint, surface as a one-line note.
plugin/skills/plan/SKILL.md:64:**Discovery flow** — ask at most 3 questions, one at a time. See `${CLAUDE_PLUGIN_ROOT}/skills/_shared/scope-contract.md` (the single source of truth shared with `/renmark:brainstorm`) for the full Q1–Q3 question text, stack inference rules, and option menus. Do not decompose until discovery is complete.
plugin/skills/plan/SKILL.md:78:**Record decisions.** See `${CLAUDE_PLUGIN_ROOT}/skills/_shared/scope-contract.md` for the CHANGELOG scope entry format and `stack.md` template. Write both before decomposing (skip if brainstorm already wrote them — they're the shared contract). The generated task plan must respect all locked decisions — do not introduce new major stack choices during decomposition unless the user asks.
plugin/skills/plan/SKILL.md:94:**Reuse check — before decomposition (don't re-decompose an existing build).** Before splitting the spec into a custom task list, dispatch the reuse-check subagent from `${CLAUDE_PLUGIN_ROOT}/skills/_shared/reuse-check.md`: Agent tool call (`model: haiku`; `sonnet` for a large search surface), passing ONLY `request_description`. The subagent searches loaded skills/commands, session MCP tools, `.renmark/specs/` + `.renmark/plans/`, and `.renmark/memory/features.md` in its own context, and returns ONLY the ≤5-line `reuse: found | none` verdict (+ a one-line pointer when found). On `reuse: found`, surface the `pointer` and **default to reuse** — recommend the existing skill / MCP tool / spec / feature instead of re-decomposing a custom build, unless there is a clear, stated reason it doesn't fit. Do NOT read the searched bodies in the orchestrator context (REQ-5).
plugin/skills/plan/SKILL.md:226:`${CLAUDE_PLUGIN_ROOT}/skills/_shared/next-steps.md`:
plugin/skills/plan/SKILL.md:229:> result per `${CLAUDE_PLUGIN_ROOT}/skills/_shared/next-steps.md` (class 1 —
plugin/skills/check-plan/SKILL.md:38:**Step 0 — Context check.** Call `lifecycle.skill_preamble(repo, 'check-plan')`. If it returns a non-None hint, surface as a one-line note.
plugin/skills/check-plan/SKILL.md:100:> result per `${CLAUDE_PLUGIN_ROOT}/skills/_shared/next-steps.md` (class 1 —
plugin/skills/blueprint/SKILL.md:38:**Step 0 — Context check.** Call `lifecycle.skill_preamble(repo, 'blueprint')`. If it returns a non-None hint, surface it as a one-line note. Do NOT block — the user decides whether to `/compact` or `/clear`.
plugin/skills/blueprint/SKILL.md:105:1. **Root file absent** → create it from the template (`${CLAUDE_PLUGIN_ROOT}/templates/SCHEMATIC.md.template` / `${CLAUDE_PLUGIN_ROOT}/templates/PROTOTYPE.html.template`), substituting `{{PROJECT_NAME}}` / `{{DATE}}`. The template already carries the `RENMARK:GENERATED:<id>:START…END` markers around its `## Current Architecture` block, so after creating it you splice the generated content into those markers exactly as in case 2.
plugin/skills/blueprint/SKILL.md:146:skill (per `${CLAUDE_PLUGIN_ROOT}/skills/_shared/next-steps.md`), end the run by
plugin/skills/blueprint/SKILL.md:151:> result per `${CLAUDE_PLUGIN_ROOT}/skills/_shared/next-steps.md` (class 1 —
plugin/skills/feature/SKILL.md:10:The **Feature pipeline** — adding or changing something in an existing build, with branch isolation. Creates a feature branch, checks PRD alignment (creating a PRD only if none exists), honors the reuse check (`${CLAUDE_PLUGIN_ROOT}/skills/_shared/reuse-check.md`) at plan time, runs the pipeline end-to-end, and offers PR / merge / release on finish. Continues automatically and pauses only at the Pause-Policy gates (`${CLAUDE_PLUGIN_ROOT}/skills/_shared/handoff-menu.md`) — chiefly PRD drift, the cost gate before tokens flow, and merge/release.
plugin/skills/feature/SKILL.md:34:In Agency Mode, **feature selects the next milestone/feature from the roadmap** rather than treating each feature request as an isolated change. The PRD-alignment check (Step 2) runs against the selected milestone, and scope drift is surfaced immediately — feedback that changes scope updates the roadmap and PRD rather than silently expanding the feature. See `${CLAUDE_PLUGIN_ROOT}/skills/_shared/agency-delivery.md` for the full delivery contract.
plugin/skills/feature/SKILL.md:56:**Step 0 — Context check.** Call `lifecycle.skill_preamble(repo, 'feature')`. If it returns a non-None hint, surface as a one-line note.
plugin/skills/feature/SKILL.md:84:`${CLAUDE_PLUGIN_ROOT}/skills/_shared/prd-alignment.md`: Agent tool call,
plugin/skills/feature/SKILL.md:280:> result per `${CLAUDE_PLUGIN_ROOT}/skills/_shared/next-steps.md` (class 1 —
plugin/skills/eval/SKILL.md:43:**Step 0 — Context check.** Call `lifecycle.skill_preamble(repo, 'eval')` and
plugin/skills/eval/SKILL.md:146:`${CLAUDE_PLUGIN_ROOT}/skills/_shared/next-steps.md`). It reports; it never
plugin/skills/eval/SKILL.md:150:> `${CLAUDE_PLUGIN_ROOT}/skills/_shared/next-steps.md` (class 3 — resume-pipeline
plugin/skills/eval/SKILL.md:153:> (`${CLAUDE_PLUGIN_ROOT}/skills/_shared/handoff-menu.md` rules 6–9); require an
plugin/skills/start/SKILL.md:12:**Pipeline:** intent → (brainstorm if fuzzy) → PRD → roadmap → first feature → plan → build → verify → review. renmark continues automatically and pauses only at the real gates in the Pause Policy (`${CLAUDE_PLUGIN_ROOT}/skills/_shared/handoff-menu.md`) — chiefly unclear intent, PRD approval, and cost.
plugin/skills/start/SKILL.md:22:`/renmark:start` is the **explicit opt-in entry** for Agency Mode — no auto-detect. When chosen, offer an Agency lane that frames the session as a discovery call: owner intent, users, problem, outcome, owner-level questions, and project classification (new app / feature / migration / automation / research-build). Agency Mode sits **above** Conductor/Orchestrator and does not replace them; existing `/renmark:start` behavior is unchanged when the Agency lane is not chosen. For the full contract, see `${CLAUDE_PLUGIN_ROOT}/skills/_shared/agency-delivery.md`.
plugin/skills/start/SKILL.md:34:**Step 0 — Context check.** Call `lifecycle.skill_preamble(repo, 'start')`. If it returns a non-None hint, surface as a one-line note (do not block — user decides). Also check `lifecycle.read_lifecycle(repo)` — if a feature is in flight (`stage != 'released'` and not None), redirect: *"There's an in-flight feature `<feature>` at stage `<stage>`. Run `/renmark:resume` to continue it, or `/renmark:start` will override."*
plugin/skills/start/SKILL.md:236:> result per `${CLAUDE_PLUGIN_ROOT}/skills/_shared/next-steps.md` (class 1 —
plugin/skills/help/SKILL.md:164:Reference: ${CLAUDE_PLUGIN_ROOT}/ (plugin install directory)
plugin/skills/help/SKILL.md:173:`${CLAUDE_PLUGIN_ROOT}/skills/_shared/next-steps.md` (resume-pipeline + local
plugin/skills/approve/SKILL.md:37:Call `lifecycle.skill_preamble(repo, 'approve')`. Approve is a `meta` domain skill.
plugin/skills/approve/SKILL.md:114:`${CLAUDE_PLUGIN_ROOT}/skills/_shared/next-steps.md`). It records a decision and
plugin/skills/approve/SKILL.md:118:> `${CLAUDE_PLUGIN_ROOT}/skills/_shared/next-steps.md` (class 3 — resume-pipeline
plugin/skills/approve/SKILL.md:121:> (`${CLAUDE_PLUGIN_ROOT}/skills/_shared/handoff-menu.md` rules 6–9); require an
plugin/skills/roadmap/SKILL.md:19:**Step 0 — Context check.** Call `lifecycle.skill_preamble(repo, 'roadmap')`. If it returns a non-None hint, surface as a one-line note.
plugin/skills/roadmap/SKILL.md:97:- `${CLAUDE_PLUGIN_ROOT}/skills/_shared/reuse-check.md` — before deriving a
plugin/skills/roadmap/SKILL.md:99:- `${CLAUDE_PLUGIN_ROOT}/skills/_shared/reasoning-contract.md` — governs the
plugin/skills/roadmap/SKILL.md:253:When Agency Mode delivery is selected, `/renmark:roadmap` emits **MILESTONES** instead of generic task tables. Each milestone carries: sequenced checkpoints (deterministic gates), demo points (user-observable proof), and SIGNOFF points (formal acceptance). Roadmap annotates each with risk/dependency notes and writes `roadmap_ref` into agency state for orchestration handoff. Contract details: `${CLAUDE_PLUGIN_ROOT}/skills/_shared/agency-delivery.md` (read by pointer only).
plugin/skills/roadmap/SKILL.md:260:`${CLAUDE_PLUGIN_ROOT}/skills/_shared/next-steps.md` (class 3 — resume-pipeline
plugin/skills/analytics/SKILL.md:27:hint = renmark.lifecycle.skill_preamble(repo, 'analytics')
plugin/skills/analytics/SKILL.md:65:`${CLAUDE_PLUGIN_ROOT}/skills/_shared/next-steps.md` (class 3 — resume-pipeline
plugin/skills/brainstorm/SKILL.md:12:Brainstorm does two things `plan` does not: it **researches prior art** (best practices, software that solves the same problem, reference implementations on GitHub) so the design is informed rather than invented, and it **establishes the scope contract** (stack / deployment / MVP boundary) using the shared source of truth at `${CLAUDE_PLUGIN_ROOT}/skills/_shared/scope-contract.md`. Because brainstorm writes the scope records, `/renmark:plan` detects them and skips re-asking — the two skills never double-question you.
plugin/skills/brainstorm/SKILL.md:31:**Step 0 — Context check.** Call `lifecycle.skill_preamble(repo, 'brainstorm')`. If it returns a non-None hint, surface as a one-line note. (Domain is resolved from `DOMAIN_BY_SKILL` — do not pass it manually.) For synthesis skills like brainstorm, `skill_preamble` now also surfaces a declared-tier hint (e.g. *"declared top tier: fable — … `/model fable`"*) — surface it verbatim, exactly like any other preamble hint.
plugin/skills/brainstorm/SKILL.md:33:**Premise-change re-entry.** If the user signals the premise changed — "things changed", "scope is different now", "we pivoted", a new constraint that contradicts the persisted spec/stack — do NOT continue from the persisted spec or `.renmark/memory/stack.md` as if it still holds. **Re-establish the scope contract first:** name the conflict between what's on disk and what the user just said, then re-ask the changed Q1–Q3 (stack / deployment / MVP boundary) from `${CLAUDE_PLUGIN_ROOT}/skills/_shared/scope-contract.md` and reconcile before resuming discovery. Re-establishing the contract takes priority over picking up where the persisted artifacts left off.
plugin/skills/brainstorm/SKILL.md:47:- Read templates from `${CLAUDE_PLUGIN_ROOT}/templates/` (CLAUDE.md.template, AGENTS.md.template, memory/INDEX.md, etc.).
plugin/skills/brainstorm/SKILL.md:70:  policy in `${CLAUDE_PLUGIN_ROOT}/skills/_shared/prd-alignment.md`.)
plugin/skills/brainstorm/SKILL.md:72:  `${CLAUDE_PLUGIN_ROOT}/skills/_shared/prd-alignment.md`: an **Agent tool call**
plugin/skills/brainstorm/SKILL.md:92:**Run the scope contract here.** As part of discovery, ask the Q1–Q3 stack / deployment / MVP-boundary questions from the shared source of truth at `${CLAUDE_PLUGIN_ROOT}/skills/_shared/scope-contract.md` (same questions `/renmark:plan` would ask — do NOT improvise your own). You will record these in Step 6 so `plan` skips re-asking.
plugin/skills/brainstorm/SKILL.md:107:Every research subagent prompt MUST also carry the Dispatch-reference blockquote from `${CLAUDE_PLUGIN_ROOT}/skills/_shared/reasoning-contract.md` (the same citable blockquote Step 4 carries) — research dispatches are subagent dispatches; the contract applies here too.
plugin/skills/brainstorm/SKILL.md:140:> `${CLAUDE_PLUGIN_ROOT}/skills/_shared/reuse-check.md`: Agent tool call
plugin/skills/brainstorm/SKILL.md:161:> `${CLAUDE_PLUGIN_ROOT}/skills/_shared/reasoning-contract.md` in every
plugin/skills/brainstorm/SKILL.md:177:**Write the scope contract records** so `/renmark:plan` skips re-discovery (this is the shared-source-of-truth payoff). Using the formats in `${CLAUDE_PLUGIN_ROOT}/skills/_shared/scope-contract.md`:
plugin/skills/brainstorm/SKILL.md:185:Renmark is a wizard pipeline: `brainstorm → plan (auto-validates) → orchestrate (auto-verifies) → finish`. After writing the spec, render the 3 options per `${CLAUDE_PLUGIN_ROOT}/skills/_shared/handoff-menu.md` rules (Plan [p], Wait [w], No [n]). The rendering rules, picker vs. numbered-list fallback, and required-choice contract all live there — do not duplicate them here.
plugin/skills/brainstorm/SKILL.md:194:> result per `${CLAUDE_PLUGIN_ROOT}/skills/_shared/next-steps.md` (class 1 —
plugin/skills/brainstorm/SKILL.md:211:- Template files: `${CLAUDE_PLUGIN_ROOT}/templates/`
plugin/skills/finish/SKILL.md:25:**Source of truth:** `renmark/finish_lanes.py` (`LANES`, `recommend_lane`, `lane_table`, `is_renmark_repo`). The table above is illustrative; the canonical matrix is generated by `lane_table()`. Lane contracts and default-by-stage rationale live in `${CLAUDE_PLUGIN_ROOT}/skills/_shared/finish-lanes.md` — do NOT duplicate or diverge from those definitions here.
plugin/skills/finish/SKILL.md:31:When finish runs in Agency Mode (third delivery modality), it produces a **MILESTONE DEMO summary** + owner **SIGNOFF gate** before lane selection, then routes through the standard finish lanes via `finish_lanes.recommend_lane()` — reusing existing lane machinery, not re-implementing. On fresh owner feedback, finish updates the roadmap and recommends the next milestone (via `/renmark:roadmap`). Consult the Agency Mode contract at `${CLAUDE_PLUGIN_ROOT}/skills/_shared/agency-delivery.md` for the complete flow.
plugin/skills/finish/SKILL.md:42:**Step 0 — Context check.** Call `lifecycle.skill_preamble(repo, 'finish')`. If it returns a non-None hint, surface as a one-line note.
plugin/skills/finish/SKILL.md:121:`${CLAUDE_PLUGIN_ROOT}/skills/_shared/reasoning-contract.md` in every
plugin/skills/finish/SKILL.md:261:**Headless gate (merge / release).** Before rendering the picker above, consult the headless contract for the two dangerous gates (`${CLAUDE_PLUGIN_ROOT}/skills/_shared/headless-contract.md`). For a `[m]` merge call `renmark.headless.resolve_gate(repo, "merge", kind="dangerous", originating_skill="finish", what=<one line: what is being merged>)`; for a `[r]` release call it with `"release"` and `what=<one line: what is being released>`. If it returns a `needs_input` envelope (headless: no human at a TTY), emit that JSON envelope as the fenced block **plus** `renmark.headless.render_return(envelope)` as the single prose line, then **STOP** — headless can NEVER approve a merge or release (this reinforces the REQ-12 rule above: merge / release are outward, irreversible, and only run on the user's explicit selection). If it returns `{"mode":"interactive"}`, render the existing `[m]`/`[r]` menu unchanged.
plugin/skills/finish/SKILL.md:491:> result per `${CLAUDE_PLUGIN_ROOT}/skills/_shared/next-steps.md` (class 1 —
plugin/skills/usage/SKILL.md:19:hint = renmark.lifecycle.skill_preamble(repo, 'usage')
plugin/skills/usage/SKILL.md:76:`${CLAUDE_PLUGIN_ROOT}/skills/_shared/next-steps.md` (class 3 — resume-pipeline
plugin/skills/prd/SKILL.md:24:- To check whether a change aligns with the PRD from inside another skill — do NOT read the PRD body there. Dispatch the alignment subagent at `${CLAUDE_PLUGIN_ROOT}/skills/_shared/prd-alignment.md` and consume only its bounded summary.
plugin/skills/prd/SKILL.md:29:In Agency Mode, the PRD is the owner-agreed source-of-truth LOCK. Owner approval gates all PRD changes; change control applies when milestone feedback shifts scope. See `${CLAUDE_PLUGIN_ROOT}/skills/_shared/agency-delivery.md` for the full contract. The human-gated create/update flow above remains unchanged — this rule is a reinforcement, not a new pathway.
plugin/skills/prd/SKILL.md:33:**Step 0 — Context check.** Call `lifecycle.skill_preamble(repo, 'prd')`. If it returns a non-None hint, surface it as a one-line note. Do NOT block — the user decides whether to `/compact` or `/clear`.
plugin/skills/prd/SKILL.md:66:   > *Before proposing any custom build, dispatch the reuse-check subagent from `${CLAUDE_PLUGIN_ROOT}/skills/_shared/reuse-check.md`: Agent tool call (`model: haiku`; `sonnet` for a large search surface), passing ONLY `request_description`. The subagent searches loaded skills/commands, session MCP tools, `.renmark/specs/` + `.renmark/plans/`, and `.renmark/memory/features.md` in its own context, and returns ONLY the ≤5-line `reuse: found | none` verdict (+ a one-line pointer when found). Surface the verdict and default to reuse; do NOT read the searched bodies in the orchestrator context (REQ-5).*
plugin/skills/prd/SKILL.md:68:   > *Include the reasoning/output-discipline contract from `${CLAUDE_PLUGIN_ROOT}/skills/_shared/reasoning-contract.md` in the dispatched subagent prompt: multi-perspective decomposition → explicit assumptions/edge cases → synthesis; blocking vs deferrable; findings vs recommendations; evidence preserved; missing context stated, never guessed; stance of pushing back by default (no sycophancy).*
plugin/skills/prd/SKILL.md:78:   **Headless gate.** Before rendering the approval picker, consult `renmark.headless.resolve_gate(repo, "prd-create", kind="dangerous", originating_skill="prd", what=<one-line description of the PRD draft>)`. If it returns anything other than `{"mode": "interactive"}` (headless), emit the returned `needs_input` JSON envelope + `headless.render_return(envelope)` prose line and **STOP** — the human owns the product source of truth, so PRD approval can never be auto-granted headless (PRD approval is a dangerous gate, per `${CLAUDE_PLUGIN_ROOT}/skills/_shared/headless-contract.md`). Interactive → render the approval picker unchanged.
plugin/skills/prd/SKILL.md:80:6. **On approval, write `PRD.md`** at the project root from the template at `${CLAUDE_PLUGIN_ROOT}/templates/PRD.md.template`, substituting `{{PROJECT_NAME}}` and `{{DATE}}` (today). Keep the provenance metadata header the template carries (so downstream alignment checks can read freshness without reading the body). Set `last_reviewed` to today.
plugin/skills/prd/SKILL.md:100:   **Fable lane (declared projects only).** In projects whose capability declaration says `capabilities.top_tier == "fable"`, this reconcile-and-diff analysis — ambiguity detection, dependency mapping, conflict checks against existing non-goals/capabilities — MAY be dispatched as **one non-interactive fable subagent**: a single bounded call carrying the full PRD body plus the requested change, returning the proposed diff and a ≤5-line rationale, which this skill then presents at step 3 exactly as it would its own analysis. The DIFF presentation, the human approval gate, and the write flow are completely unchanged — fable proposes, the human still approves, this skill still writes. This lane is for the analysis step only: interactive CREATE interviews stay on the session brain — never per-checkpoint fable calls. *Include the reasoning/output-discipline contract from `${CLAUDE_PLUGIN_ROOT}/skills/_shared/reasoning-contract.md` in the dispatched fable prompt: multi-perspective decomposition → explicit assumptions/edge cases → synthesis; blocking vs deferrable; findings vs recommendations; evidence preserved; missing context stated, never guessed.*
plugin/skills/prd/SKILL.md:103:   **Headless gate.** Before rendering the approval picker, consult `renmark.headless.resolve_gate(repo, "prd-update", kind="dangerous", originating_skill="prd", what=<one-line description of the PRD change>)`. If it returns anything other than `{"mode": "interactive"}` (headless), emit the returned `needs_input` JSON envelope + `headless.render_return(envelope)` prose line and **STOP** — the human owns the product source of truth, so PRD approval can never be auto-granted headless (PRD approval is a dangerous gate, per `${CLAUDE_PLUGIN_ROOT}/skills/_shared/headless-contract.md`). Interactive → render the approval picker unchanged.
plugin/skills/prd/SKILL.md:119:The template at `${CLAUDE_PLUGIN_ROOT}/templates/PRD.md.template` carries several structures the skill populates **only when the project benefits** — every one is OPTIONAL, and a lean PRD that omits all of them is fully valid. Never add an empty section to satisfy a checklist; absence is a legitimate signal that the project doesn't need it.
plugin/skills/prd/SKILL.md:155:The full PRD body is read **only inside this dedicated `/renmark:prd` invocation**. Orchestrator and router callers — `/renmark:orchestrate`, `/renmark:feature`, and any skill checking "does this change still match the product?" — **MUST NOT read the PRD body into their context.** They dispatch the alignment subagent defined at `${CLAUDE_PLUGIN_ROOT}/skills/_shared/prd-alignment.md`, which reads the PRD in isolation and returns only a bounded **≤5-line** summary (aligned / drift + which non-goal or capability is at issue). The PRD's plain-text pointer in CLAUDE.md/AGENTS.md (never an `@import`) keeps it off the always-loaded path; this skill is the only place the body legitimately enters a conversation.
plugin/skills/prd/SKILL.md:164:> result per `${CLAUDE_PLUGIN_ROOT}/skills/_shared/next-steps.md` (class 1 —
plugin/skills/CONTRIBUTING.md:64:Call `lifecycle.skill_preamble(repo, '<skill>')`. If it returns a non-None hint,
plugin/skills/scan/SKILL.md:37:**Step 0 — Context check.** Call `lifecycle.skill_preamble(repo, 'scan')`. Scan
plugin/skills/scan/SKILL.md:152:`${CLAUDE_PLUGIN_ROOT}/skills/_shared/next-steps.md`). It reports and proposes;
plugin/skills/scan/SKILL.md:156:> `${CLAUDE_PLUGIN_ROOT}/skills/_shared/next-steps.md` (class 3 — resume-pipeline
plugin/skills/scan/SKILL.md:160:> (`${CLAUDE_PLUGIN_ROOT}/skills/_shared/handoff-menu.md` rules 6–9); require an
plugin/skills/orchestrate/SKILL.md:33:In Agency Mode, orchestrate runs tasks via scoped background agents and advances to the next milestone **checkpoint** rather than halting after each task. The owner agent continues coordination while background agents execute in parallel; progress emits compact summaries only. See `${CLAUDE_PLUGIN_ROOT}/skills/_shared/agency-delivery.md` for the delivery contract. When Agency is off, orchestrate behaves as above — no changes to isolation or task dispatch.
plugin/skills/orchestrate/SKILL.md:48:**Step 0 — Context check.** Call `lifecycle.skill_preamble(repo, 'orchestrate')`. If it returns a non-None hint, surface as a one-line note. Also check `state.read_pipeline_state(repo)` — if `current_phase == "orchestrate"` and `pipeline_is_resumable(repo)`, surface: *"Existing orchestrate run paused at wave N — use `--resume` to continue, or clear pipeline state to start fresh."*  When the user passes `--resume` and an existing run is resumed from pipeline state, emit:
plugin/skills/orchestrate/SKILL.md:177:The Agent prompt MUST also include the canonical reasoning instruction blockquote — the one under "The canonical reasoning instruction (verbatim — single source)" in `${CLAUDE_PLUGIN_ROOT}/skills/_shared/reasoning-contract.md`, NOT the skill-author "Dispatch reference" blockquote — read it from that file at dispatch time and append it verbatim to the subagent prompt. This applies to BOTH dispatch paths: Agent-path dispatches above AND codex ad-hoc task specs (`renmark-execute --task`).
plugin/skills/orchestrate/SKILL.md:331:→ invoke `/renmark:verify`. From here the user follows verify's hand-off menu, rendered per `${CLAUDE_PLUGIN_ROOT}/skills/_shared/handoff-menu.md` (an interactive `AskUserQuestion` choice when available, numbered text only as fallback; the user must pick a choice to continue).
plugin/skills/orchestrate/SKILL.md:333:**Next step is state-derived (pipeline skill, next-steps.md class 1).** Orchestrate's own next action after a clean run is the stage-routed `next_recommended(repo)` (= `/renmark:verify` at stage `created`), which it auto-invokes above. On a paused/failed run it does NOT advance — it surfaces the resume command. Per `${CLAUDE_PLUGIN_ROOT}/skills/_shared/next-steps.md` (class 1 — Tier-0 stage routing); orchestrate hands directly to verify rather than rendering a separate picker.
plugin/commands/setup.md:5:Read `${CLAUDE_PLUGIN_ROOT}/skills/setup/SKILL.md` and follow its instructions exactly. The user provided this input: $ARGUMENTS
plugin/skills/guide/SKILL.md:73:`${CLAUDE_PLUGIN_ROOT}/skills/_shared/next-steps.md`. After it routes the user
tests/test_skillgen.py:67:        "${CLAUDE_PLUGIN_ROOT}/skills/_shared/reasoning-contract.md\n"
tests/test_skillgen.py:179:    body = "See ${CLAUDE_PLUGIN_ROOT}/skills/_shared/reasoning-contract.md for the stance.\n"
plugin/skills/setup/SKILL.md:32:**Step 0 — Context check.** Call `lifecycle.skill_preamble(repo, 'setup')`. If it
plugin/skills/setup/SKILL.md:48:`${CLAUDE_PLUGIN_ROOT}/skills/_shared/next-steps.md`). It sits off the main
plugin/skills/setup/SKILL.md:52:> `${CLAUDE_PLUGIN_ROOT}/skills/_shared/next-steps.md` (class 3 — resume-pipeline
plugin/commands/inventory.md:6:Read `${CLAUDE_PLUGIN_ROOT}/skills/inventory/SKILL.md` and follow its instructions exactly. The user provided this input: $ARGUMENTS
plugin/commands/loop.md:6:Read `${CLAUDE_PLUGIN_ROOT}/skills/loop/SKILL.md` and follow its instructions exactly. The user provided this input: $ARGUMENTS
plugin/commands/usage.md:5:Read `${CLAUDE_PLUGIN_ROOT}/skills/usage/SKILL.md` and follow its instructions exactly. The user provided this input: $ARGUMENTS
plugin/skills/audit/SKILL.md:34:**Step 0 — Context check.** Call `lifecycle.skill_preamble(repo, 'audit')`. Audit
plugin/skills/audit/SKILL.md:80:> `${CLAUDE_PLUGIN_ROOT}/skills/_shared/reasoning-contract.md` in every
plugin/skills/audit/SKILL.md:88:`${CLAUDE_PLUGIN_ROOT}/skills/_shared/next-steps.md`). It reports; it never
plugin/skills/audit/SKILL.md:92:> `${CLAUDE_PLUGIN_ROOT}/skills/_shared/next-steps.md` (class 3 — resume-pipeline
plugin/skills/audit/SKILL.md:95:> (`${CLAUDE_PLUGIN_ROOT}/skills/_shared/handoff-menu.md` rules 6–9); require an
plugin/skills/_shared/deterministic-first.md:109:> *Honor deterministic-first discipline in `${CLAUDE_PLUGIN_ROOT}/skills/_shared/deterministic-first.md`: before any task dispatch or model call, answer the 4-question gate (existing state? script? reusable? AI-needed?). Deterministic checks: git/worktree state, artifact existence/metadata, version/release readiness, plan lint, mirror validation, test baseline. Route judgment-heavy tasks (merge risk, release-readiness reasoning, branch strategy) only to model-based agents. See `renmark/worktree.py` for shared checks.*
plugin/commands/check-plan.md:6:Read `${CLAUDE_PLUGIN_ROOT}/skills/check-plan/SKILL.md` and follow its instructions exactly. The user provided this input: $ARGUMENTS
plugin/commands/brainstorm.md:6:Read `${CLAUDE_PLUGIN_ROOT}/skills/brainstorm/SKILL.md` and follow its instructions exactly. The user provided this input: $ARGUMENTS
plugin/skills/verify/SKILL.md:51:In projects where `capabilities.top_tier == "fable"` (per `renmark.capabilities.top_tier(repo)`), the hand-off offers a **fable QA-review subagent** via the verify-lane **extension code `[fr] Fable review`** — the same pattern codereview uses for its `[o]`/`[fix]` extension codes. Extension codes are NOT in `handoff-menu.md`'s canonical master list; `[fr]` appears only in the combined menu this skill builds for its own hand-off, and only in declared projects. Choosing `[fr]` dispatches an implementation review against the plan goal + acceptance criteria, plus regression-risk and edge-case review. Dispatch it per the reasoning/output-discipline contract — *include the reasoning/output-discipline contract from `${CLAUDE_PLUGIN_ROOT}/skills/_shared/reasoning-contract.md` in every dispatched subagent prompt: multi-perspective decomposition → explicit assumptions/edge cases → synthesis; blocking vs deferrable; findings vs recommendations; evidence preserved; missing context stated, never guessed.* The subagent returns a bounded ≤5-line verdict with each issue marked **blocking vs deferrable**; full evidence goes to a `.renmark/reviews/` artifact, never into chat.
plugin/skills/verify/SKILL.md:57:In Agency Mode, verify escalates from feature-level smoke to milestone-readiness assessment. Runs smoke tests plus browser QA (`--qa`) / edge-case checks (`--deep-qa`) when the milestone surfaces user-visible behavior. Reports DEMO-readiness against the milestone acceptance criteria (what passed, what remains unverified, confidence level) and feeds the owner's signoff checkpoint. See contract pointer: `${CLAUDE_PLUGIN_ROOT}/skills/_shared/agency-delivery.md`. Additive — existing verify behavior unchanged when agency is off.
plugin/skills/verify/SKILL.md:72:**Step 0 — Context check + pipeline gate.** Call `lifecycle.skill_preamble(repo, 'verify')`. If it returns a non-None hint, surface as a one-line note. Also check `state.read_pipeline_state(repo)` — if a prior orchestrate run is paused or in flight (`pipeline_is_resumable(repo)` is True), refuse:
plugin/skills/verify/SKILL.md:202:Render the hand-off menu from `${CLAUDE_PLUGIN_ROOT}/skills/_shared/handoff-menu.md`, applying the rendering rules:
plugin/skills/verify/SKILL.md:353:When subagents participate in QA in any capacity (e.g. a fable QA-review pass), their dispatch prompt MUST explicitly tell them they have **browser automation access via the active browser channel** (Chrome DevTools MCP or native Claude-in-Chrome, per the channel-selection rules above), and that **UI-bearing acceptance criteria MUST NOT be validated by static code inspection alone** — a PASS on a UI criterion never exercised in a live browser is a G9 violation (`validation_status: unvalidated`). See the browser-validation clause in `${CLAUDE_PLUGIN_ROOT}/skills/_shared/reasoning-contract.md`. This does not change the singleton-browser design: flows still run serially in the main agent; subagents that need rendered evidence coordinate through the same single browser session, never parallel pages.
plugin/skills/verify/SKILL.md:436:Render the menu from `${CLAUDE_PLUGIN_ROOT}/skills/_shared/handoff-menu.md`:
plugin/skills/verify/SKILL.md:574:Render the menu from `${CLAUDE_PLUGIN_ROOT}/skills/_shared/handoff-menu.md`:
plugin/commands/analytics.md:5:Read `${CLAUDE_PLUGIN_ROOT}/skills/analytics/SKILL.md` and follow its instructions exactly. The user provided this input: $ARGUMENTS
plugin/commands/doctor.md:6:Read `${CLAUDE_PLUGIN_ROOT}/skills/doctor/SKILL.md` and follow its instructions exactly. The user provided this input: $ARGUMENTS
plugin/commands/debug.md:6:Read `${CLAUDE_PLUGIN_ROOT}/skills/debug/SKILL.md` and follow its instructions exactly. The user provided this input: $ARGUMENTS
plugin/skills/inventory/SKILL.md:30:**Step 0 — Context check.** Call `lifecycle.skill_preamble(repo, 'inventory')`.
plugin/skills/inventory/SKILL.md:47:`${CLAUDE_PLUGIN_ROOT}/skills/_shared/next-steps.md`).
plugin/skills/inventory/SKILL.md:50:> `${CLAUDE_PLUGIN_ROOT}/skills/_shared/next-steps.md` (class 3 — resume-pipeline
plugin/skills/inventory/SKILL.md:53:> (`${CLAUDE_PLUGIN_ROOT}/skills/_shared/handoff-menu.md` rules 6–9); require an
plugin/commands/eval.md:6:Read `${CLAUDE_PLUGIN_ROOT}/skills/eval/SKILL.md` and follow its instructions exactly. The user provided this input: $ARGUMENTS
plugin/skills/_shared/headless-contract.md:210:> *If headless (per `${CLAUDE_PLUGIN_ROOT}/skills/_shared/headless-contract.md`
plugin/skills/_shared/subagent-budget.md:101:> *Honor subagent budget discipline in `${CLAUDE_PLUGIN_ROOT}/skills/_shared/subagent-budget.md`: local-first (grep/read before spawning); each dispatch packet carries mission, files, output_format, stop_condition, model_tier, and verification_expectation; prefer cheaper models for read-only work; warn when >5 subagents are needed. Do not pass full skill bodies in dispatch packets (see `_shared/context-taxonomy.md`).*
plugin/skills/_shared/context-taxonomy.md:77:> `${CLAUDE_PLUGIN_ROOT}/skills/_shared/context-taxonomy.md`: static rules are
plugin/skills/_shared/subagent-profiles.md:45:> *Dispatch specialized subagent role (prefer over generic `general-purpose`): `docs-editor` (docs/comments), `code-implementer` (feature code), `test-writer` (tests), `reviewer` (code review), `release-manager` (version/release), `researcher` (web research), `audit-reader` (audit artifacts), `finish-lane-specialist` (lane selection). Full registry: `${CLAUDE_PLUGIN_ROOT}/skills/_shared/subagent-profiles.md`. Fallback to `general-purpose` only when no role fits; in that case, set `role: general-purpose` and relax context scope.*
plugin/skills/_shared/cost-preview.md:130:> *Show a cost preview before expensive work via `renmark/cost.py::estimate_cost`. Format per `${CLAUDE_PLUGIN_ROOT}/skills/_shared/cost-preview.md`: model tiers, token/cost band, subagent count, escalation justification (cite `requires_escalation`), and cheaper alternatives. Do not route to Opus/Fable without justifying and surfacing the cost.*
plugin/commands/hygiene.md:6:Read `${CLAUDE_PLUGIN_ROOT}/skills/hygiene/SKILL.md` and follow its instructions exactly. The user provided this input: $ARGUMENTS
plugin/skills/_shared/reuse-check.md:82:`${CLAUDE_PLUGIN_ROOT}/skills/_shared/reasoning-contract.md`.
plugin/skills/_shared/reuse-check.md:143:> `${CLAUDE_PLUGIN_ROOT}/skills/_shared/reuse-check.md`: Agent tool call
plugin/skills/backlog/SKILL.md:44:**Step 0 — Context check.** Call `lifecycle.skill_preamble(repo, 'backlog')`. If it returns
plugin/skills/backlog/SKILL.md:205:result per `${CLAUDE_PLUGIN_ROOT}/skills/_shared/next-steps.md` (class 3 —
plugin/skills/_shared/next-steps.md:131:> result per `${CLAUDE_PLUGIN_ROOT}/skills/_shared/next-steps.md` (class 1 —
plugin/skills/_shared/next-steps.md:139:> `${CLAUDE_PLUGIN_ROOT}/skills/_shared/handoff-menu.md` (the next-step contract's
plugin/skills/_shared/next-steps.md:146:> `${CLAUDE_PLUGIN_ROOT}/skills/_shared/next-steps.md` (class 3 — resume-pipeline
plugin/skills/_shared/next-steps.md:158:When the run is headless (per `${CLAUDE_PLUGIN_ROOT}/skills/_shared/headless-contract.md`
plugin/skills/_shared/model-routing.md:70:> *Honor model routing discipline in `${CLAUDE_PLUGIN_ROOT}/skills/_shared/model-routing.md`: Haiku for docs/grep/summaries/small audits; Sonnet for planning/implementation/reviews; Codex for bounded code tasks; Opus/Fable escalation-only when `renmark.cost.requires_escalation` returns True (architecture/judgment/prior-failure). Consult `.renmark/memory/routing.md` ledger before choosing non-default tier.*
plugin/commands/init.md:5:Read `${CLAUDE_PLUGIN_ROOT}/skills/init/SKILL.md` and follow its instructions exactly. The user provided this input: $ARGUMENTS
plugin/skills/_shared/handoff-menu.md:41:> *If headless (per `${CLAUDE_PLUGIN_ROOT}/skills/_shared/headless-contract.md`
plugin/skills/_shared/handoff-menu.md:235:> *Render the hand-off menu from `${CLAUDE_PLUGIN_ROOT}/skills/_shared/handoff-menu.md`,
plugin/skills/_shared/scope-contract.md:26:**Headless mode (safe gate).** The Q1–Q3 scope questions are a SAFE gate per the headless contract: when renmark runs headless (no human at a TTY, `AskUserQuestion` absent), they are **not** asked interactively. The skill auto-picks the recommended/default option for each question (suggested stack confirmed, deployment per the inference rules / "undecided", MVP boundary per "plan everything"), records the choice in the scope records (CHANGELOG entry + `stack.md`) plus `decision: auto_picked_recommended` in the return JSON, and continues — never stalling on a picker that cannot be answered. Detection and the full contract live in `${CLAUDE_PLUGIN_ROOT}/skills/_shared/headless-contract.md`.
plugin/skills/_shared/prd-alignment.md:163:> `${CLAUDE_PLUGIN_ROOT}/skills/_shared/prd-alignment.md`: Agent tool call
plugin/commands/guide.md:5:Read `${CLAUDE_PLUGIN_ROOT}/skills/guide/SKILL.md` and follow its instructions exactly. The user provided this input: $ARGUMENTS
plugin/skills/resume/SKILL.md:31:Call `lifecycle.skill_preamble(repo, 'resume')`. Resume is a `meta` domain skill — it rarely triggers a cross-domain prompt because it touches no work. If it does return a hint, ignore: resume is cheap and should always run.
plugin/skills/resume/SKILL.md:212:In Agency Mode, resume reads `.renmark/state/agency.json` (via `renmark.agency.read_agency`) to locate the last MILESTONE checkpoint. Summarize where the workflow left off — which milestone was last reached, what triggered the checkpoint, any pending decision — and recommend continuing WITHOUT re-discovery of prior work. Still zero LLM calls; pure file IO. For the full Agency Mode contract and delivery mode semantics, see `${CLAUDE_PLUGIN_ROOT}/skills/_shared/agency-delivery.md`. This recovery path is **additive** — the existing lifecycle-based resume (Steps 1–1.75 and Step 2 onward) remains unchanged for non-Agency workflows.
plugin/skills/resume/SKILL.md:257:> *Render the printed recommendation per `${CLAUDE_PLUGIN_ROOT}/skills/_shared/next-steps.md` (class 3 — resume-pipeline + 1–2 local actions). The in-flight feature's next command is `(Recommended)`. Resume is zero-LLM, so it uses the printed numbered form (handoff-menu.md rule 7), not the interactive `AskUserQuestion` picker — and never auto-proceeds.*
plugin/skills/codereview/SKILL.md:78:**When Agency Mode is active:** codereview runs a full review before each milestone signoff, reports both merge-readiness and risk findings, and gates the owner signoff on review verdict. The review blocks premature "done" declarations until findings are addressed. See the Agency Mode contract at `${CLAUDE_PLUGIN_ROOT}/skills/_shared/agency-delivery.md` for gating rules and escalation conditions. When Agency Mode is off, existing codereview behavior is unchanged.
plugin/skills/codereview/SKILL.md:90:> `${CLAUDE_PLUGIN_ROOT}/skills/_shared/reasoning-contract.md` in every
plugin/skills/codereview/SKILL.md:240:**Step 0 — Context check.** Call `lifecycle.skill_preamble(repo, 'codereview')`. If it returns a non-None hint, surface as a one-line note.
plugin/skills/codereview/SKILL.md:330:Then append the hand-off menu from `${CLAUDE_PLUGIN_ROOT}/skills/_shared/handoff-menu.md`, applying the rendering rules:
plugin/commands/orchestrate.md:6:Read `${CLAUDE_PLUGIN_ROOT}/skills/orchestrate/SKILL.md` and follow its instructions exactly. The user provided this input: $ARGUMENTS
plugin/commands/codereview.md:6:Read `${CLAUDE_PLUGIN_ROOT}/skills/codereview/SKILL.md` and follow its instructions exactly. The user provided this input: $ARGUMENTS
plugin/skills/_shared/finish-lanes.md:113:> *Use the finish lanes in `${CLAUDE_PLUGIN_ROOT}/skills/_shared/finish-lanes.md`: quick (verify only), release (merge+tag), self-update (renmark only: merge+release+package+WSL), full (explicit-only). Consult `renmark.finish_lanes.recommend_lane` for the default by lifecycle stage. Do not invent new lanes.*
plugin/commands/backlog.md:6:Read `${CLAUDE_PLUGIN_ROOT}/skills/backlog/SKILL.md` and follow its instructions exactly. The user provided this input: $ARGUMENTS
plugin/commands/blueprint.md:6:Read `${CLAUDE_PLUGIN_ROOT}/skills/blueprint/SKILL.md` and follow its instructions exactly. The user provided this input: $ARGUMENTS
plugin/skills/_shared/agency-delivery.md:119:> *Honor the agency delivery contract in `${CLAUDE_PLUGIN_ROOT}/skills/_shared/agency-delivery.md`: discovery → PRD → stack signoff → roadmap/milestones → build → demo/feedback → verification → final signoff → finish. Ask owner-level questions only (goal, users, constraints, risks, success, signoff). Milestone checkpoints pause for owner review — they do not pass automatically when tests pass. Background agents handle implementation; main agent coordinates and reads bounded summaries. Delegate cost infra to finish_lanes / cost.py / context_budget_hint / subagent-profiles — do not inline those rules.*
plugin/commands/prd.md:6:Read `${CLAUDE_PLUGIN_ROOT}/skills/prd/SKILL.md` and follow its instructions exactly. The user provided this input: $ARGUMENTS
plugin/commands/scan.md:6:Read `${CLAUDE_PLUGIN_ROOT}/skills/scan/SKILL.md` and follow its instructions exactly. The user provided this input: $ARGUMENTS
plugin/commands/resume.md:5:Read `${CLAUDE_PLUGIN_ROOT}/skills/resume/SKILL.md` and follow its instructions exactly. The user provided this input: $ARGUMENTS
plugin/commands/plan.md:6:Read `${CLAUDE_PLUGIN_ROOT}/skills/plan/SKILL.md` and follow its instructions exactly. The user provided this input: $ARGUMENTS
plugin/skills/doctor/SKILL.md:163:`${CLAUDE_PLUGIN_ROOT}/skills/_shared/next-steps.md`). After diagnosis (and any
plugin/skills/doctor/SKILL.md:167:> `${CLAUDE_PLUGIN_ROOT}/skills/_shared/next-steps.md` (class 3 — resume-pipeline
plugin/commands/audit.md:6:Read `${CLAUDE_PLUGIN_ROOT}/skills/audit/SKILL.md` and follow its instructions exactly. The user provided this input: $ARGUMENTS
plugin/skills/_shared/reasoning-contract.md:75:> `${CLAUDE_PLUGIN_ROOT}/skills/_shared/reasoning-contract.md` in every
plugin/commands/roadmap.md:6:Read `${CLAUDE_PLUGIN_ROOT}/skills/roadmap/SKILL.md` and follow its instructions exactly. The user provided this input: $ARGUMENTS
plugin/commands/finish.md:5:Read `${CLAUDE_PLUGIN_ROOT}/skills/finish/SKILL.md` and follow its instructions exactly. The user provided this input: $ARGUMENTS
plugin/commands/help.md:5:Read `${CLAUDE_PLUGIN_ROOT}/skills/help/SKILL.md` and follow its instructions exactly. The user provided this input: $ARGUMENTS
plugin/commands/verify.md:6:Read `${CLAUDE_PLUGIN_ROOT}/skills/verify/SKILL.md` and follow its instructions exactly. The user provided this input: $ARGUMENTS
plugin/skills/debug/SKILL.md:57:**Step 0 — Context check.** Call `lifecycle.skill_preamble(repo, 'debug')`. If it returns a non-None hint, surface as a one-line note — debug is the `debug` domain, so transitioning into it from `build` or `audit` is a common cross-domain trigger.
plugin/skills/debug/SKILL.md:126:Debug is a class-3 aux / terminal skill. End by calling `renmark.lifecycle.next_steps(repo, "debug")` and render per `${CLAUDE_PLUGIN_ROOT}/skills/_shared/next-steps.md` (class 3 — resume-pipeline + 1–2 local actions). The in-flight feature's next command is `(Recommended)`; add debug's local follow-ups. Render via `AskUserQuestion` (handoff-menu.md rules 6–9); require an explicit choice — never auto-proceed.
plugin/commands/approve.md:6:Read `${CLAUDE_PLUGIN_ROOT}/skills/approve/SKILL.md` and follow its instructions exactly. The user provided this input: $ARGUMENTS
plugin/commands/feature.md:6:Read `${CLAUDE_PLUGIN_ROOT}/skills/feature/SKILL.md` and follow its instructions exactly. The user provided this input: $ARGUMENTS
plugin/commands/start.md:6:Read `${CLAUDE_PLUGIN_ROOT}/skills/start/SKILL.md` and follow its instructions exactly. The user provided this input: $ARGUMENTS
plugin/skills/init/SKILL.md:55:**Step 0 — Context check.** Call `lifecycle.skill_preamble(repo, 'init')`. If it returns a non-None hint, surface as a one-line note.
plugin/skills/init/SKILL.md:184:> `${CLAUDE_PLUGIN_ROOT}/skills/_shared/next-steps.md` (class 3 — resume-pipeline

[35m[3mcodex[0m[0m
I’ve confirmed the intended files changed and the new skill pointers are portable. I’m running the focused behavior tests now and checking whether any stale comments, docs, or callers still assume “spine-only” semantics in a way that would mislead or break follow-on work.
[35m[3mexec[0m[0m
[1m/bin/bash -lc "sed -n '1,220p' tests/test_agency_behavior.py"[0m in /home/renmark/projects/ai-system/.claude/worktrees/agency-fastfollow
[32m succeeded in 0ms:[0m
"""Behavioral tests for Agency Mode — proves CHANGES renmark behavior (AC11).

Tests pin the observable contracts:
- AC2: inactive agency leaves preamble byte-identical (no-op)
- Spine vs non-spine routing (_AGENCY_SPINE_SKILLS)
- AC4/REQ-20: active preamble carries fragment POINTER not inlined body
- Fragment registration and on-demand loadability
- Mode selection stays independent of agency state
"""

from __future__ import annotations

from pathlib import Path

from renmark import agency, context, lifecycle, mode

# ── Repo root (the live project, not a tmp dir) ────────────────────────────────
# Used to resolve plugin_root for load_fragment — body check in T4 requires
# the real fragment, not a tmp synthetic copy.

_REPO_ROOT = Path(__file__).resolve().parent.parent
_PLUGIN_ROOT = _REPO_ROOT / "plugin"


# ── Helpers ───────────────────────────────────────────────────────────────────


def _init_state_dir(repo: Path) -> None:
    """Create .renmark/state/ so agency writes don't fail on missing parent."""
    (repo / ".renmark" / "state").mkdir(parents=True, exist_ok=True)


# ── 1. Inactive preamble has no agency hint ────────────────────────────────────


def test_inactive_preamble_has_no_agency_hint(tmp_path: Path) -> None:
    """With agency inactive (fresh tmp repo), skill_preamble('start') must NOT
    contain lifecycle._AGENCY_HINT_MARKER (AC2 — byte-identical when off)."""
    _init_state_dir(tmp_path)
    # Ensure agency is inactive (fresh repo — no agency.json → default inactive).
    assert not agency.is_active(tmp_path)

    result = lifecycle.skill_preamble(tmp_path, "start")
    # None is acceptable (no hints at all); a string must not carry the marker.
    if result is not None:
        assert lifecycle._AGENCY_HINT_MARKER not in result, (
            f"skill_preamble returned the agency hint for an inactive repo: {result!r}"
        )


def test_inactive_agency_note_is_byte_identical_passthrough(tmp_path: Path) -> None:
    """Invariant #1 at the unit level: when agency is inactive, _with_agency_note
    returns its input UNCHANGED (identity) — byte-identical, not merely
    marker-free. Proven for every spine skill against a sentinel that shares no
    text with the agency hint, so any appended/reordered content would fail."""
    _init_state_dir(tmp_path)
    assert not agency.is_active(tmp_path)
    sentinel = "SENTINEL-preamble-xyz"
    for skill in sorted(lifecycle._AGENCY_SPINE_SKILLS):
        assert lifecycle._with_agency_note(tmp_path, skill, sentinel) == sentinel
        # None must stay None too (no hint fabricated when there was none).
        assert lifecycle._with_agency_note(tmp_path, skill, None) is None


def test_agency_note_noop_for_nonaware_even_when_active(tmp_path: Path) -> None:
    """Skills NOT in the agency-aware set pass through unchanged even when active.

    (debug/audit are non-pipeline skills — they never get an agency hint.)"""
    _init_state_dir(tmp_path)
    agency.activate(tmp_path, current_phase="alpha", current_milestone="M1")
    sentinel = "SENTINEL-preamble-xyz"
    assert "debug" not in lifecycle._AGENCY_AWARE_SKILLS
    assert lifecycle._with_agency_note(tmp_path, "debug", sentinel) == sentinel
    assert lifecycle._with_agency_note(tmp_path, "audit", None) is None


def test_all_pipeline_skills_gain_hint_when_active(tmp_path: Path) -> None:
    """Fast-follow: every agency-aware pipeline skill — the spine PLUS
    feature/plan/orchestrate/verify/codereview — surfaces the agency hint +
    fragment pointer when agency is active."""
    _init_state_dir(tmp_path)
    agency.activate(tmp_path, current_phase="alpha", current_milestone="M1")
    pointer = context.fragment_pointer("agency-delivery")
    for skill in ("feature", "plan", "orchestrate", "verify", "codereview"):
        note = lifecycle._with_agency_note(tmp_path, skill, None)
        assert note is not None and lifecycle._AGENCY_HINT_MARKER in note, (
            f"{skill} did not gain the agency hint when active: {note!r}"
        )
        assert pointer in note, f"{skill} note missing fragment pointer: {note!r}"


# ── 2. Active spine preamble gains the hint ────────────────────────────────────


def test_active_spine_preamble_gains_hint(tmp_path: Path) -> None:
    """After activate(repo, current_phase='alpha', current_milestone='M1'),
    skill_preamble(repo, 'start') must contain the marker AND the fragment pointer."""
    _init_state_dir(tmp_path)
    agency.activate(tmp_path, current_phase="alpha", current_milestone="M1")

    result = lifecycle.skill_preamble(tmp_path, "start")
    assert result is not None, (
        "skill_preamble returned None for an active-agency spine skill; "
        "expected a hint string containing the agency marker."
    )
    assert lifecycle._AGENCY_HINT_MARKER in result, (
        f"Agency marker not found in active preamble for 'start': {result!r}"
    )
    pointer = context.fragment_pointer("agency-delivery")
    assert pointer in result, (
        f"Fragment pointer {pointer!r} not found in active preamble: {result!r}"
    )


# ── 3. Active non-spine preamble stays clean ──────────────────────────────────


def test_active_nonaware_preamble_stays_clean(tmp_path: Path) -> None:
    """With agency active, a NON-agency-aware skill ('debug') preamble must NOT
    contain the agency hint marker."""
    _init_state_dir(tmp_path)
    agency.activate(tmp_path, current_phase="beta", current_milestone="M2")

    # 'debug' is NOT in the agency-aware pipeline set
    assert "debug" not in lifecycle._AGENCY_AWARE_SKILLS

    result = lifecycle.skill_preamble(tmp_path, "debug")
    if result is not None:
        assert lifecycle._AGENCY_HINT_MARKER not in result, (
            f"Agency hint leaked into non-aware skill 'debug': {result!r}"
        )


# ── 4. Active preamble carries POINTER not inlined body (AC4 / REQ-20) ────────


def test_preamble_carries_pointer_not_body(tmp_path: Path) -> None:
    """Active preamble must contain the fragment pointer but NOT inline the
    fragment body (dynamic-loading guarantee: AC4 / REQ-20).

    Loads the real agency-delivery.md body from the live plugin dir to pick a
    distinctive substring, then asserts that substring is absent from the
    preamble string.
    """
    _init_state_dir(tmp_path)
    agency.activate(tmp_path, current_phase="alpha", current_milestone="M1")

    result = lifecycle.skill_preamble(tmp_path, "start")
    assert result is not None, (
        "skill_preamble returned None for an active-agency spine skill."
    )

    # The pointer must be present.
    pointer = context.fragment_pointer("agency-delivery")
    assert pointer in result, (
        f"Fragment pointer not found in preamble: {result!r}"
    )

    # Load the real body to find a distinctive phrase that should NOT be inlined.
    body = context.load_fragment(_PLUGIN_ROOT, "agency-delivery")
    # "milestone checkpoint" is a distinctive multi-word phrase in the fragment body
    # that would only appear if the body were inlined.
    distinctive = "milestone checkpoint"
    assert distinctive in body, (
        f"Sanity: expected {distinctive!r} in agency-delivery body — check fragment."
    )
    assert distinctive not in result, (
        f"Fragment body appears to be inlined in the preamble (found {distinctive!r}). "
        "Dynamic loading violated — preamble must carry the pointer only."
    )


# ── 5. Fragment registered and loadable ────────────────────────────────────────


def test_fragment_registered_and_loadable() -> None:
    """'agency-delivery' must be in context.fragment_names() AND load_fragment
    must return a non-empty string that contains 'milestone'."""
    names = context.fragment_names()
    assert "agency-delivery" in names, (
        f"'agency-delivery' not in fragment_names(): {names}"
    )

    body = context.load_fragment(_PLUGIN_ROOT, "agency-delivery")
    assert body, "load_fragment('agency-delivery') returned empty string"
    assert "milestone" in body, (
        "Expected 'milestone' in agency-delivery body — check the fragment."
    )


# ── 6. Mode selection is independent of agency active/inactive (AC2) ──────────


def test_mode_selection_independent_of_agency(tmp_path: Path) -> None:
    """Setting mode via renmark.mode must be unaffected by agency state, and
    toggling agency must not alter mode state."""
    _init_state_dir(tmp_path)

    # Start: both inactive/unset.
    assert mode.read_mode(tmp_path) is None
    assert not agency.is_active(tmp_path)

    # Set conductor mode, activate agency — mode must still be conductor.
    mode.set_mode(tmp_path, "conductor")
    agency.activate(tmp_path, current_phase="gamma", current_milestone="M3")
    assert mode.read_mode(tmp_path) == "conductor"
    assert agency.is_active(tmp_path)

    # Deactivate agency — mode must still be conductor.
    agency.deactivate(tmp_path)
    assert mode.read_mode(tmp_path) == "conductor"
    assert not agency.is_active(tmp_path)

    # Clear mode — agency state must be unaffected.
    mode.clear_mode(tmp_path)
    assert mode.read_mode(tmp_path) is None
    assert not agency.is_active(tmp_path)

[35m[3mexec[0m[0m
[1m/bin/bash -lc "sed -n '720,780p' renmark/lifecycle.py"[0m in /home/renmark/projects/ai-system/.claude/worktrees/agency-fastfollow
[32m succeeded in 0ms:[0m
                return hint
        elif skill in _MODE_ENTRY_SKILLS:
            line = _choose_mode_hint(skill)
        else:
            return hint
    except Exception:
        return hint
    return line if hint is None else f"{hint} | {line}"


# Pipeline skills that receive an Agency Mode hint when agency is active.
# v0.30.0 shipped the spine (start/prd/roadmap/finish/resume); the fast-follow
# extends coverage to the remaining pipelines (feature/plan/orchestrate/verify/
# codereview) so the whole delivery loop is agency-aware.
_AGENCY_AWARE_SKILLS: frozenset[str] = frozenset(
    {
        "start", "prd", "roadmap", "finish", "resume",
        "feature", "plan", "orchestrate", "verify", "codereview",
    }
)

# Back-compat alias: the original spine-only name still resolves.
_AGENCY_SPINE_SKILLS: frozenset[str] = _AGENCY_AWARE_SKILLS

# Marker string used to identify the agency hint line — load-bearing for
# behavior tests (T15): assert active preamble contains this prefix and
# inactive preamble does NOT.
_AGENCY_HINT_MARKER: str = "Agency Mode active"


def _with_agency_note(repo: Path | str, skill: str, hint: str | None) -> str | None:
    """ADDITIVE: append an Agency Mode hint to ``hint`` when agency is active.

    Only surfaces the hint for AGENCY-AWARE pipeline skills (the spine —
    start/prd/roadmap/finish/resume — plus feature/plan/orchestrate/verify/
    codereview) — all other skills are passed through unchanged regardless of
    agency state.

    When agency is INACTIVE the return value is byte-identical to ``hint``
    (the inactive-path guarantee). DEGRADES GRACEFULLY: any exception in
    agency/context resolution falls back to ``hint`` unchanged, so agency is
    a pure enhancement and never a hard dependency of the preamble.

    Follows the same additive pattern as :func:`_with_mode_note` and
    :func:`_with_headless_note`.
    """
    if skill not in _AGENCY_AWARE_SKILLS:
        return hint
    try:
        from . import agency as _agency
        from . import context as _context

        if not _agency.is_active(repo):
            return hint
        state = _agency.read_agency(repo)
        pointer = _context.fragment_pointer("agency-delivery")
        line = (
            f"{_AGENCY_HINT_MARKER} — phase {state.current_phase}, "
            f"milestone {state.current_milestone}. Contract: {pointer}"
        )
    except Exception:

[35m[3mexec[0m[0m
[1m/bin/bash -lc 'pytest -q tests/test_agency_behavior.py'[0m in /home/renmark/projects/ai-system/.claude/worktrees/agency-fastfollow
[31m exited 1 in 394ms:[0m
Traceback (most recent call last):
  File "/opt/miniconda/envs/claude/bin/pytest", line 6, in <module>
    sys.exit(console_main())
             ~~~~~~~~~~~~^^
  File "/opt/miniconda/envs/claude/lib/python3.14/site-packages/_pytest/config/__init__.py", line 223, in console_main
    code = main()
  File "/opt/miniconda/envs/claude/lib/python3.14/site-packages/_pytest/config/__init__.py", line 193, in main
    config = _prepareconfig(new_args, plugins)
  File "/opt/miniconda/envs/claude/lib/python3.14/site-packages/_pytest/config/__init__.py", line 361, in _prepareconfig
    config: Config = pluginmanager.hook.pytest_cmdline_parse(
                     ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^
        pluginmanager=pluginmanager, args=args
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "/opt/miniconda/envs/claude/lib/python3.14/site-packages/pluggy/_hooks.py", line 512, in __call__
    return self._hookexec(self.name, self._hookimpls.copy(), kwargs, firstresult)
           ~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/miniconda/envs/claude/lib/python3.14/site-packages/pluggy/_manager.py", line 120, in _hookexec
    return self._inner_hookexec(hook_name, methods, kwargs, firstresult)
           ~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/miniconda/envs/claude/lib/python3.14/site-packages/pluggy/_callers.py", line 167, in _multicall
    raise exception
  File "/opt/miniconda/envs/claude/lib/python3.14/site-packages/pluggy/_callers.py", line 139, in _multicall
    teardown.throw(exception)
    ~~~~~~~~~~~~~~^^^^^^^^^^^
  File "/opt/miniconda/envs/claude/lib/python3.14/site-packages/_pytest/helpconfig.py", line 124, in pytest_cmdline_parse
    config = yield
             ^^^^^
  File "/opt/miniconda/envs/claude/lib/python3.14/site-packages/pluggy/_callers.py", line 121, in _multicall
    res = hook_impl.function(*args)
  File "/opt/miniconda/envs/claude/lib/python3.14/site-packages/_pytest/config/__init__.py", line 1192, in pytest_cmdline_parse
    self.parse(args)
    ~~~~~~~~~~^^^^^^
  File "/opt/miniconda/envs/claude/lib/python3.14/site-packages/_pytest/config/__init__.py", line 1562, in parse
    self.hook.pytest_load_initial_conftests(
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^
        early_config=self, args=args, parser=self._parser
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "/opt/miniconda/envs/claude/lib/python3.14/site-packages/pluggy/_hooks.py", line 512, in __call__
    return self._hookexec(self.name, self._hookimpls.copy(), kwargs, firstresult)
           ~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/miniconda/envs/claude/lib/python3.14/site-packages/pluggy/_manager.py", line 120, in _hookexec
    return self._inner_hookexec(hook_name, methods, kwargs, firstresult)
           ~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/miniconda/envs/claude/lib/python3.14/site-packages/pluggy/_callers.py", line 167, in _multicall
    raise exception
  File "/opt/miniconda/envs/claude/lib/python3.14/site-packages/pluggy/_callers.py", line 139, in _multicall
    teardown.throw(exception)
    ~~~~~~~~~~~~~~^^^^^^^^^^^
  File "/opt/miniconda/envs/claude/lib/python3.14/site-packages/_pytest/warnings.py", line 128, in pytest_load_initial_conftests
    return (yield)
            ^^^^^
  File "/opt/miniconda/envs/claude/lib/python3.14/site-packages/pluggy/_callers.py", line 116, in _multicall
    next(function_gen)  # first yield
    ~~~~^^^^^^^^^^^^^^
  File "/opt/miniconda/envs/claude/lib/python3.14/site-packages/_pytest/capture.py", line 170, in pytest_load_initial_conftests
    capman.start_global_capturing()
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^
  File "/opt/miniconda/envs/claude/lib/python3.14/site-packages/_pytest/capture.py", line 773, in start_global_capturing
    self._global_capturing = _get_multicapture(self._method)
                             ~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^
  File "/opt/miniconda/envs/claude/lib/python3.14/site-packages/_pytest/capture.py", line 714, in _get_multicapture
    return MultiCapture(in_=FDCapture(0), out=FDCapture(1), err=FDCapture(2))
                                              ~~~~~~~~~^^^
  File "/opt/miniconda/envs/claude/lib/python3.14/site-packages/_pytest/capture.py", line 493, in __init__
    TemporaryFile(buffering=0),
    ~~~~~~~~~~~~~^^^^^^^^^^^^^
  File "/opt/miniconda/envs/claude/lib/python3.14/tempfile.py", line 652, in TemporaryFile
    prefix, suffix, dir, output_type = _sanitize_params(prefix, suffix, dir)
                                       ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^
  File "/opt/miniconda/envs/claude/lib/python3.14/tempfile.py", line 126, in _sanitize_params
    dir = gettempdir()
  File "/opt/miniconda/envs/claude/lib/python3.14/tempfile.py", line 316, in gettempdir
    return _os.fsdecode(_gettempdir())
                        ~~~~~~~~~~~^^
  File "/opt/miniconda/envs/claude/lib/python3.14/tempfile.py", line 309, in _gettempdir
    tempdir = _get_default_tempdir()
  File "/opt/miniconda/envs/claude/lib/python3.14/tempfile.py", line 224, in _get_default_tempdir
    raise FileNotFoundError(_errno.ENOENT,
                            "No usable temporary directory found in %s" %
                            dirlist)
FileNotFoundError: [Errno 2] No usable temporary directory found in ['/tmp', '/var/tmp', '/usr/tmp', '/home/renmark/projects/ai-system/.claude/worktrees/agency-fastfollow']

[35m[3mcodex[0m[0m
One gap stands out in the test delta, so I’m checking whether existing tests elsewhere already cover the four older spine skills under active agency. If they don’t, this is under-built against the stated behavior-test requirement, even if the runtime code is likely correct.
[35m[3mexec[0m[0m
[1m/bin/bash -lc "nl -ba tests/test_agency_behavior.py | sed -n '1,180p'"[0m in /home/renmark/projects/ai-system/.claude/worktrees/agency-fastfollow
[32m succeeded in 0ms:[0m
     1	"""Behavioral tests for Agency Mode — proves CHANGES renmark behavior (AC11).
     2	
     3	Tests pin the observable contracts:
     4	- AC2: inactive agency leaves preamble byte-identical (no-op)
     5	- Spine vs non-spine routing (_AGENCY_SPINE_SKILLS)
     6	- AC4/REQ-20: active preamble carries fragment POINTER not inlined body
     7	- Fragment registration and on-demand loadability
     8	- Mode selection stays independent of agency state
     9	"""
    10	
    11	from __future__ import annotations
    12	
    13	from pathlib import Path
    14	
    15	from renmark import agency, context, lifecycle, mode
    16	
    17	# ── Repo root (the live project, not a tmp dir) ────────────────────────────────
    18	# Used to resolve plugin_root for load_fragment — body check in T4 requires
    19	# the real fragment, not a tmp synthetic copy.
    20	
    21	_REPO_ROOT = Path(__file__).resolve().parent.parent
    22	_PLUGIN_ROOT = _REPO_ROOT / "plugin"
    23	
    24	
    25	# ── Helpers ───────────────────────────────────────────────────────────────────
    26	
    27	
    28	def _init_state_dir(repo: Path) -> None:
    29	    """Create .renmark/state/ so agency writes don't fail on missing parent."""
    30	    (repo / ".renmark" / "state").mkdir(parents=True, exist_ok=True)
    31	
    32	
    33	# ── 1. Inactive preamble has no agency hint ────────────────────────────────────
    34	
    35	
    36	def test_inactive_preamble_has_no_agency_hint(tmp_path: Path) -> None:
    37	    """With agency inactive (fresh tmp repo), skill_preamble('start') must NOT
    38	    contain lifecycle._AGENCY_HINT_MARKER (AC2 — byte-identical when off)."""
    39	    _init_state_dir(tmp_path)
    40	    # Ensure agency is inactive (fresh repo — no agency.json → default inactive).
    41	    assert not agency.is_active(tmp_path)
    42	
    43	    result = lifecycle.skill_preamble(tmp_path, "start")
    44	    # None is acceptable (no hints at all); a string must not carry the marker.
    45	    if result is not None:
    46	        assert lifecycle._AGENCY_HINT_MARKER not in result, (
    47	            f"skill_preamble returned the agency hint for an inactive repo: {result!r}"
    48	        )
    49	
    50	
    51	def test_inactive_agency_note_is_byte_identical_passthrough(tmp_path: Path) -> None:
    52	    """Invariant #1 at the unit level: when agency is inactive, _with_agency_note
    53	    returns its input UNCHANGED (identity) — byte-identical, not merely
    54	    marker-free. Proven for every spine skill against a sentinel that shares no
    55	    text with the agency hint, so any appended/reordered content would fail."""
    56	    _init_state_dir(tmp_path)
    57	    assert not agency.is_active(tmp_path)
    58	    sentinel = "SENTINEL-preamble-xyz"
    59	    for skill in sorted(lifecycle._AGENCY_SPINE_SKILLS):
    60	        assert lifecycle._with_agency_note(tmp_path, skill, sentinel) == sentinel
    61	        # None must stay None too (no hint fabricated when there was none).
    62	        assert lifecycle._with_agency_note(tmp_path, skill, None) is None
    63	
    64	
    65	def test_agency_note_noop_for_nonaware_even_when_active(tmp_path: Path) -> None:
    66	    """Skills NOT in the agency-aware set pass through unchanged even when active.
    67	
    68	    (debug/audit are non-pipeline skills — they never get an agency hint.)"""
    69	    _init_state_dir(tmp_path)
    70	    agency.activate(tmp_path, current_phase="alpha", current_milestone="M1")
    71	    sentinel = "SENTINEL-preamble-xyz"
    72	    assert "debug" not in lifecycle._AGENCY_AWARE_SKILLS
    73	    assert lifecycle._with_agency_note(tmp_path, "debug", sentinel) == sentinel
    74	    assert lifecycle._with_agency_note(tmp_path, "audit", None) is None
    75	
    76	
    77	def test_all_pipeline_skills_gain_hint_when_active(tmp_path: Path) -> None:
    78	    """Fast-follow: every agency-aware pipeline skill — the spine PLUS
    79	    feature/plan/orchestrate/verify/codereview — surfaces the agency hint +
    80	    fragment pointer when agency is active."""
    81	    _init_state_dir(tmp_path)
    82	    agency.activate(tmp_path, current_phase="alpha", current_milestone="M1")
    83	    pointer = context.fragment_pointer("agency-delivery")
    84	    for skill in ("feature", "plan", "orchestrate", "verify", "codereview"):
    85	        note = lifecycle._with_agency_note(tmp_path, skill, None)
    86	        assert note is not None and lifecycle._AGENCY_HINT_MARKER in note, (
    87	            f"{skill} did not gain the agency hint when active: {note!r}"
    88	        )
    89	        assert pointer in note, f"{skill} note missing fragment pointer: {note!r}"
    90	
    91	
    92	# ── 2. Active spine preamble gains the hint ────────────────────────────────────
    93	
    94	
    95	def test_active_spine_preamble_gains_hint(tmp_path: Path) -> None:
    96	    """After activate(repo, current_phase='alpha', current_milestone='M1'),
    97	    skill_preamble(repo, 'start') must contain the marker AND the fragment pointer."""
    98	    _init_state_dir(tmp_path)
    99	    agency.activate(tmp_path, current_phase="alpha", current_milestone="M1")
   100	
   101	    result = lifecycle.skill_preamble(tmp_path, "start")
   102	    assert result is not None, (
   103	        "skill_preamble returned None for an active-agency spine skill; "
   104	        "expected a hint string containing the agency marker."
   105	    )
   106	    assert lifecycle._AGENCY_HINT_MARKER in result, (
   107	        f"Agency marker not found in active preamble for 'start': {result!r}"
   108	    )
   109	    pointer = context.fragment_pointer("agency-delivery")
   110	    assert pointer in result, (
   111	        f"Fragment pointer {pointer!r} not found in active preamble: {result!r}"
   112	    )
   113	
   114	
   115	# ── 3. Active non-spine preamble stays clean ──────────────────────────────────
   116	
   117	
   118	def test_active_nonaware_preamble_stays_clean(tmp_path: Path) -> None:
   119	    """With agency active, a NON-agency-aware skill ('debug') preamble must NOT
   120	    contain the agency hint marker."""
   121	    _init_state_dir(tmp_path)
   122	    agency.activate(tmp_path, current_phase="beta", current_milestone="M2")
   123	
   124	    # 'debug' is NOT in the agency-aware pipeline set
   125	    assert "debug" not in lifecycle._AGENCY_AWARE_SKILLS
   126	
   127	    result = lifecycle.skill_preamble(tmp_path, "debug")
   128	    if result is not None:
   129	        assert lifecycle._AGENCY_HINT_MARKER not in result, (
   130	            f"Agency hint leaked into non-aware skill 'debug': {result!r}"
   131	        )
   132	
   133	
   134	# ── 4. Active preamble carries POINTER not inlined body (AC4 / REQ-20) ────────
   135	
   136	
   137	def test_preamble_carries_pointer_not_body(tmp_path: Path) -> None:
   138	    """Active preamble must contain the fragment pointer but NOT inline the
   139	    fragment body (dynamic-loading guarantee: AC4 / REQ-20).
   140	
   141	    Loads the real agency-delivery.md body from the live plugin dir to pick a
   142	    distinctive substring, then asserts that substring is absent from the
   143	    preamble string.
   144	    """
   145	    _init_state_dir(tmp_path)
   146	    agency.activate(tmp_path, current_phase="alpha", current_milestone="M1")
   147	
   148	    result = lifecycle.skill_preamble(tmp_path, "start")
   149	    assert result is not None, (
   150	        "skill_preamble returned None for an active-agency spine skill."
   151	    )
   152	
   153	    # The pointer must be present.
   154	    pointer = context.fragment_pointer("agency-delivery")
   155	    assert pointer in result, (
   156	        f"Fragment pointer not found in preamble: {result!r}"
   157	    )
   158	
   159	    # Load the real body to find a distinctive phrase that should NOT be inlined.
   160	    body = context.load_fragment(_PLUGIN_ROOT, "agency-delivery")
   161	    # "milestone checkpoint" is a distinctive multi-word phrase in the fragment body
   162	    # that would only appear if the body were inlined.
   163	    distinctive = "milestone checkpoint"
   164	    assert distinctive in body, (
   165	        f"Sanity: expected {distinctive!r} in agency-delivery body — check fragment."
   166	    )
   167	    assert distinctive not in result, (
   168	        f"Fragment body appears to be inlined in the preamble (found {distinctive!r}). "
   169	        "Dynamic loading violated — preamble must carry the pointer only."
   170	    )
   171	
   172	
   173	# ── 5. Fragment registered and loadable ────────────────────────────────────────
   174	
   175	
   176	def test_fragment_registered_and_loadable() -> None:
   177	    """'agency-delivery' must be in context.fragment_names() AND load_fragment
   178	    must return a non-empty string that contains 'milestone'."""
   179	    names = context.fragment_names()
   180	    assert "agency-delivery" in names, (

[35m[3mexec[0m[0m
[1m/bin/bash -lc "rg -n \"skill_preamble\\(.*(prd|roadmap|finish|resume)|_with_agency_note\\(.*(prd|roadmap|finish|resume)|Agency Mode active\" tests -S"[0m in /home/renmark/projects/ai-system/.claude/worktrees/agency-fastfollow
[32m succeeded in 0ms:[0m
tests/test_lifecycle.py:540:    assert lifecycle.skill_preamble(tmp_path, "resume") is None
tests/test_lifecycle.py:550:    lifecycle.skill_preamble(tmp_path, "resume")
tests/test_lifecycle.py:591:    assert lifecycle.skill_preamble(tmp_path, "resume") is None  # B: minimal, records meta

[35m[3mexec[0m[0m
[1m/bin/bash -lc "nl -ba renmark/lifecycle.py | sed -n '728,770p'"[0m in /home/renmark/projects/ai-system/.claude/worktrees/agency-fastfollow
[32m succeeded in 0ms:[0m
   728	
   729	
   730	# Pipeline skills that receive an Agency Mode hint when agency is active.
   731	# v0.30.0 shipped the spine (start/prd/roadmap/finish/resume); the fast-follow
   732	# extends coverage to the remaining pipelines (feature/plan/orchestrate/verify/
   733	# codereview) so the whole delivery loop is agency-aware.
   734	_AGENCY_AWARE_SKILLS: frozenset[str] = frozenset(
   735	    {
   736	        "start", "prd", "roadmap", "finish", "resume",
   737	        "feature", "plan", "orchestrate", "verify", "codereview",
   738	    }
   739	)
   740	
   741	# Back-compat alias: the original spine-only name still resolves.
   742	_AGENCY_SPINE_SKILLS: frozenset[str] = _AGENCY_AWARE_SKILLS
   743	
   744	# Marker string used to identify the agency hint line — load-bearing for
   745	# behavior tests (T15): assert active preamble contains this prefix and
   746	# inactive preamble does NOT.
   747	_AGENCY_HINT_MARKER: str = "Agency Mode active"
   748	
   749	
   750	def _with_agency_note(repo: Path | str, skill: str, hint: str | None) -> str | None:
   751	    """ADDITIVE: append an Agency Mode hint to ``hint`` when agency is active.
   752	
   753	    Only surfaces the hint for AGENCY-AWARE pipeline skills (the spine —
   754	    start/prd/roadmap/finish/resume — plus feature/plan/orchestrate/verify/
   755	    codereview) — all other skills are passed through unchanged regardless of
   756	    agency state.
   757	
   758	    When agency is INACTIVE the return value is byte-identical to ``hint``
   759	    (the inactive-path guarantee). DEGRADES GRACEFULLY: any exception in
   760	    agency/context resolution falls back to ``hint`` unchanged, so agency is
   761	    a pure enhancement and never a hard dependency of the preamble.
   762	
   763	    Follows the same additive pattern as :func:`_with_mode_note` and
   764	    :func:`_with_headless_note`.
   765	    """
   766	    if skill not in _AGENCY_AWARE_SKILLS:
   767	        return hint
   768	    try:
   769	        from . import agency as _agency
   770	        from . import context as _context

[35m[3mcodex[0m[0m
Spec: under-built — `tests/test_agency_behavior.py` does not actually assert that all 10 agency-aware skills gain the hint when active; it covers `start` plus the 5 new skills, but omits active checks for `prd`, `roadmap`, `finish`, and `resume`.

Quality: 0 Critical, 1 Major, 0 Minor, 1 Nit

`tests/test_agency_behavior.py:77` | Major | The new “all pipeline skills” test claims to cover the full 10-skill agency-aware set, but its loop only checks `feature`, `plan`, `orchestrate`, `verify`, and `codereview`, leaving `prd`, `roadmap`, `finish`, and `resume` unverified in the active path. | Change the test to iterate `sorted(lifecycle._AGENCY_AWARE_SKILLS)` or add explicit active assertions for the four omitted legacy skills.

`tests/test_agency_behavior.py:5` | Nit | The module docstring and section labels still describe “spine vs non-spine” behavior even though the implementation now uses the broader agency-aware set, which leaves stale terminology in the canonical behavior test. | Rename the docstring/comments to “agency-aware vs non-aware” so the test file matches the new contract and avoids future confusion.

`pytest -q tests/test_agency_behavior.py` could not be run to completion here because the sandbox has no usable temporary directory, so the verdict is based on static diff review plus reference checks.
[2mtokens used[0m
98,973
Spec: under-built — `tests/test_agency_behavior.py` does not actually assert that all 10 agency-aware skills gain the hint when active; it covers `start` plus the 5 new skills, but omits active checks for `prd`, `roadmap`, `finish`, and `resume`.

Quality: 0 Critical, 1 Major, 0 Minor, 1 Nit

`tests/test_agency_behavior.py:77` | Major | The new “all pipeline skills” test claims to cover the full 10-skill agency-aware set, but its loop only checks `feature`, `plan`, `orchestrate`, `verify`, and `codereview`, leaving `prd`, `roadmap`, `finish`, and `resume` unverified in the active path. | Change the test to iterate `sorted(lifecycle._AGENCY_AWARE_SKILLS)` or add explicit active assertions for the four omitted legacy skills.

`tests/test_agency_behavior.py:5` | Nit | The module docstring and section labels still describe “spine vs non-spine” behavior even though the implementation now uses the broader agency-aware set, which leaves stale terminology in the canonical behavior test. | Rename the docstring/comments to “agency-aware vs non-aware” so the test file matches the new contract and avoids future confusion.

`pytest -q tests/test_agency_behavior.py` could not be run to completion here because the sandbox has no usable temporary directory, so the verdict is based on static diff review plus reference checks.
