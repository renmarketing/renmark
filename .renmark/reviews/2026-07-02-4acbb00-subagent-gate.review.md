OpenAI Codex v0.117.0 (research preview)
--------
[1mworkdir:[0m /home/renmark/projects/ai-system/.claude/worktrees/subagent-gate
[1mmodel:[0m gpt-5.4
[1mprovider:[0m openai
[1mapproval:[0m never
[1msandbox:[0m read-only
[1mreasoning effort:[0m none
[1mreasoning summaries:[0m none
[1msession id:[0m 019f2507-9242-7883-9960-41d066ed1a3c
--------
[36muser[0m
Review the diff main..HEAD — a new enforced subagent-justification gate (renmark/subagent_gate.py + wiring). Emit TWO verdicts at the TOP.

━━ VERDICT 1 — Spec-compliance ━━
Goal: Turn the advisory deterministic-first/subagent gate into an ENFORCED zero-LLM pre-dispatch check. justify_task answers the 4 questions; challenge_plan rolls up; preview_line + main() CLI (exit 0/1/2, mirrors plan_lint). Must COMPOSE cost.is_deterministic_item/_get + subagent_profiles.resolve_profile/profile_tier (not re-implement); NEVER raise; general-purpose without role_reason challenged (#5). Wired into orchestrate pre-flight + fragments + CLAUDE/AGENTS. Excludes context thresholds/finish lanes/model routing (already shipped).
Emit: Spec: compliant | under-built — <what> | over-built — <what>

━━ VERDICT 2 — Code-quality ━━
Find real bugs: (1) never-raise actually holds? (2) challenge_plan invariant unjustified<=subagent_tasks; deterministic tasks not counted as spawns; (3) fragility of depending on underscored cost._get / cost.is_deterministic_item; (4) CLI exit codes; (5) est_tokens bool handling / complexity casing false pos/neg; (6) dead/duplicated logic.
Each finding: file:line | Critical|Major|Minor|Nit | desc | fix. Counts per severity at top. Do not modify files. Do not exit until complete.

[1m[33mwarning:[0m[0m Codex could not find system bubblewrap at /usr/bin/bwrap. Please install bubblewrap with your package manager. Codex will use the vendored bubblewrap in the meantime.
[35m[3mcodex[0m[0m
Reviewing `main..HEAD` for the enforced subagent gate. I’m pulling the diff and the touched files first, then I’ll check the implementation against the spec and look for concrete failure modes in the gate, CLI, and orchestration wiring.
[35m[3mexec[0m[0m
[1m/bin/bash -lc 'git diff --name-only main..HEAD'[0m in /home/renmark/projects/ai-system/.claude/worktrees/subagent-gate
[32m succeeded in 0ms:[0m
AGENTS.md
CHANGELOG.md
CLAUDE.md
plugin/skills/_shared/cost-preview.md
plugin/skills/_shared/deterministic-first.md
plugin/skills/_shared/subagent-budget.md
plugin/skills/orchestrate/SKILL.md
renmark/subagent_gate.py
tests/test_subagent_gate.py

[35m[3mexec[0m[0m
[1m/bin/bash -lc 'git diff --stat main..HEAD'[0m in /home/renmark/projects/ai-system/.claude/worktrees/subagent-gate
[32m succeeded in 0ms:[0m
 AGENTS.md                                    |   2 +-
 CHANGELOG.md                                 |   9 +
 CLAUDE.md                                    |   2 +-
 plugin/skills/_shared/cost-preview.md        |   9 +
 plugin/skills/_shared/deterministic-first.md |  17 ++
 plugin/skills/_shared/subagent-budget.md     |  10 ++
 plugin/skills/orchestrate/SKILL.md           |  15 +-
 renmark/subagent_gate.py                     | 249 +++++++++++++++++++++++++++
 tests/test_subagent_gate.py                  | 125 ++++++++++++++
 9 files changed, 435 insertions(+), 3 deletions(-)

[35m[3mexec[0m[0m
[1m/bin/bash -lc 'git rev-parse --show-toplevel'[0m in /home/renmark/projects/ai-system/.claude/worktrees/subagent-gate
[32m succeeded in 0ms:[0m
/home/renmark/projects/ai-system/.claude/worktrees/subagent-gate

[35m[3mcodex[0m[0m
The change is concentrated in `renmark/subagent_gate.py`, its tests, and orchestrate/docs wiring. I’m reading those next, plus the exact diff hunk, to check both spec coverage and whether the enforcement path actually holds end to end.
[35m[3mexec[0m[0m
[1m/bin/bash -lc 'git diff main..HEAD -- renmark/subagent_gate.py tests/test_subagent_gate.py plugin/skills/orchestrate/SKILL.md CLAUDE.md AGENTS.md plugin/skills/_shared/deterministic-first.md plugin/skills/_shared/subagent-budget.md plugin/skills/_shared/cost-preview.md CHANGELOG.md'[0m in /home/renmark/projects/ai-system/.claude/worktrees/subagent-gate
[32m succeeded in 0ms:[0m
diff --git a/AGENTS.md b/AGENTS.md
index 48c0d68..08bcd5f 100644
--- a/AGENTS.md
+++ b/AGENTS.md
@@ -66,7 +66,7 @@ renmark separates working context into four kinds: **static** (always-present `C
 
 **Model-routing discipline.** Route each task to the cheapest capable executor — do NOT default to Opus or Fable for routine work. Haiku = docs/grep/summaries/changelog/small audits. Sonnet = normal planning/impl/review/dispatch. Codex = bounded code/test (single file or tight scope). Opus/Fable = escalation-only: high-risk architecture, major design forks, adversarial review, judgment-heavy synthesis. Never default for finish, docs, grep, changelog, or small verification. See `CLAUDE.md` § `model-routing-discipline-rule` + `plugin/skills/_shared/model-routing.md` + `renmark/cost.py::requires_escalation`.
 
-**Deterministic-first execution.** Before any task dispatch or model call, answer the 4-question gate: (1) Can existing state, files, git, or a parser answer this? (2) Can a deterministic script/check do it reliably? (3) Is this repeated enough to deserve a reusable check? (4) Is AI actually needed for judgment, synthesis, or ambiguous reasoning? Deterministic tasks (git/worktree state, artifact metadata, version/release checks, plan lint, mirror validation, test baseline) route to deterministic checks in `renmark/worktree.py`, `renmark/lint.py`, or shell. Route judgment-heavy tasks (merge conflict risk, release-readiness reasoning, branch strategy) only to model-based agents. Cost preview MUST label tasks as deterministic or model-driven.
+**Deterministic-first execution.** Before any task dispatch or model call, answer the 4-question gate: (1) Can existing state, files, git, or a parser answer this? (2) Can a deterministic script/check do it reliably? (3) Is this repeated enough to deserve a reusable check? (4) Is AI actually needed for judgment, synthesis, or ambiguous reasoning? Deterministic tasks (git/worktree state, artifact metadata, version/release checks, plan lint, mirror validation, test baseline) route to deterministic checks in `renmark/worktree.py`, `renmark/lint.py`, or shell. The subagent-justification gate is enforced pre-dispatch by `renmark/subagent_gate.py` (`python -m renmark.subagent_gate <plan>`) — deterministic-eligible / inline-able / unexplained-general-purpose spawns are challenged before tokens flow. Route judgment-heavy tasks (merge conflict risk, release-readiness reasoning, branch strategy) only to model-based agents. Cost preview MUST label tasks as deterministic or model-driven.
 See `CLAUDE.md` § `deterministic-first-routing` + `plugin/skills/_shared/deterministic-first.md` + `renmark/worktree.py`.
 
 **Cost preview before expensive work.** Before dispatching any expensive or multi-model operation, show: tier / estimated token+cost band / whether subagents used / whether expensive models (Opus/Fable) required / cheaper alternative if one exists. Gate on user acknowledgment for escalated-tier work. See `CLAUDE.md` § `cost-preview-rule` + `plugin/skills/_shared/cost-preview.md` + `renmark/cost.py::estimate_cost`.
diff --git a/CHANGELOG.md b/CHANGELOG.md
index 78ef750..182e3a4 100644
--- a/CHANGELOG.md
+++ b/CHANGELOG.md
@@ -1,5 +1,14 @@
 # Changelog
 
+## [2026-07-02] — enforced subagent-justification gate (REQ-21 strengthening)
+**Request:** Usage report showed subagent-heavy, >150k-context sessions running unchallenged (general-purpose subagents recurring). Turn the advisory deterministic-first / subagent gate into an ENFORCED pre-dispatch check.
+**Built:**
+- `renmark/subagent_gate.py` — pure, zero-LLM gate. `justify_task` answers REQ-21's 4 questions mechanically (deterministic path? scoped role? orchestrator-inline? large/ambiguous enough?); `challenge_plan` rolls a plan up (deterministic-eligible / inline-able / unexplained-general-purpose spawns flagged); `preview_line` for the cost preview; `main()` CLI (`python -m renmark.subagent_gate <plan>` → exit 0 clean / 1 challenged / 2 usage), mirroring `plan_lint`. Composes `cost.is_deterministic_item`/`_get` + `subagent_profiles.resolve_profile`/`profile_tier` — does not re-implement. Never raises.
+- Wiring: orchestrate pre-flight runs the gate before dispatch and requires ack on a challenged plan; `_shared/{deterministic-first,subagent-budget,cost-preview}.md` document the gate as enforced (not advised); CLAUDE.md/AGENTS.md deterministic-first rule names the new helper.
+- `tests/test_subagent_gate.py` — 11 tests: deterministic→no-subagent, simple/tiny→inline-flagged, hard-scoped→clean, general-purpose-without-reason→challenged (+reason clears it), plan-level challenge invariants, never-raises.
+**Files changed:** renmark/subagent_gate.py (new), tests/test_subagent_gate.py (new), orchestrate/SKILL.md, 3 _shared/*.md, CLAUDE.md, AGENTS.md, CHANGELOG.md.
+**Do not change:** the gate is deterministic/zero-LLM and MUST never raise (degrades to "subagent needed" + flag); it composes cost/subagent_profiles, never re-implements; general-purpose without a `role_reason` is challenged (Codex rec #5). Codex recs #2 (context thresholds), #3 (finish lanes), #4 (model routing), #6 (deterministic/model cost split) were already shipped — NOT re-touched.
+
 ## [2026-07-02] — v0.31.0 — Agency Mode full pipeline coverage
 **Release.** Bumps v0.30.0 → v0.31.0. Releases the Agency Mode fast-follow: agency-awareness
 now spans ALL 10 pipeline skills (the v0.30.0 spine start/prd/roadmap/finish/resume PLUS
diff --git a/CLAUDE.md b/CLAUDE.md
index a333275..71c255e 100644
--- a/CLAUDE.md
+++ b/CLAUDE.md
@@ -174,7 +174,7 @@ See `plugin/skills/_shared/model-routing.md` + `renmark/cost.py::requires_escala
 <!-- END:model-routing-discipline-rule -->
 <!-- BEGIN:deterministic-first-routing -->
 ## Deterministic-first execution
-Before any task dispatch or model call, answer the 4-question gate: (1) Can existing state, files, git, or a parser answer this? (2) Can a deterministic script/check do it reliably? (3) Is this repeated enough to deserve a reusable check? (4) Is AI actually needed for judgment, synthesis, or ambiguous reasoning? Deterministic tasks (git/worktree state, artifact metadata, version/release checks, plan lint, mirror validation, test baseline) route to deterministic checks in `renmark/worktree.py`, `renmark/lint.py`, or shell. Route judgment-heavy tasks (merge conflict risk, release-readiness reasoning, branch strategy) only to model-based agents. Cost preview MUST label tasks as deterministic or model-driven.
+Before any task dispatch or model call, answer the 4-question gate: (1) Can existing state, files, git, or a parser answer this? (2) Can a deterministic script/check do it reliably? (3) Is this repeated enough to deserve a reusable check? (4) Is AI actually needed for judgment, synthesis, or ambiguous reasoning? Deterministic tasks (git/worktree state, artifact metadata, version/release checks, plan lint, mirror validation, test baseline) route to deterministic checks in `renmark/worktree.py`, `renmark/lint.py`, or shell. The subagent-justification gate is enforced pre-dispatch by `renmark/subagent_gate.py` (`python -m renmark.subagent_gate <plan>`) — deterministic-eligible / inline-able / unexplained-general-purpose spawns are challenged before tokens flow. Route judgment-heavy tasks (merge conflict risk, release-readiness reasoning, branch strategy) only to model-based agents. Cost preview MUST label tasks as deterministic or model-driven.
 See `plugin/skills/_shared/deterministic-first.md` + `renmark/worktree.py`.
 <!-- END:deterministic-first-routing -->
 <!-- BEGIN:cost-preview-rule -->
diff --git a/plugin/skills/_shared/cost-preview.md b/plugin/skills/_shared/cost-preview.md
index 44b548a..8aa638f 100644
--- a/plugin/skills/_shared/cost-preview.md
+++ b/plugin/skills/_shared/cost-preview.md
@@ -130,3 +130,12 @@ When citing in a SKILL.md, write:
 > *Show a cost preview before expensive work via `renmark/cost.py::estimate_cost`. Format per `${CLAUDE_PLUGIN_ROOT}/skills/_shared/cost-preview.md`: model tiers, token/cost band, subagent count, escalation justification (cite `requires_escalation`), and cheaper alternatives. Do not route to Opus/Fable without justifying and surfacing the cost.*
 
 Do not paste the matrix or examples into the calling SKILL.md — cite this file.
+
+## Subagent-gate line (required)
+
+Every pre-dispatch cost preview MUST include the subagent-gate verdict from
+`renmark.subagent_gate` — call `challenge_plan(tasks)` then `preview_line(...)`
+and show the line (e.g. `⚠ CHALLENGE: 3 of 5 subagent(s) unjustified; 2
+deterministic-eligible; 1 general-purpose`). When the verdict is challenged,
+the dispatch gate requires explicit acknowledgment before proceeding — a
+subagent-heavy or deterministic-eligible plan is never auto-dispatched silently.
diff --git a/plugin/skills/_shared/deterministic-first.md b/plugin/skills/_shared/deterministic-first.md
index 07adb7e..2d0285f 100644
--- a/plugin/skills/_shared/deterministic-first.md
+++ b/plugin/skills/_shared/deterministic-first.md
@@ -109,3 +109,20 @@ When citing this discipline in a SKILL.md or subagent dispatch, write:
 > *Honor deterministic-first discipline in `${CLAUDE_PLUGIN_ROOT}/skills/_shared/deterministic-first.md`: before any task dispatch or model call, answer the 4-question gate (existing state? script? reusable? AI-needed?). Deterministic checks: git/worktree state, artifact existence/metadata, version/release readiness, plan lint, mirror validation, test baseline. Route judgment-heavy tasks (merge risk, release-readiness reasoning, branch strategy) only to model-based agents. See `renmark/worktree.py` for shared checks.*
 
 Do not paste the gate or matrix into the calling SKILL.md — cite this file.
+
+## Enforcement (not just advice)
+
+The subagent side of this gate is now **enforced deterministically** by
+`renmark/subagent_gate.py` (zero-LLM). Before dispatching a plan, run it like
+`plan_lint`:
+
+```bash
+python -m renmark.subagent_gate <plan.md>   # exit 0 = clean, 1 = challenged, 2 = usage
+```
+
+It answers the 4 questions mechanically per task (`justify_task`) and rolls the
+plan up (`challenge_plan`): deterministic-eligible tasks, inline-able simple
+tasks, and unexplained `general-purpose` spawns are flagged BEFORE tokens flow.
+The cost preview surfaces `subagent_gate.preview_line(...)`. This turns REQ-21's
+"prefer deterministic / challenge subagents" from a rule the orchestrator is
+asked to follow into a check it must run.
diff --git a/plugin/skills/_shared/subagent-budget.md b/plugin/skills/_shared/subagent-budget.md
index 59c443b..c1e5f1f 100644
--- a/plugin/skills/_shared/subagent-budget.md
+++ b/plugin/skills/_shared/subagent-budget.md
@@ -101,3 +101,13 @@ When citing in a SKILL.md, write:
 > *Honor subagent budget discipline in `${CLAUDE_PLUGIN_ROOT}/skills/_shared/subagent-budget.md`: local-first (grep/read before spawning); each dispatch packet carries mission, files, output_format, stop_condition, model_tier, and verification_expectation; prefer cheaper models for read-only work; warn when >5 subagents are needed. Do not pass full skill bodies in dispatch packets (see `_shared/context-taxonomy.md`).*
 
 Do not paste the contract table or examples into the calling SKILL.md — cite this file.
+
+## Enforced pre-dispatch gate
+
+This budget is no longer advice-only: `renmark/subagent_gate.py` deterministically
+challenges a plan before dispatch (`python -m renmark.subagent_gate <plan>`).
+Every planned spawn must clear `justify_task` — deterministic-eligible work,
+inline-able simple tasks, and `general-purpose` roles without a stated
+`role_reason` are flagged. Assign a specialized profile (see
+`subagent-profiles.md`) or state a reason; don't dispatch a challenged plan
+without acknowledging the challenge.
diff --git a/plugin/skills/orchestrate/SKILL.md b/plugin/skills/orchestrate/SKILL.md
index 5c244fa..20d17b6 100644
--- a/plugin/skills/orchestrate/SKILL.md
+++ b/plugin/skills/orchestrate/SKILL.md
@@ -82,7 +82,20 @@ state.write_pipeline_state(repo, current_phase="orchestrate", current_plan=<plan
 
 **Changelog / decisions check** — read the last 5 entries in `CHANGELOG.md`, and when `.renmark/memory/decisions.md` is present, also read its decision titles + guard text (titles and guards only — never full bodies; REQ-5). Flag any "Do not change" guard or recorded decision the plan would contradict. A contradiction is **semantic**: the plan would undo or overwrite a guarded decision — and this binds even when there is **no target-file overlap** (a plan can violate a decision without touching the same file). On any such contradiction, surface it and **PAUSE for reconciliation** before dispatching; never silently overwrite a recorded decision.
 
-**Cost preview** — `renmark-execute --dry-run <plan>` shows the task list + estimated cost.
+**Subagent gate (deterministic, pre-dispatch)** — run the enforced justification gate before spending:
+
+```bash
+python -m renmark.subagent_gate <plan>   # exit 0 = clean, 1 = challenged
+```
+
+It challenges the plan per REQ-21's 4 questions (deterministic-eligible tasks,
+inline-able simple tasks, `general-purpose` roles without a `role_reason`). On a
+**challenged** verdict (exit 1), surface the one-line `preview_line` verdict and
+require explicit acknowledgment before dispatch — do NOT auto-proceed on a
+subagent-heavy or deterministic-eligible plan. Prefer converting flagged tasks to
+deterministic checks or assigning a scoped profile (`subagent-profiles.md`).
+
+**Cost preview** — `renmark-execute --dry-run <plan>` shows the task list + estimated cost. The cost preview MUST also carry the subagent-gate line (`renmark.subagent_gate.preview_line`), per `${CLAUDE_PLUGIN_ROOT}/skills/_shared/cost-preview.md`.
 
 **Headless gate (cost approval).** Before the `Proceed? [y/N]` prompt below, consult the headless contract (`plugin/skills/_shared/headless-contract.md`):
 
diff --git a/renmark/subagent_gate.py b/renmark/subagent_gate.py
new file mode 100644
index 0000000..a112b3e
--- /dev/null
+++ b/renmark/subagent_gate.py
@@ -0,0 +1,249 @@
+"""Enforced subagent-justification gate — the deterministic-first check that runs
+BEFORE any subagent is dispatched (strengthens REQ-21 from advice into a gate).
+
+Renmark already ships the *advice* (``_shared/deterministic-first.md`` 4-question
+gate, ``_shared/subagent-budget.md``) and the cost machinery that *tags*
+deterministic vs model-driven work (``renmark.cost``). What was missing is a pure,
+zero-LLM function the dispatch path can actually CALL to challenge a spawn — so a
+subagent-heavy, deterministic-eligible plan gets flagged before tokens flow.
+
+This module composes the existing pieces — it does NOT re-implement them:
+- ``renmark.cost.is_deterministic_item`` — the deterministic/model-driven signal.
+- ``renmark.cost._get`` — the dict/attr accessor.
+- ``renmark.subagent_profiles.resolve_profile`` / ``profile_tier`` — the scoped
+  role + cheapest-capable tier (``general-purpose`` is fallback-only).
+
+Every function is pure and NEVER raises — on any bad input it degrades to the
+safe/conservative answer (assume a subagent IS needed rather than silently
+suppressing one), so the gate can never break a real dispatch.
+
+The 4 questions (deterministic-first.md), answered mechanically where possible:
+  Q1 Can git/grep/read/parser/state answer this?     → deterministic-eligible
+  Q2 Can a deterministic script/check answer this?    → deterministic-eligible
+  Q3 Can the orchestrator do this directly (no agent)? → trivial/simple + tiny
+  Q4 Is it large/ambiguous enough to justify a subagent? → complexity/size
+"""
+
+from __future__ import annotations
+
+from dataclasses import dataclass, field
+from typing import Any
+
+from renmark import cost, subagent_profiles
+
+# Complexity labels that, on their own, justify a subagent (Q4).
+_SUBAGENT_JUSTIFYING_COMPLEXITY: frozenset[str] = frozenset({"hard", "medium"})
+
+# Below this token estimate a "simple" task is cheap enough for the orchestrator
+# to do inline (Q3) rather than paying ~10k agent-overhead to dispatch it.
+_DIRECT_TOKEN_CEILING: int = 400
+
+
+@dataclass(frozen=True)
+class SubagentVerdict:
+    """The per-task justification verdict.
+
+    ``needs_subagent`` — the gate's recommendation (False = answerable without a
+    subagent). ``challenge`` — a non-None one-liner when the spawn is
+    questionable (deterministic-eligible, orchestrator-doable, or an unjustified
+    general-purpose role); None means the spawn is clean.
+    """
+
+    needs_subagent: bool
+    deterministic_eligible: bool
+    role: str
+    tier: str
+    reason: str
+    challenge: str | None = None
+
+
+@dataclass(frozen=True)
+class PlanChallenge:
+    """Plan-level rollup used by the cost preview to challenge a plan."""
+
+    total: int = 0
+    subagent_tasks: int = 0
+    deterministic_eligible: int = 0
+    unjustified: int = 0
+    general_purpose: int = 0
+    flagged_indices: tuple[int, ...] = field(default_factory=tuple)
+    challenged: bool = False
+    message: str = ""
+
+
+def justify_task(task: Any) -> SubagentVerdict:
+    """Return the justification :class:`SubagentVerdict` for one planned task.
+
+    Pure, zero-LLM, never raises. Accepts a dict or any object exposing
+    ``executor`` / ``complexity`` / ``est_tokens`` / ``role`` / ``role_reason``.
+    """
+    try:
+        # Q1 + Q2 — a deterministic path exists → no subagent needed.
+        if cost.is_deterministic_item(task):
+            return SubagentVerdict(
+                needs_subagent=False,
+                deterministic_eligible=True,
+                role="deterministic",
+                tier="none",
+                reason="deterministic path (git/grep/parser/state or deterministic executor)",
+                challenge="deterministic-eligible — resolve via a check/script, not a subagent",
+            )
+
+        role = subagent_profiles.resolve_profile(task)
+        tier = subagent_profiles.profile_tier(role)
+        complexity = str(cost._get(task, "complexity", "") or "").strip().lower()
+        raw_tokens = cost._get(task, "est_tokens", 0)
+        est_tokens = raw_tokens if isinstance(raw_tokens, int) and not isinstance(raw_tokens, bool) else 0
+
+        # Q3 — a trivial/simple, tiny task the orchestrator can do inline.
+        if complexity in ("", "simple") and 0 < est_tokens <= _DIRECT_TOKEN_CEILING:
+            return SubagentVerdict(
+                needs_subagent=False,
+                deterministic_eligible=False,
+                role=role,
+                tier=tier,
+                reason=f"simple + ~{est_tokens} tok — orchestrator can do this inline",
+                challenge="small/simple — do it inline or route to haiku, not a scoped subagent",
+            )
+
+        # Q4 — large/ambiguous enough → a subagent is justified.
+        justified = complexity in _SUBAGENT_JUSTIFYING_COMPLEXITY or est_tokens > _DIRECT_TOKEN_CEILING
+
+        challenge: str | None = None
+        if role == "general-purpose":
+            reason_field = str(cost._get(task, "role_reason", "") or "").strip()
+            if not reason_field:
+                challenge = (
+                    "general-purpose without a scoped role — assign a specialized "
+                    "profile (docs-editor/code-implementer/test-writer/reviewer/…) "
+                    "or state role_reason"
+                )
+        elif not justified:
+            challenge = "no hard/medium/large signal — confirm a subagent is warranted"
+
+        return SubagentVerdict(
+            needs_subagent=justified or role != "general-purpose",
+            deterministic_eligible=False,
+            role=role,
+            tier=tier,
+            reason=(
+                f"{complexity or 'unspecified'} complexity, ~{est_tokens} tok, role={role}"
+            ),
+            challenge=challenge,
+        )
+    except Exception:
+        # Conservative fallback: assume a subagent is needed (never suppress work
+        # by accident), but flag it so the human still sees the uncertainty.
+        return SubagentVerdict(
+            needs_subagent=True,
+            deterministic_eligible=False,
+            role="general-purpose",
+            tier="sonnet",
+            reason="gate could not classify this task",
+            challenge="gate could not classify — review before dispatch",
+        )
+
+
+def challenge_plan(tasks: Any, *, unjustified_share_threshold: float = 0.5) -> PlanChallenge:
+    """Roll :func:`justify_task` up across a plan and decide whether to challenge it.
+
+    ``challenged`` is True when at least ``unjustified_share_threshold`` of the
+    would-be-subagent tasks are unjustified (deterministic-eligible, inline-able,
+    or unexplained general-purpose), OR when any general-purpose spawn lacks a
+    reason. Pure, never raises — an unusable ``tasks`` yields an empty, unchallenged
+    rollup.
+    """
+    try:
+        items = list(tasks)
+    except Exception:
+        return PlanChallenge()
+
+    total = 0
+    subagent_tasks = 0            # non-deterministic tasks that would spawn a subagent
+    deterministic_eligible = 0    # tasks a check/script should replace (NOT spawns)
+    unjustified = 0              # spawns that are challenged (inline-able / gp-no-reason / no-signal)
+    general_purpose = 0
+    gp_without_reason = False
+    flagged: list[int] = []
+
+    for idx, task in enumerate(items):
+        total += 1
+        v = justify_task(task)
+        if v.deterministic_eligible:
+            # A deterministic path exists — this is a "make it a check" win, not a
+            # subagent spawn. Bucket it separately and flag it for the human.
+            deterministic_eligible += 1
+            flagged.append(idx)
+            continue
+        # Every non-deterministic task is an INTENDED model spawn in the plan.
+        subagent_tasks += 1
+        if v.role == "general-purpose":
+            general_purpose += 1
+            if v.challenge is not None:
+                gp_without_reason = True
+        if v.challenge is not None:
+            unjustified += 1
+            flagged.append(idx)
+
+    share = (unjustified / subagent_tasks) if subagent_tasks else 0.0
+    challenged = (
+        (subagent_tasks > 0 and share >= unjustified_share_threshold)
+        or gp_without_reason
+        or deterministic_eligible > 0
+    )
+
+    message = (
+        f"{unjustified} of {subagent_tasks} subagent(s) unjustified; "
+        f"{deterministic_eligible} deterministic-eligible; "
+        f"{general_purpose} general-purpose"
+        if challenged
+        else f"subagent plan OK ({subagent_tasks} justified, "
+        f"{deterministic_eligible} deterministic)"
+    )
+
+    return PlanChallenge(
+        total=total,
+        subagent_tasks=subagent_tasks,
+        deterministic_eligible=deterministic_eligible,
+        unjustified=unjustified,
+        general_purpose=general_purpose,
+        flagged_indices=tuple(flagged),
+        challenged=challenged,
+        message=message,
+    )
+
+
+def preview_line(challenge: PlanChallenge) -> str:
+    """One bounded line for the cost preview (deterministic-first labelling)."""
+    tag = "⚠ CHALLENGE" if challenge.challenged else "✓ subagent gate"
+    return f"{tag}: {challenge.message}"
+
+
+def main(argv: list[str] | None = None) -> int:
+    """CLI: ``python -m renmark.subagent_gate <plan.md>``.
+
+    Deterministic pre-flight gate — mirrors ``python -m renmark.plan_lint``. Prints
+    the one-line challenge verdict and exits 0 when the subagent plan is clean, 1
+    when it is challenged (a deterministic path exists, an unjustified spawn, or an
+    unexplained general-purpose role). Exit 2 on a usage/parse error. Zero-LLM.
+    """
+    import sys
+
+    from renmark import parser
+
+    args = argv if argv is not None else sys.argv[1:]
+    if not args:
+        sys.stderr.write("usage: python -m renmark.subagent_gate <plan.md>\n")
+        return 2
+    try:
+        tasks = parser.parse_plan(args[0])
+    except Exception as exc:
+        sys.stderr.write(f"subagent-gate: cannot read plan: {exc}\n")
+        return 2
+    ch = challenge_plan(tasks)
+    sys.stdout.write(preview_line(ch) + "\n")
+    return 1 if ch.challenged else 0
+
+
+if __name__ == "__main__":
+    raise SystemExit(main())
diff --git a/tests/test_subagent_gate.py b/tests/test_subagent_gate.py
new file mode 100644
index 0000000..d24bb64
--- /dev/null
+++ b/tests/test_subagent_gate.py
@@ -0,0 +1,125 @@
+"""Tests for the enforced subagent-justification gate (renmark.subagent_gate).
+
+Proves the deterministic-first gate CHALLENGES a spawn before dispatch:
+- common checks resolve to no-subagent (deterministic path),
+- a simple/tiny task is flagged as inline-able,
+- a genuinely hard scoped task passes clean,
+- general-purpose without a reason is challenged (and a reason clears it),
+- a subagent-heavy / deterministic-eligible plan gets challenged,
+- everything degrades safe and never raises.
+"""
+
+from __future__ import annotations
+
+from renmark import subagent_gate as g
+
+# ── per-task justification ────────────────────────────────────────────────────
+
+
+def test_deterministic_task_needs_no_subagent() -> None:
+    v = g.justify_task({"mode": "deterministic"})
+    assert v.needs_subagent is False
+    assert v.deterministic_eligible is True
+    assert v.challenge is not None  # "resolve via a check, not a subagent"
+
+
+def test_deterministic_executor_needs_no_subagent() -> None:
+    # A deterministic executor (script/check/tool/code/none) is caught by
+    # cost.is_deterministic_item.
+    v = g.justify_task({"executor": "script"})
+    assert v.deterministic_eligible is True
+    assert v.needs_subagent is False
+
+
+def test_simple_tiny_task_is_inline_flagged() -> None:
+    v = g.justify_task(
+        {"executor": "haiku", "complexity": "simple", "est_tokens": 200, "target": "a.md"}
+    )
+    assert v.needs_subagent is False
+    assert v.challenge is not None
+    assert "inline" in v.challenge or "haiku" in v.challenge
+
+
+def test_hard_scoped_task_passes_clean() -> None:
+    v = g.justify_task(
+        {"executor": "opus", "complexity": "hard", "est_tokens": 2000,
+         "target": "renmark/foo.py"}
+    )
+    assert v.needs_subagent is True
+    assert v.role != "general-purpose"      # a scoped role was resolved
+    assert v.challenge is None
+
+
+def test_general_purpose_without_reason_is_challenged() -> None:
+    v = g.justify_task(
+        {"executor": "sonnet", "complexity": "medium", "est_tokens": 1000,
+         "target": "notes.txt"}
+    )
+    assert v.role == "general-purpose"
+    assert v.challenge is not None
+    assert "general-purpose" in v.challenge
+
+
+def test_general_purpose_with_reason_clears_challenge() -> None:
+    v = g.justify_task(
+        {"executor": "sonnet", "complexity": "medium", "est_tokens": 1000,
+         "target": "notes.txt", "role_reason": "cross-cutting spike, no single role fits"}
+    )
+    assert v.role == "general-purpose"
+    assert v.challenge is None
+    assert v.needs_subagent is True
+
+
+# ── plan-level challenge ──────────────────────────────────────────────────────
+
+
+def test_plan_with_deterministic_and_gp_is_challenged() -> None:
+    plan = [
+        {"mode": "deterministic"},
+        {"executor": "haiku", "complexity": "simple", "est_tokens": 200, "target": "a.md"},
+        {"executor": "opus", "complexity": "hard", "est_tokens": 2000, "target": "b.py"},
+    ]
+    pc = g.challenge_plan(plan)
+    assert pc.challenged is True
+    assert pc.deterministic_eligible == 1
+    assert pc.unjustified <= pc.subagent_tasks      # invariant: never over-count
+    assert pc.total == 3
+    assert g.preview_line(pc).startswith("⚠")
+
+
+def test_clean_scoped_plan_is_not_challenged() -> None:
+    plan = [
+        {"executor": "opus", "complexity": "hard", "est_tokens": 2000, "target": "renmark/x.py"},
+        {"executor": "codex", "complexity": "medium", "est_tokens": 900, "target": "tests/test_x.py"},
+    ]
+    pc = g.challenge_plan(plan)
+    assert pc.challenged is False
+    assert pc.unjustified == 0
+    assert g.preview_line(pc).startswith("✓")
+
+
+def test_all_deterministic_plan_flags_every_task() -> None:
+    plan = [{"mode": "deterministic"}, {"executor": "script"}]
+    pc = g.challenge_plan(plan)
+    assert pc.deterministic_eligible == 2
+    assert pc.subagent_tasks == 0
+    assert pc.challenged is True   # a cheaper (all-deterministic) path exists
+
+
+# ── safety: never raises ──────────────────────────────────────────────────────
+
+
+def test_gate_never_raises_on_garbage() -> None:
+    for bad in (None, 123, "x", object()):
+        v = g.justify_task(bad)
+        assert isinstance(v, g.SubagentVerdict)
+    for bad_plan in (None, 123, object()):
+        pc = g.challenge_plan(bad_plan)
+        assert isinstance(pc, g.PlanChallenge)
+        assert pc.total == 0
+
+
+def test_empty_plan_is_not_challenged() -> None:
+    pc = g.challenge_plan([])
+    assert pc.total == 0
+    assert pc.challenged is False

[35m[3mexec[0m[0m
[1m/bin/bash -lc "sed -n '1,260p' renmark/subagent_gate.py"[0m in /home/renmark/projects/ai-system/.claude/worktrees/subagent-gate
[32m succeeded in 0ms:[0m
"""Enforced subagent-justification gate — the deterministic-first check that runs
BEFORE any subagent is dispatched (strengthens REQ-21 from advice into a gate).

Renmark already ships the *advice* (``_shared/deterministic-first.md`` 4-question
gate, ``_shared/subagent-budget.md``) and the cost machinery that *tags*
deterministic vs model-driven work (``renmark.cost``). What was missing is a pure,
zero-LLM function the dispatch path can actually CALL to challenge a spawn — so a
subagent-heavy, deterministic-eligible plan gets flagged before tokens flow.

This module composes the existing pieces — it does NOT re-implement them:
- ``renmark.cost.is_deterministic_item`` — the deterministic/model-driven signal.
- ``renmark.cost._get`` — the dict/attr accessor.
- ``renmark.subagent_profiles.resolve_profile`` / ``profile_tier`` — the scoped
  role + cheapest-capable tier (``general-purpose`` is fallback-only).

Every function is pure and NEVER raises — on any bad input it degrades to the
safe/conservative answer (assume a subagent IS needed rather than silently
suppressing one), so the gate can never break a real dispatch.

The 4 questions (deterministic-first.md), answered mechanically where possible:
  Q1 Can git/grep/read/parser/state answer this?     → deterministic-eligible
  Q2 Can a deterministic script/check answer this?    → deterministic-eligible
  Q3 Can the orchestrator do this directly (no agent)? → trivial/simple + tiny
  Q4 Is it large/ambiguous enough to justify a subagent? → complexity/size
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from renmark import cost, subagent_profiles

# Complexity labels that, on their own, justify a subagent (Q4).
_SUBAGENT_JUSTIFYING_COMPLEXITY: frozenset[str] = frozenset({"hard", "medium"})

# Below this token estimate a "simple" task is cheap enough for the orchestrator
# to do inline (Q3) rather than paying ~10k agent-overhead to dispatch it.
_DIRECT_TOKEN_CEILING: int = 400


@dataclass(frozen=True)
class SubagentVerdict:
    """The per-task justification verdict.

    ``needs_subagent`` — the gate's recommendation (False = answerable without a
    subagent). ``challenge`` — a non-None one-liner when the spawn is
    questionable (deterministic-eligible, orchestrator-doable, or an unjustified
    general-purpose role); None means the spawn is clean.
    """

    needs_subagent: bool
    deterministic_eligible: bool
    role: str
    tier: str
    reason: str
    challenge: str | None = None


@dataclass(frozen=True)
class PlanChallenge:
    """Plan-level rollup used by the cost preview to challenge a plan."""

    total: int = 0
    subagent_tasks: int = 0
    deterministic_eligible: int = 0
    unjustified: int = 0
    general_purpose: int = 0
    flagged_indices: tuple[int, ...] = field(default_factory=tuple)
    challenged: bool = False
    message: str = ""


def justify_task(task: Any) -> SubagentVerdict:
    """Return the justification :class:`SubagentVerdict` for one planned task.

    Pure, zero-LLM, never raises. Accepts a dict or any object exposing
    ``executor`` / ``complexity`` / ``est_tokens`` / ``role`` / ``role_reason``.
    """
    try:
        # Q1 + Q2 — a deterministic path exists → no subagent needed.
        if cost.is_deterministic_item(task):
            return SubagentVerdict(
                needs_subagent=False,
                deterministic_eligible=True,
                role="deterministic",
                tier="none",
                reason="deterministic path (git/grep/parser/state or deterministic executor)",
                challenge="deterministic-eligible — resolve via a check/script, not a subagent",
            )

        role = subagent_profiles.resolve_profile(task)
        tier = subagent_profiles.profile_tier(role)
        complexity = str(cost._get(task, "complexity", "") or "").strip().lower()
        raw_tokens = cost._get(task, "est_tokens", 0)
        est_tokens = raw_tokens if isinstance(raw_tokens, int) and not isinstance(raw_tokens, bool) else 0

        # Q3 — a trivial/simple, tiny task the orchestrator can do inline.
        if complexity in ("", "simple") and 0 < est_tokens <= _DIRECT_TOKEN_CEILING:
            return SubagentVerdict(
                needs_subagent=False,
                deterministic_eligible=False,
                role=role,
                tier=tier,
                reason=f"simple + ~{est_tokens} tok — orchestrator can do this inline",
                challenge="small/simple — do it inline or route to haiku, not a scoped subagent",
            )

        # Q4 — large/ambiguous enough → a subagent is justified.
        justified = complexity in _SUBAGENT_JUSTIFYING_COMPLEXITY or est_tokens > _DIRECT_TOKEN_CEILING

        challenge: str | None = None
        if role == "general-purpose":
            reason_field = str(cost._get(task, "role_reason", "") or "").strip()
            if not reason_field:
                challenge = (
                    "general-purpose without a scoped role — assign a specialized "
                    "profile (docs-editor/code-implementer/test-writer/reviewer/…) "
                    "or state role_reason"
                )
        elif not justified:
            challenge = "no hard/medium/large signal — confirm a subagent is warranted"

        return SubagentVerdict(
            needs_subagent=justified or role != "general-purpose",
            deterministic_eligible=False,
            role=role,
            tier=tier,
            reason=(
                f"{complexity or 'unspecified'} complexity, ~{est_tokens} tok, role={role}"
            ),
            challenge=challenge,
        )
    except Exception:
        # Conservative fallback: assume a subagent is needed (never suppress work
        # by accident), but flag it so the human still sees the uncertainty.
        return SubagentVerdict(
            needs_subagent=True,
            deterministic_eligible=False,
            role="general-purpose",
            tier="sonnet",
            reason="gate could not classify this task",
            challenge="gate could not classify — review before dispatch",
        )


def challenge_plan(tasks: Any, *, unjustified_share_threshold: float = 0.5) -> PlanChallenge:
    """Roll :func:`justify_task` up across a plan and decide whether to challenge it.

    ``challenged`` is True when at least ``unjustified_share_threshold`` of the
    would-be-subagent tasks are unjustified (deterministic-eligible, inline-able,
    or unexplained general-purpose), OR when any general-purpose spawn lacks a
    reason. Pure, never raises — an unusable ``tasks`` yields an empty, unchallenged
    rollup.
    """
    try:
        items = list(tasks)
    except Exception:
        return PlanChallenge()

    total = 0
    subagent_tasks = 0            # non-deterministic tasks that would spawn a subagent
    deterministic_eligible = 0    # tasks a check/script should replace (NOT spawns)
    unjustified = 0              # spawns that are challenged (inline-able / gp-no-reason / no-signal)
    general_purpose = 0
    gp_without_reason = False
    flagged: list[int] = []

    for idx, task in enumerate(items):
        total += 1
        v = justify_task(task)
        if v.deterministic_eligible:
            # A deterministic path exists — this is a "make it a check" win, not a
            # subagent spawn. Bucket it separately and flag it for the human.
            deterministic_eligible += 1
            flagged.append(idx)
            continue
        # Every non-deterministic task is an INTENDED model spawn in the plan.
        subagent_tasks += 1
        if v.role == "general-purpose":
            general_purpose += 1
            if v.challenge is not None:
                gp_without_reason = True
        if v.challenge is not None:
            unjustified += 1
            flagged.append(idx)

    share = (unjustified / subagent_tasks) if subagent_tasks else 0.0
    challenged = (
        (subagent_tasks > 0 and share >= unjustified_share_threshold)
        or gp_without_reason
        or deterministic_eligible > 0
    )

    message = (
        f"{unjustified} of {subagent_tasks} subagent(s) unjustified; "
        f"{deterministic_eligible} deterministic-eligible; "
        f"{general_purpose} general-purpose"
        if challenged
        else f"subagent plan OK ({subagent_tasks} justified, "
        f"{deterministic_eligible} deterministic)"
    )

    return PlanChallenge(
        total=total,
        subagent_tasks=subagent_tasks,
        deterministic_eligible=deterministic_eligible,
        unjustified=unjustified,
        general_purpose=general_purpose,
        flagged_indices=tuple(flagged),
        challenged=challenged,
        message=message,
    )


def preview_line(challenge: PlanChallenge) -> str:
    """One bounded line for the cost preview (deterministic-first labelling)."""
    tag = "⚠ CHALLENGE" if challenge.challenged else "✓ subagent gate"
    return f"{tag}: {challenge.message}"


def main(argv: list[str] | None = None) -> int:
    """CLI: ``python -m renmark.subagent_gate <plan.md>``.

    Deterministic pre-flight gate — mirrors ``python -m renmark.plan_lint``. Prints
    the one-line challenge verdict and exits 0 when the subagent plan is clean, 1
    when it is challenged (a deterministic path exists, an unjustified spawn, or an
    unexplained general-purpose role). Exit 2 on a usage/parse error. Zero-LLM.
    """
    import sys

    from renmark import parser

    args = argv if argv is not None else sys.argv[1:]
    if not args:
        sys.stderr.write("usage: python -m renmark.subagent_gate <plan.md>\n")
        return 2
    try:
        tasks = parser.parse_plan(args[0])
    except Exception as exc:
        sys.stderr.write(f"subagent-gate: cannot read plan: {exc}\n")
        return 2
    ch = challenge_plan(tasks)
    sys.stdout.write(preview_line(ch) + "\n")
    return 1 if ch.challenged else 0


if __name__ == "__main__":
    raise SystemExit(main())

[35m[3mexec[0m[0m
[1m/bin/bash -lc "sed -n '1,260p' tests/test_subagent_gate.py"[0m in /home/renmark/projects/ai-system/.claude/worktrees/subagent-gate
[32m succeeded in 0ms:[0m
"""Tests for the enforced subagent-justification gate (renmark.subagent_gate).

Proves the deterministic-first gate CHALLENGES a spawn before dispatch:
- common checks resolve to no-subagent (deterministic path),
- a simple/tiny task is flagged as inline-able,
- a genuinely hard scoped task passes clean,
- general-purpose without a reason is challenged (and a reason clears it),
- a subagent-heavy / deterministic-eligible plan gets challenged,
- everything degrades safe and never raises.
"""

from __future__ import annotations

from renmark import subagent_gate as g

# ── per-task justification ────────────────────────────────────────────────────


def test_deterministic_task_needs_no_subagent() -> None:
    v = g.justify_task({"mode": "deterministic"})
    assert v.needs_subagent is False
    assert v.deterministic_eligible is True
    assert v.challenge is not None  # "resolve via a check, not a subagent"


def test_deterministic_executor_needs_no_subagent() -> None:
    # A deterministic executor (script/check/tool/code/none) is caught by
    # cost.is_deterministic_item.
    v = g.justify_task({"executor": "script"})
    assert v.deterministic_eligible is True
    assert v.needs_subagent is False


def test_simple_tiny_task_is_inline_flagged() -> None:
    v = g.justify_task(
        {"executor": "haiku", "complexity": "simple", "est_tokens": 200, "target": "a.md"}
    )
    assert v.needs_subagent is False
    assert v.challenge is not None
    assert "inline" in v.challenge or "haiku" in v.challenge


def test_hard_scoped_task_passes_clean() -> None:
    v = g.justify_task(
        {"executor": "opus", "complexity": "hard", "est_tokens": 2000,
         "target": "renmark/foo.py"}
    )
    assert v.needs_subagent is True
    assert v.role != "general-purpose"      # a scoped role was resolved
    assert v.challenge is None


def test_general_purpose_without_reason_is_challenged() -> None:
    v = g.justify_task(
        {"executor": "sonnet", "complexity": "medium", "est_tokens": 1000,
         "target": "notes.txt"}
    )
    assert v.role == "general-purpose"
    assert v.challenge is not None
    assert "general-purpose" in v.challenge


def test_general_purpose_with_reason_clears_challenge() -> None:
    v = g.justify_task(
        {"executor": "sonnet", "complexity": "medium", "est_tokens": 1000,
         "target": "notes.txt", "role_reason": "cross-cutting spike, no single role fits"}
    )
    assert v.role == "general-purpose"
    assert v.challenge is None
    assert v.needs_subagent is True


# ── plan-level challenge ──────────────────────────────────────────────────────


def test_plan_with_deterministic_and_gp_is_challenged() -> None:
    plan = [
        {"mode": "deterministic"},
        {"executor": "haiku", "complexity": "simple", "est_tokens": 200, "target": "a.md"},
        {"executor": "opus", "complexity": "hard", "est_tokens": 2000, "target": "b.py"},
    ]
    pc = g.challenge_plan(plan)
    assert pc.challenged is True
    assert pc.deterministic_eligible == 1
    assert pc.unjustified <= pc.subagent_tasks      # invariant: never over-count
    assert pc.total == 3
    assert g.preview_line(pc).startswith("⚠")


def test_clean_scoped_plan_is_not_challenged() -> None:
    plan = [
        {"executor": "opus", "complexity": "hard", "est_tokens": 2000, "target": "renmark/x.py"},
        {"executor": "codex", "complexity": "medium", "est_tokens": 900, "target": "tests/test_x.py"},
    ]
    pc = g.challenge_plan(plan)
    assert pc.challenged is False
    assert pc.unjustified == 0
    assert g.preview_line(pc).startswith("✓")


def test_all_deterministic_plan_flags_every_task() -> None:
    plan = [{"mode": "deterministic"}, {"executor": "script"}]
    pc = g.challenge_plan(plan)
    assert pc.deterministic_eligible == 2
    assert pc.subagent_tasks == 0
    assert pc.challenged is True   # a cheaper (all-deterministic) path exists


# ── safety: never raises ──────────────────────────────────────────────────────


def test_gate_never_raises_on_garbage() -> None:
    for bad in (None, 123, "x", object()):
        v = g.justify_task(bad)
        assert isinstance(v, g.SubagentVerdict)
    for bad_plan in (None, 123, object()):
        pc = g.challenge_plan(bad_plan)
        assert isinstance(pc, g.PlanChallenge)
        assert pc.total == 0


def test_empty_plan_is_not_challenged() -> None:
    pc = g.challenge_plan([])
    assert pc.total == 0
    assert pc.challenged is False

[35m[3mexec[0m[0m
[1m/bin/bash -lc "sed -n '1,260p' plugin/skills/orchestrate/SKILL.md"[0m in /home/renmark/projects/ai-system/.claude/worktrees/subagent-gate
[32m succeeded in 0ms:[0m
---
name: orchestrate
description: "Use to execute a renmark plan — `/renmark:orchestrate` or \"execute the plan\", \"build it\", \"run the plan\". Dispatches each task in an isolated subagent and commits passing tasks."
---

# orchestrate

## Overview

Dispatches plan tasks in waves with **strict task isolation** (G11). Within a `parallel_group`, tasks run concurrently. Two dispatch paths — never mix them:

| Executor | Dispatch path | Quota consumed |
|---|---|---|
| `codex` | Bash call to `renmark-execute` (subprocess) | Codex account (OpenAI subscription) |
| `haiku`, `sonnet`, `opus` | Agent tool calls (no model override) | Claude Code account (Anthropic subscription) |
| `fable` | Agent tool call with `model: "fable"` override (one-shot fallback to no override — opus tier — if fable is unavailable; see Step 3b) | Claude Code account (Anthropic subscription) |

After each wave, the skill writes `.renmark/state/wave-summaries/wave-N.json` (the per-task `SubagentOutput` dicts) and commits passing tasks serially in task-index order.

**Token-isolation contract (G11):**
- Every task runs in an **isolated subagent context**.
- Each subagent receives only: task spec · required file paths · upstream artifact pointers · dependency summaries from the prior wave's `wave-summaries/` file · verifier expectations.
- Each subagent emits only the `SubagentOutput` schema (status, artifact_path, touched_files, sha, summary_lines ≤ 5, dependency_notes, token_count, completion_state, confidence, retry_count).
- The orchestrator validates the response via `renmark.dispatch.parse_subagent_response` — any extra field (transcript, diff, generated_code, reasoning) raises `IsolationViolation` and the task is FAIL.
- **The orchestrator never reads generated code into the conversation.** Period.

## Operating mode

**Orchestrator** is orchestrate's default: dispatch parallel scoped subagents, offload bulk/single-file emissions to Codex, and advance on reviewed PASS/FAIL outcomes. In **Conductor** mode, prefer serial single-task execution with tighter user checkpoints between tasks. Either mode keeps the G11 isolation/aggregation contract above unchanged.

## When Agency Mode is active

In Agency Mode, orchestrate runs tasks via scoped background agents and advances to the next milestone **checkpoint** rather than halting after each task. The owner agent continues coordination while background agents execute in parallel; progress emits compact summaries only. See `${CLAUDE_PLUGIN_ROOT}/skills/_shared/agency-delivery.md` for the delivery contract. When Agency is off, orchestrate behaves as above — no changes to isolation or task dispatch.

## When to Use

- User has a `.renmark/plans/*.plan.md` file ready and wants it executed
- After `/renmark:plan` + `/renmark:check-plan` complete (stage = `plan-validated`)
- To `--resume` a paused run

**Do NOT use:**
- Without a validated plan → `/renmark:plan` first, then `/renmark:check-plan`
- For brainstorming or design — that's `/renmark:brainstorm`
- To "look at the generated code" — that's a context-hygiene violation; route to `/renmark:debug` instead

## Steps

**Step 0 — Context check.** Call `lifecycle.skill_preamble(repo, 'orchestrate')`. If it returns a non-None hint, surface as a one-line note. Also check `state.read_pipeline_state(repo)` — if `current_phase == "orchestrate"` and `pipeline_is_resumable(repo)`, surface: *"Existing orchestrate run paused at wave N — use `--resume` to continue, or clear pipeline state to start fresh."*  When the user passes `--resume` and an existing run is resumed from pipeline state, emit:
```python
from renmark import usage, state, analytics
analytics.record_event(repo, ts=state.now_iso(), kind="resume")  # kind registered in EVENT_KINDS
```

### 1. Discover plan

If the user gave a path, use it. Otherwise:

```bash
ls -1t .renmark/plans/*.plan.md 2>/dev/null | head -1
```

Confirm the path with the user before continuing.

### 2. Pre-flight (free)

**Pipeline state check** — `state.read_pipeline_state(repo)`. If a prior run was paused, offer resume vs reset. New runs initialize fresh state:

```python
from renmark import state
state.write_pipeline_state(repo, current_phase="orchestrate", current_plan=<plan>,
                           wave_index=0, wave_total=<computed>, clear_tasks=True)
```

**Executor check** — `command -v codex` if the plan has any `executor: codex` tasks. If missing, stop and tell the user before running.

**Plan validation** — run `python -m renmark.plan_lint <plan>` directly before spending tokens. If it exits 1 (BLOCK), fix the plan first; WARNs can proceed with user acknowledgment. (Defense-in-depth: the same engine validated the plan at plan-time; running it again at dispatch-time means check-plan and orchestrate can never drift.)

**Refactor safety** — if the plan has any `complexity: hard` task or the spec mentions "refactor"/"rename"/"restructure"/"migrate":
1. Confirm clean working tree (`git status`).
2. Checkpoint commit: `git -c user.name="renmark-orchestrate" -c user.email="orchestrate@renmark.local" commit --allow-empty -m "chore: checkpoint before <plan name>"`.
3. Baseline each affected verifier — if any fails now, **stop**: do not orchestrate into a broken baseline.

**Changelog / decisions check** — read the last 5 entries in `CHANGELOG.md`, and when `.renmark/memory/decisions.md` is present, also read its decision titles + guard text (titles and guards only — never full bodies; REQ-5). Flag any "Do not change" guard or recorded decision the plan would contradict. A contradiction is **semantic**: the plan would undo or overwrite a guarded decision — and this binds even when there is **no target-file overlap** (a plan can violate a decision without touching the same file). On any such contradiction, surface it and **PAUSE for reconciliation** before dispatching; never silently overwrite a recorded decision.

**Subagent gate (deterministic, pre-dispatch)** — run the enforced justification gate before spending:

```bash
python -m renmark.subagent_gate <plan>   # exit 0 = clean, 1 = challenged
```

It challenges the plan per REQ-21's 4 questions (deterministic-eligible tasks,
inline-able simple tasks, `general-purpose` roles without a `role_reason`). On a
**challenged** verdict (exit 1), surface the one-line `preview_line` verdict and
require explicit acknowledgment before dispatch — do NOT auto-proceed on a
subagent-heavy or deterministic-eligible plan. Prefer converting flagged tasks to
deterministic checks or assigning a scoped profile (`subagent-profiles.md`).

**Cost preview** — `renmark-execute --dry-run <plan>` shows the task list + estimated cost. The cost preview MUST also carry the subagent-gate line (`renmark.subagent_gate.preview_line`), per `${CLAUDE_PLUGIN_ROOT}/skills/_shared/cost-preview.md`.

**Headless gate (cost approval).** Before the `Proceed? [y/N]` prompt below, consult the headless contract (`plugin/skills/_shared/headless-contract.md`):

```python
from renmark import headless
envelope = headless.resolve_gate(
    repo, "cost", kind="dangerous",
    originating_skill="orchestrate",
    what="~$X across N tasks",   # the dry-run estimate
)
```

- **Headless** (`envelope["mode"] != "interactive"`) → emit the `needs_input` JSON block + `headless.render_return(envelope)` prose line and **STOP** — do not dispatch.
- **Interactive** (`{"mode": "interactive"}`) → fall through to the prompt below, unchanged.

This human cost-approval gate is **distinct** from the Tier-1 usage-limit pause in 3a-bis (which auto-pauses on an already-exceeded local limit); leave that intact.

Interactive prompt: *"Proceed? [y/N]"*

### 3. Dispatch tasks in waves (G11 isolation)

For each wave in `dispatch.group_tasks_by_wave(tasks)` — where `tasks = parser.parse_plan(Path(plan_path))`, a plain `list[Task]` (`parse_plan` returns no object with a `.tasks` attribute):

**3a. Build dependency context for this wave**

Read prior wave summary if any:

```python
from renmark import state
prior = state.read_wave_summary(repo, wave_index - 1) if wave_index > 0 else None
dependency_summaries = []
if prior:
    for task_output in prior["task_outputs"]:
        if task_output.get("dependency_notes"):
            dependency_summaries.append(
                f"task {task_output.get('task_id', '?')}: {task_output['dependency_notes']}"
            )
```

**The orchestrator does NOT load any wave's full output.** Only the `dependency_notes` field crosses the boundary.

**3a-bis. Usage preflight (Tier-1, free) — pause before spending if a local limit is already exceeded**

Before dispatching any task in this wave, compute the bounded usage view and check it against the configured local limits in `.renmark/analytics/limits.json`. This is a deterministic file-IO check — **never read raw usage logs into conversation**; `build_usage_view` returns the bounded summary dict only.

```python
from renmark import usage, state, analytics
view = usage.build_usage_view(repo, now=state.now_iso())
if view.get("limit_exceeded"):  # a configured local limit is already over budget
    pause = usage.classify_usage_pause(
        run_id=<run_id>, plan_path=<plan>, last_task_index=wave_first_task_index,
        now=state.now_iso(), feature=<feature or "">, repo=repo,
    )
    state.write_pause(repo, pause)
    analytics.record_event(repo, ts=state.now_iso(), kind="pause")  # kind registered in EVENT_KINDS
    # Surface the resume command and STOP — do NOT dispatch this wave.
```

The PauseState carries `pause_kind="usage_limit"` and a `resume_after` timestamp (provider reset if known, else the next local rolling-window boundary, else now+60min). Surface: *"Local usage limit reached — orchestrate paused before wave N. Resume with `/renmark:orchestrate --resume` after `resume_after`."* Then stop; do not enter 3b. MVP: no polling, no auto-retry — the user (or `/renmark:resume`) re-enters later.

**3b. Dispatch each task in this wave (parallel)**

For `executor: codex` tasks:

> **RED FLAG — never dispatch a `codex` task as an Agent call.** Codex tasks run exclusively through `renmark-execute` (a Bash subprocess). Dispatching them as Agents runs them on the parent Claude model, consuming Anthropic credits and ignoring the cost/routing intent.
>
> **RED FLAG — never merge a subagent transcript into orchestrator context.** The subagent's reasoning lives in its artifact file. The orchestrator reads only the parsed `SubagentOutput` JSON.

```bash
# Pre-create target dirs so codex doesn't scaffold extras
mkdir -p "$(dirname <target>)"
# Dispatch the whole wave (renmark-execute handles parallelism internally)
renmark-execute <plan>
```

`renmark-execute` returns one JSON line per task with the `SubagentOutput` shape. The orchestrator passes each through `dispatch.parse_subagent_response()`, which raises `IsolationViolation` on any extra field.

For `executor: haiku | sonnet | opus | fable` tasks:

Plain `Agent` call — no `model` override for `haiku | sonnet | opus`; for `executor: fable`, pass `model: "fable"` on the Agent call. Build the subagent prompt from `dispatch.build_subagent_input(task, dependency_summaries=...)`. The Agent prompt MUST instruct the subagent:

> "Your final response MUST be valid JSON matching this shape:
> ```json
> {"status": "PASS|FAIL|SKIP", "artifact_path": "<path>",
>  "touched_files": [...], "sha": "<sha or null>",
>  "summary_lines": ["<≤5 lines>"], "dependency_notes": "<what downstream tasks need>",
>  "token_count": <int>, "completion_state": "complete|partial|failed",
>  "confidence": "low|medium|high", "retry_count": 0}
> ```
> The generated code goes in the artifact file at `<artifact_path>`, NOT in your response. Do not paste code or diffs back. If you cannot complete with the inputs provided, return `status: FAIL` with a one-line reason."

The Agent prompt MUST also include the canonical reasoning instruction blockquote — the one under "The canonical reasoning instruction (verbatim — single source)" in `${CLAUDE_PLUGIN_ROOT}/skills/_shared/reasoning-contract.md`, NOT the skill-author "Dispatch reference" blockquote — read it from that file at dispatch time and append it verbatim to the subagent prompt. This applies to BOTH dispatch paths: Agent-path dispatches above AND codex ad-hoc task specs (`renmark-execute --task`).

After the Agent returns, parse its response through `dispatch.parse_subagent_response()`. If it raises `IsolationViolation`, mark the task as FAIL with reason "subagent leaked forbidden fields" — do not retry.

**Fable-unavailable fallback (defense-in-depth).** If an Agent call with `model: "fable"` errors **on dispatch** — the model is unavailable or the override is rejected by the harness — retry the task **exactly once** with no `model` override (the opus tier, same as `executor: opus`). Requirements (all mandatory — degradation is never silent):

- record `fallback: fable→opus` in that task's wave-summary entry — in `dependency_notes` or a dedicated note field — so downstream waves and `/renmark:verify` see what actually ran;
- log the fallback via `memory.append_routing(repo, signature=<task signature>, executor="opus", outcome=<"passed"|"failed">)` so repeated fable fallbacks accumulate as routing evidence in `.renmark/memory/routing.md`;
- ledger the fallback call with `model="opus"` (not `task.executor`) so spend attribution matches what ran.

One retry only: if the no-override retry also fails, that is an ordinary task FAIL — no further reroutes, no second fallback tier. Note that orchestrate's pre-flight `plan_lint` fable gates (checks 9–10: undeclared `top_tier: fable`, fable-on-mechanical) make an undeclared fable dispatch unreachable in the normal flow — this fallback is defense-in-depth for harness-side unavailability, not a routing surface. It is distinct from and complementary to the codex-side "Reroute-first on codex limits" rule in Step 5: that rule handles usage limits on the subprocess path; this one handles model availability on the Agent path.

**Ledger the call.** Immediately after parsing each successful Agent return, log the spend so `/renmark:roadmap` reports honestly:

```python
from renmark import state
from renmark.roadmap import AGENT_OVERHEAD_TOKENS
state.log_agent_call(
    repo,
    task_id=task.index,
    model=task.executor,                            # 'haiku' | 'sonnet' | 'opus' | 'fable'
    tokens_in=AGENT_OVERHEAD_TOKENS,                # ~10k system + spec overhead per call
    tokens_out=out.token_count,                     # SubagentOutput.token_count
    run_id=<run_id>,
)
```

Codex tasks are ledgered by `renmark-execute` directly — do NOT call `log_agent_call` for them or spend will be double-counted.

**3c. Run verifier per task**

For each task that returned PASS status, run its verifier via `summary.verifier_tail(cmd, cwd=repo, tail_lines=3)` (`cwd` is a required keyword-only argument). Orchestrator-visible output is bounded: `exit <code> | <first 3 lines>`. If the verifier fails, downgrade the task to FAIL.

**3d. Escalation decision log**

When a task is escalated to a higher-tier executor, an ADR is appended to `.renmark/memory/decisions.md` via `memory.log_escalation_decision()`. This is automatic — handled inside `renmark/cli/_engine.py`'s `_record_escalation` when `escalated_to=` is passed. Idempotent on (title, date): re-running the same escalation on the same day does not duplicate the ADR. Best-effort: decision-logging failures do NOT break orchestrate. Pointer-only — the orchestrator never reads `decisions.md` into conversation.

### 4. Aggregate wave summary

After all tasks in the wave finish:

```python
state.write_wave_summary(repo, wave_index, task_outputs=[
    # to_dict() carries no task_id — stamp it here so step 3a can attribute notes
    {"task_id": task.index, **out.to_dict()}
    for out, task in zip(outputs, wave_tasks)
])
state.write_pipeline_state(repo, wave_index=wave_index,
                           add_completed_task=..., add_failed_task=...)
```

**Record one analytics event per task (bounded — from the WaveResult summary, NEVER transcripts).** After the wave summary is persisted, emit a structured run event for each task so usage/limits stay current. Source every field from the parsed `SubagentOutput` / verifier result already in hand — do not re-read artifacts, diffs, or raw logs.

```python
from renmark import analytics, state
for out, task in zip(outputs, wave_tasks):
    analytics.record_task_run(
        repo, ts=state.now_iso(), task_id=task.index, title=task.title,
        executor=task.executor, model=task.executor, provider="",
        status=out.status,
        # verifier_result MUST be a normalized verdict token ("pass"/"fail") —
        # analytics._agg_tasks classifies on these, NOT on a free-text exit summary.
        verifier_result=("pass" if out.status == "PASS" else "fail"),
        retry_count=out.retry_count,
        failure_reason=<one-line reason if FAIL else "">,  # human-readable tail lives here
        total_tokens=out.token_count, sha=(out.sha or ""),
    )
```

Then commit PASSing tasks serially in task-index order. For each commit, append to `CHANGELOG.md`:


[35m[3mcodex[0m[0m
I have the new module and tests. Next I’m checking the existing `cost` and `subagent_profiles` contracts it composes against, because the highest-risk failures here are interface mismatches and false classifications that the new tests may not cover.
[35m[3mexec[0m[0m
[1m/bin/bash -lc "rg -n \"def is_deterministic_item|def _get|def resolve_profile|def profile_tier|class Task|def parse_plan|est_tokens|complexity|role_reason\" renmark tests -g '"'!tests/test_subagent_gate.py'"'"[0m in /home/renmark/projects/ai-system/.claude/worktrees/subagent-gate
[32m succeeded in 0ms:[0m
renmark/parser.py:29:class Task:
renmark/parser.py:41:    complexity: str = "medium"  # "simple" | "medium" | "hard"
renmark/parser.py:45:    est_tokens: int | None = None  # planner estimate (informational)
renmark/parser.py:61:def parse_plan(path: str | Path) -> list[Task]:
renmark/parser.py:152:        elif key == "est_tokens":
renmark/parser.py:154:                current["est_tokens"] = int(value)
renmark/parser.py:156:                raise PlanError(f"line {line_no}: est_tokens must be int, got {value!r}") from e
renmark/parser.py:162:        elif key in ("mode", "target", "model", "verifier", "executor", "complexity", "serves"):
renmark/parser.py:227:    complexity = (d.get("complexity") or "medium").strip().lower()
renmark/parser.py:228:    if complexity not in ("simple", "medium", "hard"):
renmark/parser.py:229:        raise PlanError(f"complexity must be simple, medium, or hard, got {complexity!r}")
renmark/parser.py:241:        complexity=complexity,
renmark/parser.py:243:        est_tokens=d.get("est_tokens"),
tests/test_memory.py:117:        signature="target=tests/**, complexity=medium",
tests/test_memory.py:125:    assert "target=tests/**, complexity=medium" in text
tests/test_memory.py:539:            signature="target=tests/**, complexity=medium",
renmark/sizing.py:66:#: Summed planner ``est_tokens`` at/under this is "very small" and may stay
renmark/sizing.py:67:#: ``lite`` even for code (when no harder signal fires).  ``None`` est_tokens
renmark/sizing.py:72:#: Summed planner ``est_tokens`` at/over this forces ``full`` (large change).
renmark/sizing.py:129:    - any task with ``complexity == "hard"`` → never ``lite`` (>= ``standard``);
renmark/sizing.py:131:    - many tasks (> :data:`FULL_MIN_TASKS`) or large summed ``est_tokens``
renmark/sizing.py:134:      doc/config-dominant **or** very small (summed ``est_tokens`` <=
renmark/sizing.py:147:        # an unrecognized complexity, degrades the whole plan to the safe
renmark/sizing.py:153:        has_hard = any(_task_complexity(t) == "hard" for t in tasks)
renmark/sizing.py:157:        total_est = sum(_task_est_tokens(t) for t in tasks)
renmark/sizing.py:162:        all_have_est = all(getattr(t, "est_tokens", None) is not None for t in tasks)
renmark/sizing.py:320:#: A task whose complexity is anything else is treated as malformed.
renmark/sizing.py:328:    ``complexity``. A bare ``object()``, a missing/blank target, or an
renmark/sizing.py:329:    unrecognized complexity fails — so unvalidated tasks can never reach the
renmark/sizing.py:335:    complexity = getattr(task, "complexity", None)
renmark/sizing.py:336:    return isinstance(complexity, str) and complexity.strip().lower() in RECOGNIZED_COMPLEXITY
renmark/sizing.py:339:def _task_complexity(task: Task) -> str:
renmark/sizing.py:340:    value = getattr(task, "complexity", "medium")
renmark/sizing.py:349:def _task_est_tokens(task: Task) -> int:
renmark/sizing.py:350:    value = getattr(task, "est_tokens", None)
tests/test_dispatch_isolation.py:30:        complexity="simple",
tests/test_dispatch_isolation.py:34:        est_tokens=None,
tests/test_dispatch.py:32:        complexity="simple",
tests/test_dispatch.py:130:    tasks[0].est_tokens = 100
tests/test_dispatch.py:132:    tasks[1].est_tokens = 250
tests/test_parser.py:287:def test_complexity_field_parses(tmp_path: Path) -> None:
tests/test_parser.py:294:        "- **complexity:** hard\n"
tests/test_parser.py:300:    assert tasks[0].complexity == "hard"
tests/test_parser.py:303:def test_complexity_defaults_to_medium(tmp_path: Path) -> None:
tests/test_parser.py:315:    assert tasks[0].complexity == "medium"
tests/test_parser.py:318:def test_complexity_invalid_rejected(tmp_path: Path) -> None:
tests/test_parser.py:325:        "- **complexity:** trivial\n"
tests/test_parser.py:330:    with pytest.raises(PlanError, match="complexity must be"):
tests/test_parser.py:374:def test_est_tokens_and_cost_parse(tmp_path: Path) -> None:
tests/test_parser.py:381:        "- **est_tokens:** 4500\n"
tests/test_parser.py:388:    assert tasks[0].est_tokens == 4500
tests/test_parser.py:392:def test_est_tokens_non_int_rejected(tmp_path: Path) -> None:
tests/test_parser.py:399:        "- **est_tokens:** lots\n"
tests/test_parser.py:404:    with pytest.raises(PlanError, match="est_tokens must be int"):
renmark/subagent_profiles.py:164:def resolve_profile(task: Any) -> str:
renmark/subagent_profiles.py:213:def profile_tier(role: str) -> str:
renmark/subagent_profiles.py:236:def _get_field(task: Any, field: str, default: str) -> str:
renmark/init.py:1381:        f"({n_major} major, {n_warn} warn) — file-level size/complexity breaches. "
renmark/program.py:122:class TaskNode:
tests/test_engine_budget_and_rollback.py:300:        "- **est_tokens:** 2000\n"
tests/test_engine_budget_and_rollback.py:328:        "- **est_tokens:** 2000\n"
tests/test_engine_budget_and_rollback.py:359:        "- **est_tokens:** 2000\n"
tests/test_engine_budget_and_rollback.py:388:        "- **est_tokens:** 1000\n"
renmark/subagent_gate.py:24:  Q4 Is it large/ambiguous enough to justify a subagent? → complexity/size
renmark/subagent_gate.py:78:    ``executor`` / ``complexity`` / ``est_tokens`` / ``role`` / ``role_reason``.
renmark/subagent_gate.py:94:        complexity = str(cost._get(task, "complexity", "") or "").strip().lower()
renmark/subagent_gate.py:95:        raw_tokens = cost._get(task, "est_tokens", 0)
renmark/subagent_gate.py:96:        est_tokens = raw_tokens if isinstance(raw_tokens, int) and not isinstance(raw_tokens, bool) else 0
renmark/subagent_gate.py:99:        if complexity in ("", "simple") and 0 < est_tokens <= _DIRECT_TOKEN_CEILING:
renmark/subagent_gate.py:105:                reason=f"simple + ~{est_tokens} tok — orchestrator can do this inline",
renmark/subagent_gate.py:110:        justified = complexity in _SUBAGENT_JUSTIFYING_COMPLEXITY or est_tokens > _DIRECT_TOKEN_CEILING
renmark/subagent_gate.py:114:            reason_field = str(cost._get(task, "role_reason", "") or "").strip()
renmark/subagent_gate.py:119:                    "or state role_reason"
renmark/subagent_gate.py:130:                f"{complexity or 'unspecified'} complexity, ~{est_tokens} tok, role={role}"
tests/test_cost.py:11:            {"executor": "haiku", "est_tokens": 1000},
tests/test_cost.py:12:            {"executor": "codex", "est_tokens": 2000},
tests/test_cost.py:13:            {"executor": "sonnet", "est_tokens": 3000},
tests/test_cost.py:17:    assert preview.est_tokens == 26_000
tests/test_cost.py:26:    preview = estimate_cost([{"executor": "haiku", "est_tokens": 500}])
tests/test_cost.py:34:    preview = estimate_cost([{"executor": "opus", "est_tokens": 1000, "complexity": "medium"}])
tests/test_cost.py:42:    preview = estimate_cost([{"executor": "mystery-tier"}, {"executor": None, "est_tokens": None}])
tests/test_cost.py:44:    assert preview.est_tokens == 20_000
tests/test_cost.py:58:    assert requires_escalation(complexity="hard") is True
tests/test_cost.py:60:    assert requires_escalation(complexity="routine", kind="doc") is False
tests/test_cost.py:64:def test_estimate_cost_rejects_bool_est_tokens() -> None:
tests/test_cost.py:66:    with_bool = estimate_cost([{"executor": "codex", "est_tokens": True}])
tests/test_cost.py:67:    baseline = estimate_cost([{"executor": "codex", "est_tokens": 0}])
tests/test_cost.py:68:    assert with_bool.est_tokens == baseline.est_tokens
tests/test_cost.py:107:    assert is_deterministic_item({"est_tokens": 500}) is False
tests/test_cost.py:112:        {"executor": "script", "est_tokens": 100},    # deterministic
tests/test_cost.py:113:        {"executor": "tool", "est_tokens": 200},      # deterministic
tests/test_cost.py:114:        {"executor": "sonnet", "est_tokens": 500},    # model-driven
tests/test_cost.py:115:        {"executor": "haiku", "est_tokens": 300},     # model-driven
tests/test_cost.py:139:        {"executor": "check", "est_tokens": 50},
tests/test_cost.py:140:        {"executor": "opus", "est_tokens": 1000, "complexity": "hard"},
tests/test_cost.py:154:        {"executor": "haiku", "est_tokens": 1000},
tests/test_cost.py:155:        {"executor": "sonnet", "est_tokens": 2000},
tests/test_cost.py:158:    assert isinstance(preview.est_tokens, int)
tests/test_cost.py:159:    assert preview.est_tokens > 0
tests/test_subagent_profiles.py:21:        complexity="medium",
tests/test_subagent_profiles.py:25:        est_tokens=None,
tests/test_subagent_profiles.py:73:        signature="target=tests/test_subagent_profiles.py, complexity=medium",
tests/test_subagent_profiles.py:87:            {"executor": "codex", "est_tokens": 500, "role": "test-writer"},
tests/test_subagent_profiles.py:88:            {"executor": "haiku", "est_tokens": 100, "role": "docs-editor"},
tests/test_subagent_profiles.py:89:            {"executor": "codex", "est_tokens": 250, "role": "test-writer"},
tests/test_subagent_profiles.py:101:        executor="codex", complexity="medium", parallel_group=1,
tests/test_plan_lint.py:22:- Added a mechanical-task BLOCK test for `executor: fable` with `complexity: simple`.
tests/test_plan_lint.py:62:    est_tokens: int | str | None = None,
tests/test_plan_lint.py:76:    if est_tokens is not None:
tests/test_plan_lint.py:77:        lines.append(f"- **est_tokens:** {est_tokens}\n")
tests/test_plan_lint.py:228:# 7. Bad est_tokens type → BLOCK gracefully (parse error caught, no exception)
tests/test_plan_lint.py:232:def test_bad_est_tokens_type_block_no_exception(tmp_path: Path) -> None:
tests/test_plan_lint.py:238:        "- **est_tokens:** lots\n"
tests/test_plan_lint.py:380:            extra_fields="- **complexity:** medium\n",
tests/test_plan_lint.py:401:            extra_fields="- **complexity:** medium\n",
tests/test_plan_lint.py:421:            extra_fields="- **complexity:** simple\n",
tests/test_plan_lint.py:446:            extra_fields="- **complexity:** medium\n",
tests/test_plan_lint.py:470:            extra_fields="- **complexity:** medium\n",
tests/test_plan_lint.py:543:# 15. Negative est_tokens → WARN
tests/test_plan_lint.py:547:def test_negative_est_tokens_warn(tmp_path: Path) -> None:
tests/test_plan_lint.py:548:    plan = _write(tmp_path, _BASE_HEADER + _task(est_tokens=-100))
tests/test_plan_lint.py:551:    assert any("negative" in issue.lower() or "est_tokens" in issue for issue in report.issues)
tests/test_handoff_helpers.py:29:- **complexity:** simple
tests/test_handoff_helpers.py:38:- **complexity:** medium
renmark/plan_lint.py:312:        if t.executor == "fable" and t.complexity == "simple":
renmark/plan_lint.py:328:        if t.est_tokens is not None:
renmark/plan_lint.py:329:            if t.est_tokens < 0:
renmark/plan_lint.py:333:                        f"Task {t.index}: est_tokens is negative ({t.est_tokens}). Check planner estimate.",
renmark/plan_lint.py:336:            elif t.est_tokens > _MAX_EST_TOKENS:
renmark/plan_lint.py:340:                        f"Task {t.index}: est_tokens is {t.est_tokens} "
tests/test_modularity.py:216:# ── Metric 3: cyclomatic complexity ────────────────────────────────────────────
tests/test_modularity.py:270:# ── Metric 5: cognitive complexity ─────────────────────────────────────────────
tests/test_modularity.py:322:    assert len(cog) == 1, "deep nesting must trip cognitive complexity"
renmark/modularity.py:25:5. **cognitive complexity** per function (nesting-weighted: each branching
renmark/modularity.py:45:complexity. Code lines are counted, never raw lines.
renmark/modularity.py:74:#: Cognitive complexity per function (SonarQube-style nesting-weighted).
renmark/modularity.py:433:# ── Metric 3: cyclomatic complexity ─────────────────────────────────────────────
renmark/modularity.py:461:# ── Metric 5: cognitive complexity ──────────────────────────────────────────────
renmark/modularity.py:465:    """Nesting-weighted cognitive complexity (SonarQube-style approximation).
renmark/modularity.py:508:    A nested ``def``/``async def`` carries its own complexity score, so we don't
renmark/modularity.py:600:            f"High cyclomatic complexity: `{rel}` → `{qual}` ({value} branches)",
renmark/modularity.py:617:            f"High cognitive complexity: `{rel}` → `{qual}` (score {value})",
renmark/modularity.py:618:            f"`{qual}` in `{rel}` has a nesting-weighted cognitive-complexity score of {value} "
tests/test_sizing.py:33:    complexity: str = "medium",
tests/test_sizing.py:34:    est_tokens: int | None = None,
tests/test_sizing.py:44:        complexity=complexity,
tests/test_sizing.py:45:        est_tokens=est_tokens,
tests/test_sizing.py:63:        _task(2, "docs/b.md", complexity="hard"),
tests/test_sizing.py:72:    tasks = [_task(1, "renmark/parser.py", complexity="simple")]
tests/test_sizing.py:98:    # Bare objects miss target/complexity entirely → standard, never lite.
tests/test_sizing.py:107:        complexity = "simple"
tests/test_sizing.py:112:def test_unrecognized_complexity_degrades_to_standard() -> None:
tests/test_sizing.py:113:    """A task whose complexity is not simple/medium/hard → standard (never lite)."""
tests/test_sizing.py:117:        complexity = "trivial"  # not a recognized complexity
tests/test_sizing.py:127:    contains 'template'. With non-trivial est_tokens (so the very-small
tests/test_sizing.py:128:    est_tokens lite path does NOT fire), a code file that was wrongly seen as
tests/test_sizing.py:135:            complexity="simple",
tests/test_sizing.py:136:            est_tokens=sizing.LITE_MAX_EST_TOKENS + 1,
tests/test_sizing.py:334:# ── sizing lite-floor: missing est_tokens guard ──────────────────────────────
tests/test_sizing.py:340:    Prior bug: missing est_tokens contributed 0 to the sum, so total_est=0 <=
tests/test_sizing.py:344:    tasks = [_task(i + 1, f"src/module{i}.py", complexity="simple") for i in range(3)]
tests/test_sizing.py:345:    assert all(t.est_tokens is None for t in tasks)
tests/test_sizing.py:347:    assert result != TIER_LITE, "A code plan with no estimates must never be lite (missing est_tokens != 0 tokens)"
tests/test_sizing.py:353:    tasks = [_task(i + 1, f"docs/page{i}.md", est_tokens=500) for i in range(LITE_MAX_TASKS)]
tests/test_sizing.py:354:    assert all(t.est_tokens is not None for t in tasks)
tests/test_sizing.py:361:        _task(1, "docs/a.md", est_tokens=100),
tests/test_sizing.py:363:        _task(3, "docs/c.md", est_tokens=100),
tests/test_sizing.py:371:        _task(1, "src/a.py", est_tokens=100),
renmark/cost.py:18:  Opus and Fable are reserved for genuinely hard work — ``complexity == "hard"``
renmark/cost.py:93:    est_tokens: int
renmark/cost.py:144:    - ``est_tokens`` (int | None, optional) — planner token estimate; treated
renmark/cost.py:146:    - ``complexity`` (str | None, optional) — task complexity label.  Used to
renmark/cost.py:171:                raw_tokens = _get(item, "est_tokens", None)
renmark/cost.py:194:                    raw_complexity = _get(item, "complexity", None)
renmark/cost.py:195:                    complexity = raw_complexity.strip().lower() if isinstance(raw_complexity, str) else ""
renmark/cost.py:196:                    if complexity != "hard":
renmark/cost.py:218:            est_tokens=total_tokens,
renmark/cost.py:232:            est_tokens=0,
renmark/cost.py:241:def requires_escalation(*, complexity: str | None = None, kind: str | None = None) -> bool:
renmark/cost.py:246:    - ``complexity == "hard"`` — the task is explicitly labelled hard, OR
renmark/cost.py:254:        if isinstance(complexity, str) and complexity.strip().lower() == "hard":
renmark/cost.py:264:def is_deterministic_item(item: object) -> bool:
renmark/cost.py:294:def _get(item: object, key: str, default: object) -> object:
renmark/memory.py:265:    signature: str,  # e.g. "target=tests/**, complexity=medium"
renmark/dispatch.py:27:class TaskResult:
renmark/dispatch.py:160:    """Sum est_tokens and est_cost_usd across a wave (treating None as 0)."""
renmark/dispatch.py:161:    tok = sum(t.est_tokens or 0 for t in wave)
tests/test_state_pause_usage.py:170:def test_tokens_by_feature_ranks_descending_and_respects_top(tmp_path):
renmark/cli/commands.py:316:        f"**complexity:** {task.complexity}",
renmark/cli/_engine.py:305:def _default_tokens_for_complexity(complexity: str) -> int:
renmark/cli/_engine.py:306:    """Rough output-token estimate when the plan doesn't specify est_tokens."""
renmark/cli/_engine.py:307:    return {"simple": 200, "medium": 1000, "hard": 4000}.get(complexity, 1000)
renmark/cli/_engine.py:322:    return f"target={glob}, complexity={task.complexity}, mode={task.mode}"
renmark/cli/_engine.py:478:                tok = t.est_tokens or _default_tokens_for_complexity(t.complexity)
renmark/cli/_engine.py:495:                    f"    [{mark}] task {t.index} {ex_display:<8} {t.complexity:<6} "

[35m[3mexec[0m[0m
[1m/bin/bash -lc "sed -n '1,260p' renmark/cost.py"[0m in /home/renmark/projects/ai-system/.claude/worktrees/subagent-gate
[32m succeeded in 0ms:[0m
"""Deterministic cost-preview and escalation-gate helpers — zero-LLM, stdlib-only.

This module is the **single source of truth** for executor pricing, per-task token
estimation, cost banding, and the "escalate only when justified" gate used by the
finish lane and, in future, Agency Mode.

It is reusable by any caller that needs a cost preview before dispatching:

- **plan preview** — ``estimate_cost(items)`` runs on the validated task list to
  produce a :class:`CostPreview` before any token is spent (complements plan §6
  inline math, which is left untouched).
- **finish lane** — the finish skill calls ``estimate_cost`` to surface a cost
  summary and ``requires_escalation`` to gate opus/fable dispatch.
- **Agency Mode (future)** — the same helpers wire into the autonomous dispatch
  loop without any change to this module.

The "escalate only when justified" contract:
  Opus and Fable are reserved for genuinely hard work — ``complexity == "hard"``
  or structural tasks (architecture, adversarial-review, design-fork).  Routing
  them on medium/simple work is a cost violation; ``requires_escalation`` is the
  programmatic gate that enforces this.

Design contract:

- Pure functions of their inputs.
- **Never raises into the caller.** Every access step is defensive; missing or
  garbage fields degrade to ``0`` tokens / sonnet pricing.
- Every threshold and price is a documented, tunable module-level constant.
"""

from __future__ import annotations

from dataclasses import dataclass

# ── Pricing (USD per 1 000 tokens) ──────────────────────────────────────────

#: Per-executor price in USD per 1 000 tokens.
#: Codex ``0.03`` is the midpoint of the observed ``0.01``–``0.05`` range.
#: Unknown executors are priced at the ``"sonnet"`` rate (conservative default).
PRICE_PER_KTOK: dict[str, float] = {
    "haiku": 0.0001,
    "codex": 0.03,
    "sonnet": 0.003,
    "opus": 0.015,
    "fable": 0.030,
}

# ── Overhead ─────────────────────────────────────────────────────────────────

#: Extra tokens added per non-codex agent task to account for system-prompt,
#: tool definitions, and routing overhead — matches plan §6 inline math.
#: Codex is a subprocess executor; it has NO agent overhead.
AGENT_OVERHEAD_TOKENS: int = 10_000

# ── Cost-band thresholds ─────────────────────────────────────────────────────

#: A run priced below this is "low" band (green light, no gate).
BAND_LOW_MAX_USD: float = 0.10

#: A run priced below this (but >= BAND_LOW_MAX_USD) is "medium" band (proceed
#: with a note). At or above this threshold the run is "high" (pause for approval).
BAND_MEDIUM_MAX_USD: float = 1.00

# ── Executor sets ────────────────────────────────────────────────────────────

#: Executors that run as Claude Code agent calls (carry agent overhead).
_AGENT_EXECUTORS: frozenset[str] = frozenset({"haiku", "sonnet", "opus", "fable"})

#: Executors classified as expensive (trigger ``requires_expensive_model``).
_EXPENSIVE_EXECUTORS: frozenset[str] = frozenset({"opus", "fable"})

#: Task kinds that always warrant escalation to opus/fable.
_ESCALATION_KINDS: frozenset[str] = frozenset({"architecture", "adversarial-review", "design-fork"})

#: Executor names that denote a deterministic (code/tool/script) step — no model call.
#: Any executor not in this set (including all model names) is classified model-driven.
_DETERMINISTIC_EXECUTORS: frozenset[str] = frozenset(
    {"deterministic", "script", "check", "tool", "code", "none"}
)

# ── Public types ──────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class CostPreview:
    """Immutable cost estimate for a set of planned tasks.

    Produced by :func:`estimate_cost`; consumed by the finish lane and plan
    preview callers.  All monetary values are in USD.
    """

    #: Total estimated tokens across all tasks (including agent overhead).
    est_tokens: int
    #: Total estimated cost in USD, rounded to 4 decimal places.
    est_cost_usd: float
    #: Cost band: ``"low"``, ``"medium"``, or ``"high"``.
    cost_band: str
    #: True if any task uses a Claude Code agent executor (haiku/sonnet/opus/fable).
    uses_subagents: bool
    #: True if any task routes to opus or fable.
    requires_expensive_model: bool
    #: One-line suggestion when opus/fable is routed on non-hard work, else None.
    cheaper_alternative: str | None
    #: Sorted tuple of distinct role/profile strings seen across items (empty when none provided).
    roles: tuple[str, ...] = ()
    #: Number of items classified as deterministic (code/tool/script steps — no model call).
    deterministic_count: int = 0
    #: Number of items classified as model-driven (any model executor).
    model_driven_count: int = 0
    #: Estimated tokens attributed to deterministic items (base tokens only, no agent overhead).
    deterministic_tokens: int = 0
    #: Estimated tokens attributed to model-driven items (base tokens only, no agent overhead).
    model_driven_tokens: int = 0


# ── Public API ────────────────────────────────────────────────────────────────


def cost_band(usd: float) -> str:
    """Map a USD cost to a cost-band string.

    Returns ``"low"`` if ``usd < BAND_LOW_MAX_USD``, ``"medium"`` if
    ``usd < BAND_MEDIUM_MAX_USD``, else ``"high"``.  Never raises — bad input
    is coerced to ``0.0`` and classified as ``"low"``.
    """
    try:
        amount = float(usd)
    except (TypeError, ValueError):
        amount = 0.0
    if amount < BAND_LOW_MAX_USD:
        return "low"
    if amount < BAND_MEDIUM_MAX_USD:
        return "medium"
    return "high"


def estimate_cost(items: list) -> CostPreview:
    """Estimate the cost of a set of planned tasks.

    Each item in ``items`` may be a :class:`dict` or any object exposing:

    - ``executor`` (str) — the executor name (e.g. ``"haiku"``, ``"codex"``).
      Unknown values are priced at the ``"sonnet"`` rate.
    - ``est_tokens`` (int | None, optional) — planner token estimate; treated
      as ``0`` when absent or non-positive.
    - ``complexity`` (str | None, optional) — task complexity label.  Used to
      detect cheaper-alternative opportunities.

    Returns a :class:`CostPreview`.  **Never raises** — any missing or garbage
    field degrades to ``0`` tokens / sonnet pricing.
    """
    try:
        total_tokens: int = 0
        total_cost: float = 0.0
        uses_subagents: bool = False
        requires_expensive_model: bool = False
        has_expensive_non_hard: bool = False
        seen_roles: set[str] = set()
        deterministic_count: int = 0
        model_driven_count: int = 0
        deterministic_tokens: int = 0
        model_driven_tokens: int = 0

        for item in items:
            try:
                raw_exec = _get(item, "executor", None)
                executor = raw_exec.strip().lower() if isinstance(raw_exec, str) and raw_exec.strip() else "sonnet"
                if executor not in PRICE_PER_KTOK:
                    executor = "sonnet"

                raw_tokens = _get(item, "est_tokens", None)
                base_tokens = (
                    raw_tokens
                    if isinstance(raw_tokens, int)
                    and not isinstance(raw_tokens, bool)
                    and raw_tokens > 0
                    else 0
                )

                overhead = AGENT_OVERHEAD_TOKENS if executor in _AGENT_EXECUTORS else 0
                item_tokens = base_tokens + overhead

                price = PRICE_PER_KTOK[executor]
                item_cost = item_tokens / 1000.0 * price

                total_tokens += item_tokens
                total_cost += item_cost

                if executor in _AGENT_EXECUTORS:
                    uses_subagents = True

                if executor in _EXPENSIVE_EXECUTORS:
                    requires_expensive_model = True
                    raw_complexity = _get(item, "complexity", None)
                    complexity = raw_complexity.strip().lower() if isinstance(raw_complexity, str) else ""
                    if complexity != "hard":
                        has_expensive_non_hard = True

                raw_role = _get(item, "role", None)
                if isinstance(raw_role, str) and raw_role.strip():
                    seen_roles.add(raw_role.strip())

                if is_deterministic_item(item):
                    deterministic_count += 1
                    deterministic_tokens += base_tokens
                else:
                    model_driven_count += 1
                    model_driven_tokens += base_tokens

            except Exception:
                pass

        cheaper_alternative: str | None = None
        if has_expensive_non_hard:
            cheaper_alternative = "Task(s) route opus/fable on non-hard work — consider sonnet/haiku"

        return CostPreview(
            est_tokens=total_tokens,
            est_cost_usd=round(total_cost, 4),
            cost_band=cost_band(total_cost),
            uses_subagents=uses_subagents,
            requires_expensive_model=requires_expensive_model,
            cheaper_alternative=cheaper_alternative,
            roles=tuple(sorted(seen_roles)),
            deterministic_count=deterministic_count,
            model_driven_count=model_driven_count,
            deterministic_tokens=deterministic_tokens,
            model_driven_tokens=model_driven_tokens,
        )
    except Exception:
        return CostPreview(
            est_tokens=0,
            est_cost_usd=0.0,
            cost_band="low",
            uses_subagents=False,
            requires_expensive_model=False,
            cheaper_alternative=None,
        )


def requires_escalation(*, complexity: str | None = None, kind: str | None = None) -> bool:
    """Return True iff this task warrants escalation to opus or fable.

    Escalation is justified when:

    - ``complexity == "hard"`` — the task is explicitly labelled hard, OR
    - ``kind`` is one of ``{"architecture", "adversarial-review", "design-fork"}``
      — structural task kinds where frontier reasoning pays off.

    All other inputs (including None, garbage, or unrecognised values) return
    False.  **Never raises.**
    """
    try:
        if isinstance(complexity, str) and complexity.strip().lower() == "hard":
            return True
        return isinstance(kind, str) and kind.strip().lower() in _ESCALATION_KINDS
    except Exception:
        return False



[35m[3mexec[0m[0m
[1m/bin/bash -lc "sed -n '1,260p' renmark/subagent_profiles.py"[0m in /home/renmark/projects/ai-system/.claude/worktrees/subagent-gate
[32m succeeded in 0ms:[0m
"""Specialized subagent role profiles for the renmark dispatch system.

renmark prefers specialized profiles over generic general-purpose assignment.
``general-purpose`` is the FALLBACK ONLY — every other profile is narrower,
cheaper-capable (Haiku for read-only/docs/audit roles, Sonnet for code/tests/review),
and declares a deliberately narrow ``context_scope`` so the dispatch packet
carries less context.

The UI may still surface Claude's built-in "general-purpose" label, but renmark
tracks and logs the intended role from this module, which drives packet shaping
and future Agency Mode routing. Specialized profiles declared here are reused by
the Agency Mode (forthcoming).

Design contract:
- Pure data — no LLM calls, no I/O, no side effects.
- ``resolve_profile`` and ``profile_tier`` never raise into the caller.
- On any error both return the safe fallback (``"general-purpose"`` / ``"sonnet"``).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# ── Profile dataclass ─────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ProfileSpec:
    """Specification for a single subagent role.

    Fields
    ------
    role:
        Stable name key; must match the key in ``PROFILES``.
    model_tier:
        Cheapest-capable model tier for this role (``"haiku"`` / ``"sonnet"``
        / ``"codex"`` / ``"opus"``). Dispatch uses this when no explicit
        executor is specified.
    allowed_targets:
        Glob pattern or human-readable description of which file/path targets
        this role is authorized to touch. Informational for now; enforced in
        future Agency Mode.
    output_format:
        Expected output structure (e.g. ``"structured JSON per G11"``).
    stop_condition:
        When the subagent in this role is considered done.
    verification:
        What the orchestrator checks to verify success for this role.
    context_scope:
        ``"narrow"`` = the dispatch packet carries only task-local context;
        ``"broad"`` = general-purpose fallback, wider context permitted.
    """

    role: str
    model_tier: str
    allowed_targets: str
    output_format: str
    stop_condition: str
    verification: str
    context_scope: str


# ── Profile registry ──────────────────────────────────────────────────────────


PROFILES: dict[str, ProfileSpec] = {
    # ── Documentation / markdown edits ───────────────────────────────────────
    "docs-editor": ProfileSpec(
        role="docs-editor",
        model_tier="haiku",
        allowed_targets="**/*.md, plugin/skills/**/*.md, docs/**",
        output_format="structured JSON per G11; touched_files + summary_lines only",
        stop_condition="all target .md files updated, no code files touched",
        verification="diff contains only .md changes; no .py / .sh touched",
        context_scope="narrow",
    ),
    # ── Core Python / shell implementation ───────────────────────────────────
    "code-implementer": ProfileSpec(
        role="code-implementer",
        model_tier="sonnet",
        allowed_targets="renmark/**/*.py, bin/*, *.py",
        output_format="structured JSON per G11; artifact_path + sha + summary_lines",
        stop_condition="target file written, py_compile passes, verifier expectation met",
        verification="py_compile clean; no unexpected files outside target scope",
        context_scope="narrow",
    ),
    # ── Test scaffolding / pytest ─────────────────────────────────────────────
    "test-writer": ProfileSpec(
        role="test-writer",
        model_tier="codex",
        allowed_targets="tests/test_*.py, tests/*_test.py",
        output_format="structured JSON per G11; artifact_path + summary_lines",
        stop_condition="test file written; pytest -q on the new file passes",
        verification="pytest exit-code 0 on new file; no production code touched",
        context_scope="narrow",
    ),
    # ── Code / plan review ────────────────────────────────────────────────────
    "reviewer": ProfileSpec(
        role="reviewer",
        model_tier="sonnet",
        allowed_targets=".renmark/reviews/**/*.md (read-only review of any file)",
        output_format="structured review JSON: findings list + severity + summary_lines",
        stop_condition="review artifact written to .renmark/reviews/; no production file edited",
        verification="review artifact exists; no production files in touched_files",
        context_scope="narrow",
    ),
    # ── Audit / inventory reads ───────────────────────────────────────────────
    "audit-reader": ProfileSpec(
        role="audit-reader",
        model_tier="haiku",
        allowed_targets=".renmark/audits/** (read-only; writes audit artifacts only)",
        output_format="audit JSON or .md artifact in .renmark/audits/; summary_lines ≤ 5",
        stop_condition="audit artifact written; no source files modified",
        verification="only .renmark/audits/ files in touched_files; no .py edits",
        context_scope="narrow",
    ),
    # ── Release / finish lane ─────────────────────────────────────────────────
    "release-manager": ProfileSpec(
        role="release-manager",
        model_tier="sonnet",
        allowed_targets="CHANGELOG.md, pyproject.toml, plugin/commands/*.md, .renmark/state/**",
        output_format="structured JSON per G11; version bump diff + summary_lines",
        stop_condition="version bumped in pyproject.toml; CHANGELOG entry appended; lifecycle.json updated",
        verification="version string incremented; CHANGELOG entry present; lifecycle stage = ready-to-release",
        context_scope="narrow",
    ),
    # ── Research / web / library lookups ─────────────────────────────────────
    "researcher": ProfileSpec(
        role="researcher",
        model_tier="sonnet",
        allowed_targets=".renmark/research/**/*.md (writes research artifacts only)",
        output_format="research artifact in .renmark/research/; compact summary_lines ≤ 5",
        stop_condition="research artifact written with provenance metadata",
        verification="artifact exists at .renmark/research/<topic>.md; no source edits",
        context_scope="narrow",
    ),
    # ── Finish-lane specialist (verify + QA + ship gates) ────────────────────
    "finish-lane-specialist": ProfileSpec(
        role="finish-lane-specialist",
        model_tier="sonnet",
        allowed_targets=".renmark/reviews/**, .renmark/state/lifecycle.json, CHANGELOG.md",
        output_format="structured JSON per G11; gate verdict + summary_lines ≤ 5",
        stop_condition="all finish-lane checks passed; lifecycle gate advanced or blocked with reason",
        verification="lifecycle.json stage advanced; no unreviewed open blockers",
        context_scope="narrow",
    ),
    # ── Fallback — do NOT use unless no specialized profile matches ───────────
    "general-purpose": ProfileSpec(
        role="general-purpose",
        model_tier="sonnet",
        allowed_targets="any (fallback — no target restriction)",
        output_format="structured JSON per G11",
        stop_condition="task spec fulfilled",
        verification="verifier expectation met; subagent output valid per G11",
        context_scope="broad",
    ),
}


# ── Public API ────────────────────────────────────────────────────────────────


def resolve_profile(task: Any) -> str:
    """Infer the best-fit role name from a Task (or any task-shaped object/dict).

    Accepts objects with attributes *or* plain dicts. Heuristic priority order:

    1. ``tests/`` path prefix OR ``test_*`` / ``*_test.*`` filename → ``"test-writer"``
    2. ``.md`` suffix OR path under ``plugin/skills/`` / ``docs/`` → ``"docs-editor"``
    3. title / task kind mentioning ``review`` → ``"reviewer"``
    4. title / task kind mentioning ``audit`` or ``audit-read`` → ``"audit-reader"``
    5. target under ``renmark/`` or ``bin/`` (core code) → ``"code-implementer"``
    6. fallback → ``"general-purpose"``

    Never raises: any exception returns ``"general-purpose"``.
    """
    try:
        target = _get_field(task, "target", "")
        title = _get_field(task, "title", "") or _get_field(task, "spec", "")
        kind = _get_field(task, "kind", "")

        target = (target or "").strip()
        title = (title or "").strip().lower()
        kind = (kind or "").strip().lower()

        # ── 1. Test files ─────────────────────────────────────────────────────
        if _is_test_target(target):
            return "test-writer"

        # ── 2. Docs / markdown / skill files ─────────────────────────────────
        if _is_doc_target(target):
            return "docs-editor"

        # ── 3. Review ─────────────────────────────────────────────────────────
        if "review" in title or "review" in kind:
            return "reviewer"

        # ── 4. Audit ─────────────────────────────────────────────────────────
        if "audit" in title or "audit" in kind:
            return "audit-reader"

        # ── 5. Core code ──────────────────────────────────────────────────────
        if _is_core_code_target(target):
            return "code-implementer"

        # ── 6. Fallback ───────────────────────────────────────────────────────
        return "general-purpose"
    except Exception:
        return "general-purpose"


def profile_tier(role: str) -> str:
    """Return the ``model_tier`` for *role*, or ``"sonnet"`` if unknown.

    Never raises.
    """
    try:
        spec = PROFILES.get(role)
        return spec.model_tier if spec is not None else "sonnet"
    except Exception:
        return "sonnet"


def profile_of(role: str) -> ProfileSpec | None:
    """Safe lookup — returns ``None`` when *role* is not in ``PROFILES``."""
    try:
        return PROFILES.get(role)
    except Exception:
        return None


# ── Internal helpers ──────────────────────────────────────────────────────────


def _get_field(task: Any, field: str, default: str) -> str:
    """Retrieve a field from an object-or-dict, returning *default* on miss."""
    try:
        if isinstance(task, dict):
            return str(task.get(field, default))
        return str(getattr(task, field, default))
    except Exception:
        return default


def _is_test_target(target: str) -> bool:
    """True when *target* looks like a test file path."""
    if not target:
        return False
    from pathlib import Path

    p = Path(target)
    norm = target.replace("\\", "/")
    # Under tests/ directory
    if norm.startswith("tests/") or "/tests/" in norm:
        return True
    # Filename patterns test_*.py or *_test.py / *_test.ts etc.
    name = p.name
    if name.startswith("test_"):
        return True

[35m[3mexec[0m[0m
[1m/bin/bash -lc "sed -n '1,260p' renmark/parser.py"[0m in /home/renmark/projects/ai-system/.claude/worktrees/subagent-gate
[32m succeeded in 0ms:[0m
"""Plan file parser for renmark-execute.

Parses markdown plan files of the form:

    ### Task N: <title>
    - **mode:** A | B
    - **target:** path/to/file
    - **context_files:** []
    - **model:** optional
    - **verifier:** shell command
    - **verifier_timeout_s:** 60
    - **spec:**
      free prose
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class PlanError(ValueError):
    """Raised when a plan file is malformed."""


@dataclass
class Task:
    index: int  # 1-based as written in the plan
    title: str
    mode: str  # "A" or "B"
    target: str
    context_files: list[str] = field(default_factory=list)
    model: str | None = None
    verifier: str = ""
    verifier_timeout_s: int = 60
    spec: str = ""
    executor: str = "codex"  # "haiku" | "codex" | "sonnet" | "opus" | <litellm-string>
    # Phase 1 fields (v0.0.3+):
    complexity: str = "medium"  # "simple" | "medium" | "hard"
    parallel_group: int | None = (
        None  # tasks sharing a group run concurrently; default None = serial (each in its own group = index)
    )
    est_tokens: int | None = None  # planner estimate (informational)
    est_cost_usd: float | None = None  # planner estimate (informational)
    serves: str | None = None  # optional PRD traceability note, e.g. "REQ-3" or "new"


_HEADER_RE = re.compile(r"^###\s+Task\s+(\d+)\s*:\s*(.+?)\s*$")
# Loose pattern: a "### Task <digits>" heading that does NOT match the strict
# _HEADER_RE is a malformed numbered header and must raise. The digit is
# required so prose headings ("### Task overview", "### Task description")
# stay legal preamble; a word-numbered typo ("### Task Four:") is therefore
# absorbed silently — the contiguous-index check still catches the gap.
_LOOSE_TASK_RE = re.compile(r"^###\s*Task\s*\d", re.IGNORECASE)
_FIELD_RE = re.compile(r"^-\s+\*\*([a-z_]+):\*\*\s*(.*?)\s*$")
_LIST_RE = re.compile(r"^\[(.*)\]$")


def parse_plan(path: str | Path) -> list[Task]:
    """Parse a plan file and return validated tasks.

    Raises PlanError on any structural problem.
    """
    p = Path(path)
    if not p.is_file():
        raise PlanError(f"plan file not found: {path}")
    lines = p.read_text(encoding="utf-8").splitlines()

    tasks: list[Task] = []
    current: dict[str, Any] | None = None
    spec_lines: list[str] | None = None
    reading_spec = False
    line_no = 0

    def _close_current(end_line: int) -> None:
        nonlocal current, spec_lines, reading_spec
        if current is None:
            return
        if spec_lines is not None:
            current["spec"] = "\n".join(spec_lines).strip()
        try:
            tasks.append(_build_task(current))
        except PlanError as e:
            raise PlanError(f"task {current.get('index', '?')} (ending at line {end_line}): {e}") from None
        current = None
        spec_lines = None
        reading_spec = False

    for raw in lines:
        line_no += 1
        header = _HEADER_RE.match(raw)
        if header:
            _close_current(line_no - 1)
            current = {
                "index": int(header.group(1)),
                "title": header.group(2),
                "context_files": [],
                "model": None,
                "verifier_timeout_s": 60,
                "spec": "",
            }
            spec_lines = None
            reading_spec = False
            continue

        # A line that looks like a task header but doesn't match the strict
        # format (missing colon, no space after ###, etc.) is malformed — raise
        # rather than silently absorbing it into the previous task's spec.
        if _LOOSE_TASK_RE.match(raw) and not _HEADER_RE.match(raw):
            raise PlanError(f"malformed task header at line {line_no}: {raw!r}")

        if current is None:
            continue

        if reading_spec:
            stripped = raw.strip()
            if stripped.startswith("### Task ") or (raw.startswith("## ") and not raw.startswith("### ")):
                _close_current(line_no - 1)
                continue
            if spec_lines is None:
                spec_lines = []
            if raw.startswith("  "):
                spec_lines.append(raw[2:])
            else:
                spec_lines.append(raw)
            continue

        field_m = _FIELD_RE.match(raw)
        if not field_m:
            if raw.startswith("## ") and not raw.startswith("### "):
                _close_current(line_no - 1)
            continue

        key, value = field_m.group(1), field_m.group(2)
        if key == "spec":
            reading_spec = True
            spec_lines = [value] if value else []
        elif key == "context_files":
            current["context_files"] = _parse_list(value)
        elif key == "verifier_timeout_s":
            try:
                current["verifier_timeout_s"] = int(value)
            except ValueError as e:
                raise PlanError(f"line {line_no}: verifier_timeout_s must be int, got {value!r}") from e
        elif key == "parallel_group":
            try:
                current["parallel_group"] = int(value)
            except ValueError as e:
                raise PlanError(f"line {line_no}: parallel_group must be int, got {value!r}") from e
        elif key == "est_tokens":
            try:
                current["est_tokens"] = int(value)
            except ValueError as e:
                raise PlanError(f"line {line_no}: est_tokens must be int, got {value!r}") from e
        elif key == "est_cost_usd":
            try:
                current["est_cost_usd"] = float(value)
            except ValueError as e:
                raise PlanError(f"line {line_no}: est_cost_usd must be float, got {value!r}") from e
        elif key in ("mode", "target", "model", "verifier", "executor", "complexity", "serves"):
            current[key] = value
        else:
            raise PlanError(f"line {line_no}: unknown field {key!r}")

    _close_current(line_no)

    if not tasks:
        raise PlanError("plan has no tasks (no '### Task N:' headers found)")

    _validate_indices(tasks)
    return tasks


def _parse_list(raw: str) -> list[str]:
    raw = raw.strip()
    if raw in ("", "[]"):
        return []
    m = _LIST_RE.match(raw)
    if not m:
        raise PlanError(f"context_files must be a bracketed list, got {raw!r}")
    inner = m.group(1).strip()
    if not inner:
        return []
    items = [item.strip().strip('"').strip("'") for item in inner.split(",")]
    return [i for i in items if i]


def _build_task(d: dict[str, Any]) -> Task:
    required = ("mode", "target", "verifier")
    for k in required:
        v = d.get(k)
        if v is None or (isinstance(v, str) and not v.strip()):
            raise PlanError(f"missing required field: {k}")

    mode = d["mode"].strip().upper()
    if mode == "C":
        raise PlanError("mode C (cross-file) is forbidden; decompose into A/B tasks")
    if mode not in ("A", "B"):
        raise PlanError(f"invalid mode {mode!r}; must be A or B")

    target = d["target"].strip()
    if not target:
        raise PlanError("target is empty")
    if ".." in Path(target).parts:
        raise PlanError(f"target path must not contain '..': {target}")
    if Path(target).is_absolute():
        raise PlanError(f"target must be repo-relative, got absolute: {target}")

    verifier = d["verifier"].strip()
    if not verifier:
        raise PlanError("verifier is empty")

    spec = d.get("spec", "").strip()
    if not spec:
        raise PlanError("spec is empty")

    executor = (d.get("executor") or "codex").strip().lower()
    # Allow haiku, codex, sonnet, opus, or any provider-string of form "<provider>/<model>".
    # nim was removed in v0.2.0 — use haiku for simple tasks instead.
    if executor not in ("haiku", "codex", "sonnet", "opus", "fable") and "/" not in executor:
        raise PlanError(
            f"executor must be one of haiku, codex, sonnet, opus, fable, or a provider/model string, got {executor!r}"
        )

    complexity = (d.get("complexity") or "medium").strip().lower()
    if complexity not in ("simple", "medium", "hard"):
        raise PlanError(f"complexity must be simple, medium, or hard, got {complexity!r}")

    return Task(
        index=d["index"],
        title=d["title"].strip(),
        mode=mode,
        target=target,
        context_files=d["context_files"],
        model=(d["model"].strip() if d.get("model") else None),
        verifier=verifier,
        verifier_timeout_s=d["verifier_timeout_s"],
        spec=spec,
        complexity=complexity,
        parallel_group=d.get("parallel_group"),
        est_tokens=d.get("est_tokens"),
        est_cost_usd=d.get("est_cost_usd"),
        executor=executor,
        serves=(d["serves"].strip() if d.get("serves") else None),
    )


def _validate_indices(tasks: list[Task]) -> None:
    seen: set[int] = set()
    for t in tasks:
        if t.index in seen:
            raise PlanError(f"duplicate task index: {t.index}")
        seen.add(t.index)
    expected = list(range(1, len(tasks) + 1))
    actual = sorted(t.index for t in tasks)
    if actual != expected:
        raise PlanError(f"task indices must be contiguous starting at 1; got {actual}")

[35m[3mexec[0m[0m
[1m/bin/bash -lc "rg -n \"def main\\(|SystemExit\\(|usage: python -m renmark.plan_lint|return 1 if\" renmark/plan_lint.py"[0m in /home/renmark/projects/ai-system/.claude/worktrees/subagent-gate
[32m succeeded in 0ms:[0m
451:def main(argv: list[str] | None = None) -> int:
456:        sys.stdout.write("usage: python -m renmark.plan_lint <plan.md>\n")

[35m[3mexec[0m[0m
[1m/bin/bash -lc "sed -n '1,220p' renmark/plan_lint.py"[0m in /home/renmark/projects/ai-system/.claude/worktrees/subagent-gate
[32m succeeded in 0ms:[0m
"""Deterministic plan-validation engine shared by /renmark:check-plan and
/renmark:orchestrate pre-flight.

This module is the SINGLE authoritative implementation of the 8 checks that
``plugin/skills/check-plan/SKILL.md`` defines.  Both surfaces — the
``/renmark:check-plan`` skill and the orchestrate pre-flight gate — MUST run
``python -m renmark.plan_lint <plan.md>`` so they can never produce different
verdicts.  No LLM reasoning is used; every check is deterministic Python.

Public API
----------
``lint_plan(path) -> PlanLintReport``
    Run all checks against *path* and return a structured report.  Never
    raises — a ``PlanError`` from the parser is converted to a single BLOCK
    issue so callers always receive a valid report.

``PlanLintReport``
    Dataclass: ``verdict`` (PASS | WARN | BLOCK), ``issues`` (list[str]),
    ``task_count`` (int), ``executor_counts`` (dict[str, int]).

CLI
---
``python -m renmark.plan_lint <plan.md>``
    Prints the check-plan report format and exits 0 (PASS/WARN) or 1 (BLOCK).

Check severities (behaviour-preserving — mirrors the SKILL's definitions):
  BLOCK: 1 task-count >15, 2 missing/empty verifier, 3 duplicate target in
         parallel_group, 4 heavy-read G5 (>200-line context file with
         sonnet/opus executor), 5 transcript-leak G11 (denylist phrase in
         spec), 6 dependency-hygiene G11 (full-output reference without
         artifact path), 9 fable-undeclared REQ-2 (executor fable without
         a declared `top_tier: fable`), 10 fable-mechanical REQ-2 (executor
         fable on a simple/mechanical task).
  WARN:  2b test -f only verifier, 7 unbounded verifier output, 8 spec
         length >80 lines, and sanity extras (negative/absurd est_ fields).
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from renmark.parser import PlanError, Task, parse_plan

# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------

Verdict = str  # "PASS" | "WARN" | "BLOCK"


@dataclass
class PlanLintReport:
    """Result of running lint_plan()."""

    verdict: Verdict  # "PASS" | "WARN" | "BLOCK"
    issues: list[str] = field(default_factory=list)
    task_count: int = 0
    executor_counts: dict[str, int] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MAX_TASK_COUNT = 15
_MAX_SPEC_LINES = 80
_HEAVY_READ_LINE_THRESHOLD = 200
_MAX_EST_TOKENS = 200_000
_MAX_EST_COST_USD = 50.0

# Executors that BLOCK on heavy-read (G5); codex/haiku are exempt.
_HEAVY_READ_BLOCK_EXECUTORS = frozenset({"sonnet", "opus", "fable"})

# Transcript-leak denylist — verbatim from check-plan SKILL.md §2.5.
_TRANSCRIPT_LEAK_PHRASES = (
    "show me the code",
    "paste the diff",
    "return the contents",
    "include the full",
    "print the file",
    "explain the change in your response",
    "output the code",
)

# Dependency-hygiene heuristic patterns (G11).
_DEP_FULL_OUTPUT_RE = re.compile(
    r"depends\s+on\s+the\s+output\s+of\s+task\s+\d+|"
    r"uses\s+what\s+task\s+\d+\s+produced",
    re.IGNORECASE,
)

# Verifier-output-bound patterns (G3) — WARN triggers.
# We check for the presence of these tokens WITHOUT a downstream cap keyword.
# Shapes per check-plan SKILL §2.5 (refined at v0.10.0 codereview): `find`
# only without -name; `git log` accepts -n N / -nN / -N / --max-count as caps;
# node/python verifiers that print arbitrary computed output WARN unless
# capped — `py_compile` is the SKILL's sanctioned bounded form and is exempt.
_UNBOUNDED_VERIFIER_TOKENS = re.compile(
    r"\bcat\b"
    r"|\bfind\b(?!.*\s-name\b)"
    r"|git\s+diff(?!\s+--stat)(?!\s+\S+\s+\S+)"
    r"|git\s+log(?!\s+(?:-n\s*\d|-\d|--max-count))"
    r"|\b(?:node|python3?)\b(?!.*py_compile)"
)
_BOUND_CAPS = re.compile(r"\|\s*(head|tail|grep|wc|awk\s+['\"]NR|tee)\b|>\s*/dev/null")

# test -f only: matches verifier that is purely "test -f <path>" (possibly with
# an alias like "[ -f ... ]") with nothing else meaningful after.
_TEST_F_ONLY_RE = re.compile(r"^\s*(?:test\s+-[fF]\s+\S+|\[\s+-[fF]\s+\S+\s*\])\s*$")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _count_lines(path_str: str, repo_root: Path) -> int | None:
    """Return the on-disk line count of *path_str* relative to *repo_root*.

    Returns None if the file cannot be read (not found, binary, etc.).
    """
    p = repo_root / path_str
    if not p.is_file():
        return None
    try:
        return len(p.read_text(encoding="utf-8", errors="replace").splitlines())
    except OSError:
        return None


def _check_task_count(tasks: list[Task]) -> list[tuple[str, str]]:
    """Check 1 — task count ≤ 15."""
    if len(tasks) > _MAX_TASK_COUNT:
        return [
            (
                "BLOCK",
                f"Task count is {len(tasks)} (limit {_MAX_TASK_COUNT}). "
                "Split into part1/part2 plan files before orchestrate will accept this.",
            )
        ]
    return []


def _check_verifiers(tasks: list[Task]) -> list[tuple[str, str]]:
    """Check 2 — every task has a non-empty verifier (BLOCK); test -f only → WARN."""
    issues: list[tuple[str, str]] = []
    for t in tasks:
        v = (t.verifier or "").strip()
        if not v:
            issues.append(("BLOCK", f"Task {t.index}: verifier is missing or empty."))
        elif _TEST_F_ONLY_RE.match(v):
            issues.append(
                (
                    "WARN",
                    f"Task {t.index}: verifier proves file existence only (`{v}`). Consider adding a behavioral check.",
                )
            )
    return issues


def _check_parallel_group_targets(tasks: list[Task]) -> list[tuple[str, str]]:
    """Check 3 — no two tasks in the same parallel_group share a target."""
    issues: list[tuple[str, str]] = []
    groups: dict[int, dict[str, int]] = {}  # group → {target: first_task_index}
    for t in tasks:
        pg = t.parallel_group
        if pg is None:
            continue
        if pg not in groups:
            groups[pg] = {}
        if t.target in groups[pg]:
            first = groups[pg][t.target]
            issues.append(
                (
                    "BLOCK",
                    f"Task {t.index}: parallel_group {pg} already has task {first} "
                    f"targeting `{t.target}`. Parallel tasks must not share a target.",
                )
            )
        else:
            groups[pg][t.target] = t.index
    return issues


def _check_heavy_read(tasks: list[Task], repo_root: Path) -> list[tuple[str, str]]:
    """Check 4 — heavy-read G5: context file >200 lines with sonnet/opus → BLOCK."""
    issues: list[tuple[str, str]] = []
    for t in tasks:
        if t.executor not in _HEAVY_READ_BLOCK_EXECUTORS:
            continue
        for cf in t.context_files:
            lc = _count_lines(cf, repo_root)
            if lc is not None and lc > _HEAVY_READ_LINE_THRESHOLD:
                issues.append(
                    (
                        "BLOCK",
                        f"Task {t.index}: reads `{cf}` ({lc} lines) with "
                        f"executor `{t.executor}`. Heavy reads belong in codex or haiku "
                        "(G5 / executor-dispatch-rule). Reassign the task to "
                        "`executor: codex`, or split the read into a codex pre-task "
                        "that produces a summary artifact.",
                    )
                )
    return issues


def _check_transcript_leak(tasks: list[Task]) -> list[tuple[str, str]]:
    """Check 5 — transcript-leak G11: denylist phrases in spec → BLOCK."""
    issues: list[tuple[str, str]] = []
    for t in tasks:
        spec_lower = t.spec.lower()
        for phrase in _TRANSCRIPT_LEAK_PHRASES:
            if phrase in spec_lower:
                issues.append(
                    (
                        "BLOCK",
                        f"Task {t.index}: spec contains the phrase `{phrase}`. "

[35m[3mexec[0m[0m
[1m/bin/bash -lc "sed -n '220,420p' renmark/plan_lint.py"[0m in /home/renmark/projects/ai-system/.claude/worktrees/subagent-gate
[32m succeeded in 0ms:[0m
                        f"Task {t.index}: spec contains the phrase `{phrase}`. "
                        "This implies the subagent will paste generated content into "
                        "its response, violating G11 task isolation. The artifact "
                        "lives in the file at the task's target; the orchestrator "
                        "reads only summary fields. Rewrite the spec to ask for "
                        "behaviour, not output.",
                    )
                )
    return issues


def _check_dependency_hygiene(tasks: list[Task]) -> list[tuple[str, str]]:
    """Check 6 — dependency-hygiene G11: full-output reference without artifact path."""
    issues: list[tuple[str, str]] = []
    for t in tasks:
        if _DEP_FULL_OUTPUT_RE.search(t.spec):
            issues.append(
                (
                    "BLOCK",
                    f"Task {t.index}: spec references the full output of a prior task "
                    "without naming an artifact path or interface. Downstream tasks must "
                    "reference only `dependency_notes` from the prior wave's "
                    "`.renmark/state/wave-summaries/wave-X.json`, not what a prior task "
                    "did. Rewrite the spec to name the specific interface (function name, "
                    "file path, exported symbol) it depends on.",
                )
            )
    return issues


def _check_verifier_output_bound(tasks: list[Task]) -> list[tuple[str, str]]:
    """Check 7 — verifier-output-bound G3: unbounded stdout → WARN."""
    issues: list[tuple[str, str]] = []
    for t in tasks:
        v = (t.verifier or "").strip()
        if not v:
            continue  # already caught by check 2
        if _UNBOUNDED_VERIFIER_TOKENS.search(v) and not _BOUND_CAPS.search(v):
            issues.append(
                (
                    "WARN",
                    f"Task {t.index}: verifier may emit unbounded stdout (`{v}`). "
                    "Pipe through `head`, `tail`, or `grep` so verifiers answer "
                    "pass/fail in ≤ 3 lines of stdout.",
                )
            )
    return issues


def _check_spec_length(tasks: list[Task]) -> list[tuple[str, str]]:
    """Check 8 — spec length > 80 lines → WARN."""
    issues: list[tuple[str, str]] = []
    for t in tasks:
        n = len(t.spec.splitlines())
        if n > _MAX_SPEC_LINES:
            issues.append(
                (
                    "WARN",
                    f"Task {t.index}: spec is {n} lines (limit {_MAX_SPEC_LINES}). "
                    "Long specs hide multiple implicit tasks. Consider splitting into "
                    "2 atomic tasks, or extracting context into a sibling `.md` file "
                    "(`scope-contract.md` pattern).",
                )
            )
    return issues


def _check_fable_declared(tasks: list[Task], repo_root: Path) -> list[tuple[str, str]]:
    """Check 9 — fable-undeclared REQ-2: executor fable without `top_tier: fable` → BLOCK."""
    from . import capabilities

    issues: list[tuple[str, str]] = []
    fable_tasks = [t for t in tasks if t.executor == "fable"]
    if not fable_tasks:
        return issues
    if capabilities.top_tier(repo_root) != "fable":
        for t in fable_tasks:
            issues.append(
                (
                    "BLOCK",
                    f"Task {t.index}: executor `fable` but this project has not "
                    "declared `top_tier: fable`. Declare it in "
                    ".renmark/memory/routing.md (## Model tiers) or reassign to `opus`.",
                )
            )
    return issues


def _check_fable_mechanical(tasks: list[Task]) -> list[tuple[str, str]]:
    """Check 10 — fable-mechanical REQ-2: executor fable on a simple task → BLOCK."""
    issues: list[tuple[str, str]] = []
    for t in tasks:
        if t.executor == "fable" and t.complexity == "simple":
            issues.append(
                (
                    "BLOCK",
                    f"Task {t.index}: executor `fable` on a simple/mechanical task — "
                    "REQ-2 prohibits fable for mechanical or bulk work regardless of "
                    "declaration. Route to haiku/codex.",
                )
            )
    return issues


def _check_sanity_extras(tasks: list[Task]) -> list[tuple[str, str]]:
    """Sanity extras — all WARN only, never BLOCK (behaviour-preserving)."""
    issues: list[tuple[str, str]] = []
    for t in tasks:
        if t.est_tokens is not None:
            if t.est_tokens < 0:
                issues.append(
                    (
                        "WARN",
                        f"Task {t.index}: est_tokens is negative ({t.est_tokens}). Check planner estimate.",
                    )
                )
            elif t.est_tokens > _MAX_EST_TOKENS:
                issues.append(
                    (
                        "WARN",
                        f"Task {t.index}: est_tokens is {t.est_tokens} "
                        f"(> {_MAX_EST_TOKENS:,}). Consider splitting the task.",
                    )
                )
        if t.est_cost_usd is not None:
            if t.est_cost_usd < 0:
                issues.append(
                    (
                        "WARN",
                        f"Task {t.index}: est_cost_usd is negative ({t.est_cost_usd}). Check planner estimate.",
                    )
                )
            elif t.est_cost_usd > _MAX_EST_COST_USD:
                issues.append(
                    (
                        "WARN",
                        f"Task {t.index}: est_cost_usd is ${t.est_cost_usd:.2f} "
                        f"(> ${_MAX_EST_COST_USD:.2f}). Consider splitting the task.",
                    )
                )
    return issues


def _derive_verdict(raw_issues: list[tuple[str, str]]) -> Verdict:
    """Derive overall verdict from (severity, message) pairs."""
    severities = {sev for sev, _ in raw_issues}
    if "BLOCK" in severities:
        return "BLOCK"
    if "WARN" in severities:
        return "WARN"
    return "PASS"


def _build_executor_counts(tasks: list[Task]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for t in tasks:
        counts[t.executor] = counts.get(t.executor, 0) + 1
    return counts


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def lint_plan(path: str | Path) -> PlanLintReport:
    """Run all plan checks and return a ``PlanLintReport``.

    Never raises.  A ``PlanError`` from the parser surfaces as a single BLOCK
    issue so the caller always receives a valid report even for empty/corrupt
    plan files.
    """
    repo_root = Path.cwd()

    # Parse — any PlanError → one graceful BLOCK issue.
    try:
        tasks = parse_plan(path)
    except PlanError as exc:
        return PlanLintReport(
            verdict="BLOCK",
            issues=[f"BLOCK: plan parse error — {exc}"],
            task_count=0,
            executor_counts={},
        )
    except Exception as exc:
        return PlanLintReport(
            verdict="BLOCK",
            issues=[f"BLOCK: unexpected error reading plan — {exc}"],
            task_count=0,
            executor_counts={},
        )

    # Run all checks and collect (severity, message) pairs.
    raw: list[tuple[str, str]] = []
    raw.extend(_check_task_count(tasks))
    raw.extend(_check_verifiers(tasks))
    raw.extend(_check_parallel_group_targets(tasks))
    raw.extend(_check_heavy_read(tasks, repo_root))
    raw.extend(_check_transcript_leak(tasks))
    raw.extend(_check_dependency_hygiene(tasks))
    raw.extend(_check_verifier_output_bound(tasks))

[35m[3mexec[0m[0m
[1m/bin/bash -lc "sed -n '420,520p' renmark/plan_lint.py"[0m in /home/renmark/projects/ai-system/.claude/worktrees/subagent-gate
[32m succeeded in 0ms:[0m
    raw.extend(_check_verifier_output_bound(tasks))
    raw.extend(_check_spec_length(tasks))
    raw.extend(_check_fable_declared(tasks, repo_root))
    raw.extend(_check_fable_mechanical(tasks))
    raw.extend(_check_sanity_extras(tasks))

    verdict = _derive_verdict(raw)
    # Format issues as "BLOCK: ..." / "WARN: ..." strings for the report.
    issues = [f"{sev}: {msg}" for sev, msg in raw]
    return PlanLintReport(
        verdict=verdict,
        issues=issues,
        task_count=len(tasks),
        executor_counts=_build_executor_counts(tasks),
    )


# ---------------------------------------------------------------------------
# CLI  (python -m renmark.plan_lint <plan.md>)
# ---------------------------------------------------------------------------


def _fmt_executor_counts(counts: dict[str, int]) -> str:
    if not counts:
        return ""
    parts = []
    for name in sorted(counts):
        parts.append(f"{name}×{counts[name]}")
    return "  Executors: " + "  ".join(parts)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point.  Exit 0 = PASS or WARN; 1 = BLOCK."""
    argv = sys.argv[1:] if argv is None else list(argv)

    if not argv or argv[0] in ("-h", "--help"):
        sys.stdout.write("usage: python -m renmark.plan_lint <plan.md>\n")
        return 0

    plan_path = argv[0]
    report = lint_plan(plan_path)

    # --- Header ---
    plan_name = Path(plan_path).name
    sys.stdout.write(f"check-plan: {plan_name}\n")
    sys.stdout.write(f"Tasks: {report.task_count}{_fmt_executor_counts(report.executor_counts)}\n")
    sys.stdout.write("\n")

    blocks = [msg for msg in report.issues if msg.startswith("BLOCK:")]
    warns = [msg for msg in report.issues if msg.startswith("WARN:")]

    if blocks:
        sys.stdout.write("BLOCK (must fix before running):\n")
        for b in blocks:
            # Strip the "BLOCK: " prefix so format matches SKILL's spec.
            sys.stdout.write(f"- {b[len('BLOCK: ') :]}\n")
        sys.stdout.write("\n")

    if warns:
        sys.stdout.write("WARN (review before running):\n")
        for w in warns:
            sys.stdout.write(f"- {w[len('WARN: ') :]}\n")
        sys.stdout.write("\n")

    if report.verdict in ("PASS", "WARN"):
        sys.stdout.write("PASS: structural constraints met\n")
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())

[35m[3mexec[0m[0m
[1m/bin/bash -lc "rg -n \"subagent_gate|preview_line\\(|challenge_plan\\(\" -S ."[0m in /home/renmark/projects/ai-system/.claude/worktrees/subagent-gate
[35m[3mexec[0m[0m
[1m/bin/bash -lc "git diff main..HEAD --unified=20 -- plugin/skills/orchestrate/SKILL.md | sed -n '1,220p'"[0m in /home/renmark/projects/ai-system/.claude/worktrees/subagent-gate
[32m succeeded in 0ms:[0m
./CLAUDE.md:177:Before any task dispatch or model call, answer the 4-question gate: (1) Can existing state, files, git, or a parser answer this? (2) Can a deterministic script/check do it reliably? (3) Is this repeated enough to deserve a reusable check? (4) Is AI actually needed for judgment, synthesis, or ambiguous reasoning? Deterministic tasks (git/worktree state, artifact metadata, version/release checks, plan lint, mirror validation, test baseline) route to deterministic checks in `renmark/worktree.py`, `renmark/lint.py`, or shell. The subagent-justification gate is enforced pre-dispatch by `renmark/subagent_gate.py` (`python -m renmark.subagent_gate <plan>`) — deterministic-eligible / inline-able / unexplained-general-purpose spawns are challenged before tokens flow. Route judgment-heavy tasks (merge conflict risk, release-readiness reasoning, branch strategy) only to model-based agents. Cost preview MUST label tasks as deterministic or model-driven.
./AGENTS.md:69:**Deterministic-first execution.** Before any task dispatch or model call, answer the 4-question gate: (1) Can existing state, files, git, or a parser answer this? (2) Can a deterministic script/check do it reliably? (3) Is this repeated enough to deserve a reusable check? (4) Is AI actually needed for judgment, synthesis, or ambiguous reasoning? Deterministic tasks (git/worktree state, artifact metadata, version/release checks, plan lint, mirror validation, test baseline) route to deterministic checks in `renmark/worktree.py`, `renmark/lint.py`, or shell. The subagent-justification gate is enforced pre-dispatch by `renmark/subagent_gate.py` (`python -m renmark.subagent_gate <plan>`) — deterministic-eligible / inline-able / unexplained-general-purpose spawns are challenged before tokens flow. Route judgment-heavy tasks (merge conflict risk, release-readiness reasoning, branch strategy) only to model-based agents. Cost preview MUST label tasks as deterministic or model-driven.
./CHANGELOG.md:6:- `renmark/subagent_gate.py` — pure, zero-LLM gate. `justify_task` answers REQ-21's 4 questions mechanically (deterministic path? scoped role? orchestrator-inline? large/ambiguous enough?); `challenge_plan` rolls a plan up (deterministic-eligible / inline-able / unexplained-general-purpose spawns flagged); `preview_line` for the cost preview; `main()` CLI (`python -m renmark.subagent_gate <plan>` → exit 0 clean / 1 challenged / 2 usage), mirroring `plan_lint`. Composes `cost.is_deterministic_item`/`_get` + `subagent_profiles.resolve_profile`/`profile_tier` — does not re-implement. Never raises.
./CHANGELOG.md:8:- `tests/test_subagent_gate.py` — 11 tests: deterministic→no-subagent, simple/tiny→inline-flagged, hard-scoped→clean, general-purpose-without-reason→challenged (+reason clears it), plan-level challenge invariants, never-raises.
./CHANGELOG.md:9:**Files changed:** renmark/subagent_gate.py (new), tests/test_subagent_gate.py (new), orchestrate/SKILL.md, 3 _shared/*.md, CLAUDE.md, AGENTS.md, CHANGELOG.md.
./tests/test_subagent_gate.py:1:"""Tests for the enforced subagent-justification gate (renmark.subagent_gate).
./tests/test_subagent_gate.py:14:from renmark import subagent_gate as g
./tests/test_subagent_gate.py:82:    pc = g.challenge_plan(plan)
./tests/test_subagent_gate.py:87:    assert g.preview_line(pc).startswith("⚠")
./tests/test_subagent_gate.py:95:    pc = g.challenge_plan(plan)
./tests/test_subagent_gate.py:98:    assert g.preview_line(pc).startswith("✓")
./tests/test_subagent_gate.py:103:    pc = g.challenge_plan(plan)
./tests/test_subagent_gate.py:117:        pc = g.challenge_plan(bad_plan)
./tests/test_subagent_gate.py:123:    pc = g.challenge_plan([])
./plugin/skills/orchestrate/SKILL.md:88:python -m renmark.subagent_gate <plan>   # exit 0 = clean, 1 = challenged
./plugin/skills/orchestrate/SKILL.md:98:**Cost preview** — `renmark-execute --dry-run <plan>` shows the task list + estimated cost. The cost preview MUST also carry the subagent-gate line (`renmark.subagent_gate.preview_line`), per `${CLAUDE_PLUGIN_ROOT}/skills/_shared/cost-preview.md`.
./plugin/skills/_shared/deterministic-first.md:116:`renmark/subagent_gate.py` (zero-LLM). Before dispatching a plan, run it like
./plugin/skills/_shared/deterministic-first.md:120:python -m renmark.subagent_gate <plan.md>   # exit 0 = clean, 1 = challenged, 2 = usage
./plugin/skills/_shared/deterministic-first.md:126:The cost preview surfaces `subagent_gate.preview_line(...)`. This turns REQ-21's
./plugin/skills/_shared/subagent-budget.md:107:This budget is no longer advice-only: `renmark/subagent_gate.py` deterministically
./plugin/skills/_shared/subagent-budget.md:108:challenges a plan before dispatch (`python -m renmark.subagent_gate <plan>`).
./renmark/subagent_gate.py:147:def challenge_plan(tasks: Any, *, unjustified_share_threshold: float = 0.5) -> PlanChallenge:
./renmark/subagent_gate.py:216:def preview_line(challenge: PlanChallenge) -> str:
./renmark/subagent_gate.py:223:    """CLI: ``python -m renmark.subagent_gate <plan.md>``.
./renmark/subagent_gate.py:236:        sys.stderr.write("usage: python -m renmark.subagent_gate <plan.md>\n")
./renmark/subagent_gate.py:243:    ch = challenge_plan(tasks)
./renmark/subagent_gate.py:244:    sys.stdout.write(preview_line(ch) + "\n")
./plugin/skills/_shared/cost-preview.md:137:`renmark.subagent_gate` — call `challenge_plan(tasks)` then `preview_line(...)`

[32m succeeded in 0ms:[0m
diff --git a/plugin/skills/orchestrate/SKILL.md b/plugin/skills/orchestrate/SKILL.md
index 5c244fa..20d17b6 100644
--- a/plugin/skills/orchestrate/SKILL.md
+++ b/plugin/skills/orchestrate/SKILL.md
@@ -65,41 +65,54 @@ Confirm the path with the user before continuing.
 
 **Pipeline state check** — `state.read_pipeline_state(repo)`. If a prior run was paused, offer resume vs reset. New runs initialize fresh state:
 
 ```python
 from renmark import state
 state.write_pipeline_state(repo, current_phase="orchestrate", current_plan=<plan>,
                            wave_index=0, wave_total=<computed>, clear_tasks=True)
 ```
 
 **Executor check** — `command -v codex` if the plan has any `executor: codex` tasks. If missing, stop and tell the user before running.
 
 **Plan validation** — run `python -m renmark.plan_lint <plan>` directly before spending tokens. If it exits 1 (BLOCK), fix the plan first; WARNs can proceed with user acknowledgment. (Defense-in-depth: the same engine validated the plan at plan-time; running it again at dispatch-time means check-plan and orchestrate can never drift.)
 
 **Refactor safety** — if the plan has any `complexity: hard` task or the spec mentions "refactor"/"rename"/"restructure"/"migrate":
 1. Confirm clean working tree (`git status`).
 2. Checkpoint commit: `git -c user.name="renmark-orchestrate" -c user.email="orchestrate@renmark.local" commit --allow-empty -m "chore: checkpoint before <plan name>"`.
 3. Baseline each affected verifier — if any fails now, **stop**: do not orchestrate into a broken baseline.
 
 **Changelog / decisions check** — read the last 5 entries in `CHANGELOG.md`, and when `.renmark/memory/decisions.md` is present, also read its decision titles + guard text (titles and guards only — never full bodies; REQ-5). Flag any "Do not change" guard or recorded decision the plan would contradict. A contradiction is **semantic**: the plan would undo or overwrite a guarded decision — and this binds even when there is **no target-file overlap** (a plan can violate a decision without touching the same file). On any such contradiction, surface it and **PAUSE for reconciliation** before dispatching; never silently overwrite a recorded decision.
 
-**Cost preview** — `renmark-execute --dry-run <plan>` shows the task list + estimated cost.
+**Subagent gate (deterministic, pre-dispatch)** — run the enforced justification gate before spending:
+
+```bash
+python -m renmark.subagent_gate <plan>   # exit 0 = clean, 1 = challenged
+```
+
+It challenges the plan per REQ-21's 4 questions (deterministic-eligible tasks,
+inline-able simple tasks, `general-purpose` roles without a `role_reason`). On a
+**challenged** verdict (exit 1), surface the one-line `preview_line` verdict and
+require explicit acknowledgment before dispatch — do NOT auto-proceed on a
+subagent-heavy or deterministic-eligible plan. Prefer converting flagged tasks to
+deterministic checks or assigning a scoped profile (`subagent-profiles.md`).
+
+**Cost preview** — `renmark-execute --dry-run <plan>` shows the task list + estimated cost. The cost preview MUST also carry the subagent-gate line (`renmark.subagent_gate.preview_line`), per `${CLAUDE_PLUGIN_ROOT}/skills/_shared/cost-preview.md`.
 
 **Headless gate (cost approval).** Before the `Proceed? [y/N]` prompt below, consult the headless contract (`plugin/skills/_shared/headless-contract.md`):
 
 ```python
 from renmark import headless
 envelope = headless.resolve_gate(
     repo, "cost", kind="dangerous",
     originating_skill="orchestrate",
     what="~$X across N tasks",   # the dry-run estimate
 )
 ```
 
 - **Headless** (`envelope["mode"] != "interactive"`) → emit the `needs_input` JSON block + `headless.render_return(envelope)` prose line and **STOP** — do not dispatch.
 - **Interactive** (`{"mode": "interactive"}`) → fall through to the prompt below, unchanged.
 
 This human cost-approval gate is **distinct** from the Tier-1 usage-limit pause in 3a-bis (which auto-pauses on an already-exceeded local limit); leave that intact.
 
 Interactive prompt: *"Proceed? [y/N]"*
 
 ### 3. Dispatch tasks in waves (G11 isolation)

[35m[3mcodex[0m[0m
The first concrete gap is already visible: there’s no runtime reference to `renmark.subagent_gate` outside the new module and tests. I’m checking the actual orchestrate/dry-run implementation now to confirm whether the “enforced pre-flight” and “cost preview carries the line” parts were wired in code or only documented.
[35m[3mexec[0m[0m
[1m/bin/bash -lc "rg -n \"dry-run|estimate_cost\\(|Proceed\\? \\[y/N\\]|plan_lint|subagent gate|subagent-gate|preview_line|challenge_plan\\(\" renmark/cli renmark -g '"'!renmark/subagent_gate.py'"'"[0m in /home/renmark/projects/ai-system/.claude/worktrees/subagent-gate
[32m succeeded in 0ms:[0m
renmark/cli/_engine.py:1169:    ap.add_argument("--dry-run", action="store_true", help="parse plan, list tasks, exit")
renmark/plan_lint.py:7:``python -m renmark.plan_lint <plan.md>`` so they can never produce different
renmark/plan_lint.py:23:``python -m renmark.plan_lint <plan.md>``
renmark/plan_lint.py:438:# CLI  (python -m renmark.plan_lint <plan.md>)
renmark/plan_lint.py:456:        sys.stdout.write("usage: python -m renmark.plan_lint <plan.md>\n")
renmark/cli/_engine.py:1169:    ap.add_argument("--dry-run", action="store_true", help="parse plan, list tasks, exit")
renmark/roadmap.py:135:        cost = _estimate_cost(models, tokens)
renmark/roadmap.py:154:        cost = _estimate_cost(models, tokens)
renmark/roadmap.py:179:def _estimate_cost(model_str: str, tokens: int) -> float:
renmark/cost.py:9:- **plan preview** — ``estimate_cost(items)`` runs on the validated task list to
renmark/cost.py:137:def estimate_cost(items: list) -> CostPreview:
renmark/hygiene.py:265:            "Defaults to dry-run; pass --apply to make changes."
renmark/hygiene.py:273:        help="Make changes on disk (default is dry-run).",
renmark/hygiene.py:306:    mode_label = "apply" if args.apply else "dry-run"
renmark/behavior.py:441:def _render_plan_lint(repo: Path, case: Case) -> str:
renmark/behavior.py:448:    :func:`plan_lint._check_transcript_leak`, is a scaffolding-level invariant:
renmark/behavior.py:454:    from . import plan_lint
renmark/behavior.py:467:    # rendered verdict reflects the live plan_lint logic, not a hand-copy.
renmark/behavior.py:477:    leak_issues = plan_lint._check_transcript_leak([task])
renmark/behavior.py:493:    "plan_lint": _render_plan_lint,

[35m[3mexec[0m[0m
[1m/bin/bash -lc "sed -n '430,560p' renmark/cli/_engine.py"[0m in /home/renmark/projects/ai-system/.claude/worktrees/subagent-gate
[32m succeeded in 0ms:[0m
    done: set[int] = set()
    if resume:
        pause = read_pause(repo)
        if pause is None:
            _print("note: no PAUSED state found; running from start")
        else:
            _print(f"resuming run {pause.run_id}; last attempted task: {pause.last_task_index}")
        raw_done = completed_task_indices(repo)
        # Cross-check: a git-log scan may include indices from a DIFFERENT plan
        # (reused task numbers, ``(task N)``-suffix side commits, etc.).
        # Silently skipping tasks that don't exist in the current plan is the
        # single most expensive observed failure — the ledger and git log must
        # be trusted, but ONLY for indices that unambiguously belong to THIS plan.
        done, ambiguous = _cross_check_skip_list(raw_done, tasks)
        if ambiguous:
            _print(
                f"warning: skip-list cross-check found {len(ambiguous)} orphaned "
                f"index(es) {sorted(ambiguous)} not in current plan "
                f"({len(tasks)} tasks).  These will NOT be silently skipped — "
                f"re-running to avoid false completions.  "
                f"(Likely cause: reused task numbers or commits from a different plan.)"
            )
        if done:
            _print(f"skipping already-committed tasks: {sorted(done)}")

    run_id = new_run_id()
    state_dir(repo)  # ensure exists
    _print(
        f"renmark  plan: {plan_path}  run: {run_id}\n"
        f"model_default: {cfg.prefer_small_model}   "
        f"budget: {cfg.max_tokens_per_run} tok / {cfg.max_minutes_per_run} min"
    )

    if dry_run:
        from .. import capabilities as _caps
        from .. import dispatch as _d

        waves = _d.group_tasks_by_wave(tasks)
        _print(f"\n[DRY RUN] {len(tasks)} tasks in {len(waves)} wave(s):\n")
        # Cost estimates per executor — approximate $/kT (output tokens).
        cost_per_kt = {"haiku": 0.0001, "codex": 0.05, "sonnet": 0.003, "opus": 0.015, "fable": 0.030}
        total_tokens = 0
        total_cost = 0.0
        for w_idx, w in enumerate(waves, 1):
            wave_tag = "(parallel)" if len(w) > 1 else ""
            _print(f"  Wave {w_idx}: {len(w)} task(s) {wave_tag}")
            for t in w:
                mark = "DONE" if t.index in done else "TODO"
                tok = t.est_tokens or _default_tokens_for_complexity(t.complexity)
                # Resolve declared-tier fallback (fable→opus when undeclared) so
                # the preview prices and labels what will actually run.
                ex = _caps.effective_executor(t.executor, repo)
                ex_display = f"{t.executor}→{ex}" if ex != t.executor else ex
                # A downgraded executor (e.g. fable→opus) invalidates any prefilled
                # est_cost_usd — it was estimated at the wrong tier. Reprice from
                # the effective executor's rate so display matches what's charged.
                cost = t.est_cost_usd if ex == t.executor else None
                if cost is None:
                    # Infer from executor.
                    rate = cost_per_kt.get(ex, 0.0)
                    if "/" in ex:  # provider/model — assume openai-compatible mid-tier
                        rate = cost_per_kt.get("sonnet", 0.003)
                    cost = (tok / 1000.0) * rate
                cost_str = f"${cost:.3f}" if cost > 0 else "free"
                _print(
                    f"    [{mark}] task {t.index} {ex_display:<8} {t.complexity:<6} "
                    f"~{tok:>5} tok  {cost_str:>8}  → {t.target}  ({t.title})"
                )
                total_tokens += tok
                total_cost += cost
        _print(f"\n  TOTAL estimate: ~{total_tokens:,} tokens · ~${total_cost:.3f}")
        _print(
            "  (codex metered separately; haiku/sonnet/opus/fable bill to your Claude Code quota, ~10k overhead/task)"
        )
        return 0

    # Start anchor tag.
    _git_tag(repo, f"renmark-run-{run_id}-start")
    clear_pause(repo)

    deadline = time.monotonic() + (cfg.max_minutes_per_run * 60)
    tokens_used = 0
    passed: list[int] = []
    failed_task: Task | None = None
    failure_kind: str | None = None
    skipped: list[int] = []

    # Group tasks into waves for parallel execution. Tasks sharing a
    # `parallel_group` run concurrently; defaults to one wave per task.
    from .. import dispatch as _dispatch

    try:
        waves = _dispatch.group_tasks_by_wave(tasks)
        for w in waves:
            _dispatch.validate_wave(w)
    except ValueError as e:
        _print(f"ERROR: plan has invalid wave: {e}")
        return 2

    needs_agent: list[int] = []  # tasks executor=opus/sonnet, skill must dispatch

    # Holder for the current wave's task list, set per-wave below so the
    # runner can compute each task's sibling targets (for rollback isolation).
    current_wave: list[Task] = []

    def _runner(task: Task, _repo: Path) -> _dispatch.TaskResult:
        """Adapter: existing _execute_task tuple → dispatch.TaskResult."""
        sibling_targets = [t.target for t in current_wave if t.index != task.index]
        ok, reason, used, sha = _execute_task(
            task=task,
            repo=_repo,
            run_id=run_id,
            cfg=cfg,
            remaining_token_budget=max(0, cfg.max_tokens_per_run - tokens_used),
            total=len(tasks),
            sibling_targets=sibling_targets,
        )
        return _dispatch.TaskResult(
            task_index=task.index,
            executor=task.executor,
            status="passed" if ok else "failed",
            sha=sha,
            tokens_out=used,
            note=reason,
        )

    # Set when a wave-level budget/deadline gate trips. Unlike a per-task
    # failure, this is not tied to one task — it means "stop, out of budget".
    budget_kind: str | None = None

    def _skip_all_remaining(from_wave_idx: int) -> None:

[35m[3mexec[0m[0m
[1m/bin/bash -lc "sed -n '560,760p' renmark/cli/_engine.py"[0m in /home/renmark/projects/ai-system/.claude/worktrees/subagent-gate
[32m succeeded in 0ms:[0m
    def _skip_all_remaining(from_wave_idx: int) -> None:
        """Mark every not-done, not-yet-run task from this wave onward skipped.

        Without this the run only recorded the CURRENT wave's tasks as skipped,
        silently dropping later waves from the count and the pause state.
        """
        for later in waves[from_wave_idx:]:
            for t in later:
                if t.index in done or t.index in passed or t.index in skipped:
                    continue
                skipped.append(t.index)

    for wave_idx, wave in enumerate(waves):
        # Already-committed tasks (from --resume) just emit DONE lines.
        for t in wave:
            if t.index in done:
                _print(
                    _format_status_line(
                        t.index,
                        len(tasks),
                        t.title,
                        "DONE",
                        0.0,
                        0,
                        "(prev run)",
                    )
                )
                if t.index not in passed:
                    passed.append(t.index)

        runnable = [t for t in wave if t.index not in done]
        if not runnable or failed_task is not None:
            continue

        # Wave-level budget gates. Trip → record EVERY remaining task (this wave
        # and all later waves) as skipped, then break to the budget-pause path.
        if tokens_used >= cfg.max_tokens_per_run:
            budget_kind = "token_budget"
            _skip_all_remaining(wave_idx)
            break
        if time.monotonic() > deadline:
            budget_kind = "time_budget"
            _skip_all_remaining(wave_idx)
            break

        # Dispatch the wave. codex/haiku run in parallel; opus/sonnet are
        # marked `needs_agent` for the skill to handle via Agent tool.
        # Publish the wave so _runner can derive each task's sibling targets.
        current_wave = runnable
        try:
            wave_result = _dispatch.dispatch_wave(
                runnable,
                repo=repo,
                run_task=_runner,
            )
        except Exception as exc:  # pragma: no cover — defense in depth
            import traceback as _tb

            tb = _tb.format_exc()
            _print(f"ERROR dispatching wave: {type(exc).__name__}: {str(exc)[:100]}")
            for t in runnable:
                _record_escalation(
                    repo,
                    t,
                    run_id,
                    _choose_model(t, cfg),
                    base_prompt="(wave dispatch failed)",
                    response="",
                    verifier_log=tb,
                    retry_count=0,
                    prompt_tokens=0,
                    completion_tokens=0,
                )
            failed_task = runnable[0]
            failure_kind = "wave_dispatch_failed"
            break

        # Process results in task-index order so the log reads naturally.
        for r in sorted(wave_result.tasks, key=lambda x: x.task_index):
            task_obj = next(t for t in runnable if t.index == r.task_index)
            if r.status == "passed":
                passed.append(r.task_index)
                tokens_used += r.tokens_out
                _memory_log_outcome(repo, task_obj, "passed", run_id)
            elif r.status == "needs_agent":
                needs_agent.append(r.task_index)
                _print(
                    _format_status_line(
                        r.task_index,
                        len(tasks),
                        task_obj.title,
                        "NEEDS-AGENT",
                        0.0,
                        0,
                        f"executor={r.executor} — orchestrate skill must dispatch via Agent tool",
                    )
                )
            else:  # failed
                failed_task = task_obj
                failure_kind = r.note or "task_failed"
                tokens_used += r.tokens_out
                _memory_log_outcome(repo, task_obj, "failed", run_id, note=r.note)
                break  # stop wave processing; outer loop also breaks via failed_task check

    # End-of-run summary.
    _print("")
    parts = [
        f"{len(passed)}/{len(tasks)} passed",
        f"{1 if (failed_task or budget_kind) else 0} failed",
        f"{len(skipped)} skipped",
    ]
    if needs_agent:
        parts.append(f"{len(needs_agent)} needs-agent ({sorted(needs_agent)})")
    _print(", ".join(parts))
    today = usage_today(repo)
    # Token-gate honesty: codex usage rolls up to OpenAI's dashboard, recorded
    # here as 0 tokens — so for a codex-only run tokens_used stays 0 and the
    # RENMARK_MAX_TOKENS_PER_RUN gate is INERT (the time/task budgets are the
    # real gates). Printing "0 / 50000 (0.0%)" would falsely imply the token
    # gate is live. When nothing was metered locally, say so plainly instead.
    if tokens_used == 0:
        _print(
            f"Tokens this run: n/a (codex usage reported upstream) | Today: {today} | Month: {usage_this_month(repo)}"
        )
    else:
        _print(
            f"Tokens this run: {tokens_used} / {cfg.max_tokens_per_run} "
            f"({100 * tokens_used / max(cfg.max_tokens_per_run, 1):.1f}%) | "
            f"Today: {today} | Month: {usage_this_month(repo)}"
        )
    waves_count = len(waves)
    _print(f"Waves: {waves_count} (parallel-grouped from {len(tasks)} tasks)")

    # Budget/deadline exhaustion: NOT a success. Write an honest pause keyed to
    # the first skipped task and exit non-zero — never the "All tasks completed"
    # branch. Checked before the success branch so a tripped gate can't fall
    # through to exit 0.
    if budget_kind is not None and failed_task is None:
        first_skipped = min(skipped) if skipped else 0
        reason = "budget" if budget_kind == "token_budget" else "deadline"
        write_pause(
            repo,
            PauseState(
                run_id=run_id,
                plan_path=str(plan_path),
                last_task_index=first_skipped,
                reason=reason,
                ts=now_iso(),
            ),
        )
        _print(
            f"PAUSED ({reason}): {budget_kind} gate tripped with "
            f"{len(skipped)} task(s) unrun {sorted(skipped)}.\n"
            f"Resume with: renmark-execute --resume {plan_path}"
        )
        return 10

    if failed_task is None and not needs_agent:
        _git_tag(repo, f"renmark-run-{run_id}-end")
        clear_pause(repo)
        _print("All tasks completed.")
        return 0
    if failed_task is None and needs_agent:
        _print(
            f"Note: tasks {sorted(needs_agent)} need Claude (opus/sonnet) dispatch "
            f"via the /renmark:orchestrate skill's Agent-tool path. "
            f"renmark-execute (CLI) doesn't dispatch Claude executors."
        )
        # We did not fail — orchestrate skill is expected to follow up.
        # Don't tag run-end yet; that's the skill's job after Agent tasks land.
        return 0

    # Failure path: write pause state and exit non-zero.
    # Both early-return branches above guarantee failed_task is non-None here.
    assert failed_task is not None
    write_pause(
        repo,
        PauseState(
            run_id=run_id,
            plan_path=str(plan_path),
            last_task_index=failed_task.index,
            reason=failure_kind or "unknown",
            ts=now_iso(),
        ),
    )
    _print(
        f"PAUSED at task {failed_task.index} ({failure_kind}). "
        f"Artifacts: .renmark/state/escalations/task-{failed_task.index}/\n"
        f"Resume with: renmark-execute --resume {plan_path}"
    )
    return 10


def _execute_task(
    *,
    task: Task,
    repo: Path,
    run_id: str,
    cfg: Config,
    remaining_token_budget: int,
    total: int,

[35m[3mcodex[0m[0m
I’ve confirmed the new gate is not referenced by runtime code outside its own module and tests. I’m validating that against behavior now by checking line-level details and, if possible, running the focused test file plus a couple of direct function/CLI probes.
[35m[3mexec[0m[0m
[1m/bin/bash -lc "nl -ba renmark/subagent_gate.py | sed -n '1,260p'"[0m in /home/renmark/projects/ai-system/.claude/worktrees/subagent-gate
[32m succeeded in 0ms:[0m
     1	"""Enforced subagent-justification gate — the deterministic-first check that runs
     2	BEFORE any subagent is dispatched (strengthens REQ-21 from advice into a gate).
     3	
     4	Renmark already ships the *advice* (``_shared/deterministic-first.md`` 4-question
     5	gate, ``_shared/subagent-budget.md``) and the cost machinery that *tags*
     6	deterministic vs model-driven work (``renmark.cost``). What was missing is a pure,
     7	zero-LLM function the dispatch path can actually CALL to challenge a spawn — so a
     8	subagent-heavy, deterministic-eligible plan gets flagged before tokens flow.
     9	
    10	This module composes the existing pieces — it does NOT re-implement them:
    11	- ``renmark.cost.is_deterministic_item`` — the deterministic/model-driven signal.
    12	- ``renmark.cost._get`` — the dict/attr accessor.
    13	- ``renmark.subagent_profiles.resolve_profile`` / ``profile_tier`` — the scoped
    14	  role + cheapest-capable tier (``general-purpose`` is fallback-only).
    15	
    16	Every function is pure and NEVER raises — on any bad input it degrades to the
    17	safe/conservative answer (assume a subagent IS needed rather than silently
    18	suppressing one), so the gate can never break a real dispatch.
    19	
    20	The 4 questions (deterministic-first.md), answered mechanically where possible:
    21	  Q1 Can git/grep/read/parser/state answer this?     → deterministic-eligible
    22	  Q2 Can a deterministic script/check answer this?    → deterministic-eligible
    23	  Q3 Can the orchestrator do this directly (no agent)? → trivial/simple + tiny
    24	  Q4 Is it large/ambiguous enough to justify a subagent? → complexity/size
    25	"""
    26	
    27	from __future__ import annotations
    28	
    29	from dataclasses import dataclass, field
    30	from typing import Any
    31	
    32	from renmark import cost, subagent_profiles
    33	
    34	# Complexity labels that, on their own, justify a subagent (Q4).
    35	_SUBAGENT_JUSTIFYING_COMPLEXITY: frozenset[str] = frozenset({"hard", "medium"})
    36	
    37	# Below this token estimate a "simple" task is cheap enough for the orchestrator
    38	# to do inline (Q3) rather than paying ~10k agent-overhead to dispatch it.
    39	_DIRECT_TOKEN_CEILING: int = 400
    40	
    41	
    42	@dataclass(frozen=True)
    43	class SubagentVerdict:
    44	    """The per-task justification verdict.
    45	
    46	    ``needs_subagent`` — the gate's recommendation (False = answerable without a
    47	    subagent). ``challenge`` — a non-None one-liner when the spawn is
    48	    questionable (deterministic-eligible, orchestrator-doable, or an unjustified
    49	    general-purpose role); None means the spawn is clean.
    50	    """
    51	
    52	    needs_subagent: bool
    53	    deterministic_eligible: bool
    54	    role: str
    55	    tier: str
    56	    reason: str
    57	    challenge: str | None = None
    58	
    59	
    60	@dataclass(frozen=True)
    61	class PlanChallenge:
    62	    """Plan-level rollup used by the cost preview to challenge a plan."""
    63	
    64	    total: int = 0
    65	    subagent_tasks: int = 0
    66	    deterministic_eligible: int = 0
    67	    unjustified: int = 0
    68	    general_purpose: int = 0
    69	    flagged_indices: tuple[int, ...] = field(default_factory=tuple)
    70	    challenged: bool = False
    71	    message: str = ""
    72	
    73	
    74	def justify_task(task: Any) -> SubagentVerdict:
    75	    """Return the justification :class:`SubagentVerdict` for one planned task.
    76	
    77	    Pure, zero-LLM, never raises. Accepts a dict or any object exposing
    78	    ``executor`` / ``complexity`` / ``est_tokens`` / ``role`` / ``role_reason``.
    79	    """
    80	    try:
    81	        # Q1 + Q2 — a deterministic path exists → no subagent needed.
    82	        if cost.is_deterministic_item(task):
    83	            return SubagentVerdict(
    84	                needs_subagent=False,
    85	                deterministic_eligible=True,
    86	                role="deterministic",
    87	                tier="none",
    88	                reason="deterministic path (git/grep/parser/state or deterministic executor)",
    89	                challenge="deterministic-eligible — resolve via a check/script, not a subagent",
    90	            )
    91	
    92	        role = subagent_profiles.resolve_profile(task)
    93	        tier = subagent_profiles.profile_tier(role)
    94	        complexity = str(cost._get(task, "complexity", "") or "").strip().lower()
    95	        raw_tokens = cost._get(task, "est_tokens", 0)
    96	        est_tokens = raw_tokens if isinstance(raw_tokens, int) and not isinstance(raw_tokens, bool) else 0
    97	
    98	        # Q3 — a trivial/simple, tiny task the orchestrator can do inline.
    99	        if complexity in ("", "simple") and 0 < est_tokens <= _DIRECT_TOKEN_CEILING:
   100	            return SubagentVerdict(
   101	                needs_subagent=False,
   102	                deterministic_eligible=False,
   103	                role=role,
   104	                tier=tier,
   105	                reason=f"simple + ~{est_tokens} tok — orchestrator can do this inline",
   106	                challenge="small/simple — do it inline or route to haiku, not a scoped subagent",
   107	            )
   108	
   109	        # Q4 — large/ambiguous enough → a subagent is justified.
   110	        justified = complexity in _SUBAGENT_JUSTIFYING_COMPLEXITY or est_tokens > _DIRECT_TOKEN_CEILING
   111	
   112	        challenge: str | None = None
   113	        if role == "general-purpose":
   114	            reason_field = str(cost._get(task, "role_reason", "") or "").strip()
   115	            if not reason_field:
   116	                challenge = (
   117	                    "general-purpose without a scoped role — assign a specialized "
   118	                    "profile (docs-editor/code-implementer/test-writer/reviewer/…) "
   119	                    "or state role_reason"
   120	                )
   121	        elif not justified:
   122	            challenge = "no hard/medium/large signal — confirm a subagent is warranted"
   123	
   124	        return SubagentVerdict(
   125	            needs_subagent=justified or role != "general-purpose",
   126	            deterministic_eligible=False,
   127	            role=role,
   128	            tier=tier,
   129	            reason=(
   130	                f"{complexity or 'unspecified'} complexity, ~{est_tokens} tok, role={role}"
   131	            ),
   132	            challenge=challenge,
   133	        )
   134	    except Exception:
   135	        # Conservative fallback: assume a subagent is needed (never suppress work
   136	        # by accident), but flag it so the human still sees the uncertainty.
   137	        return SubagentVerdict(
   138	            needs_subagent=True,
   139	            deterministic_eligible=False,
   140	            role="general-purpose",
   141	            tier="sonnet",
   142	            reason="gate could not classify this task",
   143	            challenge="gate could not classify — review before dispatch",
   144	        )
   145	
   146	
   147	def challenge_plan(tasks: Any, *, unjustified_share_threshold: float = 0.5) -> PlanChallenge:
   148	    """Roll :func:`justify_task` up across a plan and decide whether to challenge it.
   149	
   150	    ``challenged`` is True when at least ``unjustified_share_threshold`` of the
   151	    would-be-subagent tasks are unjustified (deterministic-eligible, inline-able,
   152	    or unexplained general-purpose), OR when any general-purpose spawn lacks a
   153	    reason. Pure, never raises — an unusable ``tasks`` yields an empty, unchallenged
   154	    rollup.
   155	    """
   156	    try:
   157	        items = list(tasks)
   158	    except Exception:
   159	        return PlanChallenge()
   160	
   161	    total = 0
   162	    subagent_tasks = 0            # non-deterministic tasks that would spawn a subagent
   163	    deterministic_eligible = 0    # tasks a check/script should replace (NOT spawns)
   164	    unjustified = 0              # spawns that are challenged (inline-able / gp-no-reason / no-signal)
   165	    general_purpose = 0
   166	    gp_without_reason = False
   167	    flagged: list[int] = []
   168	
   169	    for idx, task in enumerate(items):
   170	        total += 1
   171	        v = justify_task(task)
   172	        if v.deterministic_eligible:
   173	            # A deterministic path exists — this is a "make it a check" win, not a
   174	            # subagent spawn. Bucket it separately and flag it for the human.
   175	            deterministic_eligible += 1
   176	            flagged.append(idx)
   177	            continue
   178	        # Every non-deterministic task is an INTENDED model spawn in the plan.
   179	        subagent_tasks += 1
   180	        if v.role == "general-purpose":
   181	            general_purpose += 1
   182	            if v.challenge is not None:
   183	                gp_without_reason = True
   184	        if v.challenge is not None:
   185	            unjustified += 1
   186	            flagged.append(idx)
   187	
   188	    share = (unjustified / subagent_tasks) if subagent_tasks else 0.0
   189	    challenged = (
   190	        (subagent_tasks > 0 and share >= unjustified_share_threshold)
   191	        or gp_without_reason
   192	        or deterministic_eligible > 0
   193	    )
   194	
   195	    message = (
   196	        f"{unjustified} of {subagent_tasks} subagent(s) unjustified; "
   197	        f"{deterministic_eligible} deterministic-eligible; "
   198	        f"{general_purpose} general-purpose"
   199	        if challenged
   200	        else f"subagent plan OK ({subagent_tasks} justified, "
   201	        f"{deterministic_eligible} deterministic)"
   202	    )
   203	
   204	    return PlanChallenge(
   205	        total=total,
   206	        subagent_tasks=subagent_tasks,
   207	        deterministic_eligible=deterministic_eligible,
   208	        unjustified=unjustified,
   209	        general_purpose=general_purpose,
   210	        flagged_indices=tuple(flagged),
   211	        challenged=challenged,
   212	        message=message,
   213	    )
   214	
   215	
   216	def preview_line(challenge: PlanChallenge) -> str:
   217	    """One bounded line for the cost preview (deterministic-first labelling)."""
   218	    tag = "⚠ CHALLENGE" if challenge.challenged else "✓ subagent gate"
   219	    return f"{tag}: {challenge.message}"
   220	
   221	
   222	def main(argv: list[str] | None = None) -> int:
   223	    """CLI: ``python -m renmark.subagent_gate <plan.md>``.
   224	
   225	    Deterministic pre-flight gate — mirrors ``python -m renmark.plan_lint``. Prints
   226	    the one-line challenge verdict and exits 0 when the subagent plan is clean, 1
   227	    when it is challenged (a deterministic path exists, an unjustified spawn, or an
   228	    unexplained general-purpose role). Exit 2 on a usage/parse error. Zero-LLM.
   229	    """
   230	    import sys
   231	
   232	    from renmark import parser
   233	
   234	    args = argv if argv is not None else sys.argv[1:]
   235	    if not args:
   236	        sys.stderr.write("usage: python -m renmark.subagent_gate <plan.md>\n")
   237	        return 2
   238	    try:
   239	        tasks = parser.parse_plan(args[0])
   240	    except Exception as exc:
   241	        sys.stderr.write(f"subagent-gate: cannot read plan: {exc}\n")
   242	        return 2
   243	    ch = challenge_plan(tasks)
   244	    sys.stdout.write(preview_line(ch) + "\n")
   245	    return 1 if ch.challenged else 0
   246	
   247	
   248	if __name__ == "__main__":
   249	    raise SystemExit(main())

[35m[3mexec[0m[0m
[1m/bin/bash -lc "nl -ba renmark/cli/_engine.py | sed -n '458,520p'"[0m in /home/renmark/projects/ai-system/.claude/worktrees/subagent-gate
[32m succeeded in 0ms:[0m
   458	        f"renmark  plan: {plan_path}  run: {run_id}\n"
   459	        f"model_default: {cfg.prefer_small_model}   "
   460	        f"budget: {cfg.max_tokens_per_run} tok / {cfg.max_minutes_per_run} min"
   461	    )
   462	
   463	    if dry_run:
   464	        from .. import capabilities as _caps
   465	        from .. import dispatch as _d
   466	
   467	        waves = _d.group_tasks_by_wave(tasks)
   468	        _print(f"\n[DRY RUN] {len(tasks)} tasks in {len(waves)} wave(s):\n")
   469	        # Cost estimates per executor — approximate $/kT (output tokens).
   470	        cost_per_kt = {"haiku": 0.0001, "codex": 0.05, "sonnet": 0.003, "opus": 0.015, "fable": 0.030}
   471	        total_tokens = 0
   472	        total_cost = 0.0
   473	        for w_idx, w in enumerate(waves, 1):
   474	            wave_tag = "(parallel)" if len(w) > 1 else ""
   475	            _print(f"  Wave {w_idx}: {len(w)} task(s) {wave_tag}")
   476	            for t in w:
   477	                mark = "DONE" if t.index in done else "TODO"
   478	                tok = t.est_tokens or _default_tokens_for_complexity(t.complexity)
   479	                # Resolve declared-tier fallback (fable→opus when undeclared) so
   480	                # the preview prices and labels what will actually run.
   481	                ex = _caps.effective_executor(t.executor, repo)
   482	                ex_display = f"{t.executor}→{ex}" if ex != t.executor else ex
   483	                # A downgraded executor (e.g. fable→opus) invalidates any prefilled
   484	                # est_cost_usd — it was estimated at the wrong tier. Reprice from
   485	                # the effective executor's rate so display matches what's charged.
   486	                cost = t.est_cost_usd if ex == t.executor else None
   487	                if cost is None:
   488	                    # Infer from executor.
   489	                    rate = cost_per_kt.get(ex, 0.0)
   490	                    if "/" in ex:  # provider/model — assume openai-compatible mid-tier
   491	                        rate = cost_per_kt.get("sonnet", 0.003)
   492	                    cost = (tok / 1000.0) * rate
   493	                cost_str = f"${cost:.3f}" if cost > 0 else "free"
   494	                _print(
   495	                    f"    [{mark}] task {t.index} {ex_display:<8} {t.complexity:<6} "
   496	                    f"~{tok:>5} tok  {cost_str:>8}  → {t.target}  ({t.title})"
   497	                )
   498	                total_tokens += tok
   499	                total_cost += cost
   500	        _print(f"\n  TOTAL estimate: ~{total_tokens:,} tokens · ~${total_cost:.3f}")
   501	        _print(
   502	            "  (codex metered separately; haiku/sonnet/opus/fable bill to your Claude Code quota, ~10k overhead/task)"
   503	        )
   504	        return 0
   505	
   506	    # Start anchor tag.
   507	    _git_tag(repo, f"renmark-run-{run_id}-start")
   508	    clear_pause(repo)
   509	
   510	    deadline = time.monotonic() + (cfg.max_minutes_per_run * 60)
   511	    tokens_used = 0
   512	    passed: list[int] = []
   513	    failed_task: Task | None = None
   514	    failure_kind: str | None = None
   515	    skipped: list[int] = []
   516	
   517	    # Group tasks into waves for parallel execution. Tasks sharing a
   518	    # `parallel_group` run concurrently; defaults to one wave per task.
   519	    from .. import dispatch as _dispatch
   520	

[35m[3mexec[0m[0m
[1m/bin/bash -lc "python - <<'PY'
from renmark.subagent_gate import justify_task, challenge_plan
print(justify_task({'executor':'haiku','complexity':'simple','est_tokens':None,'target':'a.md'}))
print(justify_task({'executor':'haiku','complexity':'SIMPLE','est_tokens':True,'target':'a.md'}))
print(challenge_plan([{'executor':'haiku','complexity':'simple','est_tokens':None,'target':'a.md'}]))
PY"[0m in /home/renmark/projects/ai-system/.claude/worktrees/subagent-gate
[32m succeeded in 0ms:[0m
SubagentVerdict(needs_subagent=True, deterministic_eligible=False, role='docs-editor', tier='haiku', reason='simple complexity, ~0 tok, role=docs-editor', challenge='no hard/medium/large signal — confirm a subagent is warranted')
SubagentVerdict(needs_subagent=True, deterministic_eligible=False, role='docs-editor', tier='haiku', reason='simple complexity, ~0 tok, role=docs-editor', challenge='no hard/medium/large signal — confirm a subagent is warranted')
PlanChallenge(total=1, subagent_tasks=1, deterministic_eligible=0, unjustified=1, general_purpose=0, flagged_indices=(0,), challenged=True, message='1 of 1 subagent(s) unjustified; 0 deterministic-eligible; 0 general-purpose')

[35m[3mexec[0m[0m
[1m/bin/bash -lc 'PYTHONDONTWRITEBYTECODE=1 pytest -q tests/test_subagent_gate.py -o cache_dir=/tmp/pytest-subagent-gate'[0m in /home/renmark/projects/ai-system/.claude/worktrees/subagent-gate
[31m exited 1 in 248ms:[0m
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
FileNotFoundError: [Errno 2] No usable temporary directory found in ['/tmp', '/var/tmp', '/usr/tmp', '/home/renmark/projects/ai-system/.claude/worktrees/subagent-gate']

[35m[3mexec[0m[0m
[1m/bin/bash -lc "nl -ba renmark/cost.py | sed -n '240,320p'"[0m in /home/renmark/projects/ai-system/.claude/worktrees/subagent-gate
[32m succeeded in 0ms:[0m
   240	
   241	def requires_escalation(*, complexity: str | None = None, kind: str | None = None) -> bool:
   242	    """Return True iff this task warrants escalation to opus or fable.
   243	
   244	    Escalation is justified when:
   245	
   246	    - ``complexity == "hard"`` — the task is explicitly labelled hard, OR
   247	    - ``kind`` is one of ``{"architecture", "adversarial-review", "design-fork"}``
   248	      — structural task kinds where frontier reasoning pays off.
   249	
   250	    All other inputs (including None, garbage, or unrecognised values) return
   251	    False.  **Never raises.**
   252	    """
   253	    try:
   254	        if isinstance(complexity, str) and complexity.strip().lower() == "hard":
   255	            return True
   256	        return isinstance(kind, str) and kind.strip().lower() in _ESCALATION_KINDS
   257	    except Exception:
   258	        return False
   259	
   260	
   261	# ── Internal helpers ─────────────────────────────────────────────────────────
   262	
   263	
   264	def is_deterministic_item(item: object) -> bool:
   265	    """Return True iff ``item`` represents a deterministic (non-model) execution step.
   266	
   267	    Classification priority:
   268	
   269	    1. Explicit ``mode`` field: ``'deterministic'`` → True, ``'model-driven'`` → False.
   270	    2. ``executor`` field in :data:`_DETERMINISTIC_EXECUTORS` → True.
   271	    3. All other executors (model names: haiku/sonnet/opus/fable/codex) → False.
   272	
   273	    Degrades safely: unknown or missing fields default to ``False`` (model-driven),
   274	    the conservative/expensive assumption.  Never raises.
   275	    """
   276	    try:
   277	        raw_mode = _get(item, "mode", None)
   278	        if isinstance(raw_mode, str) and raw_mode.strip():
   279	            mode = raw_mode.strip().lower()
   280	            if mode == "deterministic":
   281	                return True
   282	            if mode == "model-driven":
   283	                return False
   284	
   285	        raw_exec = _get(item, "executor", None)
   286	        if isinstance(raw_exec, str) and raw_exec.strip():
   287	            return raw_exec.strip().lower() in _DETERMINISTIC_EXECUTORS
   288	
   289	        return False
   290	    except Exception:
   291	        return False
   292	
   293	
   294	def _get(item: object, key: str, default: object) -> object:
   295	    """Read ``key`` from ``item`` whether it is a dict or an object attribute.
   296	
   297	    Dict items use ``item[key]``; object items use ``getattr(item, key, default)``.
   298	    Missing keys return ``default``.  Never raises.
   299	    """
   300	    try:
   301	        if isinstance(item, dict):
   302	            return item.get(key, default)
   303	        return getattr(item, key, default)
   304	    except Exception:
   305	        return default

[35m[3mexec[0m[0m
[1m/bin/bash -lc "nl -ba renmark/subagent_profiles.py | sed -n '160,230p'"[0m in /home/renmark/projects/ai-system/.claude/worktrees/subagent-gate
[32m succeeded in 0ms:[0m
   160	
   161	# ── Public API ────────────────────────────────────────────────────────────────
   162	
   163	
   164	def resolve_profile(task: Any) -> str:
   165	    """Infer the best-fit role name from a Task (or any task-shaped object/dict).
   166	
   167	    Accepts objects with attributes *or* plain dicts. Heuristic priority order:
   168	
   169	    1. ``tests/`` path prefix OR ``test_*`` / ``*_test.*`` filename → ``"test-writer"``
   170	    2. ``.md`` suffix OR path under ``plugin/skills/`` / ``docs/`` → ``"docs-editor"``
   171	    3. title / task kind mentioning ``review`` → ``"reviewer"``
   172	    4. title / task kind mentioning ``audit`` or ``audit-read`` → ``"audit-reader"``
   173	    5. target under ``renmark/`` or ``bin/`` (core code) → ``"code-implementer"``
   174	    6. fallback → ``"general-purpose"``
   175	
   176	    Never raises: any exception returns ``"general-purpose"``.
   177	    """
   178	    try:
   179	        target = _get_field(task, "target", "")
   180	        title = _get_field(task, "title", "") or _get_field(task, "spec", "")
   181	        kind = _get_field(task, "kind", "")
   182	
   183	        target = (target or "").strip()
   184	        title = (title or "").strip().lower()
   185	        kind = (kind or "").strip().lower()
   186	
   187	        # ── 1. Test files ─────────────────────────────────────────────────────
   188	        if _is_test_target(target):
   189	            return "test-writer"
   190	
   191	        # ── 2. Docs / markdown / skill files ─────────────────────────────────
   192	        if _is_doc_target(target):
   193	            return "docs-editor"
   194	
   195	        # ── 3. Review ─────────────────────────────────────────────────────────
   196	        if "review" in title or "review" in kind:
   197	            return "reviewer"
   198	
   199	        # ── 4. Audit ─────────────────────────────────────────────────────────
   200	        if "audit" in title or "audit" in kind:
   201	            return "audit-reader"
   202	
   203	        # ── 5. Core code ──────────────────────────────────────────────────────
   204	        if _is_core_code_target(target):
   205	            return "code-implementer"
   206	
   207	        # ── 6. Fallback ───────────────────────────────────────────────────────
   208	        return "general-purpose"
   209	    except Exception:
   210	        return "general-purpose"
   211	
   212	
   213	def profile_tier(role: str) -> str:
   214	    """Return the ``model_tier`` for *role*, or ``"sonnet"`` if unknown.
   215	
   216	    Never raises.
   217	    """
   218	    try:
   219	        spec = PROFILES.get(role)
   220	        return spec.model_tier if spec is not None else "sonnet"
   221	    except Exception:
   222	        return "sonnet"
   223	
   224	
   225	def profile_of(role: str) -> ProfileSpec | None:
   226	    """Safe lookup — returns ``None`` when *role* is not in ``PROFILES``."""
   227	    try:
   228	        return PROFILES.get(role)
   229	    except Exception:
   230	        return None

[35m[3mexec[0m[0m
[1m/bin/bash -lc "python - <<'PY'
from renmark.subagent_gate import justify_task
for tokens in (-5, 0, 1, 400, 401):
    v = justify_task({'executor':'haiku','complexity':'simple','est_tokens':tokens,'target':'a.md'})
    print(tokens, v.needs_subagent, v.challenge)
PY"[0m in /home/renmark/projects/ai-system/.claude/worktrees/subagent-gate
[32m succeeded in 0ms:[0m
-5 True no hard/medium/large signal — confirm a subagent is warranted
0 True no hard/medium/large signal — confirm a subagent is warranted
1 False small/simple — do it inline or route to haiku, not a scoped subagent
400 False small/simple — do it inline or route to haiku, not a scoped subagent
401 True None

[35m[3mcodex[0m[0m
There’s another structural mismatch: the plan parser doesn’t accept `role` or `role_reason`, so the one escape hatch for `general-purpose` tasks can’t actually be expressed in real plan files. I’m confirming that with the parser and linting surface now.
[35m[3mexec[0m[0m
[1m/bin/bash -lc "nl -ba renmark/parser.py | sed -n '20,90p'"[0m in /home/renmark/projects/ai-system/.claude/worktrees/subagent-gate
[32m succeeded in 0ms:[0m
    20	from pathlib import Path
    21	from typing import Any
    22	
    23	
    24	class PlanError(ValueError):
    25	    """Raised when a plan file is malformed."""
    26	
    27	
    28	@dataclass
    29	class Task:
    30	    index: int  # 1-based as written in the plan
    31	    title: str
    32	    mode: str  # "A" or "B"
    33	    target: str
    34	    context_files: list[str] = field(default_factory=list)
    35	    model: str | None = None
    36	    verifier: str = ""
    37	    verifier_timeout_s: int = 60
    38	    spec: str = ""
    39	    executor: str = "codex"  # "haiku" | "codex" | "sonnet" | "opus" | <litellm-string>
    40	    # Phase 1 fields (v0.0.3+):
    41	    complexity: str = "medium"  # "simple" | "medium" | "hard"
    42	    parallel_group: int | None = (
    43	        None  # tasks sharing a group run concurrently; default None = serial (each in its own group = index)
    44	    )
    45	    est_tokens: int | None = None  # planner estimate (informational)
    46	    est_cost_usd: float | None = None  # planner estimate (informational)
    47	    serves: str | None = None  # optional PRD traceability note, e.g. "REQ-3" or "new"
    48	
    49	
    50	_HEADER_RE = re.compile(r"^###\s+Task\s+(\d+)\s*:\s*(.+?)\s*$")
    51	# Loose pattern: a "### Task <digits>" heading that does NOT match the strict
    52	# _HEADER_RE is a malformed numbered header and must raise. The digit is
    53	# required so prose headings ("### Task overview", "### Task description")
    54	# stay legal preamble; a word-numbered typo ("### Task Four:") is therefore
    55	# absorbed silently — the contiguous-index check still catches the gap.
    56	_LOOSE_TASK_RE = re.compile(r"^###\s*Task\s*\d", re.IGNORECASE)
    57	_FIELD_RE = re.compile(r"^-\s+\*\*([a-z_]+):\*\*\s*(.*?)\s*$")
    58	_LIST_RE = re.compile(r"^\[(.*)\]$")
    59	
    60	
    61	def parse_plan(path: str | Path) -> list[Task]:
    62	    """Parse a plan file and return validated tasks.
    63	
    64	    Raises PlanError on any structural problem.
    65	    """
    66	    p = Path(path)
    67	    if not p.is_file():
    68	        raise PlanError(f"plan file not found: {path}")
    69	    lines = p.read_text(encoding="utf-8").splitlines()
    70	
    71	    tasks: list[Task] = []
    72	    current: dict[str, Any] | None = None
    73	    spec_lines: list[str] | None = None
    74	    reading_spec = False
    75	    line_no = 0
    76	
    77	    def _close_current(end_line: int) -> None:
    78	        nonlocal current, spec_lines, reading_spec
    79	        if current is None:
    80	            return
    81	        if spec_lines is not None:
    82	            current["spec"] = "\n".join(spec_lines).strip()
    83	        try:
    84	            tasks.append(_build_task(current))
    85	        except PlanError as e:
    86	            raise PlanError(f"task {current.get('index', '?')} (ending at line {end_line}): {e}") from None
    87	        current = None
    88	        spec_lines = None
    89	        reading_spec = False
    90	

[35m[3mexec[0m[0m
[1m/bin/bash -lc "nl -ba renmark/parser.py | sed -n '140,180p'"[0m in /home/renmark/projects/ai-system/.claude/worktrees/subagent-gate
[32m succeeded in 0ms:[0m
   140	        elif key == "context_files":
   141	            current["context_files"] = _parse_list(value)
   142	        elif key == "verifier_timeout_s":
   143	            try:
   144	                current["verifier_timeout_s"] = int(value)
   145	            except ValueError as e:
   146	                raise PlanError(f"line {line_no}: verifier_timeout_s must be int, got {value!r}") from e
   147	        elif key == "parallel_group":
   148	            try:
   149	                current["parallel_group"] = int(value)
   150	            except ValueError as e:
   151	                raise PlanError(f"line {line_no}: parallel_group must be int, got {value!r}") from e
   152	        elif key == "est_tokens":
   153	            try:
   154	                current["est_tokens"] = int(value)
   155	            except ValueError as e:
   156	                raise PlanError(f"line {line_no}: est_tokens must be int, got {value!r}") from e
   157	        elif key == "est_cost_usd":
   158	            try:
   159	                current["est_cost_usd"] = float(value)
   160	            except ValueError as e:
   161	                raise PlanError(f"line {line_no}: est_cost_usd must be float, got {value!r}") from e
   162	        elif key in ("mode", "target", "model", "verifier", "executor", "complexity", "serves"):
   163	            current[key] = value
   164	        else:
   165	            raise PlanError(f"line {line_no}: unknown field {key!r}")
   166	
   167	    _close_current(line_no)
   168	
   169	    if not tasks:
   170	        raise PlanError("plan has no tasks (no '### Task N:' headers found)")
   171	
   172	    _validate_indices(tasks)
   173	    return tasks
   174	
   175	
   176	def _parse_list(raw: str) -> list[str]:
   177	    raw = raw.strip()
   178	    if raw in ("", "[]"):
   179	        return []
   180	    m = _LIST_RE.match(raw)

[35m[3mexec[0m[0m
[1m/bin/bash -lc "nl -ba renmark/parser.py | sed -n '220,250p'"[0m in /home/renmark/projects/ai-system/.claude/worktrees/subagent-gate
[32m succeeded in 0ms:[0m
   220	    # Allow haiku, codex, sonnet, opus, or any provider-string of form "<provider>/<model>".
   221	    # nim was removed in v0.2.0 — use haiku for simple tasks instead.
   222	    if executor not in ("haiku", "codex", "sonnet", "opus", "fable") and "/" not in executor:
   223	        raise PlanError(
   224	            f"executor must be one of haiku, codex, sonnet, opus, fable, or a provider/model string, got {executor!r}"
   225	        )
   226	
   227	    complexity = (d.get("complexity") or "medium").strip().lower()
   228	    if complexity not in ("simple", "medium", "hard"):
   229	        raise PlanError(f"complexity must be simple, medium, or hard, got {complexity!r}")
   230	
   231	    return Task(
   232	        index=d["index"],
   233	        title=d["title"].strip(),
   234	        mode=mode,
   235	        target=target,
   236	        context_files=d["context_files"],
   237	        model=(d["model"].strip() if d.get("model") else None),
   238	        verifier=verifier,
   239	        verifier_timeout_s=d["verifier_timeout_s"],
   240	        spec=spec,
   241	        complexity=complexity,
   242	        parallel_group=d.get("parallel_group"),
   243	        est_tokens=d.get("est_tokens"),
   244	        est_cost_usd=d.get("est_cost_usd"),
   245	        executor=executor,
   246	        serves=(d["serves"].strip() if d.get("serves") else None),
   247	    )
   248	
   249	
   250	def _validate_indices(tasks: list[Task]) -> None:

[35m[3mexec[0m[0m
[1m/bin/bash -lc "python - <<'PY'
from pathlib import Path
from renmark.parser import parse_plan, PlanError
p = Path('/dev/shm')
print('dev_shm_exists', p.exists(), p.is_dir())
PY"[0m in /home/renmark/projects/ai-system/.claude/worktrees/subagent-gate
[32m succeeded in 0ms:[0m
dev_shm_exists True True

[35m[3mexec[0m[0m
[1m/bin/bash -lc "python - <<'PY'
from pathlib import Path
p = Path('/dev/shm/subagent_gate_test.plan.md')
p.write_text(\"\"\"### Task 1: doc tweak\\n- **mode:** A\\n- **target:** docs/readme.md\\n- **executor:** haiku\\n- **complexity:** simple\\n- **est_tokens:** 200\\n- **verifier:** python -m py_compile renmark/parser.py\\n- **spec:**\\n  update docs\\n\"\"\", encoding='utf-8')
print(p)
PY"[0m in /home/renmark/projects/ai-system/.claude/worktrees/subagent-gate
[32m succeeded in 0ms:[0m
/dev/shm/subagent_gate_test.plan.md

[35m[3mexec[0m[0m
[1m/bin/bash -lc 'python -m renmark.subagent_gate /dev/shm/subagent_gate_test.plan.md; echo EXIT:$?'[0m in /home/renmark/projects/ai-system/.claude/worktrees/subagent-gate
[32m succeeded in 0ms:[0m
subagent-gate: cannot read plan: plan file not found: /dev/shm/subagent_gate_test.plan.md
EXIT:2

[35m[3mexec[0m[0m
[1m/bin/bash -lc 'python -m renmark.subagent_gate; echo EXIT:$?'[0m in /home/renmark/projects/ai-system/.claude/worktrees/subagent-gate
[32m succeeded in 0ms:[0m
usage: python -m renmark.subagent_gate <plan.md>
EXIT:2

[35m[3mcodex[0m[0m
The sandbox won’t preserve temp files across separate commands, but I did confirm the CLI’s no-arg usage path returns exit `2`. I’m doing one in-process probe for a real plan parse + `main()` return so I can verify the clean/challenged exit behavior directly.
[35m[3mexec[0m[0m
[1m/bin/bash -lc "python - <<'PY'
from pathlib import Path
from renmark.subagent_gate import main
p = Path('/dev/shm/subagent_gate_test.plan.md')
p.write_text(\"\"\"### Task 1: doc tweak\\n- **mode:** A\\n- **target:** docs/readme.md\\n- **executor:** haiku\\n- **complexity:** simple\\n- **est_tokens:** 200\\n- **verifier:** python -m py_compile renmark/parser.py\\n- **spec:**\\n  update docs\\n\"\"\", encoding='utf-8')
print('exit', main([str(p)]))
PY"[0m in /home/renmark/projects/ai-system/.claude/worktrees/subagent-gate
[32m succeeded in 0ms:[0m
⚠ CHALLENGE: 1 of 1 subagent(s) unjustified; 0 deterministic-eligible; 0 general-purpose
exit 1

[35m[3mexec[0m[0m
[1m/bin/bash -lc "python - <<'PY'
from pathlib import Path
from renmark.subagent_gate import main
p = Path('/dev/shm/subagent_gate_test2.plan.md')
p.write_text(\"\"\"### Task 1: core code\\n- **mode:** A\\n- **target:** renmark/parser.py\\n- **executor:** sonnet\\n- **complexity:** hard\\n- **est_tokens:** 2000\\n- **verifier:** python -m py_compile renmark/parser.py\\n- **spec:**\\n  inspect and improve parser logic\\n\"\"\", encoding='utf-8')
print('exit', main([str(p)]))
PY"[0m in /home/renmark/projects/ai-system/.claude/worktrees/subagent-gate
[32m succeeded in 0ms:[0m
✓ subagent gate: subagent plan OK (1 justified, 0 deterministic)
exit 0

[35m[3mcodex[0m[0m
━━ VERDICT 1 — Spec-compliance ━━  
Spec: under-built — the gate module/CLI landed, but end-to-end enforcement is not actually wired into the runtime preflight or dry-run cost preview, and real plans cannot carry `role_reason`; over-built — none

━━ VERDICT 2 — Code-quality ━━  
Counts: Critical 0 | Major 4 | Minor 0 | Nit 0

1. [renmark/cli/_engine.py:463](/home/renmark/projects/ai-system/.claude/worktrees/subagent-gate/renmark/cli/_engine.py:463) | Major | The claimed “wiring” is docs-only. The only implemented cost-preview/preflight surface still hand-rolls preview output and never calls `renmark.subagent_gate.challenge_plan()` or `preview_line()`, so the new gate is callable but not enforced before dispatch in code. | Fix: add a shared preflight helper that runs `plan_lint` + `subagent_gate` and make both orchestrate and `--dry-run` consume it; print the gate line from that helper instead of duplicating preview logic.

2. [renmark/parser.py:28](/home/renmark/projects/ai-system/.claude/worktrees/subagent-gate/renmark/parser.py:28) | Major | `general-purpose` can supposedly be justified by `role_reason`, but real plan files cannot express that. `Task` has no `role`/`role_reason`, and the parser rejects unknown fields, so “general-purpose with reason clears it” only works in dict-based unit tests, not on parsed plans. | Fix: extend `Task` and `parse_plan()` to accept `role` and `role_reason`, then add parser + CLI integration tests for a real plan file.

3. [renmark/subagent_gate.py:180](/home/renmark/projects/ai-system/.claude/worktrees/subagent-gate/renmark/subagent_gate.py:180) | Major | `challenge_plan()` mislabels any challenged `general-purpose` task as “general-purpose without reason”. `gp_without_reason` is set whenever `v.role == "general-purpose"` and `v.challenge is not None`, but `v.challenge` can also mean “inline-able” or “no hard/medium/large signal”. That makes the plan-level gate stricter than its own contract and forces `challenged=True` for the wrong reason. | Fix: carry a structured challenge code from `justify_task()` (for example `missing_role_reason`, `inlineable`, `no_signal`) and set `gp_without_reason` only for the explicit missing-reason case.

4. [renmark/subagent_gate.py:95](/home/renmark/projects/ai-system/.claude/worktrees/subagent-gate/renmark/subagent_gate.py:95) | Major | The inlineability heuristic produces broad false positives whenever `est_tokens` is missing, zero, negative, or bool-like. Since `parser.Task.est_tokens` is optional, a simple docs/code task with no estimate falls through the inline check and returns `needs_subagent=True` plus a challenge. Manual probe: `{'executor':'haiku','complexity':'simple','est_tokens':None,'target':'a.md'}` is treated as an unjustified subagent spawn. | Fix: distinguish “unknown estimate” from `0`; either use the existing complexity-based default token estimate, or treat `complexity == "simple"` with missing estimate as inline-able unless another strong signal justifies a subagent.

Residual notes:
- `justify_task()`/`challenge_plan()` themselves do degrade safely and I did not find a direct throw path in normal use.
- I could not run `pytest` in this sandbox because there is no usable temp directory, so verification here is from static review plus direct Python probes of `justify_task()`, `challenge_plan()`, and `main()`.
[2mtokens used[0m
77,097
━━ VERDICT 1 — Spec-compliance ━━  
Spec: under-built — the gate module/CLI landed, but end-to-end enforcement is not actually wired into the runtime preflight or dry-run cost preview, and real plans cannot carry `role_reason`; over-built — none

━━ VERDICT 2 — Code-quality ━━  
Counts: Critical 0 | Major 4 | Minor 0 | Nit 0

1. [renmark/cli/_engine.py:463](/home/renmark/projects/ai-system/.claude/worktrees/subagent-gate/renmark/cli/_engine.py:463) | Major | The claimed “wiring” is docs-only. The only implemented cost-preview/preflight surface still hand-rolls preview output and never calls `renmark.subagent_gate.challenge_plan()` or `preview_line()`, so the new gate is callable but not enforced before dispatch in code. | Fix: add a shared preflight helper that runs `plan_lint` + `subagent_gate` and make both orchestrate and `--dry-run` consume it; print the gate line from that helper instead of duplicating preview logic.

2. [renmark/parser.py:28](/home/renmark/projects/ai-system/.claude/worktrees/subagent-gate/renmark/parser.py:28) | Major | `general-purpose` can supposedly be justified by `role_reason`, but real plan files cannot express that. `Task` has no `role`/`role_reason`, and the parser rejects unknown fields, so “general-purpose with reason clears it” only works in dict-based unit tests, not on parsed plans. | Fix: extend `Task` and `parse_plan()` to accept `role` and `role_reason`, then add parser + CLI integration tests for a real plan file.

3. [renmark/subagent_gate.py:180](/home/renmark/projects/ai-system/.claude/worktrees/subagent-gate/renmark/subagent_gate.py:180) | Major | `challenge_plan()` mislabels any challenged `general-purpose` task as “general-purpose without reason”. `gp_without_reason` is set whenever `v.role == "general-purpose"` and `v.challenge is not None`, but `v.challenge` can also mean “inline-able” or “no hard/medium/large signal”. That makes the plan-level gate stricter than its own contract and forces `challenged=True` for the wrong reason. | Fix: carry a structured challenge code from `justify_task()` (for example `missing_role_reason`, `inlineable`, `no_signal`) and set `gp_without_reason` only for the explicit missing-reason case.

4. [renmark/subagent_gate.py:95](/home/renmark/projects/ai-system/.claude/worktrees/subagent-gate/renmark/subagent_gate.py:95) | Major | The inlineability heuristic produces broad false positives whenever `est_tokens` is missing, zero, negative, or bool-like. Since `parser.Task.est_tokens` is optional, a simple docs/code task with no estimate falls through the inline check and returns `needs_subagent=True` plus a challenge. Manual probe: `{'executor':'haiku','complexity':'simple','est_tokens':None,'target':'a.md'}` is treated as an unjustified subagent spawn. | Fix: distinguish “unknown estimate” from `0`; either use the existing complexity-based default token estimate, or treat `complexity == "simple"` with missing estimate as inline-able unless another strong signal justifies a subagent.

Residual notes:
- `justify_task()`/`challenge_plan()` themselves do degrade safely and I did not find a direct throw path in normal use.
- I could not run `pytest` in this sandbox because there is no usable temp directory, so verification here is from static review plus direct Python probes of `justify_task()`, `challenge_plan()`, and `main()`.
