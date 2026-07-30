# Changelog

## [2026-07-29] - plan: compile M2 two-mode routing and interaction

**Request:** After accepting M1, plan M2 only: the Agency/Orchestrator public contract, canonical entry routing, host-adaptive decisions, and cross-host behavior proof.
**Built:** Reused the approved M2 master milestone and split its current-format implementation at the 15-task ceiling into a 13-task runtime/interaction plan followed by a 9-task entry-skill/behavior plan; encoded build and review loop bounds, compatibility guards, execution order, and an honest combined preview of 101,700 tokens including Agent overhead at USD 1.0955, with no Opus/Fable and no dispatch.
**Files changed:** `.renmark/plans/2026-07-29-two-mode-milestone-delivery-m2-part1-runtime.plan.md`, `.renmark/plans/2026-07-29-two-mode-milestone-delivery-m2-part2-entry-contract.plan.md`, `CHANGELOG.md`; runtime lifecycle state in `.renmark/state/lifecycle.json`.
**Do not change:** M2 Part 2 cannot execute before Part 1 is green and committed; M2 execution still requires a fresh explicit high-band cost/dispatch approval; REQ-25 propagation stays in M5; the current one-target packets are a temporary backend that M3 replaces with bounded multi-file work packages.

## [2026-07-29] - approve: accept M1 and authorize M2 planning

**Request:** Accept M1, acknowledge its recorded review-budget exception, and authorize M2 planning only.
**Built:** Recorded durable owner signoff with the accepted 186,615-token review exception and an explicit boundary that permits M2 planning and deterministic validation but no M2 implementation dispatch or spend.
**Files changed:** `.renmark/reviews/2026-07-29-d3269b6.milestone-signoff.md`, `CHANGELOG.md`; runtime approval state in `.renmark/state/lifecycle.json`.
**Do not change:** M2 execution still requires a fresh explicit cost/dispatch approval; this signoff cannot be interpreted as authorization to run executors or implementation subagents.

## [2026-07-29] - demo: stage M1 owner checkpoint

**Request:** Present M1’s owner-visible status and drift-repair behavior, then stop before M2 at the required signoff and budget-exception gate.
**Built:** Captured bounded live `delivery_state` output, demonstrated stable legacy run identity plus Agency/Conductor drift repair, linked verification/review/remediation evidence, and staged the lifecycle approval gate.
**Files changed:** `.renmark/reviews/2026-07-29-d865cc4.milestone-demo.md`, `CHANGELOG.md`; runtime approval state in `.renmark/state/lifecycle.json`.
**Do not change:** M2 cannot begin before explicit M1 owner signoff; approving this checkpoint authorizes M2 planning only, not M2 execution spend; retain the independent review’s 186,615-token budget overrun in the handoff.

## [2026-07-29] - review: close M1 canonical-state findings

**Request:** Prove the full M1 review findings are resolved before moving to the milestone checkpoint.
**Built:** Recorded high-confidence remediation evidence for stable legacy run identity and writer-validator convergence, with both original Major findings closed and all focused/static/full-suite gates green.
**Files changed:** `.renmark/reviews/2026-07-29-402c3ed.review-remediation.md`, `.renmark/memory/learnings.md`, `CHANGELOG.md`.
**Do not change:** Preserve the original review artifact as finding evidence; remediation does not erase review history; M1 cannot advance if either canonical identity or schema convergence regresses.

## [2026-07-29] - fix(delivery-state): resolve M1 review blockers

**Request:** Fix every blocking finding from the full M1 code review before allowing milestone signoff or M2 planning.
**Built:** Derived stable legacy run IDs from persisted Program/Lifecycle/Agency identity, normalized schema/contract/run metadata to the canonical validator contract, and added repeat-read plus writer-validator convergence regressions; the affected matrix and full suite pass.
**Files changed:** `renmark/delivery_state.py`, `renmark/lifecycle.py`, `tests/test_delivery_state.py`, `tests/test_delivery_state_integration.py`, `tests/test_cli_delivery_state.py`, `.renmark/reviews/2026-07-29-d185b66.review.md`, `.renmark/memory/bugs.md`, `.renmark/memory/learnings.md`, `CHANGELOG.md`; runtime debug evidence under `.renmark/debug/20260730-001342-658d/`.
**Do not change:** Legacy projection must return the same run ID for unchanged persisted workflow identity; every serialized `DeliveryState` must satisfy `schemas.validate_delivery_state`; canonical version fields are writer-owned invariants, not caller-owned passthrough.

## [2026-07-29] - verify: M1 canonical delivery state

**Request:** Re-verify M1 after repairing the live delivery-state inspection path, and do not advance to milestone review until the complete state flow is green.
**Built:** Verified the bounded read-only CLI, canonical legacy projection, Agency/Program/Lifecycle/Pipeline compatibility, all 15 task verifiers, lint, strict typing, and the repository-wide regression suite (`1539 passed, 31 skipped`).
**Files changed:** `.renmark/reviews/2026-07-29-4702acb.verification.md`, `.renmark/memory/learnings.md`, `CHANGELOG.md`.
**Do not change:** Deterministic smoke remains required before milestone review; task-level PASS results alone are not milestone acceptance; browser QA is not applicable to this CLI/library milestone.

## [2026-07-29] - fix(delivery-state): preserve typed legacy projections

**Request:** Complete M1 verification by fixing the live `--delivery-state` crash and any related quality-gate findings before milestone review.
**Built:** Replaced lossy `asdict()` lifecycle cloning with typed dataclass replacement, made stable work-package ID normalization idempotent, added live legacy-program CLI and exact persistence round-trip regressions, and cleared the affected lint/type defects.
**Files changed:** `renmark/delivery_state.py`, `renmark/agency.py`, `renmark/lifecycle.py`, `tests/test_delivery_state.py`, `tests/test_cli_delivery_state.py`, `.renmark/memory/bugs.md`, `.renmark/memory/learnings.md`, `.renmark/memory/routing.md`, `.renmark/reviews/2026-07-29-3a35610.verification.md`, `CHANGELOG.md`; runtime debug evidence under `.renmark/debug/20260729-220633-3642/`.
**Do not change:** Delivery-state cloning must preserve nested dataclass types; stable milestone/work-package IDs must remain unchanged across repeated normalization and write/read cycles; `--delivery-state` stays bounded and read-only.

## [2026-07-29] - debug(plan): make M1 dispatch WSL-safe

**Request:** Resume M1 after the first task repeated without landing and fix the verified dispatch blocker rather than spending a third blind attempt.
**Built:** Confirmed the Windows-app Codex binary lacks WSL's `bubblewrap` helper, installed the matching Linux Codex CLI in ignored project runtime state for this run, changed every M1 verifier to use `.venv`, removed forward references from Tasks 1 and 13 to tests created in later waves, and bumped the plan retry provenance.
**Files changed:** `.renmark/plans/2026-07-29-two-mode-milestone-delivery-m1.plan.md`, `.renmark/debug/20260729-212046-79d2/session.md`, `CHANGELOG.md`; runtime-only tool cache under `.renmark/state/tool-cache/codex-linux/`.
**Do not change:** Keep Codex on `workspace-write`; do not bypass sandboxing; use project-local virtual-environment executables in plan verifiers; source-task verification cannot depend on a later test-task target.

## [2026-07-29] - plan: integrate adaptive decision interaction

**Request:** Incorporate Claude/Codex selector capability, Codex Plan-versus-Default behavior, overflow navigation, and decision-only menus into the approved two-mode milestone roadmap.
**Built:** Updated the master program so M2 owns surface-aware host capabilities and semantic choice sets, M4 consumes them for loop/review/signoff decisions, M5 propagates the concise rule, and M6 proves cross-surface golden trajectories; refreshed M1 provenance to the approved PRD SHA without changing its 15 tasks, scope, or cost.
**Files changed:** `.renmark/plans/2026-07-29-two-mode-milestone-delivery.plan.md`, `.renmark/plans/2026-07-29-two-mode-milestone-delivery-m1.plan.md`, `CHANGELOG.md`.
**Do not change:** M1 remains the canonical-state bootstrap only; native picker availability and pagination are presentation details resolved in M2; numbered fallback is fully functional; informational status does not create a gate; no host collaboration mode is switched programmatically.

## [2026-07-29] - prd: clarify surface-adaptive decisions

**Request:** Make Renmark selector-capable across Claude Code and Codex while acknowledging that native clickability depends on the active host surface.
**Built:** Amended REQ-23 with decision-only menus, runtime picker capability, recommended-first fallback, bounded overflow navigation, continuation/resume semantics, and Codex Plan-versus-Default behavior; amended REQ-25 and success metrics so the concise contract propagates and is proven across hosts.
**Files changed:** `PRD.md`, `CHANGELOG.md`.
**Do not change:** Renmark never promises or creates host UI that is unavailable; informational status stays prose; every real decision has exactly one recommended-first action and a complete fallback; dangerous gates retain an explicit refusal path and never default-forward.

## [2026-07-29] - plan: stage two-mode delivery migration

**Request:** Proceed from the approved two-mode PRD into milestone planning for the cohesive Agency / Orchestrator redesign.
**Built:** Created a six-milestone master program and a validated 15-task M1 bootstrap plan for canonical delivery state; corrected plan pricing against `renmark.cost` to 28,900 tokens and $0.867.
**Files changed:** `.renmark/plans/2026-07-29-two-mode-milestone-delivery.plan.md`, `.renmark/plans/2026-07-29-two-mode-milestone-delivery-m1.plan.md`, `CHANGELOG.md`.
**Do not change:** M1 uses one-file task packets only as a temporary current-engine bridge; later milestones introduce bounded multi-file work packages. Agency delegates milestone execution to Orchestrator, and every milestone retains verify, independent review, bounded repair, demo/signoff, and rollback gates.

## [2026-07-29] - prd: define two-mode milestone delivery

**Request:** Make Renmark a cohesive vibe-coding solution with Agency and Orchestrator as its two modes, place bounded loops inside milestones, and propagate a concise mirrored project contract through `init`, `start`, and `feature`.
**Built:** Amended REQ-22 with the two-mode hierarchy and milestone-local build/review loops; added REQ-25 for non-destructive `CLAUDE.md` / `AGENTS.md` contract propagation; added parity, preservation, idempotency, and two-mode success criteria.
**Files changed:** `PRD.md`, `CHANGELOG.md`.
**Do not change:** Agency owns product governance and delegates milestone execution to Orchestrator; Conductor is internal policy only; loops cannot change scope or bypass signoff; `init` remains the single managed-contract writer and `start` / `feature` route through it.

## [2026-07-17] - release: proactive repeated-issue prevention v0.38.2

**Request:** Deploy the completed proactive repeated-issue prevention feature as a new Codex release and distribution zip.
**Built:** Bumped Renmark to v0.38.2 and packaged the committed recurrence guard, Codex/Claude rule parity, and verification work for Codex deployment.
**Files changed:** `VERSION`, `pyproject.toml`, `renmark/__init__.py`, `.claude-plugin/marketplace.json`, `README.md`, `CHANGELOG.md`; external artifact `/home/renmark/projects/releases/ai-system-renmark-v0.38.2-2026-07-17.zip`.
**Do not change:** Keep Codex deployment separate from the user's Claude/Renmark-AI installation; retain version parity across all release metadata and validate the archive before distribution.

## [2026-07-17] - verify: proactive repeated-issue monitor

**Request:** Auto-verify the resumed feature after isolating and fixing its repeated failures.
**Built:** Verified four goal-level behaviors for equivalent-attempt blocking, patch/guard/retry decisions, actionable escalation evidence, and mirrored Claude/Codex rule propagation; all nine task verifiers and repository-wide gates also passed.
**Files changed:** `.renmark/reviews/2026-07-17-f87b955.verification.md`, `.renmark/memory/learnings.md`, `CHANGELOG.md`.
**Do not change:** A green deterministic smoke run does not bypass code review, merge, release, or human approval gates.

## [2026-07-17] - docs(template): propagate Codex repeated-issue rule

**Request:** Ensure Codex receives proactive repeated-issue prevention when Renmark initializes or refreshes a project.
**Built:** Added the root AGENTS rule verbatim to the managed AGENTS template while preserving every existing rule and marker.
**Files changed:** `plugin/templates/AGENTS.md.template`, `CHANGELOG.md`.
**Do not change:** Keep the managed block byte-for-byte aligned with the root AGENTS rule and preserve surrounding template content.

## [2026-07-17] - docs(codex): mirror repeated-issue prevention

**Request:** Give Codex the same proactive repeated-issue contract as Claude Code.
**Built:** Added the concise AGENTS rule requiring the persisted recurrence ledger before a third equivalent implementation/test attempt, bounded evidence, explicit patch-or-durable-guard guidance, and mirrored approved guards.
**Files changed:** `AGENTS.md`, `CHANGELOG.md`.
**Do not change:** Keep this rule semantically synchronized with the authoritative `CLAUDE.md` contract and never retry or edit rules silently.

## [2026-07-17] - docs(template): propagate repeated-issue prevention

**Request:** Ensure projects adopted through Renmark receive the same proactive Claude rule as this repository.
**Built:** Added the semantically identical repeated-issue prevention block to the managed Claude template while preserving managed markers and existing content.
**Files changed:** `plugin/templates/CLAUDE.md.template`, `CHANGELOG.md`.
**Do not change:** Keep the template rule identical to the authoritative `CLAUDE.md` block and preserve both managed block markers.

## [2026-07-17] - docs(claude): require proactive repeated-issue prevention

**Request:** Make Claude's authoritative project contract stop materially equivalent implementation/test attempts before a third retry.
**Built:** Added a host-neutral core rule requiring the deterministic recurrence ledger, bounded evidence, an explicit patch-or-durable-guard recommendation, human acknowledgement, and mirrored approved guards without weakening Codex context invariants.
**Files changed:** `CLAUDE.md`, `CHANGELOG.md`.
**Do not change:** Never retry or edit rules silently; approved durable guards must remain mirrored in `CLAUDE.md` and `AGENTS.md`; Codex must not receive unsupported clear/compact/resume instructions.

## [2026-07-17] - test(recurrence): prove bounded retries and preserve evidence

**Request:** Resume the proactive monitor build after fixing the recurrence classifier, without spending another blind Codex retry.
**Built:** Added deterministic coverage for stable Scan identity, cross-run recurrence, changed fingerprints, bounded/corrupt/atomic/lock state, raw-signal exclusion, patch/guard/retry acknowledgements, two-attempt Codex limits, and host-neutral Orchestrate wording; recurrence stops now retain the concrete current verifier, executor, or lane evidence in escalation artifacts.
**Files changed:** `tests/test_recurrence.py`, `renmark/cli/_codex_runner.py`, `.renmark/memory/bugs.md`, `.renmark/memory/learnings.md`, `.renmark/memory/routing.md`, `CHANGELOG.md`.
**Do not change:** Never launch a third equivalent attempt; never replace actionable failure evidence with only a guard summary; keep raw model transcripts out of recurrence state and rule-file changes human-gated.

## [2026-07-17] - fix(recurrence): classify remediation by failure kind

**Request:** Isolate the repeated-issue monitor failure, fix its root cause, and resume the paused feature run without another wasteful Codex retry.
**Built:** Replaced count-based remediation selection with stable rule-kind classification, persisted bounded check/rule identity with legacy-key recovery, and proved verifier failures recommend a patch while lane/instruction failures recommend a durable guard.
**Files changed:** `renmark/recurrence.py`, `.renmark/plans/2026-07-17-debug-recurrence-remediation.plan.md`, `.renmark/debug/20260717-200049-c9ee/`, `.renmark/memory/bugs.md`, `.renmark/memory/learnings.md`, `CHANGELOG.md`.
**Do not change:** Occurrence count controls when another attempt is blocked, never which remediation is recommended; technical failures default to a code patch and process/instruction failures to a human-approved durable guard.

## [2026-07-17] — feat(orchestrate): surface repeated-issue remediation

**Request:** Give Claude Code and Codex the same proactive warning and remediation choice before another equivalent implementation attempt.
**Built:** Added host-neutral recurrence observation and pre-attempt gating to Orchestrate, with bounded evidence and recommended-first patch, durable-guard, or explicit one-time-retry choices; rule-document changes remain proposal-only and human-gated.
**Files changed:** `plugin/skills/orchestrate/SKILL.md`, `CHANGELOG.md`.
**Do not change:** Preserve usage-limit handling, fable fallback, Codex rerouting, SubagentOutput isolation, recommended-first host selectors, and Codex's no-clear/compact/resume invariant.

## [2026-07-17] — feat(codex): stop equivalent retries before a third call

**Request:** Prevent Codex from repeatedly spending model calls on the same implementation or verifier failure.
**Built:** Added recurrence observations for executor exits, lane violations, and verifier failures; the second equivalent failure returns a bounded `repeated_issue_guard` result instead of launching a third Codex call, while preserving rollback, usage, escalation, and sibling-lane behavior.
**Files changed:** `renmark/cli/_codex_runner.py`, `CHANGELOG.md`.
**Do not change:** Keep Codex tasks on the subprocess lane; preserve provider-limit pauses and truthful retry accounting; never persist raw model or verifier bodies in recurrence state.

## [2026-07-17] — feat(recurrence): add bounded repeated-issue state

**Request:** Detect equivalent implementation and verifier failures across attempts and runs without storing raw histories or wasting a third model call.
**Built:** Added a stdlib-only recurrence ledger with stable fingerprints, second-occurrence blocking decisions, bounded summaries, atomic/capped persistence, corruption recovery, and explicit patch, durable-guard, resolve, and one-time-retry acknowledgements; the focused Ruff, mypy, and compile gates pass.
**Files changed:** `renmark/recurrence.py`, `CHANGELOG.md`.
**Do not change:** Keep recurrence state separate from Scan's proposal ledger; persist no raw verifier/model bodies; block an unacknowledged third equivalent attempt; keep acknowledgement and resolution explicit.

## [2026-07-17] — feat(recurrence): expose stable Scan identity helpers

**Request:** Reuse Scan's proven finding identity model as the foundation for proactive repeated-issue detection.
**Built:** Added public key-from-parts and content-fingerprint helpers while preserving `finding_key` behavior and the private compatibility alias; corrected the plan's pytest verifiers to use the repository virtual environment explicitly.
**Files changed:** `renmark/scan.py`, `.renmark/plans/2026-07-17-proactive-repeated-issue-monitor.plan.md`, `CHANGELOG.md`.
**Do not change:** Preserve Scan's `check:rule_id:target` key, SHA-1/12-hex fingerprint semantics, proposal ledger, backlog resurface behavior, and read-only lane invariants.

## [2026-07-17] — PRD updated: proactive recurring-issue prevention

**Request:** Detect materially equivalent implementation or testing issues before Codex or Claude repeats a futile attempt, then proactively recommend either a patch or a durable mirrored instruction.
**Built:** Added human-approved `REQ-24` and a success metric covering host-neutral recurrence fingerprints, bounded within-run and cross-run evidence, early notification, and patch-or-`CLAUDE.md`/`AGENTS.md` remediation guidance; bumped `last_reviewed`.
**Files changed:** `PRD.md`, `CHANGELOG.md`.
**Do not change:** Warn before a third equivalent model attempt; keep evidence local and bounded; preserve approval gates; never auto-write `PRD.md`, `CLAUDE.md`, or `AGENTS.md`; keep Claude Code and Codex behavior equivalent.

## [2026-07-17] — v0.38.1: ship and route Claude specialist subagents

**Request:** Stop Renmark's Claude runs from falling back to general-purpose agents and make the expected nine-role dispatch model install automatically.
**Built:** Added eight Claude plugin agent definitions under `plugin/agents/`, dispatched them with collision-safe `renmark:<role>` names, made native-agent detection verify shipped files, honored explicit plan roles, and classified ordinary project source as `code-implementer`. Plans now require a specialist role and a reason for any `general-purpose` fallback. Claude supplies the ninth role through its built-in general-purpose agent; no global `~/.claude/agents/` copy is required, and Renmark intentionally spawns only the roles relevant to each plan. The Windows installer now rejects unreadable WSL-to-NTFS junctions and falls back to a verified copy, doctor reports degrade unsupported console glyphs instead of crashing, and deployable archives exclude mypy/Ruff caches.
**Files changed:** `plugin/agents/`, `renmark/subagent_profiles.py`, `renmark/dispatch.py`, `renmark/lint.py`, `renmark/plan_lint.py`, `renmark/doctor.py`, `renmark/release.py`, subagent/plan shared contracts and rules, installers, README, version files, regression tests, `.renmark/debug/20260717-130707-1eb8/session.md`, `.renmark/memory/bugs.md`, `.renmark/memory/learnings.md`, `CHANGELOG.md`; external artifact `/home/renmark/projects/releases/ai-system-renmark-v0.38.1-2026-07-17.zip`.
**Do not change:** Keep the eight specialists plugin-scoped and file-verified; do not require global Claude agent files or spawn all roles on every run; preserve explicit plan roles and require `role_reason` whenever general-purpose is chosen; verify a Windows junction by reading the plugin manifest before accepting it.

## [2026-07-17] — fix: restore Claude Code native selectors after install

**Request:** Restore Renmark's Claude Code arrow-key selector and the recommended-first option after the parity installation regressed to plain prose.
**Built:** Reproduced an enabled-but-unloadable Claude plugin whose registry pointed at a missing cache path, repaired the live cache, and made `install.sh` perform an authoritative post-install doctor check. The installer now fails instead of announcing success when Claude's registry/cache repair is unhealthy, and integration coverage pins both the valid cache path and the failure exit.
**Files changed:** `install.sh`, `tests/integration/test_plugin_install.py`, `CHANGELOG.md`, `.renmark/debug/20260717-124915-8d72/session.md`, `.renmark/memory/bugs.md`, `.renmark/memory/learnings.md`; external artifact `/home/renmark/projects/releases/ai-system-renmark-v0.38.0-2026-07-17.zip`.
**Do not change:** A successful install must leave `renmark@renmark-local` enabled with an existing registered cache path; Claude uses `AskUserQuestion` with exactly one `(Recommended)` option first, while Codex keeps `request_user_input` and never receives clear/resume instructions.

## [2026-07-16] — package: deployable Renmark v0.38.0 archive

**Request:** Create a deployable Renmark zip in the shared `/home/renmark/projects/releases/` folder.
**Built:** Prepared the sanitized offline distribution `ai-system-renmark-v0.38.0-2026-07-16.zip` using Renmark's version-drift-aware packager; the archive excludes repository state, virtual environments, caches, generated `.renmark/` data, and secret-bearing file patterns.
**Files changed:** `CHANGELOG.md`; external artifact `/home/renmark/projects/releases/ai-system-renmark-v0.38.0-2026-07-16.zip`.
**Do not change:** Keep deployable archives version-anchored, rooted under one extraction directory, free of `.git`/`.venv`/`.renmark` and secret-bearing files, and validate archive integrity before distribution.

## [2026-07-16] — release: Claude Code / Codex parity (v0.38.0)

**Request:** Give Renmark first-class Claude Code and Codex parity across distribution, recommended-first selectors, natural-language routing, isolated dispatch, pipelines, loops, recovery, and installed-machine behavior; Codex must never ask the user to run unsupported `/clear`, `/compact`, or `/renmark:resume` commands.
**Built:** Unified both hosts under the canonical `plugin/` bundle with synchronized manifests and a Codex personal-marketplace installer; added host capability resolution, exactly-one/recommended-first selector adapters with numbered fallback, exact natural triggers such as “plan this” and “dispatch this,” native Codex subagent dispatch semantics, host-aware lifecycle/context gates, and deterministic cross-host pipeline/loop E2E proof. Hidden shared contracts now live under `plugin/skills/.shared/` so Codex discovers only callable skills, all skill frontmatter permits implicit routing, and the Windows installer is ASCII-safe, uses Codex Desktop's bundled Python when needed, and installs a PATH-visible native `renmark-execute` launcher that preserves UNC project directories. The CLI now exposes its documented `--version` proof. Verified Codex plugin validation, release drift, Ruff, mypy, strict plugin lint, six behavioral fixtures, installer smoke tests, and the full suite (1,462 passed, 29 skipped).
**Files changed:** `plugin/`, `renmark/`, `tests/`, `install.sh`, `install.ps1`, host manifests/templates, `README.md`, `VERSION`, `pyproject.toml`, `CLAUDE.md`, `AGENTS.md`, `.renmark/memory/features.md`, `CHANGELOG.md`.
**Do not change:** Keep one product identity and artifact/state model across hosts; every choice has exactly one `(Recommended)` option at index 0; selector unavailability alone is not headless mode; pass the active host explicitly at Windows/WSL boundaries; Codex must continue from persisted state without clear/compact/resume instructions; keep internal shared contracts hidden from Codex skill discovery.

## [2026-07-16] — fix: restore repository quality gates

**Request:** Repair the pre-existing lint and type-check debt before implementing Claude Code / Codex parity.
**Built:** Applied safe Ruff cleanup, restored compatibility aliases removed by the mechanical pass, fixed the heartbeat datetime annotation, and wrapped remaining long lines. Verified Ruff, mypy, focused regression tests, and the full suite (1,423 passed, 28 skipped).
**Files changed:** `renmark/`, `tests/`, `.renmark/memory/bugs.md`, `CHANGELOG.md`.
**Do not change:** Keep the `_engine` compatibility aliases until their direct test/API consumers migrate; repository-wide Ruff, mypy, and pytest must all remain green.

## [2026-07-15] — PRD updated: Claude Code / Codex host parity

**Request:** Make Renmark a first-class Codex host with the same selector, natural-language routing, pipeline, loop, and resume outcomes as Claude Code.
**Built:** Reconciled Vision, Non-goals, Requirements, Success metrics, and Scope boundaries; added REQ-23 with product-level parity acceptance criteria; bumped `last_reviewed` to 2026-07-15.
**Files changed:** `PRD.md`, `CHANGELOG.md`.
**Do not change:** Both hosts share one product workflow and artifact/state semantics; every choice has exactly one `(Recommended)` option at index 0; selector unavailability alone never means an interactive Codex session is headless; PRD changes remain human-approved.

## [2026-07-15] — audit: Codex / Claude Code parity

**Request:** Deep-audit renmark's Codex parity with Claude Code, especially native selectors, recommended-first ordering, natural-language pipeline triggers, orchestration, loops, and resume behavior.
**Built:** Wrote a provenance-bearing parity audit with a P0/P1 gap map, host-neutral interaction and dispatch architecture, trigger matrix, implementation sequence, and acceptance criteria. Ran the full deterministic audit, skill consistency lint, behavior fixtures, a 211-test focused parity slice, and the full suite (1,423 passed, 28 skipped); no runtime/source behavior was changed.
**Files changed:** `.renmark/audits/2026-07-15-codex-claude-parity.audit.md`, `.renmark/audits/audit-report-2026-07-15.{md,json}`, `.renmark/audits/inventory-2026-07-15.{md,json}`, `CHANGELOG.md`.
**Do not change:** Keep recommended action at option index 0 on both hosts; never equate an unavailable Claude picker with Codex headless mode; do not claim host parity without installed-package identity plus live Claude and Codex trajectory proof.

## [2026-07-09] — feat(heartbeat): add cron setup hint to init/start/feature handoff menus

**Request:** Surface heartbeat cron install command in /renmark:init, /renmark:start, and /renmark:feature handoffs when cron is not yet set up.
**Built:** is_cron_installed() in renmark/heartbeat.py, --heartbeat-check-cron CLI flag, cron hint added to plugin/skills/init/SKILL.md, plugin/skills/start/SKILL.md, plugin/skills/feature/SKILL.md.
**Files changed:** renmark/heartbeat.py, renmark/cli/commands.py, renmark/cli/_engine.py, plugin/skills/init/SKILL.md, plugin/skills/start/SKILL.md, plugin/skills/feature/SKILL.md, tests/test_heartbeat.py.
**Do not change:** is_cron_installed() checks only crontab (Unix); Windows Task Scheduler detection not implemented.

## [2026-07-09] — feat(heartbeat): expand to general proactive scheduler — 5 check types

**Request:** Heartbeat should also nudge stuck backlog items and stalled pipelines, not just monitor usage limits.
**Built:** `renmark/heartbeat_checks.py` with check_usage_limit_pause, check_stalled_feature, check_stalled_pipeline, check_blocked_backlog, check_awaiting_loop; heartbeat.check() now fans out to all 5.
**Files changed:** renmark/heartbeat_checks.py (new), renmark/heartbeat.py (updated check()), plugin/skills/heartbeat/SKILL.md, tests/test_heartbeat_checks.py.
**Do not change:** Individual check function thresholds (stall_hours) are module-level defaults — don't tune without data.

## [2026-07-09] — feat: heartbeat proactive usage-limit recovery monitor

**Request:** Add a scheduled heartbeat check that monitors for usage-limit pauses and notifies when the limit clears, inspired by OpenClaw's heartbeat pattern.
**Built:** `renmark/heartbeat.py` (check, auto_resume, emit_cron), `--heartbeat` CLI flag (--emit-cron, --auto-resume), `/renmark:heartbeat` skill.
**Files changed:** renmark/heartbeat.py, renmark/cli/commands.py, renmark/cli/_engine.py, plugin/skills/heartbeat/SKILL.md, plugin/commands/heartbeat.md, tests/test_heartbeat.py.
**Do not change:** PauseState schema in renmark/state/pause.py — heartbeat reads it but never writes it.

## [2026-07-06] — release: bump v0.35.0 -> v0.36.0 (reduce-complexity)

**Request:** Reduce all 32 modularity danger items (cyclomatic/cognitive complexity, oversized modules, long functions).
**Built:** Extracted helpers across 15 files; split renmark/init.py -> health.py and cli/_engine.py -> _codex_runner.py. Fixed spec-parsing bug introduced during refactor. Final danger count: 5 (all marginal engine.py metrics).
**Files changed:** renmark/audit.py, bootstrap.py, cli/_engine.py, cli/_codex_runner.py (new), cli/commands.py, health.py (new), init.py, judge.py, lifecycle.py, lint.py, memory.py, parser.py, release.py, shadow.py, subagent_gate.py, summary.py, worktree.py
**Do not change:** spec_lines-is-not-None guard in parser.py (bare 'or []' creates new list on empty, causing silent data loss in spec blocks).

## [2026-07-06] — release: bump v0.34.0 -> v0.35.0 (agency-mode BL-0002)

behavior tests + CLI flags for Agency Mode (AC11 proof, mode.behavior.json regression fix,
_with_agency_note unit tests, --agency-status/--activate-agency/--deactivate-agency CLI).

## 2026-07-06 — Agency Mode: behavior tests + CLI flags

**Request**: Close BL-0002 — add AC11 behavior proof, CLI agency state management,
_with_agency_note unit tests, fix pre-existing mode.behavior.json regression.

**Built**:
- renmark/behavior.py: `lifecycle.skill_preamble_fresh` and
  `lifecycle.skill_preamble_agency_active` adapters registered in `_DISPATCH`
- tests/behavioral/mode.behavior.json: switched to `lifecycle.skill_preamble_fresh` —
  fixes regression where live repo's mode=orchestrator broke the assertion
- tests/behavioral/agency.behavior.json: new deterministic case asserting
  "Agency Mode active" fires in start-skill preamble when agency is active (AC11)
- tests/test_lifecycle.py: 4 _with_agency_note unit tests (inactive passthrough x2,
  active-aware-skill marker, non-aware passthrough)
- renmark/cli/_engine.py: --agency-status, --activate-agency, --deactivate-agency

**Files changed**: renmark/behavior.py, tests/behavioral/mode.behavior.json,
tests/behavioral/agency.behavior.json (new), tests/test_lifecycle.py,
renmark/cli/_engine.py, CHANGELOG.md

**Do not change**: renmark/agency.py state API, lifecycle._with_agency_note logic,
plugin/skills/*/SKILL.md agency sections, tests/test_agency.py, agency-delivery.md

## [2026-07-06] — Context hygiene gates (selectable AskUserQuestion menus)

**Request:** Add hard-stop context hygiene gates to renmark — a blocking AskUserQuestion menu at cross-domain transitions (clear gate) and at ≥60% context (compact gate) — without claiming to invoke /compact or /clear programmatically.

**Built:**
- `renmark/config.py`: `compact_gate_tokens(repo) -> int` + `set_compact_gate_tokens(repo, value)` — configurable threshold (default 120k, 0=disabled)
- `renmark/lifecycle.py`: `persist_compact_checkpoint(repo, skill, reason)` — writes `.renmark/state/compact_checkpoint.json`; `_CONTEXT_BYPASS_SKILLS = {"finish", "approve", "resume"}`; `skill_preamble` clear-verdict upgraded from advisory "consider /clear" to `CONTEXT_GATE_CLEAR:` prefixed hard-stop with full AskUserQuestion menu spec (bypass skills stay advisory)
- `renmark/cli/_engine.py`: `--compact-checkpoint` flag (calls persist_compact_checkpoint + prints /compact+/renmark:resume instructions); `--set-compact-gate-tokens TOKENS` (configures threshold)
- `CLAUDE.md` + `AGENTS.md`: Context budget rule block replaced with selectable hygiene gates spec (AskUserQuestion menus, CONTEXT_GATE_CLEAR: sentinel, compact-checkpoint CLI, bypass skill list, configurable threshold note)
- `plugin/skills/_shared/context-taxonomy.md`: Added "Context hygiene gates" section documenting both gate types
- Tests: 9 new tests (5 config + 4 lifecycle); 1359 total, all pass

**Files changed:** renmark/config.py, renmark/lifecycle.py, renmark/cli/_engine.py, CLAUDE.md, AGENTS.md, plugin/skills/_shared/context-taxonomy.md, tests/test_config.py, tests/test_lifecycle.py

**Do not change:**
- `_CONTEXT_BYPASS_SKILLS` must include finish/approve/resume — these flows must never be blocked mid-stream
- `compact_gate_tokens` must return 0 when 0 is stored (0 = disabled, not default)
- `CONTEXT_GATE_CLEAR:` prefix is load-bearing — CLAUDE.md rule pattern-matches it to trigger AskUserQuestion
- `persist_compact_checkpoint` is exported (no underscore) — tests and CLI import it directly

## [2026-07-06] — Claude-native subagent definitions + wave-level Workflow fan-out
**Request:** Upgrade renmark to use Claude Code's native `.claude/agents/*.md` subagent-type
files for the 8 specialized dispatch roles and add an optional wave-level `Workflow`-tool
fan-out path to `/renmark:orchestrate` — without migrating to Agent Teams or touching the
deterministic Python policy layer.
**Built:**
- `.claude/agents/{docs-editor,code-implementer,test-writer,reviewer,release-manager,researcher,audit-reader,finish-lane-specialist}.md` — 8 native Claude Code subagent-type files with enforced tool allowlists and model tiers.
- `renmark/subagent_profiles.py::has_native_agent_file` — pure helper (static frozenset + optional on-disk check, never raises) used by orchestrate to pass `subagent_type: <role>` on Agent calls.
- `renmark/dispatch.py::build_workflow_fanout_args` — packet-shaping helper that builds Workflow `args` payloads (pre-resolves `agent_type` per task via `has_native_agent_file`), skipping codex tasks.
- `plugin/skills/_shared/workflow-fanout.md` — contract doc for wave-level fan-out (when to use, what stays Python, G11 validation ownership, cost/ledger note).
- `plugin/skills/orchestrate/SKILL.md` Step 3b — updated with `subagent_type` dispatch and Workflow fan-out branch for waves with >1 needs_agent task.
- `plugin/skills/_shared/subagent-profiles.md` — added "Native agent file" column; fixed pre-existing model-tier drift (release-manager/researcher/finish-lane-specialist were stale Haiku).
- 3 codex-review fixes: `agent_type` field in fanout payloads, `docs-editor.md` stop condition, `researcher.md` `Write` tool.
**Files changed:** `.claude/agents/*.md` (8 new), `renmark/subagent_profiles.py`, `renmark/dispatch.py`, `plugin/skills/_shared/subagent-profiles.md`, `plugin/skills/_shared/workflow-fanout.md`, `plugin/skills/orchestrate/SKILL.md`, `tests/test_dispatch.py`, `tests/test_subagent_profiles.py`.
**Do not change:** Python policy layer stays the backbone — `dispatch.py` wave grouping/validation, `subagent_gate.py`, `cost.py`, G11 `SubagentInput`/`SubagentOutput`/`parse_subagent_response`. Do not broaden Workflow use to whole-plan execution (breaks G12 cross-`/clear` resumability).

## [2026-07-02] — v0.32.0 — enforced subagent-justification gate
**Release.** Bumps v0.31.0 → v0.32.0. Ships the enforced subagent gate (strengthens
REQ-21) in response to a usage report (subagent-heavy, >150k-context sessions running
unchallenged). Of Codex's 6 cost-control recs, 4 were already shipped (context
thresholds, finish lanes, model routing, deterministic/model cost split); this releases
the 2 real gaps.
**Built:**
- `renmark/subagent_gate.py` — pure zero-LLM gate: `justify_task` (4-question verdict with
  structured `challenge_code`), `challenge_plan` (rollup), `preview_line`, and a
  `python -m renmark.subagent_gate <plan>` CLI (exit 0 clean / 1 challenged / 2 usage,
  mirroring `plan_lint`). Composes `cost`/`subagent_profiles`; never raises.
- Real enforcement: `renmark-execute --dry-run` runs the gate and prints the verdict; the
  orchestrate pre-flight surfaces it and requires acknowledgment on a challenged plan.
- General-purpose reduction: `parser.Task` gained `role`/`role_reason` so plans can justify
  a general-purpose spawn; unexplained general-purpose is challenged.
- Docs: `_shared/{deterministic-first,subagent-budget,cost-preview}.md` mark the gate enforced;
  CLAUDE.md/AGENTS.md deterministic-first rule names the helper.
- Codex-reviewed: 4 Major findings all fixed (wiring, parser role_reason, challenge_code, est_tokens).
**Files changed:** renmark/subagent_gate.py (new), tests/test_subagent_gate.py (new), renmark/parser.py, renmark/cli/_engine.py, orchestrate/SKILL.md, 3 _shared/*.md, CLAUDE.md, AGENTS.md, version files, CHANGELOG.md.
**Do not change:** gate is deterministic/zero-LLM, must never raise; composes cost/subagent_profiles (no reimplementation); general-purpose without role_reason is challenged. It surfaces+acks, does NOT hard-block dispatch (agent-driven). Codex recs #2/#3/#4/#6 already shipped — not re-touched.

## [2026-07-02] — enforced subagent-justification gate (REQ-21 strengthening)
**Request:** Usage report showed subagent-heavy, >150k-context sessions running unchallenged (general-purpose subagents recurring). Turn the advisory deterministic-first / subagent gate into an ENFORCED pre-dispatch check.
**Built:**
- `renmark/subagent_gate.py` — pure, zero-LLM gate. `justify_task` answers REQ-21's 4 questions mechanically (deterministic path? scoped role? orchestrator-inline? large/ambiguous enough?); `challenge_plan` rolls a plan up (deterministic-eligible / inline-able / unexplained-general-purpose spawns flagged); `preview_line` for the cost preview; `main()` CLI (`python -m renmark.subagent_gate <plan>` → exit 0 clean / 1 challenged / 2 usage), mirroring `plan_lint`. Composes `cost.is_deterministic_item`/`_get` + `subagent_profiles.resolve_profile`/`profile_tier` — does not re-implement. Never raises.
- Wiring: orchestrate pre-flight runs the gate before dispatch and requires ack on a challenged plan; `_shared/{deterministic-first,subagent-budget,cost-preview}.md` document the gate as enforced (not advised); CLAUDE.md/AGENTS.md deterministic-first rule names the new helper.
- `tests/test_subagent_gate.py` — 11 tests: deterministic→no-subagent, simple/tiny→inline-flagged, hard-scoped→clean, general-purpose-without-reason→challenged (+reason clears it), plan-level challenge invariants, never-raises.
**Files changed:** renmark/subagent_gate.py (new), tests/test_subagent_gate.py (new), orchestrate/SKILL.md, 3 _shared/*.md, CLAUDE.md, AGENTS.md, CHANGELOG.md.
**Do not change:** the gate is deterministic/zero-LLM and MUST never raise (degrades to "subagent needed" + flag); it composes cost/subagent_profiles, never re-implements; general-purpose without a `role_reason` is challenged (Codex rec #5). Codex recs #2 (context thresholds), #3 (finish lanes), #4 (model routing), #6 (deterministic/model cost split) were already shipped — NOT re-touched.

## [2026-07-02] — v0.31.0 — Agency Mode full pipeline coverage
**Release.** Bumps v0.30.0 → v0.31.0. Releases the Agency Mode fast-follow: agency-awareness
now spans ALL 10 pipeline skills (the v0.30.0 spine start/prd/roadmap/finish/resume PLUS
feature/plan/orchestrate/verify/codereview). Completes REQ-22 pipeline coverage.
**Request:** Extend Agency Mode to the 5 deferred pipelines and release it.
**Built:**
- `renmark/lifecycle.py` — `_AGENCY_SPINE_SKILLS` → `_AGENCY_AWARE_SKILLS` (all 10 pipelines;
  back-compat alias retained); `_with_agency_note` surfaces the hint for the newly-covered pipelines.
- Agency blocks in `plugin/skills/{feature,plan,orchestrate,verify,codereview}/SKILL.md`
  (pointer to `_shared/agency-delivery.md` via `${CLAUDE_PLUGIN_ROOT}`, never inline).
- `tests/test_agency_behavior.py` — iterates the full agency-aware set (asserts all 10 gain the
  hint when active; non-aware skills stay clean; inactive path byte-identical).
- Codex-reviewed (fixed test-coverage gap + docstring); portability bug caught (absolute path → ${CLAUDE_PLUGIN_ROOT}).
**Files changed:** renmark/lifecycle.py, 5 SKILL.md, tests/test_agency_behavior.py, version files, CHANGELOG.md.
**Do not change:** agency hint only for `_AGENCY_AWARE_SKILLS`; inactive path byte-identical;
bodies load on demand (pointer only); reuses cost-control/finish-lanes/deterministic-first infra.

## [2026-07-02] — Agency Mode fast-follow (full pipeline coverage)
**Request:** Extend Agency Mode awareness to the 5 pipelines the v0.30.0 walking-skeleton MVP deferred (feature, plan, orchestrate, verify, codereview) so the whole delivery loop is agency-aware.
**Built:**
- `renmark/lifecycle.py` — `_AGENCY_SPINE_SKILLS` → `_AGENCY_AWARE_SKILLS` (now all 10 pipeline skills; back-compat alias kept). `_with_agency_note` surfaces the agency hint for the newly-covered pipelines when agency is active.
- Agency blocks added to `plugin/skills/{feature,plan,orchestrate,verify,codereview}/SKILL.md` — each referencing `_shared/agency-delivery.md` by pointer (never inline): feature=select-next-milestone + PRD-alignment + no drift; plan=atomic tasks + milestone acceptance criteria + cost preview; orchestrate=background agents + continue-until-checkpoint + progress summaries; verify=tests/browser + demo-readiness + unverified; codereview=full review before signoff + merge readiness.
- `tests/test_agency_behavior.py` — asserts all 10 pipeline skills gain the hint when active; non-aware skills (debug/audit) stay clean; inactive path still byte-identical.
**Files changed:** renmark/lifecycle.py, 5 SKILL.md, tests/test_agency_behavior.py, CHANGELOG.md.
**Do not change:** agency hint only for `_AGENCY_AWARE_SKILLS`; inactive path byte-identical; bodies load on demand (pointer only); reuses cost-control/finish-lanes/deterministic-first infra.

## [2026-07-02] — v0.30.0 — Agency Mode (walking-skeleton MVP)
**Release.** Bumps v0.29.0 → v0.30.0. Ships **Agency Mode** (REQ-22) — an OPTIONAL
higher-level project-delivery workflow ABOVE Conductor/Orchestrator (does not replace
them), the third delivery modality. Walking-skeleton MVP over the core pipeline spine.
**Request:** Build Agency Mode — owner gives intent + signs off milestones while renmark
runs discovery → PRD → roadmap → milestones → build → demo → feedback → signoff → release.
**Built:**
- `renmark/agency.py` — lightweight resumable agency state (`.renmark/state/agency.json`):
  `AgencyState`, `read_agency`/`write_agency` (atomic via `tempfile.mkstemp`), `is_active`,
  `activate`/`deactivate`; `AGENCY_JSON_BYTE_BUDGET`=1KB + `AgencyBloatError` (mirrors lifecycle).
- `plugin/skills/_shared/agency-delivery.md` — shared agency delivery contract, loaded ON
  DEMAND only (registered in `context.FRAGMENT_NAMES`); never eager.
- `renmark/lifecycle.py` — mode-conditioned `skill_preamble`: when agency active, appends an
  agency hint + fragment POINTER (not body) for the 5 spine skills only; byte-identical when
  inactive (`_with_agency_note`, `_AGENCY_SPINE_SKILLS`, `_AGENCY_HINT_MARKER`).
- Agency blocks in the 5 spine skills (start/prd/roadmap/finish/resume); `/renmark:start` is
  the explicit opt-in entry (seeds agency.json via `agency.activate`). help + CLAUDE.md/AGENTS.md.
- Tests: `tests/test_agency.py` (state) + `tests/test_agency_behavior.py` (AC11 — proves agency
  changes behavior without loading skill bodies; inactive path byte-identical).
- Standalone lint hotfix: cleared pre-existing ruff debt in cost.py/subagent_profiles.py.
**Files changed:** renmark/agency.py (new), plugin/skills/_shared/agency-delivery.md (new),
renmark/context.py, renmark/lifecycle.py, 5 spine SKILL.md, help/SKILL.md, CLAUDE.md, AGENTS.md,
PRD.md (REQ-22), tests/test_agency*.py (new), cost.py, subagent_profiles.py, version files.
**Do not change:** Agency Mode must NOT replace Conductor/Orchestrator; explicit opt-in only
(no auto-detect); agency bodies load on demand (never eager); `cites` in skillmeta is a CLOSED
3-block vocab (reasoning-contract/next-steps/handoff-menu) — spine source of truth is
`lifecycle._AGENCY_SPINE_SKILLS`. Reuses cost-control/finish-lanes/deterministic-first infra.
Fast-follow (deferred): feature/plan/orchestrate/verify/codereview agency-awareness.

## [2026-07-02] — PRD updated
**Request:** Add REQ-22 (Agency Mode) to the PRD, resolving the drift verdict from the agency-mode brainstorm.
**Built:** Reconciled the Requirements + Scope-boundaries sections of PRD.md; added REQ-22 (optional higher-level project-delivery workflow above Conductor/Orchestrator), an In-scope clause, and a 2026-07-02 revision note; bumped last_reviewed.
**Files changed:**
- `PRD.md` — added REQ-22 (Agency Mode), In-scope clause, revision note; last_reviewed → 2026-07-02.
**Do not change:**
- Agency Mode must NOT replace Conductor/Orchestrator; explicit opt-in only (no auto-detect); reuses cost-control/finish-lane/deterministic-first infra; agency bodies load on demand. PRD.md is human-owned — automated stages propose, never write without approval.

## [2026-07-02] — project scope: agency-mode (spec)
**Request:** Brainstorm/spec for Agency Mode — a higher-level project-delivery workflow above Conductor/Orchestrator. Spec-first, no implementation this session.
**Stack:** Python >=3.10 + Claude Code plugin (fixed — renmark-internal feature; no new stack).
**Deployment:** Plugin install (WSL + Windows clone), same as all renmark features.
**MVP boundary (walking skeleton):** agency state (`renmark/agency.py` + `.renmark/state/agency.json`) + shared `agency-delivery.md` fragment (loaded on demand) + mode-conditioned preamble + agency-aware CORE SPINE only (start → prd → roadmap → finish → resume) + behavior tests + help/docs.
**Out of scope:** third `mode.py` value (decided: higher-level workflow, NOT a mode); auto-detection (explicit opt-in via /renmark:start); full 9-pipeline coverage (feature/plan/orchestrate/verify/codereview = fast-follow); any new execution/inference engine.
**Do not change:** Agency Mode must NOT replace Conductor/Orchestrator; must reuse cost-control/finish-lanes/deterministic-first infra, not re-implement it; agency bodies load on demand only (never eager). PRD gate: REQ-22 addition is human-gated via /renmark:prd before build. Spec: `.renmark/specs/2026-07-02-agency-mode.spec.md`.

## [2026-07-02] — deterministic-first (REQ-21 + worktree cost-control sub-scope)
**Request:** Deterministic-first execution discipline (REQ-21 AC2) — wire into existing gate docs + establish worktree-backed release readiness checks for Agency Mode (AC6).
**Built:**
- `plugin/skills/_shared/deterministic-first.md` — new shared fragment: 4-question gate (git/grep/parser before AI), deterministic task taxonomy (state, artifact integrity, package/release, file sync, execution baseline), cost-saving principle.
- Gate wiring: `model-routing.md` (ask deterministic-first before model choice) + `subagent-budget.md` (deterministic-first before spawn).
- `renmark/worktree.py` — git-backed helpers: clean-tree validation, diff-size thresholds, merge-to-main checks, stale-worktree cleanup, test-baseline comparisons.
- `renmark/finish_lanes.py::release_readiness()` — deterministic lane-readiness gate (no model, git + artifact checks).
- Agency-Mode cross-ref: `_shared/deterministic-first.md` + worktree.py serve milestone-verification checks (AC6).
- Worktree cost-control sub-scope: lane_table adds "Worktree" column; cost.py tags checks as deterministic vs. model-driven.
**Files changed:** deterministic-first.md (new), model-routing.md, subagent-budget.md, renmark/worktree.py, finish_lanes.py, cost.py, 2026-07-02-agency-mode.request.md, CHANGELOG.md.
**Do not change:** worktree isolation must NOT be removed; worktree/release checks stay deterministic (git + file ops, no model calls); deterministic-first gate must precede all model dispatch.

## [2026-07-02] — v0.28.0 — cost-control, finish lanes, model-routing & subagent profiles
**Release.** Bumps v0.27.0 → v0.28.0. Adds cost-control / context-budget / model-routing /
finish-lane infrastructure so renmark stays cost-aware in long agentic sessions — and lays
the reusable groundwork for a future Agency Mode (queued, not built).
**Request:** Add cost-control, context-budget, model-routing, and finish-lane infrastructure
(prerequisite for Agency Mode); plus an owner addendum for specialized subagent profiles.
**Built:**
- `renmark/finish_lanes.py` — declarative finish lanes (quick / release / self-update / full),
  each stating merges/releases/packages/updates_wsl/cleans_worktrees/verification/cost;
  `recommend_lane` (self-update when the repo IS renmark), `resolve_lane` (menu-alias aware),
  `is_renmark_repo`, `lane_table`, `describe_lane`.
- `renmark/cost.py` — reusable `estimate_cost` / `cost_band` + `requires_escalation`
  (Opus/Fable only when justified); `CostPreview.roles` reports subagent role/profile.
- `renmark/state/skills.py::context_budget_hint` — absolute 100k/120k/150k tiers
  (additive; existing 60/80% cross-domain logic unchanged).
- `renmark/subagent_profiles.py` — 8 specialized roles + general-purpose fallback
  (mission/targets/output/stop/tier/verification/context_scope); `resolve_profile`
  (fallback-only). `SubagentInput.role` flows into the serialized dispatch packet;
  `memory.append_routing(role=...)` logs the role.
- `plugin/skills/finish/SKILL.md` — wired to lane selection + per-lane cost, gated WSL
  install/verify and worktree cleanup for self-update/full; every existing capability preserved.
- `_shared/` fragments: model-routing, subagent-budget, finish-lanes, cost-preview,
  subagent-profiles; mirrored CLAUDE.md/AGENTS.md rule blocks; help + routing.md updates.
- Agency Mode queued: `.renmark/specs/2026-07-02-agency-mode.request.md`.
**Files changed:** finish_lanes.py, cost.py, subagent_profiles.py, dispatch.py, memory.py,
state/skills.py, finish/SKILL.md, help/SKILL.md, 5 `_shared/*.md`, CLAUDE.md, AGENTS.md,
routing.md, 4 new test modules.
**Verification:** 1277 passed / 28 skipped; renmark.lint OK; Codex full review (5 findings, all fixed).
**Do not change:** the self-update finish workflow (merge → release → zip → WSL install →
verify installed CLI/plugin → clean worktree → document) must stay intact; quick lane must
never *skip* verification (only the release ceremony); Opus/Fable stay escalation-only.

## [2026-07-02] — profiles tests (Task 10)
**Request:** Add deterministic coverage for subagent profiles, role propagation, routing persistence, and cost-preview role exposure in `tests/test_subagent_profiles.py`.
**Built:**
- New `tests/test_subagent_profiles.py` covering `PROFILES` field completeness plus specialized `model_tier` assertions for the non-fallback roles called out by the spec.
- Verifies `resolve_profile` maps test targets to `test-writer`, markdown targets to `docs-editor`, core code targets to `code-implementer`, and unmatched targets to `general-purpose`.
- Verifies `build_subagent_input` populates `role`, `memory.append_routing(..., role=...)` persists the role string, and `estimate_cost` returns sorted unique `roles`.
**Files changed:**
- `tests/test_subagent_profiles.py` — new deterministic pytest module
**Do not change:**
- Keep this file hermetic and `tmp_path`-scoped; no network, no non-deterministic time dependence.
- Preserve the fallback contract: unmatched tasks still resolve to `general-purpose`, while cost preview reports distinct roles via `preview.roles`.

## [2026-07-02] — v0.27.0 — agent-turn eval runner (/renmark:eval in-session path)
**Release.** Bumps v0.26.0 → v0.27.0. Ships the deferred SECOND eval-tier injection path from
live-eval-runner: the **in-session, agent-driven** `/renmark:eval` skill. Where v0.26.0's
subprocess runner shells to an external CLI, `/renmark:eval` runs the eval **inside the current
agent session** — the agent composes the prompt, issues a real Agent tool call (session model +
dynamic skill loading + Agent-tool access), and feeds the transcript to the existing capture/judge
path. Proves whether a skill changes behavior inside the active session. NOT a P8-v2 reopen.
**Built:**
- New `/renmark:eval` skill + shim (`disable-model-invocation: true`, opt-in / out-of-CI / no auto-spend).
- `behavior.compose_eval_prompt` + `behavior.capture_from_transcript` (extracted from `capture()`,
  byte-identical) and `judge.compose_judge_prompt` + `judge.parse_judge_verdict` public wrappers.
- Registry wiring (skillmeta build/aux class 3, lifecycle IMPLEMENTED_SKILLS/AUX_SKILLS).
**Verified:** full suite 1257 passed / 28 skipped; `renmark.audit --quick` clean; ruff+mypy clean.
Codereview (codex): spec under-built + 2 Major + 1 Minor (skill prose / test completeness; code paths clean), all fixed + regression-tested.
**Do not change:**
- Subprocess runner (`eval_runner.py`), the deterministic tier, dynamic skill loading, mode,
  Codex routing, and the dispatch-packet schema are all UNTOUCHED.
- `/renmark:eval` stays `disable-model-invocation: true`; the deterministic tier is the CI-safe default.

## [2026-07-02] — agent-turn eval runner (/renmark:eval, in-session eval path)
**Request:** Add the deferred in-session eval path (the agent drives the eval turn) as a new /renmark:eval skill.
**Built:**
- New agent-driven `/renmark:eval` skill (plugin/skills/eval/SKILL.md + plugin/commands/eval.md): the current agent composes the eval prompt, issues a real in-session Agent tool call, and feeds the transcript to the existing capture/judge path. disable-model-invocation: true.
- `behavior.compose_eval_prompt` + `behavior.capture_from_transcript` extracted from `capture()` (behavior-preserving); `judge.compose_judge_prompt` + `judge.parse_judge_verdict` public wrappers.
- Registered eval in skillmeta.SKILLS (build/aux, class 3) + lifecycle IMPLEMENTED_SKILLS/AUX_SKILLS.
**Verified:** tests/test_eval_agent_turn.py (6) + behavior/judge suites green; renmark.audit --quick clean.
**Do not change:**
- Subprocess runner (eval_runner.py), the deterministic tier, dynamic skill loading, mode, Codex routing, and the dispatch-packet schema are all UNTOUCHED.
- /renmark:eval stays opt-in (disable-model-invocation: true), out-of-CI, no auto token spend.

## [2026-07-02] — v0.26.0 — live-eval-runner (P8 eval-tier execution bridge)
**Release.** Bumps v0.25.0 → v0.26.0. Wires the deferred P8 **eval-tier live runner** so `renmark-execute --behavior --accept/--judge` can run real model trajectories when explicitly configured — the missing execution bridge for the mission's behavioral-proof acceptance criterion (NOT a P8-v2 reopen).
**Built:**
- New `renmark/providers/eval_runner.py` — pluggable `EvalRunner` seam + shipped subprocess-command runner (`build_subprocess_runner`: `shlex.split` + `shell=False`, prompt on stdin → stdout; uniformly raises `EvalRunnerError` on unparseable/empty cmd, not-on-PATH, any launch `OSError`, non-zero exit, timeout). Agent-turn runner left as a documented seam.
- `renmark/config.py` — `eval_runner_cmd` accessor (`RENMARK_EVAL_RUNNER_CMD` env > `.renmark` config key > `None`; both stripped, blank = unset) + `eval_runner_source`, via shared `_config_eval_runner_cmd`.
- `renmark/behavior.py` — `build_subagent_runner` delegates to `eval_runner.resolve_eval_runner`; returns the configured runner or raises `LiveRunnerUnavailable` when unconfigured. Deterministic tier untouched.
- Docs: P8 tier note refreshed in CLAUDE.md/AGENTS.md (byte-identical). Tests: `tests/test_eval_runner.py` (12).
**Verified:** smoke 7/7; full suite 1245 passed / 28 skipped; ruff + mypy clean. Codereview: 3 Major + 1 Minor found across 3 codex passes, all fixed + regression-tested.
**Do not change:**
- Default MUST stay unavailable / CI-safe / no auto token spend — unconfigured `build_subagent_runner` raises `LiveRunnerUnavailable`.
- Do not touch the deterministic tier or the dispatch-packet schema; keep `shell=False` on the subprocess runner.

## [2026-07-02] — eval-runner seam tests (Task 4)
**Request:** Add focused coverage for the eval-runner seam and behavior-layer delegation in `tests/test_eval_runner.py`.
**Built:**
- New `tests/test_eval_runner.py` covers env/config/default precedence for `config.eval_runner_cmd`.
- Verifies the subprocess runner path with a real `cat` stdin→stdout round-trip and failure modes for blank, missing, and non-zero commands via `EvalRunnerError`.
- Covers `resolve_eval_runner` returning `None` when unconfigured and a working callable when `RENMARK_EVAL_RUNNER_CMD` is set.
- Covers `behavior.build_subagent_runner` raising `LiveRunnerUnavailable` when unconfigured and delegating successfully into `behavior.capture` when configured, including snapshot write assertions.
**Files changed:**
- `tests/test_eval_runner.py` — new pytest module with artifact docstring + seam/delegation coverage
**Do not change:**
- Keep these tests hermetic: env var cleared per test, temp repo only, no network.
- Preserve the real subprocess seam coverage with `cat`; do not replace it with a pure mock.

## [2026-07-01] — v0.25.0 — true dynamic skill loading (AC5 / REQ-20)
**Release.** Bumps v0.24.0 → v0.25.0. Ships the second net-new slice of the agentic-engineering harness mission: **true dynamic skill loading** with a codified context taxonomy, wired into the production dispatch path.
- New `renmark/context.py` (stdlib-only) — a four-way context taxonomy (`ContextKind`: STATIC/DYNAMIC/MEMORY/TASK_LOCAL) + `TAXONOMY`; `classify_path` (segment-aware); metadata-upfront helpers (`skill_metadata`/`all_skill_metadata`/`fragment_names`, reuse `skillmeta.SKILLS`, never read bodies); on-demand loaders (`skill_pointer`/`fragment_pointer` refs; `load_skill_body`/`load_fragment` with traversal guard); `upfront_kinds_for_skill` (dynamic bodies never pre-loaded); `assert_metadata_only` guardrail.
- `renmark/dispatch.py` — the production task-local packet (`SubagentInput`/`build_subagent_input`) now carries `required_skills` as METADATA refs (name + pointer, guarded), never full skill bodies. Additive + backward-compatible; function-local imports avoid cycles.
- New `plugin/skills/_shared/context-taxonomy.md` fragment; mirrored "Context taxonomy" rule block in CLAUDE.md/AGENTS.md; PRD REQ-20.
- `tests/test_context.py` (20 tests) incl. the metadata-not-body integration proof; isolation contract test updated to sanction `required_skills`.

Full unit suite **1233 passed, 28 skipped**; ruff + mypy clean; 7/7 version locations at v0.25.0. Codereview clean (Spec: compliant; 0 Critical, 2 Major + 2 Minor all resolved). Pre-existing out-of-scope failure noted: `test_plugin_has_required_skill_files` (stale roster, also fails on origin/main). See per-change entries below.

## [2026-07-01] — codereview fixes for dynamic-skill-loading (AC5)
**Request:** Resolve the full codex review findings before finish (0 Critical, 2 Major, 2 Minor; Spec: compliant).
**Built:**
- Major — updated the isolation contract test `test_subagent_input_does_not_carry_orchestrator_context` to sanction `required_skills` as an intentional bounded field (it was SKIPPED without `RENMARK_SMOKE=1`, hiding that `to_dict()`'s new key broke the "only these fields" assertion). Now passes under `RENMARK_SMOKE=1`.
- Major — `renmark/context.py`: `load_skill_body`/`load_fragment` now reject traversal-style `name` (separators / `..` / empty / NUL) via `_reject_unsafe_name` before reading.
- Minor — `classify_path` is now segment-aware (`_has_contiguous` over path parts), so lookalikes like `xplugin/skills/foo/SKILL.md` no longer falsely classify as DYNAMIC.
- Minor — `assert_metadata_only` now requires a slug-shaped reference (`_SKILL_REF_RE`), rejecting short prose (spaces) that previously slipped past the newline/fence/length checks.
**Files changed:**
- `renmark/context.py` — traversal guard, segment-aware classify_path, stricter guardrail
- `tests/integration/test_dispatch_isolation_e2e.py` — allow the sanctioned `required_skills` field
**Do not change:**
- `required_skills` is a sanctioned bounded field (metadata only, guarded); the contract test's `allowed` set must include it.
- Loaders MUST reject traversal names; `classify_path` MUST use segment matching, not substrings.
- NOTE (pre-existing, out of scope): `test_plugin_has_required_skill_files` fails on origin/main too — stale pinned roster missing `guide`/`scan`. Not touched here.

## [2026-07-01] — context taxonomy rule block, mirrored (AC5 wave 3, tasks 5 & 6)
**Request:** Document the four-way context taxonomy + dynamic-loading contract in the project rule files (PRD REQ-20).
**Built:** Added a byte-identical "## Context taxonomy — static / dynamic / memory / task-local" rule block to both `CLAUDE.md` and `AGENTS.md` (after the context-hygiene block): the four kinds, metadata-upfront/bodies-on-demand via `renmark/context.py`, and the dispatch-packet metadata-only contract; cites the shared fragment. Committed together to honor the mirror rule.
**Files changed:**
- `CLAUDE.md` — new context-taxonomy rule block
- `AGENTS.md` — byte-identical mirror
**Do not change:**
- The two blocks MUST stay byte-identical (mirror rule); dynamic bodies are never pre-loaded; dispatch packets carry required-skill metadata only.

## [2026-07-01] — tests for context module + dispatch integration (AC5 wave 3, task 4)
**Request:** Prove AC5 behavior — the taxonomy/loader API and that the dispatch packet uses skill metadata without loading full bodies (PRD REQ-20).
**Built:** New `tests/test_context.py` (20 cases) covering `ContextKind`/`TAXONOMY`, `classify_path`, metadata-upfront helpers (no body), body-on-demand loaders, `upfront_kinds_for_skill` (DYNAMIC/TASK_LOCAL excluded), the `assert_metadata_only` guardrail, and the load-bearing integration test: `build_subagent_input(required_skills=["plan"])` carries plan's metadata + pointer while the real SKILL.md body phrase is asserted ABSENT from the packet JSON.
**Files changed:**
- `tests/test_context.py` — new test module (codex-generated; orchestrator added one `-> None` annotation for convention)
**Do not change:**
- The metadata-not-body integration assertion is the behavioral proof of AC5 — keep it.

## [2026-07-01] — wire context into the production dispatch packet (AC5 wave 2, task 3)
**Request:** Make AC5 behaviorally real — connect `renmark/context.py` to a real production surface, not just a standalone helper (PRD REQ-20).
**Built:** `renmark/dispatch.py` — `SubagentInput` gained `required_skills: list[str]` (names only); `to_dict()` renders each as a metadata reference `{name, pointer, metadata}` via a function-local `from renmark import context` (never a SKILL.md body); `build_subagent_input` gained a kw-only `required_skills` param and calls `context.assert_metadata_only` at build time. Additive + backward-compatible (12/12 dispatch tests still pass); function-local imports avoid any cycle.
**Files changed:**
- `renmark/dispatch.py` — the production task-local packet now consumes context.py (metadata-upfront, bodies never)
**Do not change:**
- The `context` imports MUST stay function-local (cycle guard); `required_skills` MUST render as metadata refs only (never a body); `build_subagent_input` MUST call `assert_metadata_only` before constructing the packet; no second packet type — `SubagentInput` is the one production dispatch packet.

## [2026-07-01] — context taxonomy + dynamic-loader primitives (AC5 wave 1, task 1)
**Request:** Codify renmark's four-way context taxonomy and metadata-upfront/body-on-demand loading (PRD REQ-20).
**Built:** New stdlib-only `renmark/context.py` — `ContextKind` enum (STATIC/DYNAMIC/MEMORY/TASK_LOCAL); `ContextSource`/`TAXONOMY`; `classify_path`; metadata-upfront helpers `skill_metadata`/`all_skill_metadata`/`fragment_names` (reuse `skillmeta.SKILLS`, never read bodies); on-demand `skill_pointer`/`fragment_pointer` + `load_skill_body`/`load_fragment`; `upfront_kinds_for_skill` (STATIC+MEMORY only); `assert_metadata_only` guardrail. Lazy imports avoid cycles; mypy strict clean.
**Files changed:**
- `renmark/context.py` — new module (the codified taxonomy + dynamic-loader primitives)
**Do not change:**
- `skill_metadata` MUST NOT read/return SKILL.md body text; `upfront_kinds_for_skill` MUST exclude DYNAMIC and TASK_LOCAL (dynamic bodies never pre-loaded); read functions never raise (body loaders raise FileNotFoundError by design).

## [2026-07-01] — shared context-taxonomy fragment (AC5 wave 1, task 2)
**Request:** Give skills a citable single-source doc for the four-way context taxonomy (PRD REQ-20).
**Built:** New `plugin/skills/_shared/context-taxonomy.md` — the four kinds + kind·source·persistence·load-policy table, the metadata-upfront/bodies-on-demand rule, and the dispatch-packet metadata-only contract. Cited by pointer, never inlined.
**Files changed:**
- `plugin/skills/_shared/context-taxonomy.md` — new reference fragment (skipped by `renmark.lint`)
**Do not change:**
- Reference-dir fragment: skills cite it via `${CLAUDE_PLUGIN_ROOT}/skills/_shared/context-taxonomy.md`, never re-inline it (skillgen doc-slimming guard).

## [2026-07-01] — PRD updated (REQ-20, dynamic skill loading / AC5)
**Request:** Capture the deferred harness-mission acceptance criterion AC5 (true dynamic skill loading) as a PRD requirement before building it on branch `feature/dynamic-skill-loading`.
**Built:** Reconciled the Requirements section of PRD.md; added REQ-20 (four-way context taxonomy — static/dynamic/memory/task-local — with skill & `_shared/` fragment metadata upfront and bodies on demand; subagent packets carry task-local + required-skill metadata only). Added a 2026-07-01 revision note; bumped `last_reviewed`.
**Files changed:**
- `PRD.md` — new REQ-20 operationalizing the REQ-5 context-hygiene pillar; revision note; `last_reviewed` → 2026-07-01
**Do not change:**
- PRD.md is human-owned. REQ-20 was proposed by the feature drift gate and explicitly approved by the owner on 2026-07-01; do not re-open its scope without a new `/renmark:prd` gate.

## [2026-07-01] — v0.24.0 — harness operating modes (Conductor/Orchestrator MVP)
**Release.** Bumps v0.23.0 → v0.24.0. Ships the first slice of the agentic-engineering harness mission: an explicit **Conductor vs Orchestrator** operating mode.
- New `renmark/mode.py` — persisted mode (`.renmark/state/mode.json`): `read_mode`/`set_mode`/`clear_mode`/`default_mode_for_skill` + `mode_state_path`; reads never raise, writes are atomic and surface real failures.
- `skill_preamble` emits a mode-specific directive when set, or a choose-mode prompt for entry skills when unset (ask-once, smart per-skill default; additive after existing tiers, degrades gracefully).
- CLI `renmark-execute --set-mode {conductor,orchestrator}` / `--get-mode` / `--clear-mode` (invalid value exits 2; write failure exits 1, no false success).
- Harness mission framing in `/renmark:help` + an "Operating modes" rule block mirrored in CLAUDE.md/AGENTS.md; short mode blocks in the pipeline skills.
- Deferred to a follow-up: true dynamic skill loading (AC5). No hard dispatch guards (guidance only).

Full suite **1213 passed, 28 skipped**; ruff + mypy clean; behavior tier 3/3; version drift clean (7/7 at v0.24.0). Codereview: spec-compliant, 0 open findings. See the per-change entries below.

## [2026-07-01] — harness-modes codereview fixes (1 Major + 2 Minor)
**Request:** Fix the codex review findings on the harness-modes diff.
**Built:**
- Major — `set_mode`/`clear_mode` no longer swallow filesystem errors: `set_mode` lets OSError propagate (atomic temp-write + `os.replace()`), `clear_mode` surfaces genuine delete failures but stays idempotent when the file is absent. The CLI `--set-mode`/`--clear-mode` now catch OSError, print to stderr, and exit 1 — no more false success. `read_mode` still never raises; invalid value still argparse-exit-2.
- Minor — added `renmark.mode.mode_state_path(repo)` + `MODE_REL` constant; the CLI sources every user-facing path string (help + success + error) from it, so `.renmark/state/mode.json` can't drift.
- Minor — mode writes are now atomic (temp file + `os.replace()`), closing the partial-read → transient-None window.
**Files changed:** `renmark/mode.py`, `renmark/cli/_engine.py`, `tests/test_mode.py`, `tests/test_mode_cli.py`.
**Verification:** full suite 1213 passed, 28 skipped; mypy + ruff clean; behavior tier 3/3; write-failure repro confirms CLI exit 1 (no false success).
**Do not change:** `read_mode` must never raise; the write mutators MUST surface real OSError (never swallow) while `clear_mode` stays idempotent on an absent file; all user-facing path strings source from `mode_state_path`/`MODE_REL`.

## [2026-07-01] — harness-modes waves 1–2: preamble/CLI wiring + tests
**Request:** Finish the harness operating-modes MVP — wire mode into skill_preamble + CLI, and prove behavior with tests.
**Built:**
- `renmark/lifecycle.py` — `skill_preamble` now emits a mode directive line (Conductor/Orchestrator) when set, or a choose-mode prompt for entry skills when unset; appended after existing tiers (record-before-check ordering preserved); mode logic wrapped in try/except (graceful degrade).
- `renmark/cli/_engine.py` — `--set-mode {conductor,orchestrator}` / `--get-mode` / `--clear-mode` (mirrors `--set-proactive`; invalid value exits 2, state unchanged).
- `CLAUDE.md` + `AGENTS.md` — mirrored "Operating modes" rule block.
- Tests: `tests/test_mode.py` (19), mode cases in `tests/test_lifecycle.py` (+5, incl. by-mode diff + graceful degrade), `tests/test_mode_cli.py` (6), `tests/behavioral/mode.behavior.json` (deterministic tier: unset-entry preamble emits the choose-mode prompt).
**Files changed:** `renmark/lifecycle.py`, `renmark/cli/_engine.py`, `CLAUDE.md`, `AGENTS.md`, `tests/test_mode.py`, `tests/test_lifecycle.py`, `tests/test_mode_cli.py`, `tests/behavioral/mode.behavior.json`.
**Verification:** full suite 1205 passed, 28 skipped; ruff clean; mypy clean on renmark/mode.py; behavior tier 3/3.
**Do not change:** the mode directive is additive-only in skill_preamble (never reorder the existing record-before-check tiers); behavior adapter reads real-repo mode (case asserts the unset-mode choose-prompt, not a by-mode diff — the diff is covered by test_lifecycle unit tests).
**Known (deferrable):** CLI confirmation message prints `.renmark/mode.json` instead of `.renmark/state/mode.json` (cosmetic; the write is correct) — see `.renmark/memory/bugs.md`.

## [2026-07-01] — harness-modes wave 0: mode.py + skill/help framing
**Request:** Build wave 0 of the harness operating-modes MVP (foundation + doc framing).
**Built:**
- `renmark/mode.py` — persisted operating-mode state (`.renmark/state/mode.json`): `read_mode`/`set_mode`(ValueError on bad value)/`clear_mode`/`default_mode_for_skill`; corrupt/missing → None, never raises.
- `plugin/skills/help/SKILL.md` — reframed to the agentic-engineering / vibe-coding harness mission; documents Conductor/Orchestrator modes, context hygiene, subagent discipline, memory/docs, verification.
- `plugin/skills/{feature,debug,orchestrate,start}/SKILL.md` — short "## Operating mode" behavior blocks (smart per-skill defaults).
**Files changed:** `renmark/mode.py`, `plugin/skills/help/SKILL.md`, `plugin/skills/{feature,debug,orchestrate,start}/SKILL.md`.
**Do not change:** mode state lives in gitignored `.renmark/state/mode.json`; `set_mode` MUST raise on values other than conductor/orchestrator; readers never raise on corrupt input.

## [2026-07-01] — project scope: harness-operating-modes (Conductor/Orchestrator MVP)
**Scope contract (brainstorm).** Spec: `.renmark/specs/2026-07-01-harness-operating-modes.spec.md`.
- **Stack:** unchanged — Python ≥3.10 + Claude Code plugin (markdown skills/commands). New module `renmark/mode.py`; edits to `lifecycle.skill_preamble`, `renmark-execute` CLI, pipeline SKILL.md blocks, help, CLAUDE.md/AGENTS.md.
- **Deployment:** unchanged — plugin package; mode state at `.renmark/state/mode.json` (gitignored runtime).
- **MVP boundary:** Conductor/Orchestrator mode selection (ask-once, persisted, smart per-skill default, override via `--set-mode`) + mode-conditioned `skill_preamble` line + short SKILL.md behavior blocks + help/rule-block reframing + tests (unit + behavior tier).
- **Out of scope:** true dynamic skill loading (deferred follow-up); hard dispatch guards; rework of context-hygiene / memory / verification / Codex routing (already exist).
- **Do not change:** the mode ask must stay ask-once (not a per-entry gate) so auto-routing keeps working; no programmatic subagent blocking.

## [2026-07-01] — v0.23.0 — P8 behavioral eval tier + P7 skill-consistency lint
**Release.** Bumps v0.22.0 → v0.23.0. Ships two external-skills-study items:
- **P8-v2** — behavioral skill testing, tests-vs-evals split. `renmark-execute --behavior` runs the **deterministic tier** (renmark's real behavior-shaping functions asserted live, CI-safe, zero tokens); the **eval/judge tier** (`--accept`/`--judge`) is honestly HOST-pending (`build_subagent_runner` raises rather than faking transcripts — a pure-Python process can't issue the model call). Reviewed clean (0 Critical/Major after fixes).
- **P7** — `skillgen --check`, a read-only skill-consistency lint (frontmatter discipline + doc-slimming guard) wired as precommit gate 5/7; central `skillmeta.py` registry. Clean on all 28 skills.

Full suite **1175 passed, 28 skipped**; ruff + mypy + skillgen lint clean; version drift clean (7/7 at v0.23.0). See the per-feature entries below.

## [2026-07-01] — P8-v2 codereview fixes (4 Major + 1 Minor)
**Request:** Fix the codex review findings on the P8-v2 diff (spec was under-built: eval tier never ran a real trajectory).
**Built:**
- Major 1 — `build_subagent_runner` now raises `LiveRunnerUnavailable` instead of returning the dispatch prompt text; a pure-Python process cannot issue the model call, so the eval runner is HOST-injected. CLI `--judge` degrades to the deterministic tier with a note; `--accept` reports unavailable and exits non-zero. No more prompt-as-golden.
- Major 2 — `_case_from_dict` rejects missing/empty `deterministic.assertions` (was a vacuous PASS).
- Major 3 — narrowed the `plan_lint` adapter docstring: it is a declared-policy scaffolding guard, NOT a live read-only proof (that's the eval tier).
- Minor 1 — roadmap reference case gains positive read-only assertions (`isolated subagent`, `reads only bounded summaries`).
- Major 4 — tests cover runner-unavailable, `capture()` with an injected stub runner, and missing/empty-assertion rejection.
**Files changed:** `renmark/behavior.py`, `renmark/cli/_engine.py`, `tests/test_behavior.py`, `tests/behavioral/roadmap.behavior.json`.
**Verification:** full suite 972 passed, 28 skipped; ruff + mypy clean.
**Do not change:** the eval-tier live runner is HOST-injected — `build_subagent_runner` MUST raise until a real `str->str` runner is wired; never return prompt text as a transcript. Deterministic cases MUST carry a non-empty assertion set.

## [2026-07-01] — P8-v2 build waves 1–2 (behavior tiers + CLI + cases + docs)
**Request:** Implement the P8-v2 plan (`.renmark/plans/2026-07-01-p8-behavioral-skill-testing-v2.plan.md`).
**Built:**
- `renmark/behavior.py` (opus) — deterministic tier runs real renmark functions via explicit allow-list (`lifecycle.next_steps`, `skill_preamble`, `plan_lint`), asserting genuine current output; golden-echo path removed (Major 1 closed). Eval/judge tier gated behind an explicit live runner.
- `renmark/cli/_engine.py` (sonnet) — `--behavior` runs the deterministic tier with no runner (zero-spend); `--accept` records eval goldens via `build_subagent_runner`+`capture`; `--judge` passes `judge=True`+live runner; `--accept`/`--judge` require `--behavior`.
- `tests/behavioral/{next_steps_menu,roadmap}.behavior.json` (haiku) — v2 two-block cases; assertions restored to full contract force, split deterministic vs eval; both PASS live.
- `CLAUDE.md` + `AGENTS.md` (haiku, mirrored) — honest two-tier framing.
**Orchestrator fixes (verified independently):** `golden_ref` must be a bare stem (no path separator — `_validate_ref` prepends `snapshots/`); the recommended-first `matches:` assertion needs inline `(?m)` (`_assert_matches` uses `re.search` without `re.M`).
**Do not change:** default `--behavior`/`run()` constructs NO live runner (network/token-free); the deterministic tier reads no snapshot; eval/judge tier never auto-spends. `behavior.py` `_validate_ref` rejects path separators in refs; `_assert_matches` is single-line unless the pattern sets `(?m)`.

## [2026-07-01] — P8-v2 redesign (brainstorm) — tests-vs-evals split
**Request:** Re-brainstorm P8 after two code reviews found it under-built (Major 1 fatal: deterministic "replay" collapsed to asserting a golden against itself; un-bootstrappable `--accept`; weakened assertions).
**Decided (opus synthesis lane):** split into two honestly-labelled tiers per the Google "New SDLC" tests-vs-evals doctrine. **Deterministic tier = a TEST** — runs renmark's *real* behavior-shaping functions (`lifecycle.next_steps`, `skill_preamble`, `plan_lint`) on live inputs and asserts genuine current output (recomputed every run → fixes Major 1; needs no snapshot → fixes bootstrap; CI-safe). **Eval tier = the behavioral PROOF** — live LLM-judge over a real model trajectory, wired to a `str→str` runner reachable only under `--accept`/`--judge`, out of CI. Reference-case assertions restored to full force, split across the two tiers.
**Files changed:** `.renmark/specs/2026-07-01-p8-behavioral-skill-testing.spec.md` (v2 revision), lifecycle → `brainstorm-complete`.
**Do not change:** docs/command names must keep the split explicit — green `--behavior` (deterministic tier) is a scaffolding/regression guard, NOT proof the skill works; the load-bearing behavioral proof lives only in the eval tier. The eval/judge tier never auto-spends without explicit `--accept`/`--judge`.

## [2026-07-01] — rewrite tests/test_behavior.py for assertion-based replay
**Request:** Rewrite `tests/test_behavior.py` to match the redesigned `renmark/behavior.py` contract.
**Built:** Replaced the old golden-vs-baseline tests with artifact-shaped deterministic coverage for case loading, assertion-based replay PASS/FAIL/ERROR outcomes, judge gating, unsafe ref rejection, and the assertion mini-format using inline `{transcript, inputs}` snapshots.
**Files changed:** `tests/test_behavior.py`
**Do not change:** keep these tests deterministic and snapshot-driven; missing snapshots or empty `inputs` must stay `ERROR`, and judge escalation must remain opt-in and skipped for `ERROR` results.

## [2026-07-01] — P8 behavioral skill testing + LLM-judge tier (build complete)
**Request:** Build P8 (the last queued external-skills-study item) toward v0.23.0 — a tier that proves a skill *changes agent behavior*, not just that it lints.
**Built (8 tasks, all verified):**
- `renmark/judge.py` — escalation-only LLM-as-judge (`judge_behavior` → `Verdict`); defensive parse (bad/timeout/garbage → `validation_status=unvalidated`, never a silent pass); `JUDGE_EST_COST_USD=0.15`; no import side effects.
- `renmark/behavior.py` — harness on `shadow.py`'s record-replay: `load_cases`/`replay`/`capture`/`run`. Deterministic replay is pure snapshot I/O (no network/tokens); missing snapshot → ERROR ("run --accept first"); judge invoked only when `judge=True`.
- `renmark/cli/_engine.py` — `--behavior` (deterministic replay, exit≠0 on FAIL/ERROR), `--behavior --accept` (record snapshots), `--behavior --judge` (escalate). OFFER line (~$0.15) on deterministic FAIL only; never auto-spends; `--accept`/`--judge` require `--behavior`.
- `tests/behavioral/{roadmap,next_steps_menu}.behavior.json` — 2 reference cases (roadmap read-only/zero-LLM; next-steps-menu recommended-first).
- `tests/test_behavior.py` (6) + `tests/test_judge.py` (5) — codex-authored; assert judge never auto-invoked, no-silent-pass, ERROR on missing snapshot.
- Behavioral tier documented in `CLAUDE.md` + `AGENTS.md` (mirrored).
**Verification:** all 8 task verifiers pass; ruff + mypy clean; full suite **962 passed, 28 skipped** (+11 new, no regressions).
**Do not change:** the deterministic tier stays network-free / token-free in CI; the judge tier never auto-triggers without explicit `--judge` opt-in; `.behavior.json` cases stay snapshot-driven (no live capture in CI). Golden snapshots for the 2 reference cases are captured via `renmark-execute --behavior --accept` (a deliberate live step, not run yet).

## [2026-07-01] — behavior harness unit tests
**Request:** Add deterministic unit coverage for `renmark/behavior.py` with inline temp snapshots and mocked judge/subagent paths.
**Built:** Added `tests/test_behavior.py` as a renmark artifact/test module covering case loading, replay PASS/FAIL/ERROR behavior, and `run()` judge gating.
**Files changed:** `tests/test_behavior.py`.
**Do not change:** keep these tests snapshot-driven and deterministic; they must not require live capture, network access, or automatic judge escalation.

## [2026-07-01] — project scope: p8-behavioral-skill-testing
**Scope contract (brainstorm).** Feature spec: `.renmark/specs/2026-07-01-p8-behavioral-skill-testing.spec.md`.
- **Stack:** unchanged — Python ≥3.10 renmark runtime + Claude Code plugin (no new stack).
- **Deployment:** in-repo tooling; ships in v0.23.0 alongside the P7 consistency lint (branch `worktree-p7-skill-templates`, merge-only).
- **MVP boundary:** deterministic behavioral tier (recorded golden transcripts replayed + diffed in CI, reusing `renmark/shadow.py`) covering **2 reference skills** (roadmap read-only contract; the next-steps-menu contract); LLM-as-judge tier (`renmark/judge.py`) implemented but **escalation-only** — offered on deterministic failure, opt-in to run (~$0.15), never silent.
- **Out of scope:** behavioral coverage of all ~30 skills; the P7 `.tmpl`→SKILL.md generator (deliberately dropped — shared blocks already single-sourced); changes to the structure audit; any auto-spend on the judge tier.
- **Do not change:** the deterministic tier stays network-free / token-free in CI; the judge tier never auto-triggers without explicit opt-in.
## [2026-06-29] — P7 skill-consistency lint (pivoted from generator)
**Request:** Build P7 (template-generated SKILL.md).
**Pivot (mid-build, owner-approved):** the premise — duplicated boilerplate to DRY via a generator — proved FALSE. Doc-slimming (ADR-027/028) already single-sourced all shared boilerplate into `_shared/*` via pointer citations; the 28 skills carry no byte-identical duplicated block. Generating managed blocks would *re-inline* what doc-slimming removed. So generation + the 28-file migration were DROPPED.
**Built:**
- `renmark/skillmeta.py` — central per-skill metadata registry (28 skills: domain, next_steps_class, cites, has_handoff, disable_model_invocation); `lifecycle.domain_for_skill`/`DOMAIN_BY_SKILL` now derive from it (single source).
- `renmark/init.py` — extracted reusable `merge_marked_block`/`count_begin_markers` marker primitive (init behavior unchanged; tests green).
- `renmark/skillgen.py` — **pure consistency lint** (`--check`): frontmatter discipline (trigger-only description + `disable-model-invocation` == registry) + doc-slimming guard (flags any skill that re-inlines a `_shared` blockquote verbatim). Clean on all 28.
- `tools/precommit.sh` — `skillgen --check` wired as gate 5/7.
- Tests: `test_skillmeta.py` (registry vs disk), `test_skillgen.py` (lint categories). Full suite 1148 passed.
**Files changed:** `renmark/skillmeta.py`, `renmark/skillgen.py`, `renmark/init.py`, `renmark/lifecycle.py`, `tools/precommit.sh`, `tests/test_skillmeta.py`, `tests/test_skillgen.py`.
**Do not change:** skillgen is READ-ONLY (never writes SKILL.md / frontmatter) — re-introducing generation would reverse doc-slimming; the doc-slimming guard exists to prevent re-inlining single-sourced blockquotes.

## [2026-06-29] — project scope: P7 template-generated SKILL.md (spec)
**Request:** Brainstorm P7 — a managed-block generator so the cross-cutting SKILL.md boilerplate (Step-0 preamble + shared-contract citations) regenerates from one source across all 28 skills instead of 28 manual edits.
**Scope (confirmed):**
- **Stack:** unchanged — Python ≥3.10 stdlib-only; Markdown skills.
- **Deployment:** the renmark plugin itself (P7 targets ≥v0.23.0, with P8).
- **MVP boundary:** (1) managed-block model (marker-merge, reuse init.py); (2) generator owns Step-0 + reasoning-contract/next-steps/handoff-menu citations, pulled from `_shared`; frontmatter hand-authored + lint-checked; (3) central registry `renmark/skillmeta.py` extending `lifecycle.DOMAIN_BY_SKILL`; (4) `--check` lint fails on block-drift or frontmatter-discipline violation.
- **Out of scope:** full-file generation; generating frontmatter/descriptions/bodies; PRD change (internal tooling — PRD-drift benign); P8.
**Files changed:** `.renmark/specs/2026-06-29-p7-skill-templates.spec.md` (new); CHANGELOG + decisions.md.
**Do not change:** the generator MUST NEVER write frontmatter — v0.20.0 trigger-only descriptions + `disable-model-invocation` are load-bearing; lint validates, never auto-fixes.

## [2026-06-26] — v0.22.0 — P10 headless / spawned-session contract
**Release.** Ships the P10 headless-session contract (detection, doctrine, lifecycle halt path, `renmark/headless.py` `resolve_gate`/`render_return`, `--set-headless` CLI, and dangerous-gate wiring in finish/plan/orchestrate/prd) **plus** the previously-unreleased batch on `main` (P5/P4/P12/P11/P6/P9). Full suite 951 passed; version drift clean; 3 codex review passes. See the per-feature entries below for detail. P7/P8 remain queued for ≥v0.23.0.

## [2026-06-26] — P10 wire resolve_gate into dangerous-gate skills
**Request:** Complete the "under-built" follow-up — wire the runtime helper into the skills that gate dangerous actions.
**Scope (per gate-point audit):** NOT all 28 skills — the 22 safe-gate skills already inherit headless behavior via the shared menu files. The real surface is 5 dangerous-gate callsites in 4 skills.
**Built:**
- `finish/SKILL.md` (merge/release), `plan/SKILL.md` (dispatch — standalone path only), `orchestrate/SKILL.md` (cost approval), `prd/SKILL.md` (create + update) — each consults `renmark.headless.resolve_gate(..., kind="dangerous")` before its picker: headless emits `needs_input` JSON + `render_return` prose and STOPS; interactive renders the existing menu unchanged. Frontmatter untouched (v0.20.0 trigger-only preserved).
- `tests/test_dangerous_gate_wiring.py` — guard test asserting each of the 4 skills references `resolve_gate` + `kind="dangerous"` (prd ≥2). Full suite 951 passed.
**Files changed:** `finish/plan/orchestrate/prd` SKILL.md, `tests/test_dangerous_gate_wiring.py`.
**Do not change:** safe gates stay inherited via the shared files (do not add per-skill wiring to the 22 safe-only skills); the interactive (human-present) path at each gate is unchanged.

## [2026-06-26] — P10 review fixes + runtime gate-resolution helper
**Request:** Address the codex review (2 Major + 1 Minor) and the "under-built" verdict by adding the runtime core.
**Built:**
- Fixed review Major #1 (`config.py`): config `"headless"` honored only when a real bool; non-bool → default False / source `default` (was `bool(val)` coercion → fail-dangerous).
- Fixed review Major #2 + re-review residual (`lifecycle.py`): `halt_for_human_review` arms the gate before the artifact write and suppresses `write_lifecycle` AND `mkdir` failures — now provably never raises (returns `needs_input` even on forced mkdir/lifecycle failure). Returns repo-relative `artifacts[]` (Minor #3).
- Added `renmark/headless.py` — `resolve_gate(repo, gate, kind, recommended, tool_available, …)` bridges primitives to skills (interactive when human present, auto-pick on safe gates, halt on dangerous/uncertain); `render_return` emits the classifier prose line (re-review Minor: now descriptive, not the internal token). +12 tests.
- Documented the helper as the canonical gate call in `headless-contract.md`.
**Routing:** code review + re-review ran on codex (read-only sandbox). Full suite **946 passed, 28 skipped**.
**Do not change (ADR-035):** `resolve_gate` returns interactive when `tool_available is None` (assume human present) — halting only on positive-headless. Do NOT make `None` halt dangerous gates; it breaks live merge approval. Per-skill adoption of `resolve_gate` across all 28 SKILL.md is a tracked follow-up.

## [2026-06-26] — P10 wave 2: menu files honor contract + tests + CLI flag
**Request:** Wire the headless contract into the shared menu files, add tests, and expose a `--set-headless` CLI flag.
**Built:**
- `plugin/skills/_shared/handoff-menu.md`, `next-steps.md`, `scope-contract.md` — each now references `headless-contract.md` and honors it: headless suppresses `AskUserQuestion`, auto-picks `(Recommended)` on safe gates, halts on dangerous gates (reinforcing REQ-12).
- `renmark/cli/_engine.py` — `--set-headless true|false` mirroring `--set-proactive` (calls `config.set_headless`).
- `tests/test_config.py` — +24 headless detection cases (env tri-state, `=0`-overrides-config, fall-through, default, key preservation); 36 total.
- `tests/test_lifecycle.py` — +3 cases (headless preamble note present/absent, `halt_for_human_review` writes artifact + arms gate + returns `needs_input`); 51 total.
**Routing note:** tasks 2 & 8 (test files) rerouted codex→sonnet — codex verifier sandbox lacked `python3`/`pytest` (exit 127); ledgered in `routing.md`, not silent. Full suite 87 passed, ruff clean.
**Files changed:** the 3 `_shared/*.md`, `renmark/cli/_engine.py`, `tests/test_config.py`, `tests/test_lifecycle.py`.
**Do not change:** the 3 menu files defer to `headless-contract.md` as source of truth — do not duplicate the gate policy into them.

## [2026-06-26] — P10 wave 1: headless detection + contract doctrine + lifecycle halt path
**Request:** Implement the core of the P10 headless contract (detection, the shared doctrine doc, and the dangerous-gate halt path).
**Built:**
- `renmark/config.py` — `is_headless` / `set_headless` / `headless_source`, mirroring the P11 proactive pattern. Precedence: env `RENMARK_HEADLESS` tri-state (`1/true/yes/on`, `0/false/no/off`, else fall-through) > `.renmark/config.json` `"headless"` > default False. Explicit `=0` overrides config. `CLAUDE_JOB_DIR`/`CLAUDECODE` deliberately NOT read.
- `plugin/skills/_shared/headless-contract.md` (new) — single-source doctrine: detection precedence + uncertainty rule, safe/dangerous gate table, JSON return schema + 3 examples + prose vocab, decision-artifact format.
- `renmark/lifecycle.py` — additive headless note in `skill_preamble` (P3 record-before-check ordering preserved) + `halt_for_human_review(repo, gate, *, originating_skill, what)` that writes `.renmark/decisions/<gate>-approval.json`, arms `human_review_required`/`human_review_for`, and returns the `needs_input` envelope.
**Files changed:** `renmark/config.py`, `plugin/skills/_shared/headless-contract.md`, `renmark/lifecycle.py`.
**Do not change:** detection never reads `CLAUDE_JOB_DIR`/`CLAUDECODE`; `=0` overrides config; `skill_preamble` record-before-check ordering is load-bearing (P3); `needs_input` ≠ `failed` for dangerous-gate halts.

## [2026-06-26] — project scope: P10 headless / spawned-session contract (spec)
**Request:** Brainstorm P10 — a formal headless-session contract so renmark behaves when run in background jobs / driven by an outer orchestrator instead of interactively.
**Scope (confirmed):**
- **Stack:** unchanged — Python ≥3.10, stdlib-only runtime (no new deps; `config.py` json pattern). Markdown skills.
- **Deployment:** the renmark plugin itself (combined release ≥v0.22.0 with P7/P8).
- **MVP boundary:** (1) detection precedence `RENMARK_HEADLESS=1` > `=0` > `.renmark/config.json` > tool-availability fallback, never from `CLAUDE_JOB_DIR`/`CLAUDECODE`; (2) safe gates auto-pick recommended, dangerous gates (merge/release/destructive/PRD-approval/over-budget cost) halt + write decision artifact + `human_review_required=true` + return `needs_input`; (3) structured JSON return + one classifier-friendly prose line; (4) uncertain detection → dangerous gates fail safe (halt).
- **Out of scope:** auto-detect from ambient signals; rewriting all 28 SKILL.md (inherited via shared menu files); a daemon/HTTP API; reverse-engineering Claude Code internals as truth; P7/P8 (separate).
**Files changed:** `.renmark/specs/2026-06-26-p10-headless-contract.spec.md` (new); `.renmark/research/2026-06-26-p10-headless-detection.research.md` (new); CHANGELOG + decisions.md.
**Do not change:** the detection precedence and the dangerous-gate list are owner-specified (2026-06-26) — do not relax them in plan/build without re-approval.

## [2026-06-25] — external-skills-study batch P4/P5/P6/P9/P11/P12 (unreleased)
**Request:** Autonomously plan + implement the remaining external-skills-study items (`.renmark/research/2026-06-25-external-skills-study.research.md`). Approved scope: build + merge stages 1–6 (P5, P4, P12, P11, P6, P9), then brainstorm the 3 design-heavy ones (P10, P7, P8). Driven as a staged program via `/renmark:feature` (each stage: implement → verify → independent review → commit).
**Built:**
- **P5** anti-re-dispatch ledger doctrine — rule block (CLAUDE.md/AGENTS.md + templates) + `_cross_check_skip_list()` in `_engine.py`: orphaned task indices (in git log, absent from the live plan) are excluded from the `--resume` skip-list with a warning instead of silently dropped. +8 tests.
- **P4** file-handoff helpers — `renmark-execute --task-brief PLAN N` / `--review-package BASE HEAD` write a uniquely-named file under `.renmark/state/handoffs/` and print ONLY the path (REQ-5 as mechanism). +19 tests. (Fixed a CLI str-vs-int index bug + a silent diff-failure path in review.)
- **P12** feedback-loop-first debug gate — debug step 2 is now a gate: a red-capable repro before hypothesizing; Iron Law + root-cause rule updated.
- **P11** persisted proactivity toggle — `renmark/config.py` (`is_proactive`/`set_proactive`, default on, never raises) + `renmark-execute --set-proactive true|false`; `.renmark/config.json`. +11 tests. **Known limitation (logged in bugs.md):** persists + documents the flag, but runtime enforcement of auto-routing stays doc-level — no per-turn injection yet.
- **P6** two-verdict codereview — spec-compliance (compliant/under-built/over-built) AND code-quality scored separately; `[d] Debug` fires on either.
- **P9** `/renmark:guide` — interactive decision-tree on-ramp routing to the right pipeline (kept separate from the zero-LLM `help`); 27→28 commands.
- Each stage independently verified + reviewed (codex usage-limited → reviews rerouted to isolated sonnet, ledgered). Final: 906 pytest pass, audit PASS (0 issues), version-drift clean.
**Files changed:** `renmark/cli/_engine.py`, `renmark/cli/commands.py`, `renmark/config.py`, `renmark/state/_core.py`+`__init__.py`, `renmark/lifecycle.py`, `plugin/skills/{debug,codereview,help,guide}/`, `plugin/commands/guide.md`, CLAUDE.md/AGENTS.md + templates, plugin.json/marketplace.json, +5 test files.
**Do not change:**
- P5 cross-check is by task INDEX (commit messages carry no target info) — catches reused-number/orphan, not reused-index-different-task; don't claim more.
- P4 helpers MUST print only the path (no body to stdout) — REQ-5 load-bearing.
- `guide` and `help` are intentionally separate: help stays zero-LLM (`disable-model-invocation`); guide is the interactive wizard.
- P10 shipped on its own as **v0.22.0** (2026-06-26); P5/P4/P12/P11/P6/P9 from the batch above are folded into this release. P7/P8 remain queued for a later version (≥v0.23.0).

## [2026-06-25] — v0.21.0 — graduated preamble-tier (P3)
**Request:** Build P3 from the external-skills study (`.renmark/research/2026-06-25-external-skills-study.research.md`): make `lifecycle.skill_preamble` graduated instead of all-or-nothing, so zero-LLM/meta skills carry a minimal/no preamble while heavy pipelines get the full block. Complements v0.20.0's trigger-only descriptions + disable-model-invocation. Dogfooded via the full `/renmark:feature` pipeline.
**Built:**
- **`PREAMBLE_TIER_BY_SKILL` + `preamble_tier()`** in `renmark/lifecycle.py` — 3 tiers: `minimal` (resume, help, doctor, usage, analytics, approve, hygiene, check-plan), `standard` (audit, scan, inventory), `full` (default).
- **Tier-aware `skill_preamble`** — minimal records the invocation then returns None (no hint); standard surfaces the cross-domain `/clear` hint but never the fable hint; full is byte-identical to before. `record_skill_invocation` runs for ALL tiers so cross-domain detection is never compromised; for standard/full the budget check reads last-skill state BEFORE record overwrites it (load-bearing ordering).
- **Tests** — 43 → 48 lifecycle tests, incl. a discriminating `full→minimal→full` chain test proving a minimal mid-link stays visible to downstream cross-domain detection (codereview Minor).
- Verified: 868 pytest pass, ruff clean; code review 0 critical/0 major (codex usage-limited → rerouted to isolated sonnet, ledgered).
**Files changed:** `renmark/lifecycle.py` (tier map + helper + refactor); `tests/test_lifecycle.py` (+5 tests); `PRD.md` (In-scope scope note); 7 version locations; `CHANGELOG.md`.
**Do not change:**
- **`record_skill_invocation` MUST run for every tier** (including minimal) and BEFORE-vs-AFTER ordering relative to `context_budget_check` is load-bearing: for standard/full the budget check reads last-skill state first, then record overwrites it. Reordering breaks cross-domain `/clear` detection.
- Minimal-tier skills returning `None` is intentional — they must stay zero-LLM/cheap; do not re-add hints to them.
- The `tier == "full"` guard on the fable hint must stay — a `standard` skill must never emit the fable synthesis hint.

## [2026-06-25] — PRD updated — graduated preamble-tier scope note
**Request:** The `/renmark:feature graduated preamble-tier` (P3) alignment gate flagged the feature as drift — aligned with the PRD's spirit (REQ-2 cost routing, REQ-5 context hygiene) but absent from explicit scope. Reconcile with a clarifying scope note.
**Built:** Reconciled the **Scope boundaries → In scope** list of `PRD.md` to cover graduated skill-preamble tiers (zero-LLM/meta skills get minimal/no preamble; pipeline skills get the full block); added a 2026-06-25 revision note; bumped `last_reviewed`.
**Files changed:**
- `PRD.md` — In-scope clause for graduated preamble tiers (complements REQ-5); revision note; `last_reviewed` → 2026-06-25.
**Do not change:**
- This is a scope *clarification*, not a new requirement — no new `REQ-n`, no non-goal changes. Graduated preamble tiers must never compromise cold-start zero-LLM recovery (`/renmark:resume`) or cross-domain `/clear` detection.

## [2026-06-25] — v0.20.0 — trigger-only skill descriptions + disable-model-invocation (context-hygiene)
**Request:** After a deep study of three external skill frameworks (mattpocock/skills, obra/superpowers, garrytan/gstack), apply the two highest-leverage learnings (P1+P2 from `.renmark/research/2026-06-25-external-skills-study.research.md`): rewrite every skill `description` to be trigger-only (state WHEN to invoke, not the full workflow — both repos independently showed a workflow-summary in the description gets used as a shortcut that skips the body), and reclassify the zero-LLM/meta skills as `disable-model-invocation: true` so their descriptions leave the model's per-turn context entirely. Dogfooded via the full `/renmark:feature` pipeline.
**Built:**
- **Trigger-only descriptions** — all 27 skill `description:` fields rewritten to lead with WHEN + distinct plain-word triggers; internal workflow/stage/model-routing recap removed (it already lives in each SKILL.md body). Synonym trigger lists collapsed to distinct branches; `start`/`feature`/`debug` now cross-reference instead of all claiming the same verbs (net disambiguation win, confirmed by review). SKILL.md + command shim kept byte-identical per skill so `audit description_drift` stays 0.
- **`disable-model-invocation: true`** added to 11 zero-LLM/meta skills (analytics, usage, inventory, help, approve, resume, doctor, hygiene, audit, scan, check-plan) — descriptions drop from the model's context while the slash commands keep working. `audit`/`scan` correctly silenced (they run project code / are cron-driven, shouldn't auto-fire).
- **Net effect:** skill-description context cut ~50% (12,764 → 6,764 bytes, ~1,500 tokens; ~832 tokens/turn removed entirely via the silenced set). Plain-word auto-routing preserved (focused review: no lost triggers, no ambiguity).
- Verified: 863 pytest pass, ruff clean (mypy errors pre-existing in `browser*.py` only); independent routing-quality review clean (2 minor nits, both fixed).
**Files changed:** `plugin/skills/*/SKILL.md` (27) + `plugin/commands/*.md` (27) descriptions; `disable-model-invocation` on 11 SKILL.md; `.renmark/research/2026-06-25-external-skills-study.research.md` (new); `.renmark/plans/2026-06-25-skill-descriptions-trigger-only.plan.md` (new); + 7 version locations.
**Do not change:**
- **Per-skill SKILL.md and command-shim descriptions MUST stay byte-identical** (or ≥25% token overlap) — `audit description_drift` BLOCKS otherwise. Edit both together.
- Descriptions stay **trigger-only** — do not migrate workflow/stage recaps back into them; that recap belongs in the SKILL.md body, and a workflow-summary in the description gets used as a shortcut that skips the body.
- The auto-routing pipeline skills (start, feature, debug, roadmap, finish, init, brainstorm, plan, orchestrate, verify, codereview, prd, backlog, blueprint, loop, setup) MUST stay model-invocable — never add `disable-model-invocation` to them. `disable-model-invocation` goes on SKILL.md only (exact hyphenated spelling; a typo silently no-ops).

## [2026-06-23] — v0.19.0 — auto-routing: renmark is the default for build/dev work
**Request:** Make renmark the default path for plain-English build/dev requests so the user doesn't have to remember `/renmark:*` commands (and so it wins over other skill frameworks like superpowers), without removing manual control. Built via the full pipeline (`/renmark:feature` → plan → orchestrate → verify → codereview → finish), dogfooding the 0.18.0 model.
**Built:**
- **Broadened pipeline triggers** — `start`/`feature`/`debug` SKILL + shim descriptions now match plain-English dev verbs (build/develop/implement/add/make/create/code up/fix/change) while keeping existing triggers + pipeline framing; `audit description-drift=0`.
- **`routing-preference-rule`** block in the `CLAUDE.md`/`AGENTS.md` templates (+ repo mirror), back-fillable by `/renmark:init`: route build/feature/debug/ship work through renmark pipelines; use other frameworks only when named. DEFAULT, not a lock — explicit `/renmark:` always wins.
- **`renmark/global_routing.py`** — manages a `renmark-routing` block in the GLOBAL `~/.claude/CLAUDE.md` (every-session file): `detect_global_rule`/`install_global_rule(claude_dir=None)`. Create-if-missing / append-if-present / skip-if-there; **unique non-clobbering `.bak.N` backup**; **`present-malformed`→`needs-manual-repair`** (never appends to an unbalanced/duplicate block); idempotent; hermetic tests (7).
- **`/renmark:doctor`** — advisory `[i]` global-routing check (never flips pass/fail) + **`--install-routing`** as the ONLY write path (opt-in); non-zero exit when an explicit `--install-routing` fails.
- **Surfaced** from `/renmark:init` (one-time non-blocking offer) and `/renmark:start` (single light nudge), both pointing at `--install-routing`.
- **Codereview (codex) caught a Critical + 3 Major**, all fixed + independently re-verified before merge.
**Files changed:** `plugin/skills/{start,feature,debug,init,doctor}/SKILL.md` + their `plugin/commands/*.md` shims; `plugin/templates/{CLAUDE.md,AGENTS.md}.template`; `CLAUDE.md`; `AGENTS.md`; `renmark/global_routing.py` (new); `renmark/doctor.py`; `tests/test_global_routing.py` (new); + 7 version locations.
**Do not change:**
- **Plain `/renmark:doctor --fix` must NEVER write `~/.claude/CLAUDE.md`** — the global routing write is opt-in via `--install-routing` ONLY (the Critical fix). Auto-routing is a model-followed instruction (not a hard interlock); explicit `/renmark:` always wins; takes effect next session; the global write is always user-approved + backed up; per-machine (WSL `~/.claude` vs Windows `%USERPROFILE%\.claude`).
- `install_global_rule` backups must stay non-clobbering (`.bak.N`); a `present-malformed` block is reported for manual repair, NEVER auto-appended (prevents infinite-append).

## [2026-06-18] — v0.18.0 — pipeline-first model: 6 user-facing pipelines + Cursor-style concise replies
**Request:** Align renmark to a pipeline-first mental model (Matthew Berman's "levels of AI coding" + the owner's simplified dev-stage spec): surface a few pipelines instead of 27 skills, run them autonomously and pause only at real gates, rewrite `/renmark:help` to teach the workflow, and make renmark's replies short and plain like Cursor/Codex. (A Codex patch attempted this; per owner decision it was redone fresh against the live tree.)
**Built:**
- **`/renmark:help` rewritten pipeline-first** (`plugin/skills/help/SKILL.md` + shim): 6 pipelines with their internal stage sequences, a "which one?" map, then all 27 commands grouped by purpose (Product/spec · Planning/build · Verification/QA · Debug/autofix · Governance/maintenance · Reporting/release) with each command's real modifiers. Stays zero-LLM prose.
- **New `response-style-rule`** mirrored across `CLAUDE.md`, `AGENTS.md`, and both templates: 1–2 sentence status, no essays/diffs/internal chatter unless asked; continue automatically; pause only at the 7 gates. Explicitly does NOT relax the bounded-summary / context-hygiene / task-isolation rules.
- **Canonical Pause Policy** added to `plugin/skills/_shared/handoff-menu.md` — the 7 gates (unclear intent · PRD approval · scope change · risky/destructive · cost · blocker · merge/release), tied to the existing rule-8 default-forward + REQ-12 classification.
- **6 pipeline skills + shims reframed** (init/start/feature/debug/roadmap/finish): descriptions+overviews lead with the pipeline name + honest stage sequence. `start` keeps adaptive routing (brainstorm/staged-program) but establishes a PRD before build (lightweight for simple scope) and offers blueprint only for non-trivial architecture; `feature` auto-proceeds on branch name (no longer a gate).
- **Honesty fix:** `--verifier` → `--verify` in `plugin/commands/loop.md` (the real loop flag; pre-existing typo). Every help-advertised modifier verified to exist in its argparse.
- **Metadata:** pipeline-first descriptions in `plugin/.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `renmark/__init__.py`; README restructured with a six-pipelines table.
**Files changed:**
- `plugin/skills/help/SKILL.md`, `plugin/skills/{init,start,feature,debug,roadmap,finish}/SKILL.md`, `plugin/skills/_shared/handoff-menu.md`, `plugin/commands/{help,init,start,feature,debug,roadmap,finish,loop}.md`, `CLAUDE.md`, `AGENTS.md`, `plugin/templates/CLAUDE.md.template`, `plugin/templates/AGENTS.md.template`, `plugin/.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `renmark/__init__.py`, `README.md`
**Do not change:**
- Help must stay **honest** — never advertise a pipeline stage or modifier the skill doesn't implement (audit `description_drift` enforces shim↔SKILL parity; modifiers verified against argparse).
- `start` must keep its adaptive routing and the brainstorm + staged-program internals — do not flatten it to a single linear path (the owner explicitly rejected that).
- The 7-gate Pause Policy is the single source; skills cite it rather than re-deriving gates. REQ-12 gates (PRD writes, merge/release, destructive, budget) never default.
- Deferred to their own follow-on features (NOT this change): context-hygiene gate in finish, scheduled QA proposer, worktree manager, merge train, docs-drift loop. Version bump to 0.18.0 is a separate release step at `/renmark:finish`.

## [2026-06-18] — v0.17.0 — `/renmark:scan` QA proposer lane + analytics disposition close-out
**Request:** Release the work merged to `main` since v0.16.1 (2026-06-14): the REQ-14 `/renmark:scan` read-only QA proposer lane and the analytics `branch_disposition` close-out fix.
**Built:** Bumped 0.16.1 → 0.17.0 across all 7 locations (drift gate clean). Ships:
- **REQ-14 `/renmark:scan`** — scheduled read-only QA proposer lane: `renmark/scan.py` engine + `--scan`/`--propose`/`--emit-cron` CLI flags + `plugin/skills/scan/SKILL.md`. Inspects via verifiers (audit + pytest/ruff/mypy), dedupes findings, proposes `source=qa` backlog items for human triage. Never edits product code, commits, merges, releases, or executes fixes. Hardened through code review (uuid4 nonce + `O_EXCL` report reservation, explicit rollback marker, honest "not a sandbox — verifiers run project code at test-suite trust" claim).
- **Analytics disposition close-out** — `analytics.close_feature_disposition` transforms the non-terminal feature-run row to `merged-deleted` in place (feature-name primary match, branch narrowing, legacy-only branch-miss fallback); `/renmark:finish` `[m]`/`[r]` paths wire it in. Fixes dispositions reported as perpetually `open`.
- Program reconciled to all-19-REQs-shipped via `--setup`.
**Files changed:**
- VERSION + 6 version locations (this commit); `renmark/scan.py`, `renmark/analytics.py`, `plugin/skills/scan/SKILL.md`, `plugin/skills/finish/SKILL.md`, `tests/test_scan.py`, `tests/test_reports_analytics.py` (in prior merged commits)
**Do not change:**
- `/renmark:scan` is read-only by construction (no git/product mutation by scan itself); do not add a write path. Disposition close-out matches by feature name (sha is unreliable post-`--no-ff`-merge) and stays non-blocking.

## [2026-06-16] — finish-branch-disposition (re-review fix): wrong-branch fallback no longer over-closes
**Request:** Codex re-review of the fixes found one residual Major: when `branch` is given but matches no row, the fallback closed ALL same-feature non-terminal rows — a wrong branch on a reused slug could still over-close.
**Built:**
- `renmark/analytics.close_feature_disposition` — when a given `branch` matches no candidate, the fallback now closes ONLY legacy rows with no recorded `branch`; it never closes rows carrying a *different* branch (those are other runs). A wrong branch on a reused slug now returns `False` and closes nothing.
- New regression test `test_close_feature_disposition_wrong_branch_does_not_overclose` (verified to fail against the old logic). Full suite 856 passed, 28 skipped. SKILL.md `[m]`/`[r]` snippet fixes confirmed correct by the re-review.
**Files changed:**
- `renmark/analytics.py`, `tests/test_reports_analytics.py`
**Do not change:**
- Branch-miss fallback is **legacy-only** (rows with empty/missing `branch`); never fall back to rows with a different recorded branch — that re-opens the over-close bug.
- The sha-mismatch fallback (no branch passed) is a separate, intentional safety net — keep it; it's what closes the row when only a stale sha is known.

## [2026-06-16] — finish-branch-disposition (codereview fixes): branch narrowing + self-contained merge snippet
**Request:** Apply 2 actionable Major findings from the codex review of `main..HEAD` (2 others deferred with rationale).
**Built:**
- **#3 (Major)** — `plugin/skills/finish/SKILL.md` merge-path `[m]` close-out snippet was not self-contained: it referenced `repo` without defining it / importing `Path`, so standalone it would `NameError`, get swallowed by the broad `except`, and silently fail to close (reintroducing the bug). Now imports `Path`, defines `repo = Path('.')`, reads `branch`, mirrors the release block.
- **#1 (Major)** — `renmark/analytics.close_feature_disposition` gained an optional `branch` narrowing key (branch is stable across a `--no-ff` merge, unlike sha, and is recorded per run). Match order: feature → branch (when given) → sha (with the post-merge fallback intact). Prevents over-closing when a feature slug is reused across runs. Both finish callers ([m]/[r]) now pass `branch`.
- New regression test `test_close_feature_disposition_branch_narrows_when_feature_slug_reused`; full suite 855 passed, 28 skipped.
- **Deferred (recorded in the review artifact):** #2 lock-free read-modify-write (module-wide design — `_append`/`write_summary` are also lock-free; analytics is observational, single-writer-serial); #4 fsync before `os.replace` (sibling `write_summary` also omits it — matching the established pattern).
**Files changed:**
- `renmark/analytics.py`, `plugin/skills/finish/SKILL.md`, `tests/test_reports_analytics.py`
**Do not change:**
- Match order is feature → branch → sha; `branch` is the stable narrowing key (sha is NOT reliable post-merge). Don't drop branch narrowing — it's what prevents over-closing a reused slug.
- Keep both finish close-out snippets **self-contained** (`repo = Path('.')`) and non-blocking — a bare `repo` ref silently NameErrors and reintroduces the bug.

## [2026-06-16] — finish-branch-disposition (tasks 2-3 + robustness fix): wire close-out + feature-name matching
**Request:** Wire `close_feature_disposition` into finish's `[m]` merge and `[r]` release paths, with tests; then fix a no-op bug found in review.
**Built:**
- `plugin/skills/finish/SKILL.md` — `[m]` merge path (after branch delete) and `[r]` release path (4c-post, after `record_event`, before `clear_lifecycle`) now call `analytics.close_feature_disposition(repo, feature=feature_name, disposition="merged-deleted")`, non-blocking. Step 2.5 guard note added: the `open`/`merged` row is intentionally non-terminal, closed later by `[m]`/`[r]`.
- `tests/test_reports_analytics.py` — 6 new tests (transform-not-append, no-double-count rollup, idempotent, absent no-op, legacy-`merged` treated non-terminal, sha-mismatch fallback). Whole suite: 854 passed, 28 skipped.
- **Robustness fix (caught in orchestrate review):** the merge path runs `git merge --no-ff`, so post-merge `git rev-parse HEAD` is the merge-commit sha, not the feature-tip sha step 2.5 recorded — matching on feature+sha would no-op and silently fail to close. `close_feature_disposition` is now **feature-primary**: matches non-terminal rows by feature name; `sha` (now optional, default `""`) only narrows, and **falls back to feature-identity** when a passed sha matches no open row. Callers drop the fragile `git rev-parse HEAD` derivation.
**Files changed:**
- `plugin/skills/finish/SKILL.md`, `tests/test_reports_analytics.py`, `renmark/analytics.py`
**Do not change:**
- Close-out matches by **feature name** (the stable identity across the open row and merge); do NOT reintroduce sha-equality as a hard match — post-merge HEAD ≠ recorded feature sha, which silently no-ops.
- Keep the close-out calls **non-blocking** (try/except) — analytics must never abort a merge/release.
- Do NOT write a terminal `branch_disposition` in step 2.5; the open row must stay non-terminal until `[m]`/`[r]` (PR/nothing paths leave it legitimately open).

## [2026-06-16] — finish-branch-disposition (task 1): analytics close-out helper
**Request:** /renmark:analytics reports merged/released features as perpetually `open` because finish never closes the disposition row. Add the source helper to fix it.
**Built:**
- `renmark/analytics.close_feature_disposition(repo, *, feature, sha, disposition='merged-deleted') -> bool` — transforms the existing non-terminal disposition row (matched on feature AND sha; non-terminal = `''|'open'|'merged'`) to its terminal value **in place** via atomic rewrite (mkstemp + os.replace), never appends.
- Idempotent no-op (returns False) when already terminal / row absent; non-raising (swallows OSError/TypeError/ValueError) — analytics stays observational.
**Files changed:**
- `renmark/analytics.py` — new helper + `__all__` export; `record_feature_run`/`_agg_features` untouched.
**Do not change:**
- Must TRANSFORM the row, never append — `_agg_features` counts `branch_disposition` per row, so a second row double-counts (open + merged-deleted).
- Keep the helper non-raising and idempotent; do not alter `record_feature_run`'s append-only contract.

## [2026-06-17] — req14-scan: honest read-only claim + final hardening (pivot re-review)
**Request:** The pivot re-review found the "structural read-only" wording overstated (running `pytest` executes project code → not a sandbox) plus 2 hardening Majors. REQ-14 explicitly authorizes running tests as read-only checks, so behavior is compliant — the claim just needed to be accurate.
**Built:**
- Corrected `emit_cron` + module docstring + `plugin/skills/scan/SKILL.md`: scan.py itself does NO git/product-file/PRD mutation and never commits/merges/pushes/releases/executes fixes (true, structural), but it is **NOT a sandbox** — the verifiers it runs (pytest/ruff/mypy) execute the project's own code, so run the scheduled scan at the same trust level as your test suite. Write-path inventory now also lists the backlog reservation file (next_id/rollback) under `.renmark/state/`.
- **Major** — report-path nonce widened to `uuid4().hex` and the report is reserved with `O_EXCL` (re-roll on collision), so a same-name report is never overwritten.
- **Major** — rollback now uses an explicit reservation marker (`__renmark_scan_reservation__:<uuid>` in `BacklogItem.pending_decision`); `_rollback_reserved(repo, id, token)` unlinks ONLY when that exact token is still on disk — never another writer's real item.
- Tests → 26; full suite 848 green. write_lifecycle refs = 0 (invariant holds).
**Files changed:** `renmark/scan.py`, `plugin/skills/scan/SKILL.md`, `tests/test_scan.py`
**Do not change:**
- Do NOT re-introduce a "sandboxed / nothing-it-runs-can-mutate" claim. scan's guarantee is: no git/product mutation BY SCAN ITSELF; the read-only CHECKS run project code at test-suite trust. That distinction is the honest contract.

## [2026-06-17] — req14-scan: pivot read-only to STRUCTURAL (resolves 2 Critical re-review findings)
**Request:** A focused re-review of the fix commit found the Bash-denylist hook *still* bypassable (absolute-path/`env`/`command`/wrapper forms; `$(…)`/backtick substitution). Decision (user-approved): stop hardening a leaky denylist.
**Built:**
- **Pivot (resolves both Criticals):** `emit_cron` now emits `renmark-execute --scan --propose` as the PRIMARY scheduled trigger — pure Python, no LLM, no Bash tool, no token spend. Read-only is now **structural**: the scan engine's only write paths are the report, the dedup ledger, and backlog `write_item`; it has no commit/merge/push/edit code, so the guarantee no longer depends on a runtime hook. The `READONLY_HOOK` is retained but demoted to OPTIONAL best-effort defense-in-depth, relevant only if a user triggers via `claude -p`.
- **Major** — `_report_rel_path` now folds `checks_failed_to_run` into the hash + appends an `os.urandom(4)` nonce (no same-second collision).
- **Major** — `_ledger_lock` surfaces lock-acquire failure (stderr warning `renmark:scan WARNING: ledger lock unavailable` + `degraded` list) instead of silently running unlocked.
- **Major** — `_rollback_reserved` reads the file back and only unlinks its own empty placeholder (never another writer's real item).
- Tests → 25; full suite 847 green. Structural read-only independently verified (0 mutate paths; only `run_verifier` runs the read-only gates).
**Files changed:** `renmark/scan.py`, `plugin/skills/scan/SKILL.md`, `tests/test_scan.py`
**Do not change:**
- Read-only is guaranteed STRUCTURALLY by the direct `renmark-execute --scan` Python trigger (no mutate path), NOT by the Bash hook. Do not reintroduce a denylist hook as the trust boundary, and do not route the scheduled trigger through `claude -p` as the default.

## [2026-06-17] — req14-scan: code-review fixes (1 Critical, 4 Major, 1 Minor)
**Request:** Fix the codex review findings (`.renmark/reviews/2026-06-17-e6244a2.review.md`) before merging the scan lane.
**Built:**
- **CRITICAL** — `renmark/scan.py` `READONLY_HOOK` denylist was bypassable (`git -C x commit`, `git --git-dir=… commit`, `FOO=1 git commit`). Replaced the brittle regex with a base64-embedded `shlex` tokenizer that skips env-assignments + git global options and blocks any mutating git subcommand by position; `emit_cron` now states the restricted `--tools`/`--disallowedTools`/`dontAsk` allowlist is the primary boundary and the hook is defense-in-depth.
- **MAJOR** — unique report paths (`<date>-<HHMMSS>-<hash>-scan.review.md`) so same-day scans don't overwrite + retarget `evidence_path`; `propose_findings` links the exact written path via `ScanReport.evidence_path`.
- **MAJOR** — stale-ledger entries (missing `backlog_id`) now recreate the item instead of permanently suppressing the finding.
- **MAJOR** — proposal dedup serialized under an `fcntl.flock` on `.renmark/state/proposals.lock` (concurrent-scan safe).
- **MAJOR** — failed `write_item` rolls back the reserved `next_id` placeholder (no ghost items).
- **MAJOR (partial)** — `cmd_scan` returns `2` on a partial run (`checks_failed_to_run` non-empty); still `0` for clean/with-findings (proposer, not a gate).
- **MINOR** — `--propose`/`--emit-cron` now require `--scan` (fail fast, exit 2).
- Tests extended to 22 (subprocess-driven hook deny/allow, path uniqueness, stale-ledger recreate, partial exit, flag gating). Full suite 844 green.
**Files changed:** `renmark/scan.py`, `renmark/cli/commands.py`, `renmark/cli/_engine.py`, `tests/test_scan.py`
**Do not change:**
- The read-only boundary is the restricted tool-list (`--tools`/`--disallowedTools`/`--permission-mode dontAsk`); the Bash-denylist hook is best-effort defense-in-depth, NOT the sole guarantee. Do not reintroduce a single-regex hook.

## [2026-06-16] — refresh scan tests for post-review contract fixes
**Request:** Update `tests/test_scan.py` for the fixed `renmark/scan.py` behavior: unique report paths, behavioral read-only hook checks, stale-ledger recreation, partial exit codes, and `--scan` flag gating.
**Built:** Replaced the stale path-equality and regex-literal assertions with behavior that matches the current scan contract. Added subprocess-driven deny/allow coverage for `_READONLY_HOOK_COMMAND`, same-day report-path uniqueness and evidence-path propagation checks, stale-ledger recreation coverage, direct `cmd_scan()` exit-code tests, and top-level `python3 -m renmark` flag-gating tests. Kept `tests/test_scan.py` as a valid renmark artifact envelope while remaining importable by pytest.
**Files changed:**
- `tests/test_scan.py`
**Do not change:**
- Do not regress these tests to date-only report-path assumptions or hook substring checks; the supported contract is exact evidence-path propagation plus real deny/allow semantics.

## [2026-06-16] — req14-scan-proposer wave 1: engine + skill wiring (tasks 1,5,6,7,8)
**Request:** Build the REQ-14 read-only scheduled QA proposer lane `/renmark:scan`.
**Built:** `renmark/scan.py` engine (zero-LLM, never raises): `run_scan` composes `audit.run_audit` + pytest/ruff/mypy verifiers into normalized `Finding`s; `.renmark/state/proposals.json` dedup ledger keyed `{check}:{rule_id}:{target}` (unseen→propose, same fingerprint→skip, changed→re-surface); `propose_findings` lands `source="qa"`/`status="needs review"` items via the REQ-13 backlog seam; `emit_cron` prints the read-only external trigger + a PreToolUse Bash-denylist hook (`READONLY_HOOK`) that blocks git commit/push/merge/rebase/reset --hard/tag/branch -d/checkout -b/rm -rf. Registered `scan` (audit domain) in lifecycle; added `/renmark:scan` SKILL.md, command shim, and help entry.
**Files changed:**
- `renmark/scan.py` (new engine), `renmark/lifecycle.py` (registry +3 lines)
- `plugin/skills/scan/SKILL.md`, `plugin/commands/scan.md` (new), `plugin/skills/help/SKILL.md` (help entry)
**Do not change:**
- `renmark/scan.py` MUST NOT import/call `lifecycle.write_lifecycle`; sole writes are the report artifact, the dedup ledger, and backlog `write_item(source="qa")`. Read-only is the REQ-14 invariant.

## [2026-06-15] — project scope: scan-proposer (REQ-14)
**Request:** "REQ-14 — scheduled read-only QA proposer lane (propose backlog items, never execute)." Brainstormed → spec at `.renmark/specs/2026-06-15-req14-scan-proposer.spec.md`.
**Scope contract (confirmed):**
- **Stack:** unchanged — Python ≥3.10 Claude Code plugin; stdlib + existing pytest/ruff/mypy gates; **no new runtime deps**.
- **Deployment / trigger:** scheduling stays **external** to renmark (Option 1). renmark ships the `/renmark:scan` worker + a `--emit-cron` helper that *prints* the trigger command; the recurring trigger is the user's WSL `cron` / Windows Task Scheduler running `claude -p "/renmark:scan --propose"` headless. Cloud Routines (`/schedule`) ruled out — fresh-clone, no local repo access.
- **MVP boundary (v1):** `/renmark:scan` (read-only scan→report), `/renmark:scan --propose` (scan + dedupe + `write_item(source="qa", status="needs review")`), `/renmark:scan --emit-cron`. v1 checks = `run_audit()` + shell verifiers. Read-only **enforced** via restricted tool-list + `--permission-mode dontAsk` + a PreToolUse Bash-denylist hook (ships in v1). Dedup ledger (`.renmark/state/proposals.json`, key `{check}:{rule_id}:{target}`) is a prerequisite before any backlog write.
- **Out-of-scope (this build):** `verify --qa`/`--deep-qa` composition (→ v2); renmark-managed scheduling / `/renmark:schedule`; autonomous scheduled *execution* (product-level non-goal, see PRD REQ-14); merge/PR/release/PRD-edit/budget-escalation.
**Do not change:**
- The single backlog seam is `write_item(..., source="qa", status="needs review", evidence_path=...)` (REQ-13 `SCHEDULED-QA.md`) — do not widen the lane's mutation surface.
- Scheduling stays external (Option 1). Do not add a renmark-managed scheduler without revisiting this scope decision.

## [2026-06-14] — fix(handoff): re-render the picker on hand-off continuation turns
**Request:** "Renmark is not giving me clickable options after an interaction and that should be a rule." Found live: after the `/renmark:init` what's-next picker, the user replied with a clarifying question instead of selecting, and the agent answered with a prose `1./2.` list rather than re-rendering the clickable `AskUserQuestion` picker.
**Built:** Root cause (debug session 20260614-164412-9580) — `handoff-menu.md` rules 6–9 + `next-steps.md` mandated the clickable picker only at the first turn a skill ends with a question; no rule required re-rendering when the hand-off continues across turns (user replies with a non-selection), so the agent legitimately dropped to prose and the visible-choices guarantee lapsed. Fix strengthens the existing rule-9 hard-guarantee (the range all 21 SKILL citations already point at) with a **continuation clause**, tightens the rule-6 dispatch bullet (a non-selection free-text reply keeps the hand-off OPEN → answer + re-render), and updates the `next-steps.md` rule-9 gloss. Zero renumbering → every citing skill inherits the fix. Suite 822 passed.
**Files changed:**
- `plugin/skills/_shared/handoff-menu.md` (rule 6 dispatch bullet + rule 9 continuation clause)
- `plugin/skills/_shared/next-steps.md` (rule-9 gloss)
**Do not change:**
- Keep the rule range cited by skills at "6–9" — the continuation fix lives INSIDE rule 9 precisely to avoid renumbering all 21 SKILL citations. Do not promote it to a "rule 10" without bulk-updating every citation.

## [2026-06-14] — v0.16.1 — fix: project-map freshness header wedged --setup staleness
**Request:** Release the stale-map fix found by live-running `/renmark:roadmap --setup`.
**Built:** Bumped 0.16.0 → 0.16.1 (7 locations, drift clean). Fixes the bug where `renmark.init.write_full_map` preserved a stale `Last refreshed @ <sha>` header on body-unchanged refreshes, so `renmark.roadmap.program_map_is_stale` wedged `True` after any structure-neutral commit and `/renmark:roadmap --setup` could never clear it via `/renmark:init`. `write_full_map` now advances the header whenever the full text differs (body still byte-skipped, still reports `unchanged`). +regression test; suite 822. Found via debug session 20260614-061609-c4c6.
**Files changed:**
- `renmark/init.py`, `tests/test_roadmap_staged.py` (in prior commit); VERSION + 6 version locations (this commit)
**Do not change:**
- The freshness header must advance independently of body-content equality — do not re-couple `write_full_map`'s header write to body diff.

## [2026-06-14] — v0.16.0 — PRD-anchored staged program planner
**Request:** Release the `roadmap-staged-planner` feature.
**Built:** Bumped version 0.15.0 → 0.16.0 across all 7 locations (drift gate clean). Ships: `renmark/program.py` (staged-program data model, atomic+durable persistence, strict corruption-raising read), `renmark/program_driver.py` (stage-sequencing state machine: next_stage, structured-field stop logic, next-stage sha snapshot, blocked-halt), `renmark/roadmap.py` (forward plan mode + `--setup` brownfield reconcile + in-flight render), and SKILL wiring for roadmap/resume/start/feature. Reuses loop/backlog/orchestrate/verify within the PRD's bounded-loop limits. Verified 6/6; codereview 0 Critical/5 Major (all fixed); opus-tier release-readiness pass (fable disabled) verdict SHIP with 2 deferrables (both fixed). Full suite 821 passed.
**Files changed:**
- VERSION, pyproject.toml, renmark/__init__.py, plugin/.claude-plugin/plugin.json, .claude-plugin/marketplace.json (×2), README.md — version bump
**Do not change:**
- Keep the 7 version locations in sync (renmark.release check enforces).

## [2026-06-14] — roadmap-staged-planner: codereview fixes (5 Major)
**Request:** Address all 5 Major findings from the codex review of HEAD~7..HEAD (0 Critical). Applied directly (not via a fresh plan) — small, well-scoped fixes with full context — each guarded by a new regression test.
**Built:**
- `renmark/program.py` — (1) `read_program` now wraps `UnicodeDecodeError` → `ProgramStateError` (a non-UTF8 file is corruption, not "absent"); (2) `write_program` uses a UNIQUE `mkstemp` temp + `flush`+`fsync` before `os.replace` (durable, no shared-`.tmp` clobber), cleaning up on failure; (3) `_parse_program` now raises `ProgramStateError` on a `current_stage_id` or `stage_completion_sha` key that references no real stage (dangling-ref corruption).
- `renmark/program_driver.py` — (4) `next_stage` resumes an `in_progress` stage first, and HALTS (returns None) at an earlier `blocked`/`partial` stage instead of skipping past it to run a later stage out of order.
- `renmark/roadmap.py` — (5) `reconcile_setup` recomputes `current_stage_id` to the first non-`done` stage (or None) so `position()` reports correctly after `--setup`.
- Tests: +8 regressions (invalid-UTF8, dangling current_stage_id, dangling completion_sha, no-temp-litter; next_stage halt-at-blocked/partial + in_progress priority; reconcile current_stage_id repoint). Full suite 812 → 820.
**Files changed:**
- `renmark/program.py`, `renmark/program_driver.py`, `renmark/roadmap.py`, `tests/test_program.py`, `tests/test_program_driver.py`, `tests/test_roadmap_staged.py`
**Do not change:**
- `read_program` returns None ONLY for an absent file; ALL corruption (bad bytes, bad JSON, bad schema, dangling refs) raises `ProgramStateError`.
- `next_stage` must not skip past an earlier `blocked`/`partial` stage.
- `reconcile_setup` must leave `current_stage_id` pointing at the first unfinished stage (or None).

## [2026-06-14] — roadmap-staged-planner wave 3: skill wiring (tasks 7–10)
**Request:** Wire the staged planner into the user-facing skills.
**Built (additive SKILL.md edits, +170 lines, plugin lint clean):**
- `plugin/skills/roadmap/SKILL.md` — forward plan mode (PRD→program via bounded subagent, orchestrator never reads PRD body), `--setup` brownfield reconciliation (halt to `/renmark:init` when project-map stale), in-flight render via `render_program_table`. Existing retrospective table + `--gaps` unchanged.
- `plugin/skills/resume/SKILL.md` — step 1.85 surfaces an in-flight staged program (`read_program` + `position`, zero-LLM, bounded).
- `plugin/skills/start/SKILL.md` — feature-planner offered branch (greenfield whole-program planning); default adaptive routing intact.
- `plugin/skills/feature/SKILL.md` — staged mode (multi-stage decomposition via the program driver); single dispatch gate preserved (feature owns it), REQ-12 hard gates intact.
**Files changed:**
- `plugin/skills/{roadmap,resume,start,feature}/SKILL.md`
**Do not change:**
- All four edits are ADDITIVE — the existing default flows (retrospective roadmap, `--gaps`, single-feature pipeline, adaptive start routing) must stay the defaults; staged/forward/feature-planner are offered branches.
- feature stays single-dispatch-gate; staged mode must not add a second approval gate.

## [2026-06-14] — roadmap-staged-planner wave 2: test suite (tasks 4–6)
**Request:** Tests for the program model, driver, and roadmap staged modes — including the task-1 hardening and the binding next-stage-snapshot semantics.
**Built (codex, 32 tests, all green):**
- `tests/test_program.py` (14) — round-trip/render/position/mutators/stage_digest, plus hardening: empty `{}` valid, corrupt existing file raises `ProgramStateError`, mutators raise `ValueError` on unknown ids / invalid status.
- `tests/test_program_driver.py` (13) — `next_stage` skip/resume/none, `evaluate_stop` structured-field-only mapping (incl. PAUSED/AWAITING not hard), `advance_on_success` asserts `stage_completion_sha == {"<next>": sha}` (keyed to NEXT stage, not completed) + persist-before-return, `drift_warning`.
- `tests/test_roadmap_staged.py` (5) — `render_program_table`, `reconcile_setup`, `program_map_is_stale`; existing retrospective table asserted intact.
Full suite 812 passed (780→812), ruff clean; tests excluded from mypy by project config.
**Files changed:**
- `tests/test_program.py`, `tests/test_program_driver.py`, `tests/test_roadmap_staged.py` — new
**Do not change:**
- The `advance_on_success` test pins next-stage sha keying — do not relax it; it guards the owner decision against regression.
- Hardening tests pin `ProgramStateError`-on-corrupt + `ValueError`-on-bad-mutator-input.

## [2026-06-14] — roadmap-staged-planner wave 1: roadmap staged modes (task 3)
**Request:** Add forward staged-program rendering + brownfield reconciliation to roadmap without regressing the existing retrospective table / --gaps.
**Built:** `renmark/roadmap.py` — `render_program_table` (zero-LLM in-flight position; absent→friendly string; corrupt program.json propagates `ProgramStateError` rather than masking it), `reconcile_setup(repo, built_signal)` (maps `built_reqs`/`partial_reqs`/`built_components` onto stage/task statuses; persists), `program_map_is_stale` (parses init's `<!-- Last refreshed: … @ <sha> -->` header vs git HEAD). Existing `build_rows`/`render_table`/`--gaps` paths untouched. ruff/mypy clean; `pytest -k roadmap` 10 passed; full suite 780.
**Files changed:**
- `renmark/roadmap.py` — added 3 functions, existing paths intact
**Do not change:**
- The retrospective table + `--gaps` paths stay as-is (do not regress).
- `render_program_table`/`reconcile_setup` must NOT swallow `ProgramStateError` — corrupt resumable state surfaces loudly; only the absent (None) case yields the friendly "no in-flight program" string.
- `reconcile_setup` operates on the structured `built_signal` dict only — never reads source code or the PRD body (REQ-5/G11).

## [2026-06-14] — roadmap-staged-planner wave 1: program driver (task 2)
**Request:** Build the deterministic stage-sequencing state machine above the single-item loop.
**Built:** `renmark/program_driver.py` — `next_stage`, `StopReason` (str-Enum) + `evaluate_stop` (reads ONLY structured fields, never LLM-interpreted text), `advance_on_success`, `drift_warning`, `driver_status`, `is_hard_stop`/`HARD_STOPS`. Stop severity order (first match wins): RETRY_EXHAUSTED > PLAN_BLOCK > PRD_DRIFT > CODEREVIEW_CRITICAL > VERIFY_FAILED > AWAITING_APPROVAL > PAUSED. PAUSED + AWAITING_APPROVAL are NOT hard stops. Independently probed in a real git tmp repo: ruff/mypy clean, full suite 780 passed.
**Files changed:**
- `renmark/program_driver.py` — new
**Do not change:**
- `advance_on_success` snapshots the **NEXT** stage's sha keyed by that next stage (the drift baseline the next stage is checked against); it must NOT snapshot the completed stage; the last stage snapshots nothing. Owner decision 2026-06-13 — verified by probe.
- `evaluate_stop` reads structured fields only (`completion_state`/`validation_status`, etc.) — never infer a pass/fail from prose.
- State persisted via `program.write_program` BEFORE returning (resumable).

## [2026-06-13] — project scope: roadmap-staged-planner (brainstorm-complete)
**Request:** Enhance `/renmark:roadmap` into a PRD-anchored staged program planner that, after one approval, semi-autonomously drives a sequence of stages→tasks through the existing pipeline (loop + backlog), surfacing live progress and per-task summaries. Owner principle: "spend time on the beginning (PRD + roadmap), then don't deviate."
**Built:** Spec only (no code yet) — `.renmark/specs/2026-06-13-roadmap-staged-planner.spec.md`. Confirmed reuse map (loop/backlog/orchestrate/verify/approve/roadmap) + new pieces (program.json/program.md data model, stage-to-stage driver, entry-point divergence, per-stage digest). Probe confirmed renmark has NO forward PRD→program derivation today.
**Scope contract:**
- **Stack:** unchanged — Python >=3.10 + Claude Code plugin (markdown skills + Python runtime). No new deps.
- **Deployment:** in-repo plugin; no new runtime surface.
- **MVP boundary:** program data model + planner (PRD-as-is derivation) + driver wrapping existing `loop` per stage + `program.md` checklist + roadmap renderer + entry-point divergence + resumability. Stop-on-issue from structured fields.
- **Out of scope:** any change to `/renmark:prd` or the PRD schema; new autonomy beyond the bounded loop; multi-tree parallelism; auto-merge/-release (REQ-12 stands).
**Files changed:**
- `.renmark/specs/2026-06-13-roadmap-staged-planner.spec.md` (new)
- `.renmark/specs/2026-06-13-roadmap-staged-planner.brief.md` (4 requirement refinements appended)
- `.renmark/research/2026-06-13-roadmap-staged-planner-{reuse,bestpractice}.research.md` (new)
**Do not change:**
- The planner derives ordering from the PRD **as-is** — do not silently rewrite `PRD.md` or add a PRD schema in this feature.
- Stop-on-issue must read structured artifact fields (`completion_state`/`validation_status`), never LLM-interpreted "looks done."
- Orchestrator never ingests the PRD body, generated code, or diffs (REQ-5/G11).

## [2026-06-13] — installer: symlink renmark-browser onto PATH (REQ-19 follow-up)
**Request:** Close the v0.15.0 gap surfaced by `/renmark:roadmap --gaps` — `bin/renmark-browser` existed but wasn't on PATH after install.
**Built:** `install.sh` now symlinks `bin/renmark-browser` → `~/.local/bin/renmark-browser` (mirroring renmark-execute) and removes it on `--uninstall`. Verified: `renmark-browser list` resolves on PATH and exits 0. `install.ps1` unchanged — it has no `~/.local/bin` CLI-symlink step (Windows invokes via `python -m renmark.browser_cli`). No version bump — v0.15.0 was local-only; this rides into the next release; the 7 version locations stay consistent (no drift).
**Files changed:**
- `install.sh` — renmark-browser CLI symlink + uninstall cleanup
**Do not change:**
- Keep renmark-browser's CLI symlink mirroring renmark-execute's (safe-symlink guard + uninstall removal).

## [2026-06-13] — v0.15.0 — Playwright browser layer with session memory
**Request:** Ship the playwright-browser-control feature (REQ-19) as a release.
**Built:** Bumped all 7 version locations 0.14.3 → 0.15.0. Feature: an OPTIONAL Playwright browser-control layer with session memory — `renmark-browser login <profile>` saves storageState under gitignored `.renmark/state/browser-sessions/`, reused by deterministic Python flows AND an opt-in `@playwright/mcp` live channel; auto-detects Playwright and falls back to the Chrome DevTools MCP when absent. Core runtime stays stdlib-only. Shipped via the full pipeline: PRD REQ-19 (human-approved) → spec → 9-task plan → orchestrate (9/9) → verify (9/9 goal-backward) → codex review (1 Critical + 6 Major + 1 Minor, ALL fixed + independently verified) → merge. 780 tests pass.
**Files changed:**
- `VERSION`, `pyproject.toml`, `renmark/__init__.py`, `plugin/.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` (×2), `README.md` — version bump
- Feature code (merged): `renmark/browser.py`, `renmark/browser_cli.py`, `bin/renmark-browser`, `.mcp.json`, `tests/test_browser.py`, `plugin/skills/verify/SKILL.md`
**Do not change:**
- `.mcp.json` ships an opt-in `@playwright/mcp` server Claude Code launches via `npx`; it is REQ-19's live-QA channel (user-opt-in).
- Profile names are basename-safe-only (path-traversal guard); session artifacts stay gitignored under `.renmark/state/` and excluded from release zips.

## [2026-06-13] — playwright-browser-control: codereview fixes (1 Critical + 6 Major + 1 Minor)
**Request:** Resolve the codex review findings before finishing the feature.
**Built:**
- **Critical** — path traversal: `renmark/browser.py` now rejects profile names not matching `^[A-Za-z0-9._-]+$` (and bare `.`/`..`) via `_safe_profile_name`, with a resolve-check that paths stay under the sessions root; `browser_cli forget` validates names at the CLI boundary. Verified: `forget '../../tmp/sentinel'` exits 1 and deletes nothing outside the sessions dir.
- **Major** — `is_stale()` now treats missing/invalid/naive/non-string `saved_at` as stale (catches TypeError too), never raises; `activate()` calls `validate_storage_state()` before copying and refuses foreign/malformed JSON; channel API reconciled to the canonical contract `resolve_channel(override=None) → playwright|chrome-devtools|native` (accepts `auto` + `mcp` back-compat alias → playwright; auto → playwright if available else chrome-devtools); path helpers default to `_repo_root()` (nearest `.git`/`.renmark`) not `cwd`; `browser_cli login` catches Playwright launch errors → remediation + exit 1; verify SKILL.md examples corrected to the real signatures.
- **Minor** — `tests/test_browser.py` aligned to the canonical channel contract + added negative/edge tests (traversal names, malformed `saved_at`, foreign-schema `activate`). 13 → 34 tests.
**Verification:** Each fix independently/adversarially verified by the orchestrator (not trusting executor self-claims). Full suite 780 passed, 28 skipped; ruff + plugin lint clean.
**Files changed:**
- `renmark/browser.py`, `renmark/browser_cli.py`, `plugin/skills/verify/SKILL.md`, `tests/test_browser.py`
- `.renmark/plans/2026-06-13-playwright-browser-control-review-fixes.plan.md` (fix plan)
**Do not change:**
- Profile names are basename-safe-only; all session paths must stay under `.renmark/state/browser-sessions/` (path-traversal guard is security-load-bearing).
- Canonical channels are `playwright|chrome-devtools|native`; `mcp` is a back-compat alias for `playwright`. Keep code ↔ verify SKILL.md in sync on this contract.

## [2026-06-13] — playwright-browser-control wave 4: verify + tests + docs (tasks 6–9)
**Request:** Execute the playwright-browser-control plan (serves REQ-19).
**Built:** Task 6 — `plugin/skills/verify/SKILL.md`: documented channel resolution (`resolve_channel`: `--browser` > `RENMARK_BROWSER` > auto), `activate(<profile>)` → `active.json` before `@playwright/mcp`, graceful Chrome DevTools MCP fallback, REQ-5 bounded-output reaffirmed. Task 7 — `tests/test_browser.py` (codex): 13 unit tests (availability, channel precedence, storageState roundtrip + meta, schema validation, staleness, activate) — run WITHOUT playwright. Tasks 8/9 — `CLAUDE.md` + `AGENTS.md`: added `bin/renmark-browser` entry point + an identical "Optional browser layer" line (mirror parity verified byte-identical).
**Verification:** Full suite 759 passed (746 baseline + 13 new), 28 skipped — no regression. ruff clean on all new Python. Codex (task 7) again self-reported `partial`; orchestrator ran the tests independently (13 passed) — trust from evidence, not self-claim.
**Files changed:**
- `plugin/skills/verify/SKILL.md`, `tests/test_browser.py` (new), `CLAUDE.md`, `AGENTS.md`
**Do not change:**
- CLAUDE.md ↔ AGENTS.md "Optional browser layer" line + entry-point line must stay byte-identical (mirror convention).
- Tests must keep running without playwright installed (hermetic, mocked).

## [2026-06-13] — playwright-browser-control wave 3: CLI + wrapper (tasks 4–5)
**Request:** Execute the playwright-browser-control plan (serves REQ-19).
**Built:** Task 4 — `renmark/browser_cli.py` (codex): `login`/`list`/`status`/`forget` subcommands; playwright imported only inside `login`; `login` without playwright prints the `pip install renmark[browser]` + `python -m playwright install chromium` remediation and exits 1; never prints session secrets. Task 5 — `bin/renmark-browser` (haiku): bash wrapper mirroring `bin/renmark-execute`, execs `python -m renmark.browser_cli`.
**Verification note:** Codex self-reported `partial`/`validation_status: failed`, but the orchestrator independently verified Task 4 PASS (py_compile + import-without-playwright + functional `list`/`login` checks); one ruff UP035 fix applied. Trust came from independent evidence, not the executor's self-claim.
**Files changed:**
- `renmark/browser_cli.py` — CLI (new)
- `bin/renmark-browser` — bash wrapper (new, executable)
**Do not change:**
- browser_cli.py must import without playwright — keep all playwright imports inside `login`.
- `login` must never download binaries silently; it prints remediation and exits non-zero when playwright is unavailable.

## [2026-06-13] — playwright-browser-control wave 2: core module (task 3)
**Request:** Execute the playwright-browser-control plan (serves REQ-19).
**Built:** Task 3 — `renmark/browser.py`: the optional browser layer's core. Lazy/guarded `playwright` import (module imports cleanly with playwright absent — verified); `is_playwright_available()`, `resolve_channel()` (precedence arg > `RENMARK_BROWSER` > auto; auto → playwright else chrome-devtools), storageState save/load + sidecar meta (`saved_at`/`browser`/`mode`), `is_stale()`, `validate_storage_state()` (rejects foreign schema), `activate()` (copies profile → active.json, refuses stale). ruff clean.
**Files changed:**
- `renmark/browser.py` — core channel + session module (new)
**Do not change:**
- The `playwright` import MUST stay lazy/guarded — `import renmark.browser` must succeed on a stdlib-only install (verifier + functional check enforce this).
- storageState is the parallelism-safe default; session bytes/cookies never logged or printed.

## [2026-06-13] — playwright-browser-control wave 1: config (tasks 1–2)
**Request:** Execute waves of the playwright-browser-control plan (serves REQ-19).
**Built:** Task 1 — added `browser = ["playwright>=1.40.0"]` to `[project.optional-dependencies]` (`pip install renmark[browser]`; core deps untouched). Task 2 — created `.mcp.json` registering the opt-in `@playwright/mcp` server (`--isolated --storage-state=.renmark/state/browser-sessions/active.json`), additive alongside the global Chrome DevTools MCP.
**Files changed:**
- `pyproject.toml` — optional `browser` extra
- `.mcp.json` — opt-in Playwright MCP server (new)
**Do not change:**
- `.mcp.json` adds an opt-in MCP server Claude Code launches via `npx @playwright/mcp@latest`; it is the approved REQ-19 live-QA channel — do not silently remove, but it is user-opt-in (only runs when MCP is used).
- Core runtime stays stdlib-only; `playwright` is an optional extra, binaries via separate `python -m playwright install chromium`.

## [2026-06-12] — project scope: playwright-browser-control
**Request:** Add Playwright-based browser control with session memory (brainstorm → spec).
**Stack:** Python ≥3.10 runtime + OPTIONAL `playwright>=1.40.0` extra (`pip install renmark[browser]`; browser binaries via separate `python -m playwright install chromium`); Node `@playwright/mcp` MCP server (opt-in) added alongside the existing Chrome DevTools MCP; core runtime stays stdlib-only.
**Deployment:** Claude Code plugin — no server/host; session artifacts on-disk under gitignored `.renmark/state/browser-sessions/`.
**MVP boundary:** Full hybrid — `renmark-browser login <profile>` bootstrap (save storageState, opt-up user-data-dir) + Python scripted reuse + `@playwright/mcp` live-QA reuse + auto-detect/override channel selection (`--browser=playwright|mcp|auto` / `RENMARK_BROWSER`) + `/renmark:verify` integration + graceful fallback to Chrome DevTools MCP when Playwright absent.
**Out of scope:** cookie injection into the CDP/Chrome DevTools MCP channel; remote/CI/cloud session caches; credential storage; silent binary auto-install.
**Spec:** `.renmark/specs/2026-06-12-playwright-browser-control.spec.md` · serves `REQ-19`.
**Do not change:**
- Playwright is OPTIONAL; core runtime stays stdlib-only; absent Playwright → Chrome DevTools MCP fallback with no regression.
- Session artifacts (storageState/user-data-dir) hold live auth — gitignored under `.renmark/state/`, never logged, never inline to subagents, never in orchestrator context (REQ-5), excluded from release zips.
- storageState is the parallelism-safe default; user-data-dir is single-process opt-up only (Chromium SingletonLock).

## [2026-06-12] — PRD updated (playwright-browser-control alignment gate)
**Request:** The `/renmark:feature playwright-browser-control` PRD-alignment gate flagged drift — adding Playwright (a third-party runtime dependency) conflicts with the stdlib-only non-goal. Reconcile by allowing Playwright as an OPTIONAL, opt-in dependency with fallback to the existing Chrome DevTools MCP channel.
**Built:** Reconciled the Goals & Non-goals, Requirements, and Scope boundaries sections of PRD.md; bumped last_reviewed to 2026-06-12. Added REQ-19 (optional Playwright browser-automation layer with persisted session state — cookies/localStorage/storageState — resuming across verify runs, falling back to Chrome DevTools MCP when Playwright is absent). Amended the "No third-party runtime dependencies" non-goal to "...in the core": the core runtime stays stdlib-only while capability layers MAY require optional, opt-in external tools (Codex CLI, Playwright). Added the optional Playwright layer to the in-scope list. Appended a human-approved revision note.
**Files changed:**
- `PRD.md` — REQ-19 added; non-goal amended (core stays stdlib-only, optional opt-in capability deps permitted); in-scope clause + revision note; last_reviewed bumped
**Do not change:**
- Playwright is OPTIONAL and never required — the core Python runtime stays stdlib-only; when Playwright is absent renmark falls back to the Chrome DevTools MCP channel used by `/renmark:verify --qa`.
- Persisted browser session state stays inside `.renmark/` (REQ-6) and never enters orchestrator context (REQ-5).

## [2026-06-12] — v0.14.3 — doc-slimming regression repair
**Request:** A multi-lens post-ship review found v0.14.2's doc-slimming silently dropped governance clauses, created mirror drift, and oversold its numbers; fix all of it.
**Built:** Restored 7 mandates the v0.14.2 terse-rewrite dropped from CLAUDE.md.template (+ re-synced CLAUDE.md byte-for-byte): background-Bash `run_in_background` probe, lifecycle cold-start `/renmark:resume`, commit `compile` gate, refactor-safety `git diff HEAD~1`+`only`, failure-transparency field enums + retry monotonicity, canonical-state "structured summaries", artifact-governance "track stale". Fixed the "never after" parallelism clause to be present in ALL 4 docs (was 1 — the v0.14.2 fix-pass had inverted the mirror). Dropped stale "(v0.10.0)" stamps from both root docs. AGENTS pair: added the Codex-emitted SubagentOutput field-value contract inline + softened the sync-note to "AGENTS summarizes; CLAUDE.md authoritative" (honest pointered-summary). Corrected the v0.14.2 metrics claims (CLAUDE ~35% tok/~58% lines; AGENTS pair GREW in tokens). Fixed an `algorithms/ refactors` typo.
**Pipeline evidence:** review-as-spec → plan (5 tasks, byte-identity-ordered) → verify 6/6 → codex review 1 Major/1 Minor, BOTH FIXED. 746 tests, lint OK, audit PASS, parity 7/7 at 0.14.3. All 4 docs still <=200 lines (166/188/92/114), CLAUDE.md blocks byte-identical to template.
**Do not change:**
- Compression of governance docs must diff EVERY block in EVERY mirror file against the prior version — the v0.14.2 miss happened because the branch review was scoped to one file (lesson logged).
- AGENTS is a pointered SUMMARY (CLAUDE.md authoritative for full clause text); only Codex-emitted contracts live inline.
- Quantitative changelog/audit claims must be recomputed from files, never estimated from a /context reading.

## [2026-06-12] — codereview fixes (doc-slimming-fixes)
**Request:** Resolve the repair-review's 1 Major + 1 Minor before releasing v0.14.3.
**Built:** Major — AGENTS pair now carries the execution-critical SubagentOutput field-value contract (completion_state/confidence/validation_status enums + retry_count monotonicity) that Codex agents emit; the sync-note is softened to declare AGENTS a SUMMARY with CLAUDE.md authoritative for full clause text, making the existing 'See CLAUDE.md §' pointers honest-by-design (orchestrator-facing clauses stay as pointers). Minor — fixed the 'algorithms/ refactors' typo in CLAUDE.md's non-block line (template was already correct).
**Files changed:**
- `plugin/templates/AGENTS.md.template`, `AGENTS.md` — retry contract + sync-note
- `CLAUDE.md` — typo sync
**Do not change:**
- AGENTS is a pointered SUMMARY, not a verbatim full mirror — Codex-emitted field contracts live inline; orchestrator-facing clauses are pointers to CLAUDE.md §.

## [2026-06-12] — AGENTS.md mirror + version stamp
**Request:** doc-slimming-fixes task 4.
**Built:** repo AGENTS.md: restored compile gate + background-Bash probe + 'never after' clause (now present in all 4 onboarding files, fixing the 1-of-4 drift); dropped stale (v0.10.0); 114 lines.
**Files changed:**
- `AGENTS.md`

## [2026-06-12] — v0.14.2 metrics correction
**Request:** A post-ship review found the v0.14.2 doc-slimming changelog/audit numbers were overstated; record the honest figures.
**Built:** Verified token figures (chars/4): CLAUDE.md.template 5226→3270 (-37%); CLAUDE.md 5502→3602 (-35%, ~58% by lines — the genuine per-session Claude win). The AGENTS pair did NOT shrink — both GREW in tokens: AGENTS.md.template 2410→2677 (+11%), AGENTS.md 2576→3434 (+33%); only their line counts fell (newline-joining). AGENTS.md is not loaded by Claude Code, so per-session Claude impact = the CLAUDE.md reduction only. The earlier "all four onboarding docs ~halved" and "~7.2k→~3.5k halved" framings were optimistic: lines roughly halved for the CLAUDE pair, tokens dropped ~35%. The v0.14.2 entry also omitted its "Files changed:" field.
**Files changed:**
- `CHANGELOG.md` — honest metrics correction entry
- (the underlying clause/version/mirror fixes are tracked in the doc-slimming-fixes feature commits)
**Do not change:**
- Quantitative claims in changelog/audit entries must be recomputed from the actual files, not estimated from a /context reading (the ~7.2k figure was a real-tokenizer pre-slim reading mixed with a chars/4 post figure).

## [2026-06-12] — restore dropped governance clauses (CLAUDE template)
**Request:** doc-slimming-fixes task 1 — restore mandates the v0.14.2 slim silently dropped.
**Built:** plugin/templates/CLAUDE.md.template (166 lines, 23 blocks intact): restored parallelism background-Bash + 'never after'; lifecycle cold-start /renmark:resume; commit 'compile and pass lint'; refactor-safety git-diff-HEAD~1 + 'only'; failure-transparency field value enums + retry monotonicity; canonical-state 'structured summaries'; artifact-governance 'track stale artifacts' + formats; fixed 'algorithms/ refactors' typo.
**Files changed:**
- `plugin/templates/CLAUDE.md.template` — clause restoration (authoritative)
**Do not change:**
- These restored blocks are the byte-verbatim source CLAUDE.md must match; do not drop a mandate to save lines (166<200 with all clauses proves brevity didn't require it).

## [2026-06-12] — v0.14.2 — CLAUDE/AGENTS doc slimming
**Request:** The onboarding docs were too long; get CLAUDE.md, AGENTS.md, and both templates under 200 lines each (terse-rewrite in place).
**Built:** All four onboarding docs ~halved: CLAUDE.md.template 426→167, CLAUDE.md 450→189, AGENTS.md.template 113→92, AGENTS.md 133→114 (1122→562 total). The 23 governance rule blocks compressed to 1-3 lines each with names/markers/load-bearing clauses intact; non-block sections (Tooling, Executor prefs, Code/Testing, at-a-glance) replaced with one-line memory-file pointers noted "(generated by /renmark:init)". CLAUDE.md rule blocks stay byte-identical to the template (merge_rule_blocks/audit see no drift). Always-loaded CLAUDE.md cost ~7.2k→~3.5k tok/session.
**Pipeline evidence:** brainstorm spec → plan (4 tasks, byte-identity-ordered) → verify 5/5 → codex review 1 critical/6 major/1 minor, ALL FIXED (AGENTS had over-compressed and dropped the codex→sonnet reroute exception, full G11, bounded-output overrides, write-boundary homes, parallelism clause; both templates' memory-pointers were dangling for fresh scaffolds). 746 tests, audit PASS, parity 7/7 at 0.14.2. Plus a persisted plugin context-footprint audit (.renmark/audits/2026-06-12-plugin-context-footprint.md).
**Do not change:**
- CLAUDE.md governance blocks must stay byte-identical to CLAUDE.md.template (merge_rule_blocks back-fills missing-only; drift is silent).
- AGENTS prose mirrors CLAUDE's FULL governance clauses — compression must never drop a load-bearing clause to hit a line count (the adversarial review is the guard).
- Template memory-pointers must note "(generated by /renmark:init)" — fresh scaffolds have no .renmark/memory/*.md.

## [2026-06-12] — codereview fixes (claude-doc-slimming) + plugin footprint audit
**Request:** Close the codex review of the doc-slimming (1 critical/6 major/1 minor) + persist the plugin context-footprint audit.
**Built:** AGENTS over-compression repaired — restored the codex→sonnet reroute exception (critical), the full G11 carry/aggregates contract, bounded-output user-override + architecture-scans ban, write-boundary artifact homes, parallelism read-only-verification clause, and the skill_preamble reference (was stale context_budget_check). Both templates' dangling .renmark/memory/ pointers softened to '(generated by /renmark:init)' so fresh scaffolds don't dangle. Block byte-identity (template<->CLAUDE.md) preserved; 746 tests green. Persisted .renmark/audits/2026-06-12-plugin-context-footprint.md.
**Files changed:**
- `plugin/templates/AGENTS.md.template`, `AGENTS.md` — restored dropped governance clauses + pointer fix
- `plugin/templates/CLAUDE.md.template`, `CLAUDE.md` — dangling-pointer softening (non-block only)
- `.renmark/audits/2026-06-12-plugin-context-footprint.md` — context audit
**Do not change:**
- AGENTS prose must mirror CLAUDE's full governance clauses — the terse-rewrite proved compression silently drops them; the adversarial review is the guard.
- Memory pointers in templates must note '(generated by /renmark:init)' — a fresh scaffold has no .renmark/memory/*.md.

## [2026-06-12] — terse AGENTS.md 133->92, mirror
**Request:** claude-doc-slimming task 4.
**Built:** repo AGENTS.md rewritten to mirror the terse AGENTS template + shared CLAUDE rule wording; marker-free; non-block sections → memory pointers; real renmark specifics kept.
**Files changed:**
- `AGENTS.md` — terse mirror (92 lines)

## [2026-06-12] — terse AGENTS.md.template 113->92, prose mirror
**Request:** claude-doc-slimming wave 2.
**Built:** AGENTS template rewritten to mirror the terse CLAUDE rule wording; stays marker-free (0-block invariant); non-block sections → memory pointers.
**Files changed:**
- `plugin/templates/AGENTS.md.template`

## [2026-06-12] — terse CLAUDE.md 450->177, blocks byte-identical to template
**Request:** claude-doc-slimming wave 2.
**Built:** Repo CLAUDE.md compressed to 177 lines; all 23 rule blocks reproduced byte-for-byte from the terse template (verified zero drift); real project description kept; non-block sections → memory pointers.
**Files changed:**
- `CLAUDE.md`

## [2026-06-12] — terse CLAUDE template
**Request:** claude-doc-slimming task 1 — compress the authoritative CLAUDE template to ≤200 lines.
**Built:** plugin/templates/CLAUDE.md.template 426->167 lines; all 23 rule blocks kept (names/markers/order intact), every load-bearing clause grep-verified (codex RED-FLAG, fable override + reroute, 5-line/300-tok + 60/80% caps, G11 three-lists, lifecycle separation, provenance fields, write-boundary, contract/reuse pointers); non-block sections compressed to memory pointers.
**Files changed:**
- `plugin/templates/CLAUDE.md.template` — terse-rewrite (authoritative block source)
**Do not change:**
- This template's block bodies are now the byte-verbatim source merge_rule_blocks back-fills — the live CLAUDE.md (task 2) must match them exactly.

## [2026-06-12] — project scope: claude-doc-slimming
**Request:** Terse-rewrite CLAUDE/AGENTS templates + this repo's root docs to ≤200 lines each, in place.
**Scope contract:** Stack unchanged (renmark Python plugin). Deployment unchanged. MVP boundary: documentation-density compression only — preserve every rule-block name/marker/load-bearing clause; compress non-block sections to memory pointers. OUT: two-tier governance-doc split, block consolidation/rename, any rule-semantics change.
**Files changed:**
- `.renmark/specs/2026-06-12-claude-doc-slimming.spec.md` — design doc
**Do not change:**
- This is density-only — no governance rule may lose its enforcement clause; markers + block names are preserved so merge/lint/audit/tests stay green.

## [2026-06-12] — v0.14.1 — PRD template enrichment (surgical)
**Request:** Analyze an external 17-section PRD-generator framework against renmark's PRD, harvest only the genuinely-additive pieces, and improve the PRD output without regressing renmark's altitude separation.
**Built:** Finding: ~70% of the external template already lives in renmark's pipeline (plan/verify/brainstorm/decisions.md/reuse-check), so wholesale adoption was REFUSED as a regression. Imported the 5 additive pieces: PRD.md.template gains OPTIONAL requirement sub-groups (incl. an AI/Agent slot), [blocking|deferrable] question tags + Constraints & dependencies section, a PRD-local Decision log (distinct from decisions.md), a Recommendation verdict, and a top anti-completion guard routing build-plan/testing/risk/reversibility/asset concerns to their owning surfaces. prd SKILL CREATE now runs the reuse-check, surfaces contradictions, opens with a context-recovery/missing-info preamble, and both CREATE+UPDATE end with an advisory Final Recommendation verdict.
**Pipeline evidence:** PRD alignment aligned; plan PASS (lite tier); verify 4/4; lite-lane cheap /review 0 findings. 746 tests, audit PASS, parity 7/7 at 0.14.1.
**Do not change:**
- All template additions are OPTIONAL — a flat lean PRD stays valid; the anti-completion guard is load-bearing (don't add build-plan/testing/risk sections — they live in plan/verify/brainstorm).
- The Final Recommendation verdict is ADVISORY — never treat 'build-now' as approval to write PRD.md (REQ-4 human-owns-write).

## [2026-06-12] — prd SKILL — interview wiring + recommendation
**Request:** prd-template-enrichment task 2 — wire the prd skill to the new template + just-shipped disciplines.
**Built:** CREATE mode now runs the reuse-check before drafting, surfaces contradictions instead of silently overwriting, and opens with a context-recovery + missing-info preamble; both CREATE and UPDATE end with an advisory Final Recommendation verdict (build-now|revise-scope|discovery-first|do-not-build-yet) alongside the approval gate; optional template sections documented as populate-when-relevant.
**Files changed:**
- `plugin/skills/prd/SKILL.md` — interview wiring + recommendation rendering
**Do not change:**
- The Final Recommendation is ADVISORY — the human still owns every PRD write (REQ-4); the human gate, context-hygiene, and altitude sections are untouched.

## [2026-06-12] — PRD template enrichment
**Request:** Surgically enrich the product-PRD template with additive pieces from an external PRD-generator framework, without importing pipeline-duplicating sections.
**Built:** plugin/templates/PRD.md.template gains 5 OPTIONAL pieces — requirement sub-groups (incl. AI/Agent slot), [blocking|deferrable] question tags + Constraints & dependencies section, PRD-local Decision log, Recommendation verdict — plus a top anti-completion guard comment routing build-plan/testing/risk/reversibility/asset concerns to their owning surfaces.
**Files changed:**
- `plugin/templates/PRD.md.template` — additive optional structure
**Do not change:**
- All additions are OPTIONAL — a flat lean PRD stays valid. The anti-completion guard is load-bearing: do not add build-plan/testing/full-risk sections (they live in plan/verify/brainstorm).

## [2026-06-12] — v0.14.0 — Cowork-alignment agent disciplines
**Request:** Port the four gaps surfaced by comparing renmark against an external "Claude Cowork" operating-instructions doc: don't-reinvent-the-wheel, push-back-by-default, surface-contradictions, re-interview-on-change.
**Built:** (1) NEW reuse-check subagent contract (plugin/skills/_shared/reuse-check.md) — cheap subagent searches loaded skills/commands, MCP tools, prior specs/plans, and features.md before brainstorm/plan propose a custom build; bounded reuse:found|none verdict; default to reuse. (2) Push-back-by-default + no-sycophancy stance added to the shared reasoning contract, carried by every dispatched agent. (3) Contradiction-reconcile reflex: plan's CHANGELOG 'Do not change' read and orchestrate's pre-flight now stop-and-reconcile on a contradicting guarded decision (orchestrate strengthened to 5 entries + decisions.md + semantic contradictions). (4) Re-interview-on-premise-change guard in brainstorm (re-establish scope) and feature (router detects drift → re-runs PRD alignment → dispatches the scope-owning skill).
**Pipeline evidence:** PRD alignment aligned; plan PASS; verify 4/4; codex review 0 critical / 4 major / 1 minor — all 5 fixed (orchestrate↔plan parity, feature router-purity, AGENTS template mirror, pointer-propagation invariant). 746 tests, audit PASS, parity 7/7 at 0.14.0.
**Do not change:**
- Consumers cite the reuse-check and reasoning-contract blockquotes BY POINTER, never paste — so contract updates propagate (the pointer-propagation invariant).
- feature stays a router — scope re-establishment is always delegated to brainstorm/plan.
- The reuse check defaults to REUSE; custom builds need a stated reason.

## [2026-06-12] — codereview fixes (cowork-alignment)
**Request:** Codex review found 0 critical / 4 major / 1 minor — consistency + scope-ownership issues; fix all 5.
**Built:** orchestrate pre-flight contradiction check strengthened to match plan (last 5 CHANGELOG entries + decisions.md + semantic contradictions, not just file overlap); feature re-entry guard reworded to router-only (detect drift → re-run PRD alignment → dispatch the scope-owning skill, never re-interview itself); AGENTS.md.template gains the reuse-check + push-back bullets (mirror parity with root AGENTS.md); brainstorm Step-4 citation confirmed pointer-form + stance clause added; reasoning-contract.md header now states the pointer-propagation invariant (all 7 consumers cite by pointer, none paste).
**Files changed:**
- `plugin/skills/orchestrate/SKILL.md`, `plugin/skills/feature/SKILL.md`
- `plugin/templates/AGENTS.md.template`, `plugin/skills/brainstorm/SKILL.md`, `plugin/skills/_shared/reasoning-contract.md`
**Do not change:**
- feature stays a router — scope re-establishment is always delegated to brainstorm/plan, never done in the router.
- Consumers cite the reasoning/reuse blockquotes BY POINTER (never paste) so contract updates propagate — the pointer-propagation invariant is load-bearing.

## [2026-06-12] — reuse-check + push-back pointers
**Request:** cowork-alignment wave 2.
**Built:** Same two pointer lines in the CLAUDE template; AGENTS template had no anchor (nothing added there).
**Files changed:**
- `plugin/templates/CLAUDE.md.template`

## [2026-06-12] — reuse-check + push-back pointers, AGENTS mirror
**Request:** cowork-alignment wave 2.
**Built:** Two standing rules: run the reuse check before custom builds; dispatched agents push back and skip sycophancy. Mirrored byte-identical into AGENTS.md.
**Files changed:**
- `CLAUDE.md`
- `AGENTS.md`

## [2026-06-12] — re-interview guard on mid-feature premise change
**Request:** cowork-alignment wave 2.
**Built:** Router re-runs PRD alignment + re-establishes scope when the premise materially changes, instead of silently continuing the pipeline.
**Files changed:**
- `plugin/skills/feature/SKILL.md`

## [2026-06-12] — contradiction overlap pauses for reconcile
**Request:** cowork-alignment wave 2.
**Built:** Pre-flight changelog check escalates a contradicting overlap from a note to a stop-and-reconcile before dispatch.
**Files changed:**
- `plugin/skills/orchestrate/SKILL.md`

## [2026-06-12] — reuse check + contradiction-reconcile reflex
**Request:** cowork-alignment wave 2.
**Built:** Reuse-check before decomposition; the CHANGELOG 'Do not change' read is now a stop-and-reconcile when a task would contradict a guarded decision.
**Files changed:**
- `plugin/skills/plan/SKILL.md`

## [2026-06-12] — reuse check before approaches + re-establish scope on premise change
**Request:** cowork-alignment wave 2.
**Built:** Reuse-check subagent (internal counterpart to external prior-art) before Step 4; re-establish the scope contract when the premise shifts instead of continuing from persisted spec.
**Files changed:**
- `plugin/skills/brainstorm/SKILL.md`

## [2026-06-12] — pushback stance
**Request:** cowork-alignment wave 1.
**Built:** Reasoning contract gains a Stance clause (disagree when off-strategy/wrong/inconsistent; no hollow affirmation) carried by every dispatched agent via the citable blockquote.
**Files changed:**
- `plugin/skills/_shared/reasoning-contract.md`
**Do not change:**
- The canonical reasoning + stance text is single-sourced in this file — skills cite, never paste.

## [2026-06-12] — reuse-check contract
**Request:** cowork-alignment wave 1.
**Built:** Cheap subagent searches loaded skills/commands, MCP tools, prior specs/plans, features.md before a custom build; bounded reuse:found|none verdict; default to reuse.
**Files changed:**
- `plugin/skills/_shared/reuse-check.md`
**Do not change:**
- Orchestrator reads only the ≤5-line verdict (REQ-5), never the searched bodies; canonical dispatch blockquote lives here, skills cite it.

## [2026-06-12] — v0.13.0 — agent reasoning + routing policy
**Request:** Codify the owner's AGENT REASONING + ROUTING POLICY: required reasoning instruction for all agents, fable sub-agent lanes for the four role groups, effort defaults, browser-validation discipline.
**Built:** NEW shared reasoning/output-discipline contract (plugin/skills/_shared/reasoning-contract.md — multi-perspective → assumptions/edge cases → synthesis; blocking vs deferrable; findings vs recommendations; evidence preserved; missing context stated; confidence ≠ completion) carried by EVERY dispatch surface (orchestrate Agent+codex paths, verify, finish, prd, brainstorm, codereview, audit). Declaration-gated optional fable lanes: verify [fr] QA review extension code, finish release-readiness adversarial pass (blocking stops [r]), prd non-interactive reconcile, brainstorm Step-4 synthesis. Effort-policy routing rows (session default opus/medium for normal work; MAY-escalate fable for QA/adversarial signals — never default). Browser-access instruction for QA subagents (active channel; no static-only UI validation).
**Pipeline evidence:** PRD alignment aligned (haiku-pinned subagent's first run); plan PASS; verify 4/4; codex review 0 critical / 8 major / 2 minor — all 10 fixed (contract rollout completed, honest G11 rows, MAY-escalate wording); 746 tests, audit PASS, parity 7/7 at 0.13.0.
**Do not change:**
- The canonical reasoning instruction lives ONLY in reasoning-contract.md — skills cite, never paste.
- Interactive loops (brainstorm discovery, prd CREATE interview) never dispatch per-checkpoint fable calls.
- The fable QA route is MAY-escalate, never default.

## [2026-06-12] — codereview fixes (agent-routing-policy): contract rollout completed
**Request:** Codex review found 0 critical / 8 major / 2 minor — all consistency gaps; fix all 10.
**Built:** Contract rollout completed (codereview/audit/brainstorm-research lanes now carry the verbatim Dispatch-reference blockquote — the universal-coverage claim is now true); verify gains the [fr] Fable review extension code in its hand-off menus (codereview [o]/[fix] pattern), channel-neutral browser wording, and an honest G11 row; prd G11 row describes the optional fable reconcile dispatch; finish uses the verbatim blockquote; orchestrate names the exact contract section; routing.md QA row reworded 'MAY escalate … never default'.
**Files changed:**
- `plugin/skills/{verify,prd,finish,orchestrate,codereview,audit,brainstorm}/SKILL.md`
- `plugin/skills/_shared/reasoning-contract.md`, `.renmark/memory/routing.md`
**Do not change:**
- [fr] is a verify-lane extension code, NOT in handoff-menu.md's canonical list (same precedent as codereview's [o]/[fix]).
- The fable QA route is MAY-escalate, never default — wording is load-bearing against the escalation-only rule.

## [2026-06-12] — preferences carry the reasoning-contract pointer
**Request:** agent-routing-policy wave 2.
**Built:** Root and template lines byte-identical; AGENTS.md has no preferences block.
**Files changed:**
- `CLAUDE.md`
- `plugin/templates/CLAUDE.md.template`

## [2026-06-12] — effort-policy default rows
**Request:** agent-routing-policy wave 2.
**Built:** Session default (opus/medium) for normal work; fable subagent for QA/adversarial signals in declared projects.
**Files changed:**
- `.renmark/memory/routing.md`

## [2026-06-12] — non-interactive fable lanes
**Request:** agent-routing-policy wave 2.
**Built:** PRD reconcile and brainstorm Step-4 synthesis may dispatch ONE bounded fable subagent in declared projects; interactive loops never dispatch (judge-pinned). Human gates unchanged.
**Files changed:**
- `plugin/skills/prd/SKILL.md`
- `plugin/skills/brainstorm/SKILL.md`

## [2026-06-12] — optional fable release-readiness adversarial pass
**Request:** agent-routing-policy wave 2.
**Built:** Recommended before release-tagged closes in declared projects; blocking findings stop the [r] path, deferrable → bugs.md.
**Files changed:**
- `plugin/skills/finish/SKILL.md`

## [2026-06-12] — optional fable QA review lane + browser-access instruction
**Request:** agent-routing-policy wave 2.
**Built:** Declared projects may add a fable QA-review subagent (blocking-vs-deferrable verdict); deterministic smoke stays the always-run default (REQ-7). QA subagents are told they have Chrome DevTools MCP access — no static-only UI validation.
**Files changed:**
- `plugin/skills/verify/SKILL.md`

## [2026-06-12] — dispatch prompts carry the reasoning contract
**Request:** agent-routing-policy wave 2.
**Built:** Agent-path AND codex ad-hoc dispatch prompts must include the reasoning-contract blockquote (cited, never pasted).
**Files changed:**
- `plugin/skills/orchestrate/SKILL.md`

## [2026-06-12] — reasoning contract (shared)
**Request:** agent-routing-policy task 1 — the owner's required reasoning instruction as a single-source contract.
**Built:** plugin/skills/_shared/reasoning-contract.md: canonical multi-perspective→assumptions→synthesis instruction, output discipline mapped to G9 fields, browser-validation clause (Chrome DevTools MCP), citable dispatch blockquote.
**Files changed:**
- `plugin/skills/_shared/reasoning-contract.md` — new shared reference
**Do not change:**
- The canonical instruction text lives ONLY here — skills cite the blockquote, never paste the body.

## [2026-06-12] — v0.12.0 — declared-capability Fable routing
**Request:** Implement the adopted fable-routing strategy (per amended REQ-2 and the 2026-06-11 decision record): Fable as declared default for ideation/strategy synthesis, busy-work demoted to cheap tiers, deterministic gates; full pipeline across 2 plans (23 tasks), surviving a dual provider-limit interruption.
**Built:** NEW renmark/capabilities.py (env RENMARK_TOP_TIER > routing.md ## Model tiers > opus; case-normalized; heading-bounded parsing); plan_lint checks 9-10 (fable undeclared/mechanical BLOCKs, doc-mirrored); engine dry-run prices via effective_executor with fable→opus render + downgrade repricing; skill_preamble declared-tier hint for synthesis skills; busy-work demotions (brainstorm research → parallel sonnet subagents, prd-alignment → haiku w/ sonnet large-PRD escalation, blueprint HTML → codex split); init one-time declaration question + doctor report row; this repo declares top_tier: fable; owner rules implemented (handoff default-forward rule 8, codex usage-limit reroute-first); 23 new tests (746 total).
**Pipeline evidence:** PRD alignment aligned; both plans PASS lint; verify 6/6 goal-backward; codex review 0 critical / 3 major / 2 minor / 1 nit — 3 fixed (repricing, parsing, case), 2 ruled by-design with REQ-2 test pins (env IS a per-user declaration, both directions pinned), 1 deferred (plan_lint cwd repo_root — pre-existing convention). Dual usage-limit interruption (codex + Claude session, 2026-06-11) recovered via Tier-2 pause state + next-day codex retry.
**Do not change:**
- Env precedence (RENMARK_TOP_TIER > file > opus) is test-pinned in both directions — the REQ-2 per-user override contract.
- The Model tiers block is hand-curated; append_routing and init never overwrite an existing block.
- REQ-12 gates never default-forward; reroute-first applies only to non-bulk codex waves and is always ledgered.

## [2026-06-12] — codereview fixes (fable-routing): repricing, parsing edges, design pins
**Request:** Codex review found 0 critical / 3 major / 2 minor / 1 nit on 9b49afd..HEAD; fix the real ones, pin the by-design ones.
**Built:** Engine: downgraded fable→opus preview rows now reprice at the effective rate even with explicit est_cost_usd (major 3). Capabilities: indented headings terminate the Model tiers block; env/file tier values normalize case (minor 4 + nit 6). Design pins with REQ-2 citations: RENMARK_TOP_TIER=fable IS a per-user declaration (lint passes, hint fires — majors 1-2 ruled by-design) and env=opus on a declared repo BLOCKs fable (collaborator protection). Plan SKILL routing row clarifies env counts as declaration. Deferred: plan_lint's Path.cwd() repo_root (minor 5) — pre-existing convention shared with check 4; cross-checkout linting is a separate refactor.
**Files changed:**
- `renmark/capabilities.py`, `tests/test_capabilities.py` — parsing + case fixes, 3 new tests
- `renmark/cli/_engine.py`, `tests/test_engine_budget_and_rollback.py` — downgrade repricing + regression
- `tests/test_plan_lint.py`, `tests/test_lifecycle.py` — 3 REQ-2 design-pin tests
- `plugin/skills/plan/SKILL.md` — env-counts-as-declaration clarification
**Do not change:**
- Env precedence (RENMARK_TOP_TIER > routing.md > opus) is test-pinned in BOTH directions — changing it breaks the REQ-2 per-user override contract.
- Downgraded preview rows always reprice; explicit est_cost_usd wins only when the executor is NOT downgraded.

## [2026-06-12] — preferences pointer pair
**Request:** fable-routing part 2 wave 2.
**Built:** Frontier-reasoning row in root CLAUDE.md + template now states fable is the default for ideation/strategy/adversarial roles when declared, escalation-only otherwise. AGENTS.md had no anchor row — nothing added (task 13 SKIP by rule).
**Files changed:**
- `CLAUDE.md`
- `plugin/templates/CLAUDE.md.template`
**Do not change:**
- Root and template rows stay byte-identical; AGENTS.md gains the row only if a future sync adds the preferences block there.

## [2026-06-12] — Model tiers declarations
**Request:** fable-routing part 2 wave 2.
**Built:** Template ships top_tier: opus with fable opt-in comments; this repo declares top_tier: fable (owner-confirmed). capabilities.is_top_tier_declared(Path('.')) now True here — synthesis-skill tier hints and fable plan acceptance are live.
**Files changed:**
- `plugin/templates/memory/routing.md.template`
- `.renmark/memory/routing.md`
**Do not change:**
- The Model tiers block is hand-curated — memory.append_routing never edits it; init never overwrites an existing block.

## [2026-06-12] — codereview + audit declaration wording
**Request:** fable-routing part 2 wave 1.
**Built:** Both adversarial-escalation notes now condition fable routing on declared top_tier with documented opus fallback.
**Files changed:**
- `plugin/skills/codereview/SKILL.md`
- `plugin/skills/audit/SKILL.md`
**Do not change:**
- Both notes share the same gate language — keep them in sync.

## [2026-06-12] — doctor declaration report
**Request:** fable-routing part 2 wave 1.
**Built:** Advisory check row resolves top_tier via renmark.capabilities and flags env overrides; remediation points at /renmark:init.
**Files changed:**
- `plugin/skills/doctor/SKILL.md`
**Do not change:**
- Advisory only — doctor --fix does not write the declaration.

## [2026-06-12] — init declaration question
**Request:** fable-routing part 2 wave 1.
**Built:** New step writes the ## Model tiers block above Learned overrides on first run; idempotent; non-interactive defaults to opus; setup inherits via delegation.
**Files changed:**
- `plugin/skills/init/SKILL.md`
**Do not change:**
- Existing Model tiers blocks are NEVER overwritten — init reports them instead.

## [2026-06-12] — prd-alignment haiku pin
**Request:** fable-routing part 2 wave 1.
**Built:** Default model: haiku; sonnet when PRD.md > ~800 lines; the citable dispatch blockquote carries the pin so callers can't drift.
**Files changed:**
- `plugin/skills/_shared/prd-alignment.md`
**Do not change:**
- ≤5-line verdict contract unchanged; callers re-copy the blockquote verbatim.

## [2026-06-12] — blueprint bulk demotion
**Request:** fable-routing part 2 wave 1.
**Built:** Session brain writes the design spec; codex bulk-emits via renmark-execute --task into .renmark/state/blueprint/ staging, then the splice proceeds as before. Schematic stays inline with a never-escalate note.
**Files changed:**
- `plugin/skills/blueprint/SKILL.md`
**Do not change:**
- Marker-splice + no-invented-nodes contracts unchanged; staging dir is sanctioned scratch.

## [2026-06-12] — brainstorm research demotion
**Request:** fable-routing part 2 wave 1.
**Built:** Step 3 web research demoted off the top tier: parallel model:sonnet subagents, angle-suffixed research artifacts, ≤5-line summaries; synthesis stays on the session brain. Step 0 surfaces the declared-tier hint.
**Files changed:**
- `plugin/skills/brainstorm/SKILL.md`
**Do not change:**
- One-question-at-a-time interactive flow unchanged — no per-checkpoint fable Agent calls (judge-pinned).

## [2026-06-12] — plan SKILL declaration rows
**Request:** fable-routing part 2 wave 1.
**Built:** Routing row, complexity clause, and cost-table note now reference the declaration gate and fable→opus preview render.
**Files changed:**
- `plugin/skills/plan/SKILL.md`
**Do not change:**
- Frontmatter description untouched — reconciled 2026-06-11.

## [2026-06-12] — orchestrate fable→opus fallback
**Request:** fable-routing part 2 wave 1.
**Built:** Fable Agent-dispatch errors retry once with no override; ledgered via append_routing + wave-summary marker. Complementary to (not touching) the codex reroute-first rule.
**Files changed:**
- `plugin/skills/orchestrate/SKILL.md`
**Do not change:**
- Exactly ONE retry; second failure is ordinary FAIL. Fallback ledger uses model=opus, never task.executor.

## [2026-06-12] — default-forward + codex-reroute owner rules
**Request:** Owner (2026-06-11): 'if codex is blocked assign to sonnet and continue; if no answer, move on' — implement in renmark itself.
**Built:** handoff-menu.md rule 8 rewritten: reversible hand-offs default-forward to the (Recommended) option after one restated unanswered ask; dispatch gates default-forward only with validated plan + visible cost preview; REQ-12 gates never default. orchestrate SKILL Tier-2 gains reroute-first: codex usage-limited non-bulk tasks re-route to sonnet Agent calls (ledgered via append_routing + wave-summary note, no double-counting); Claude-side limits still pause. CLAUDE.md + template executor-dispatch blocks carry the exception line.
**Files changed:**
- `plugin/skills/_shared/handoff-menu.md` — rule 8 default-forward policy
- `plugin/skills/orchestrate/SKILL.md` — reroute-first on codex limits
- `CLAUDE.md`, `plugin/templates/CLAUDE.md.template` — dispatch-rule exception line
**Do not change:**
- REQ-12 gates (merge/release/PRD/budget/destructive) NEVER default-forward — silence is a no.
- Reroutes are always ledgered; bulk-emission waves never re-route to sonnet.

## [2026-06-12] — preamble hint tests
**Request:** fable-routing part 1 wave 3 (codex retry after usage pause).
**Built:** Synthesis-skill hint presence/absence + both-fire ' | ' composition pinned; lifecycle.py hunk is ruff-format-only.
**Files changed:**
- `tests/test_lifecycle.py`
- `renmark/lifecycle.py`
**Do not change:**
- Tests monkeypatch.delenv RENMARK_TOP_TIER — the env override is global state; new tests must do the same.

## [2026-06-12] — engine preview fallback tests
**Request:** fable-routing part 1 wave 3 (codex retry after usage pause).
**Built:** Undeclared repo renders fable→opus at 0.015; declared renders fable at 0.030.
**Files changed:**
- `tests/test_engine_budget_and_rollback.py`
**Do not change:**
- Tests monkeypatch.delenv RENMARK_TOP_TIER — the env override is global state; new tests must do the same.

## [2026-06-12] — plan_lint fable-gate tests
**Request:** fable-routing part 1 wave 3 (codex retry after usage pause).
**Built:** Undeclared BLOCK, declared pass, mechanical BLOCK-even-declared; test_executor_fable_lints_clean fixture now declares top_tier (expected-red resolved).
**Files changed:**
- `tests/test_plan_lint.py`
**Do not change:**
- Tests monkeypatch.delenv RENMARK_TOP_TIER — the env override is global state; new tests must do the same.

## [2026-06-12] — capabilities tests
**Request:** fable-routing part 1 wave 3 (codex retry after usage pause).
**Built:** 7 behaviors pinned: absent/declared/explicit/garbage file values, env override + invalid-env fallthrough, executor passthrough, heading-bounded parsing.
**Files changed:**
- `tests/test_capabilities.py`
**Do not change:**
- Tests monkeypatch.delenv RENMARK_TOP_TIER — the env override is global state; new tests must do the same.

## [2026-06-11] — check-plan doc mirror
**Request:** fable-routing part 1 wave 2.
**Built:** Checks list gains the two fable BLOCK rows; lead-in count corrected 8→10.
**Files changed:**
- `plugin/skills/check-plan/SKILL.md`
**Do not change:**
- Doc rows 9-10 mirror plan_lint._check_fable_declared/_check_fable_mechanical exactly.

## [2026-06-11] — preamble tier hint
**Request:** fable-routing part 1 wave 2.
**Built:** skill_preamble surfaces 'declared top tier: fable — … (/model fable)' for brainstorm/plan/prd/blueprint when declared; composes with cross-domain hint via ' | '.
**Files changed:**
- `renmark/lifecycle.py`
**Do not change:**
- skill_preamble still returns one bounded string or None — callers depend on that contract.

## [2026-06-11] — engine preview + env knob
**Request:** fable-routing part 1 wave 2.
**Built:** Dry-run maps executors through capabilities.effective_executor; undeclared fable rows render 'fable→opus' at opus rate; Config gains validated top_tier field.
**Files changed:**
- `renmark/cli/_engine.py`
**Do not change:**
- Config() construction now requires top_tier kwarg — from_env is the only constructor site.

## [2026-06-11] — plan_lint fable gates
**Request:** fable-routing part 1 wave 2.
**Built:** Checks 9-10: BLOCK executor:fable in undeclared projects; BLOCK fable on simple/mechanical tasks (unconditional REQ-2).
**Files changed:**
- `renmark/plan_lint.py`
**Do not change:**
- plan_lint severities mirror check-plan SKILL §1-2.5 (now 10 checks) — change both sides + tests together. NOTE: test_executor_fable_lints_clean is expected-red until task 7 (same run) declares top_tier in its fixture.

## [2026-06-11] — capabilities module
**Request:** fable-routing part 1 task 1 — the declared-capability resolver.
**Built:** renmark/capabilities.py: read_tiers parses the ## Model tiers block from .renmark/memory/routing.md; top_tier resolves RENMARK_TOP_TIER env > file > opus; effective_executor maps fable->opus when undeclared, passes everything else through.
**Files changed:**
- `renmark/capabilities.py` — new pure-function stdlib module
**Do not change:**
- Resolution order is env > file > opus and unknown values fall through (never raise) — plan_lint/engine/lifecycle all depend on this being side-effect-free.

## [2026-06-11] — PRD updated (REQ-2: declared-capability Fable routing)
**Request:** Adopt the fable-routing strategy decided 2026-06-11: make Fable the default for ideation/strategy synthesis when a project declares `top_tier: fable`.
**Built:** Reconciled REQ-2 of `PRD.md`: Fable is the DEFAULT for ideation/strategy-synthesis/adversarial-review roles in projects with a committed `top_tier: fable` declaration (`.renmark/memory/routing.md`, `RENMARK_TOP_TIER` override); undeclared projects keep escalation-only, byte-identical behavior; availability declared never detected; mechanical/bulk prohibition absolute + deterministically enforced; Fable→Opus fallback single-retry and logged. Bumped `last_reviewed` to 2026-06-11; appended revision note. Approved via the `/renmark:prd` UPDATE diff gate.
**Files changed:**
- `PRD.md` — REQ-2 amendment + revision note; `last_reviewed` bump
**Do not change:**
- PRD.md is human-owned. Automated stages may PROPOSE edits but never write without explicit approval.
- The mechanical/bulk prohibition on Fable is unconditional — no declaration unlocks it.
- Strategy decision record: `.renmark/research/2026-06-11-fable-routing-strategy.md` — the implementing feature must follow it (capabilities.py, plan_lint gates, logged fallback, init/doctor declaration).

## [2026-06-11] — v0.11.0 — fable executor tier (engine + tests + doc sync)
**Request:** Make fable (Claude Fable 5, claude-fable-5) a first-class renmark executor tier above opus per the human-approved REQ-2 amendment; full pipeline: orchestrate (2 plans, 23 tasks) → verify → codereview → fix → merge → release.
**Built:** Engine: parser allowlist, CLAUDE_EXECUTORS Agent-path routing (fable = the only executor with an explicit model override), plan_lint G5 heavy-read BLOCK, $0.030/kT in COST_PER_KT + _estimate_cost + engine dry-run table (last two were codex-review catches). Tests: 5 fable pins across parser/dispatch/plan_lint/roadmap/engine suites. Docs: 14 prose surfaces synced (SKILLs, shims, CLAUDE/AGENTS + templates, README, routing.md) + 6 review-fix sites (escalation wording, PLAN.md dispatch truth, installers, package docstring). Reviews: part 1 — 0 critical/2 major (fixed)/2 minor; part 2 — 0 critical/3 major/3 minor (5 fixed, 1 deferred by decision).
**Pipeline evidence:** verify 4/4 (part 1) + 4/4 (part 2); pytest 723 passed/28 skipped; ruff + format + mypy strict clean; audit --quick PASS; version parity 7/7 at 0.11.0.
**Do not change:**
- Fable is escalation-only under current REQ-2 — the adopted declared-capability routing strategy (.renmark/research/2026-06-11-fable-routing-strategy.md) changes this via a human-gated PRD amendment in the NEXT feature; brainstorm's "Fable 5 when available" wording is intentional under that plan.
- Fable must never dispatch as a codex subprocess; haiku/sonnet/opus stay no-override Agent calls.

## [2026-06-11] — codereview fixes (part 2): escalation wording + missed surfaces
**Request:** Codex part-2 review found 3 major / 3 minor; majors 2-3 + all minors fixed (major 1 deferred — see below).
**Built:** plan SKILL+shim descriptions now say fable routes "only by explicit escalation signals, never cost routing" (byte-synced); plan SKILL executor field line includes fable-by-escalation; PLAN.md dispatch table corrected to engine reality (haiku/sonnet/opus no-override, fable the only override-based executor); install.sh + install.ps1 orchestrate rows and renmark/__init__.py docstring gain Fable.
**Files changed:**
- `plugin/skills/plan/SKILL.md`, `plugin/commands/plan.md` — escalation-only wording, synced
- `PLAN.md` — dispatch table truth fix
- `install.sh`, `install.ps1`, `renmark/__init__.py` — missed-surface enumerations
**Do not change:**
- Major 1 (brainstorm "Fable 5 when available" vs escalation-only PRD wording) is DEFERRED BY DECISION, not missed: the adopted fable-routing strategy (.renmark/research/2026-06-11-fable-routing-strategy.md) resolves it via a human-gated REQ-2 amendment making Fable the declared default for ideation/strategy. Do not reword brainstorm back to Opus-default.
- PLAN.md is a historical architecture doc with broader staleness (nim/litellm rows) — only the flagged dispatch row was corrected; full refresh is hygiene work, out of scope.

## [2026-06-11] — routing.md fable default
**Request:** Doc-sync per REQ-2 amendment (part 2).
**Built:** Defaults gain: (signal=ideation|strategy-synthesis|adversarial-audit|refutation-pass, stakes=highest) → fable (escalation only — REQ-2).
**Files changed:**
- `.renmark/memory/routing.md`
**Do not change:**
- Learned overrides section is append-only via memory.append_routing — never hand-edit.

## [2026-06-11] — README executor row
**Request:** Doc-sync per REQ-2 amendment (part 2).
**Built:** Orchestrate row reads Haiku / Codex / Sonnet / Opus / Fable, wave-parallel.
**Files changed:**
- `README.md`
**Do not change:**
- None.

## [2026-06-11] — templates — fable mirror blocks
**Request:** Doc-sync per REQ-2 amendment (part 2); template mirror pair in one commit.
**Built:** CLAUDE template: dispatch rule + tooling row + preferences row. AGENTS template: tooling row (only anchor).
**Files changed:**
- `plugin/templates/CLAUDE.md.template`
- `plugin/templates/AGENTS.md.template`
**Do not change:**
- Templates mirror the root pair — keep shared wording byte-identical when editing either.

## [2026-06-11] — CLAUDE.md + AGENTS.md — fable rule blocks
**Request:** Doc-sync per REQ-2 amendment (part 2); mirror pair lands in one commit.
**Built:** CLAUDE.md gains the fable dispatch rule (Agent call WITH model override), Frontier-reasoning preferences row, and Opus/Fable tooling row. AGENTS.md mirrors the tooling row byte-identically; dispatch/preferences blocks don't exist there (add-nothing-without-anchor honored). Task 8's agent died at the session limit AFTER applying all edits — verified complete on resume. Task 9 verifier deviation: plan's lowercase grep can't match the capitalized-only anchor; verified with grep -qi.
**Files changed:**
- `CLAUDE.md`
- `AGENTS.md`
**Do not change:**
- CLAUDE.md and AGENTS.md are a mirror pair — shared blocks stay byte-identical, same commit.

## [2026-06-11] — check-plan skill — heavy-read mirror
**Request:** Doc-sync per REQ-2 amendment (part 2): mirror of part 1's _HEAVY_READ_BLOCK_EXECUTORS change.
**Built:** Check 4 doc reads sonnet|opus|fable; report example appends fable×e.
**Files changed:**
- `plugin/skills/check-plan/SKILL.md`
**Do not change:**
- plan_lint severities mirror check-plan SKILL §1–2.5 — change both sides + tests together (v0.10.0 guard).

## [2026-06-11] — audit skill — fable escalation note
**Request:** Doc-sync per REQ-2 amendment (part 2).
**Built:** Step 2b: adversarial/delta re-runs SHOULD route refutation subagents to fable (REQ-2 designated adversarial-audit tier); audit stays read-only.
**Files changed:**
- `plugin/skills/audit/SKILL.md`
**Do not change:**
- Audit remains read-only and artifact-bounded.

## [2026-06-11] — codereview skill — fable escalation note
**Request:** Doc-sync per REQ-2 amendment (part 2).
**Built:** Additive note: highest-stakes diffs MAY dispatch fable refutation subagents; codex sandbox pass + bounded summary contract unchanged.
**Files changed:**
- `plugin/skills/codereview/SKILL.md`
**Do not change:**
- Frontmatter description untouched (quoted; strict-YAML gate).

## [2026-06-11] — brainstorm skill + shim — Fable ideator
**Request:** Doc-sync per REQ-2 amendment (part 2).
**Built:** 'using Opus' → 'using the session's top reasoning tier (Fable 5 when available, Opus otherwise)' in both files, byte-synced.
**Files changed:**
- `plugin/skills/brainstorm/SKILL.md`
- `plugin/commands/brainstorm.md`
**Do not change:**
- Skill/shim descriptions stay byte-identical.

## [2026-06-11] — orchestrate skill — fable dispatch
**Request:** Doc-sync per REQ-2 amendment (part 2).
**Built:** Dispatch table gains fable row (Agent tool with model: "fable" override — the one executor with explicit override); ledger comment + prose enumerations extended.
**Files changed:**
- `plugin/skills/orchestrate/SKILL.md`
**Do not change:**
- Fable must never dispatch as a codex subprocess; codex RED-FLAG rule unchanged.

## [2026-06-11] — plan skill + shim — fable tier
**Request:** Doc-sync per REQ-2 amendment (part 2).
**Built:** Routing table fable row (escalation only, never default), $0.030/kT cost row, REQ-2 complexity clause; command-shim description byte-synced.
**Files changed:**
- `plugin/skills/plan/SKILL.md`
- `plugin/commands/plan.md`
**Do not change:**
- Skill frontmatter description and command shim description stay byte-identical (audit description-drift pass).

## [2026-06-11] — codereview fix — dry-run fable pricing
**Request:** Codex review major: fable tasks without est_cost_usd showed as free in dry-run previews.
**Built:** Added "fable": 0.030 to the engine's inline cost_per_kt table + quota note; test pins a fable task at $0.060/2k tokens, never 'free'.
**Files changed:**
- `renmark/cli/_engine.py`
- `tests/test_engine_budget_and_rollback.py`
**Do not change:**
- Cost-rate knowledge is intentionally duplicated in roadmap.COST_PER_KT and _engine's inline table — shared-table refactor deferred; keep both in sync when adding tiers.

## [2026-06-11] — codereview fix — roadmap fable billing
**Request:** Codex review major: fable usage rows billed as $0.0.
**Built:** Added a fable branch to _estimate_cost() (descending-price precedence, no substring shadowing); tests pin 'fable' and 'claude-fable-5' at 0.030/kT direct + end-to-end.
**Files changed:**
- `renmark/roadmap.py`
- `tests/test_roadmap.py`
**Do not change:**
- Match precedence in _estimate_cost is descending-price — new tiers must slot by price order or cheaper substrings shadow them.

## [2026-06-11] — roadmap cost test
**Request:** Test-pin the fable cost row and tier ordering.
**Built:** Added test_cost_per_kt_has_fable_tier pinning COST_PER_KT['fable'] == 0.030 and fable > opus (tier ordering guard). Includes routing.md ledger append from the engine run.
**Files changed:**
- `tests/test_roadmap.py` — task 9 artifact
- `.renmark/memory/routing.md` — task 9 artifact
**Do not change:**
- COST_PER_KT['fable'] must stay strictly greater than opus — ordering is the tier guard.

## [2026-06-11] — plan_lint fable tests
**Request:** Test-pin the G5 heavy-read BLOCK for the fable tier.
**Built:** Added test_heavy_read_fable_block (fable heavy-read BLOCKs like sonnet/opus) and test_executor_fable_lints_clean (well-formed fable plan lints clean). 38 tests now.
**Files changed:**
- `tests/test_plan_lint.py` — task 8 artifact
**Do not change:**
- plan_lint severities mirror check-plan SKILL §1–2.5 — change engine + tests together.

## [2026-06-11] — dispatch grouping test
**Request:** Test-pin that fable tasks route to the Agent path, never the codex subprocess.
**Built:** New test builds a mixed wave (fable + codex) and asserts is_claude_executor('fable') and the wave partition puts the fable task in claude_tasks.
**Files changed:**
- `tests/test_dispatch.py` — task 7 artifact
**Do not change:**
- Fable must never route to the codex subprocess path — this test is the guard.

## [2026-06-11] — parser acceptance test
**Request:** Test-pin the parser's fable acceptance.
**Built:** Added fable to the claude-models acceptance loop and a dedicated test asserting executor: fable parses while unknown executors still raise PlanError naming the allowlist.
**Files changed:**
- `tests/test_parser.py` — task 6 artifact
**Do not change:**
- test_executor_fable_accepted_and_unknown_rejected pins the PlanError allowlist wording — change parser message + test together.

## [2026-06-11] — loop blend-rate comment
**Request:** Doc-truth fix on the per-model rate enumeration.
**Built:** Extended the rate comment with fable 0.030; blended constant value unchanged.
**Files changed:**
- `renmark/loop.py` — Extended the rate comment with fable 0.030; blended constant value unchanged.
**Do not change:**
- COST_PER_KTOKEN_USD blended value itself is intentionally NOT retuned here.

## [2026-06-11] — roadmap cost table
**Request:** Price the fable tier in cost previews.
**Built:** Added "fable": 0.030 to COST_PER_KT after opus, with 2x-opus pricing rationale comment.
**Files changed:**
- `renmark/roadmap.py` — Added "fable": 0.030 to COST_PER_KT after opus, with 2x-opus pricing rationale comment.
**Do not change:**
- Legacy "nim": 0.0 row stays — historical usage rows still reference it.

## [2026-06-11] — plan_lint heavy-read tier set
**Request:** Extend the G5 heavy-read BLOCK to the most expensive tier.
**Built:** Added "fable" to _HEAVY_READ_BLOCK_EXECUTORS alongside sonnet/opus.
**Files changed:**
- `renmark/plan_lint.py` — Added "fable" to _HEAVY_READ_BLOCK_EXECUTORS alongside sonnet/opus.
**Do not change:**
- plan_lint severities mirror check-plan SKILL §1–2.5 — change both sides + tests together.

## [2026-06-11] — CLAUDE_EXECUTORS constant
**Request:** Route fable through the Claude Agent dispatch path.
**Built:** Appended "fable" last in CLAUDE_EXECUTORS (capability order) and updated the AgentDispatch.model comment.
**Files changed:**
- `renmark/providers/claude_agent.py` — Appended "fable" last in CLAUDE_EXECUTORS (capability order) and updated the AgentDispatch.model comment.
**Do not change:**
- CLAUDE_EXECUTORS stays in lowest→highest capability order; fable must remain last.

## [2026-06-11] — parser executor allowlist
**Request:** Register fable as a valid plan executor token.
**Built:** Extended executor allowlist tuple with "fable" and updated the PlanError message to match.
**Files changed:**
- `renmark/parser.py` — Extended executor allowlist tuple with "fable" and updated the PlanError message to match.
**Do not change:**
- Existing executor tokens keep their order — error-message wording is test-pinned downstream (task 6).

## [2026-06-10] — PRD updated (REQ-2 amendment: Fable executor tier)
**Request:** `/renmark:feature fable-integration` flagged PRD drift (Fable absent from the routed executor set); reconcile the Fable tier into the PRD before planning.
**Built:** Reconciled the Goals multi-LLM bullet and REQ-2 of `PRD.md`; bumped `last_reviewed` to 2026-06-10. Routed executor set is now Haiku / Codex / Sonnet / Opus / Fable (`claude-fable-5`, $10/$50 per MTok, 1M context). Approval recorded via the `/renmark:approve` surface (REQ-18 flow), gate cleared by prd after the write.
**Files changed:**
- `PRD.md` — Goals bullet + REQ-2 extension + revision note; `last_reviewed` bump
**Do not change:**
- Fable is an **escalation target, not a default**: reserved for ideation (brainstorm), strategy (plan/prd/blueprint), and adversarial audit/review passes — never mechanical or bulk work. The REQ-2 cheapest-capable-model rule still governs all routing.
- PRD.md is human-owned. Automated stages may PROPOSE edits but never write without explicit approval.

## [2026-06-10] — v0.10.0 — deterministic planning and verification hardening
**Request:** One-thing minor release via the full /renmark:feature pipeline: move check-plan's structural validation into deterministic Python, rewire both surfaces onto one engine, test-pin everything, release as v0.10.0.
**Built:** `renmark/plan_lint.py` — the single authoritative implementation of check-plan's 8 checks (severities behavior-preserved: 1–6 BLOCK incl. the `test -f`→WARN refinement, 7–8 WARN; sanity extras WARN-only), composing `parser.parse_plan`, never raising (PlanError → graceful BLOCK), with `lint_plan()` API + CLI (`python -m renmark.plan_lint`, exit 0 PASS/WARN, 1 BLOCK). `/renmark:check-plan` collapses its manual Steps 1–2.5 into the engine invocation (bounded report passed through verbatim; judgment smells stay advisory); `/renmark:orchestrate` pre-flight runs the SAME engine — a text-pin test asserts both surfaces reference it so they can never drift. 36 tests pin every check + CLI exit codes. Doc rows updated in CLAUDE/AGENTS/templates/help.
**Pipeline evidence:** PRD alignment `aligned` (REQ-5/7/3, no PRD change); plan validated by its own engine — which BLOCKed the original plan on 6 genuine G5 heavy-read violations the prose-era check missed (plan fixed, not the rule); verify 4/4 goal-backward behaviors; codereview 0 critical / 2 major / 2 minor — all four fixed before tagging (node/python verifier-bound trigger restored, find/-name and git-log cap shapes, stray audit artifacts dropped from the branch).
**Files changed:**
- `renmark/plan_lint.py` (new) + `tests/test_plan_lint.py` (new, 36 tests)
- `plugin/skills/check-plan/SKILL.md`, `plugin/skills/orchestrate/SKILL.md`, `plugin/commands/check-plan.md` — engine rewiring
- `CLAUDE.md`, `AGENTS.md`, both templates, `plugin/skills/help/SKILL.md` — check-plan row wording
**Do not change:**
- Both SKILLs must keep the literal `python -m renmark.plan_lint` invocation — tests/test_plan_lint.py text-pins it (the no-drift guard).
- plan_lint severities mirror check-plan SKILL §1–2.5; changing either side alone breaks the contract — change both + the tests together.
- Deferred (explicit): verify --bootstrap extraction; workspace-level ~/projects/CLAUDE.md still says v0.4.0 (outside repo, awaiting separate approval — needed diff: "(v0.10.0, current)").

## [2026-06-09] — v0.9.1 — leftovers patch (engine safety polish, audit passes, doc truth)
**Request:** Close the gaps left open at v0.9.0 (user-tightened patch scope: engine TOCTOU/porcelain, two new audit passes, routing.md truth, resume event, hygiene hint) — plan → execute → gate → adversarial review → release.
**Built:** Workflow with 2 implementation agents + full gate battery + 2 Opus adversarial reviewers (0 critical / 0 major / 2 minor — both minors fixed before tagging).
- **Engine:** rollback classification+action now atomic under ONE `_GIT_LOCK` (`_classify_and_rollback`, `_judge_lane_and_rollback`; lock never held during the codex subprocess; 8-thread stress-verified); porcelain switched to `-z --untracked-files=all` — unicode/space/newline paths verbatim, rename/copy records handled, and **two latent bugs fixed that the new direct tests exposed**: new-directory targets no longer collapse to `dir/` and judge out-of-lane against their own work, and out-of-lane rollback now spares the task's own target (extras only).
- **Audit:** `registry_sync` flags SKILL.md-less dirs; new `no-raw-jsonl` pass (flag-token aware, prohibition-tolerant) and `disclaimer` pass (pins usage/analytics governance markers); output keys backward compatible; both at 0 on the real repo.
- **Docs/runtime gaps:** routing.md Format section now documents the real `append_routing` format + newest-entry-wins rule (root + template); `resume` analytics event emitted at the two real resume paths; hygiene argument-hint leads with the safe default.
**Gates at release:** pytest 680 passed / 28 skipped · RENMARK_SMOKE 28 · ruff check + format clean · mypy strict clean · precommit 6/6 (incl. shadow) · audit --quick PASS across all 7 passes · version parity 7/7 at 0.9.1.
**Do not change:**
- `_GIT_LOCK` is a non-reentrant `threading.Lock` — code inside `_classify_and_rollback`/`_judge_lane_and_rollback` must only call `*_locked` helpers, never the lock-acquiring wrappers.
- `--untracked-files=all` on the porcelain snapshot is load-bearing — removing it re-introduces the new-directory out-of-lane false positive.
- Deferred by explicit scope decision (NOT forgotten): check-plan Python backing, verify --bootstrap extraction, workspace-level CLAUDE.md edit — candidates for v0.10/feature work.

## [2026-06-09] — v0.9.0 — audit-implementation release (all findings + 3 new skills)
**Request:** Orchestrate Opus/Sonnet agents to implement ALL findings from both audits (Opus original + Fable 5 delta), including the PRD scope update, build /renmark:audit + /renmark:inventory (+ the gate-completing /renmark:approve), test everything, and release as v0.9.0.
**Built:** Two implementation waves (8 agents: 2 opus engine/state, 6 sonnet) on branch `feature/audit-cleanup-v0.9.0`, gates between waves.
- **Engine criticals fixed:** execute_plan budget/deadline exhaustion now writes pause state, extends `skipped` with all remaining waves, exits 10 — never false success; parallel codex waves use per-task porcelain deltas + sibling-target exclusion + path-scoped rollback (never `git checkout -- .`); mode-aware rollback deletes untracked mode-A targets; cmd_task validates artifacts and emits all six G9 fields; UsageRecord.attempt with retry-idempotent ledgering; honest token-summary line.
- **State machine:** registries ghost-free (26 skills exact parity, test-pinned via the new audit engine); `restored` stage cut; `reviewed`/`released` stages now written (codereview/finish); `clear_lifecycle` wired into finish; approve router live; all 8 schema validators wired at writers; EVENT_KINDS registry with real emitters (release, pause/rate_limit/quota, backlog_*).
- **NEW skills (23→26):** `/renmark:audit` (read-only self-audit: registry-sync + shim-thinness + description-drift + strict lint + version parity + modularity; artifacts under `.renmark/audits/`), `/renmark:inventory` (thin alias, --inventory-only), `/renmark:approve` (sole human_review_completed flip surface). New `renmark/audit.py` + 20 tests. PRD gains REQ-17/REQ-18 (user-authorized 2026-06-09) — this supersedes the earlier "approve is not shipped" Do-not-change guard: **approve ships in 0.9.0**.
- **Dead layer deleted:** providers nim/openai_compat/openrouter/ollama, apply.py, prompts.py, write_run_report, `requests` dep — mypy strict now clean repo-wide.
- **Docs/memory:** every surface regenerated from code (help 26, CLAUDE/AGENTS/README/templates, domain tables, manifests author=renmark); 8 invalid frontmatters fixed + strict-YAML lint pass in precommit/CI; CONTRIBUTING rewritten; memory files repaired (features backfill, INDEX truth, ADR-022 correction); shadow harness wired into precommit/CI/pytest as a hard gate.
**Gates at release:** pytest 658 passed / 28 skipped (incl. RENMARK_SMOKE integration) · ruff clean · mypy strict clean (41 files) · `python -m renmark.audit --quick` → PASS (0 issues) · version parity 7/7 at 0.9.0.
**Do not change:**
- The audit engine's registry-sync pass is the permanent drift net — when adding a skill, plugin dirs AND lifecycle registries must move together or `pytest`/`renmark.audit` fail.
- `usage.append_usage` dedupes ONLY attempt>0 rows; attempt-0 rows must always append (roadmap's retry detection counts them).
- Strict-frontmatter lint is ON in precommit/CI — frontmatter descriptions containing ": " must stay quoted.

## [2026-06-09] — delta audit (Fable 5 re-run) + P0 fix wave
**Request:** Re-run the Opus audit adversarially, find what it missed, and fix the confirmed problems.
**Built:** 19-agent delta workflow: 10 verifiers (told to REFUTE each original top finding, with empirical repro), 7 novel sweeps (inline-python contracts, unexamined engine modules, plugin-spec, memory staleness, security, prose drift), live dev-gates run, PRD-alignment check. Verdicts: 8 confirmed / 2 partial / 0 refuted, plus **66 novel findings** — 3 critical (loop decision engine never receives summary_lines → every failed verify stalled the loop; execute_plan false-success on budget exhaustion; parallel codex wave rollback can destroy sibling work), 2 security (release zips packaged `.env.production`/`*.pem`/etc. and finish uploads them to GitHub releases; cmd_task ran codex with no --sandbox flag). Gates ground truth: pytest green, but ruff/mypy NOT INSTALLED in .venv and failing when run (39 test-file lint errors, 2 mypy errors in dead providers). Fix wave landed 8 commits (see below); full suite 625 passed / 28 skipped.
**Files changed:**
- `renmark/lifecycle.py`, `renmark/state/skills.py`, `renmark/dispatch.py` — resume-killer reader hardening + G9 confidence downgrade (0a4efcb, 7b2fef1, 618624c)
- `renmark/state/{usage,pipeline,logs}.py`, `renmark/roadmap.py` — remaining fragile readers (cf3a442)
- `renmark/analytics.py`, `renmark/memory.py` — idempotent record_feature_run + append_routing (41eddd8)
- `renmark/release.py`, `renmark/cli/commands.py` — secret-file package excludes (with .env.example allowlist); explicit codex sandbox (294a54e)
- `renmark/summary.py` — new `read_summary_lines` (body-bullet reader); loop/finish SKILLs rewired (29bb737)
- `plugin/skills/{orchestrate,verify,backlog,feature,prd}/SKILL.md`, `.renmark/memory/routing.md` + template — inline-python contract repairs, dead-route removals, nim→haiku (b3e37d0)
- `.renmark/audits/audit-delta-2026-06-09.md` — full delta report incl. revised P0 queue and /renmark:audit design input
**Do not change:**
- `read_summary_lines` strips the leading `- ` bullet — `loop._FAILED_RE`/`_SYMPTOM_RE` anchor on unprefixed lines; reintroducing the prefix silently re-stalls loops.
- `record_feature_run` dedup key is (feature, sha, status, branch_disposition) — a re-release with a new sha is intentionally a new row.
- `.env.example/.env.sample/.env.template` are allowlisted in PACKAGE_ALLOW; don't "simplify" the `.env*` exclude by removing the allowlist.
- Remaining P0s (engine false-success, parallel-wave rollback, registry/docs/template mega-sync, /renmark:approve + PRD addendum) are queued in audit-delta-2026-06-09.md §7 — approve needs the human-gated PRD scope update first.

## [2026-06-09] — skill-feature inventory & modularity audit (read-only)
**Request:** Run the read-only skill/feature inventory + modularity audit per the committed spec (`.renmark/audits/skill-feature-inventory-spec.md`, 9a050a8); audit artifacts only, no refactors.
**Built:** Full 23-command inventory + 13-dimension audit via 8 parallel read-only subagents, synthesized into 6 dated artifacts (+ JSON mirror) under `.renmark/audits/`. Pre-findings confirmed (hygiene is GC not inventory; DOMAIN_BY_SKILL ghosts). Top findings: (1) `lifecycle.read_lifecycle` + `state.skills.last_skill_invocation` raise on corrupt valid-JSON state — resume-killers; (2) `/renmark:approve` is cited by backlog/resume/loop/CLAUDE.md but does not exist; (3) 0/8 `schemas.py` validators have production call sites (2 fully dead); (4) `lifecycle.py` registries drifted (8 ghost skills, 5 missing real ones incl. usage/analytics; IMPLEMENTED_SKILLS missing 9); (5) finish re-run double-counts feature analytics (blind-append). 7 of 9 overlap hotspots clean; storage-layer single-source-of-truth holds everywhere; version parity healthy at 0.7.8. 24-item prioritized cleanup backlog proposed (NOT implemented).
**Files changed:**
- `.renmark/audits/skill-feature-inventory-2026-06-09.md` + `.json` — 23-row inventory matrix + machine mirror
- `.renmark/audits/ownership-source-of-truth-map-2026-06-09.md` — canonical home per concept, violators ranked
- `.renmark/audits/overlap-findings-2026-06-09.md` — 9 spec hotspots + 3 discovered
- `.renmark/audits/modularity-scorecard-2026-06-09.md` — layering grades, _shared dedup, G1–G12 matrix, dead code, version parity
- `.renmark/audits/context-hygiene-and-safety-risks-2026-06-09.md` — resume-killers, gate holes, idempotency, test gaps
- `.renmark/audits/recommended-cleanup-backlog-2026-06-09.md` — P0/P1/P2 backlog (proposed only)
**Do not change:**
- Audit pass is read-only by contract — cleanup goes through a separate follow-up feature, never retrofitted into these artifacts.
- plugin/commands ↔ plugin/skills 1:1 parity (23/23) is the only fully-correct registration surface — keep it that way when adding skills.

## [2026-06-09] — reporting-and-usage-analytics Part 2 codereview fixes (6 Major + 2 Minor)
**Request:** Fix all codex-review findings on the Part-2 surfaces+integration diff before finish.
**Built:** Codex flagged 8 integration-contract bugs (the opus-written prose referenced fields/attrs/vocab absent from the Part-1 engine); all confirmed real and fixed. Code: (F1) `cmd_usage` no longer early-returns on an empty ledger — always renders the bounded view so the mandatory disclaimer + paused/limit state always show; (F2) `build_usage_view` now returns a `limit_exceeded` boolean (True when any real per-provider percent ≥ 100) so orchestrate's Tier-1 preflight has a working signal. Skill prose: (F3) orchestrate `record_task_run` passes a normalized `verifier_result="pass"/"fail"` (analytics classifies on these, not free text); (F4) finish reads the verification result from the verify artifact's bounded metadata via `summary.read_metadata` (LifecycleState has no `verification_result` attr); (F5) finish maps the lifecycle stage to analytics vocab (`shipped`/`completed`/`blocked`) instead of passing the raw stage; (F6) loop records per-iteration metrics via `record_event(kind="loop_iteration")` and calls `record_loop_run` exactly once at the terminal break (per-iteration `record_loop_run` inflated `_agg_loops` totals); (F7) loop's `classify_usage_pause` now passes `repo=` so the local rolling-window fallback works; (F8) finish snippet imports `subprocess`. Gate: 608 passed / 28 skipped, ruff + mypy clean. Each fix independently re-probed (empty-repo disclaimer, limit_exceeded over-limit flip to True at 250%, API existence).
**Files changed:**
- `renmark/cli/commands.py` — F1: always render usage view
- `renmark/usage.py` — F2: `limit_exceeded` field in `build_usage_view`
- `plugin/skills/orchestrate/SKILL.md` — F3: normalized `verifier_result`
- `plugin/skills/finish/SKILL.md` — F4/F5/F8: artifact-metadata verification, stage→vocab map, `import subprocess`
- `plugin/skills/loop/SKILL.md` — F6/F7: per-iteration event vs terminal loop-run, `repo=` on pause classify
**Do not change:**
- `verifier_result` recorded to analytics MUST be a normalized `pass`/`fail` token; feature-run `status` MUST be analytics vocab (`shipped`/`completed`/`blocked`), NOT a raw lifecycle stage. `record_loop_run` is one-row-per-loop (terminal only) — per-iteration data goes through `record_event`.
- `build_usage_view` returns `limit_exceeded` (bool); Tier-1 preflight depends on it. The empty-ledger path of `cmd_usage` MUST still render the disclaimer.

## [2026-06-09] — reporting-and-usage-analytics Part 2 (surfaces + integration) orchestrated
**Request:** Surface the Part-1 engine to users and wire it into the live pipeline (REQ-15/REQ-16).
**Built:** 12 atomic tasks across 6 waves on `feature/reporting-and-usage-analytics` (haiku×4, sonnet×6, opus×2). CLI: `cmd_usage` now delegates to `usage.build_usage_view`/`render_usage_md`; new `cmd_analytics` (aggregate + build-health, writes `.renmark/memory/analytics.md`); `--analytics` flag wired in `_engine.py`; re-exported from `cli/__init__.py`. New command shims `plugin/commands/{usage,analytics}.md` + zero-LLM skills `plugin/skills/{usage,analytics}/SKILL.md` (invoke `renmark-execute --usage/--analytics`, display bounded output only). Integration: `finish` writes the feature report + `record_feature_run` + `[a] Analytics` menu; `orchestrate` gained Tier-1 usage preflight + per-task `record_task_run` + Tier-2 `usage_limit` pause-not-fail; `loop` records per-iteration `record_loop_run` + usage-limit pause hook; `resume` surfaces `pause_kind==usage_limit` runs with suggested resume time + disclaimer. `.gitignore` ignores raw `.renmark/analytics/*.jsonl` while keeping `summary.json`/`limits.json`/`reports/`. Full gate: 608 passed / 28 skipped, ruff + mypy clean.
**Files changed:**
- `renmark/cli/commands.py`, `renmark/cli/_engine.py`, `renmark/cli/__init__.py` — usage/analytics handlers + flag + re-export
- `plugin/commands/usage.md`, `plugin/commands/analytics.md` — command shims (new)
- `plugin/skills/usage/SKILL.md`, `plugin/skills/analytics/SKILL.md` — zero-LLM skills (new)
- `plugin/skills/finish/SKILL.md`, `plugin/skills/orchestrate/SKILL.md`, `plugin/skills/loop/SKILL.md`, `plugin/skills/resume/SKILL.md` — integration touchpoints
- `.gitignore` — raw analytics JSONL ignored, durable summary/limits/reports kept
**Do not change:**
- Skills NEVER read `.renmark/analytics/*.jsonl` or `.renmark/state/usage.jsonl` into context — they run `renmark-execute --usage/--analytics` and display only the bounded rendered output (REQ-5).
- The `*.jsonl` gitignore rule is followed by explicit `!summary.json` / `!limits.json` un-ignores — do not reorder so the wildcard shadows them; `.renmark/reports/` stays committed.
- `now`/`ts` injected everywhere via `state.now_iso()` — no `datetime.now()` in the new integration prose. Usage pause is an ADDITIONAL loop stop condition, not a replacement for REQ-9/REQ-11 budget/max-iter/goal-backward bounds.
- No AGENTS.md mirror was made: these tasks add skill behavior under existing bounded-output/context-hygiene governance rules; no governance *rule* changed.

## [2026-06-09] — reporting-and-usage-analytics Part 1 (engine) orchestrated
**Request:** Build the deterministic Python engine for local reporting/analytics/usage (REQ-15) + usage-aware pause/resume (REQ-16).
**Built:** 9 atomic tasks across 5 waves on `feature/reporting-and-usage-analytics`. New modules `renmark/usage.py` (windowed usage view, limits + percent-used, `classify_usage_pause` fallback rule, `render_usage_md` w/ mandatory disclaimer), `renmark/reports.py` (feature/run report builders → `.renmark/reports/`), `renmark/analytics.py` (append-only JSONL event ledgers under `.renmark/analytics/` + `aggregate()`→summary.json + `build_health_report`). Extended `renmark/state/pause.py` (usage-limit `PauseState` fields + `usage_limit_pause`, back-compatible) and `renmark/state/usage.py` (enriched `UsageRecord` + now-injected window helpers). Added 4 `schemas.py` validators. 15 new tests; full suite 608 passed; mypy clean.
**Files changed:**
- `renmark/usage.py`, `renmark/reports.py`, `renmark/analytics.py` — new engine modules
- `renmark/state/pause.py`, `renmark/state/usage.py`, `renmark/state/__init__.py` — back-compatible extensions
- `renmark/schemas.py` — 4 non-raising validators
- `tests/test_state_pause_usage.py`, `tests/test_usage.py`, `tests/test_reports_analytics.py` — new
**Do not change:**
- The existing `.renmark/state/usage.jsonl` ledger stays the token source of truth — analytics windows READ it; do NOT create a second token ledger. The new `.renmark/analytics/` tree holds only the new event streams + summary.json + limits.json.
- `PauseState` / `UsageRecord` extensions are additive + keyword-defaulted — old PAUSED files and usage.jsonl rows must keep loading. No `datetime.now()` in these modules — `now`/`ts` is always injected.
- `render_usage_md` output MUST always end with "Observed local usage only. Provider-side account limits may differ."
- Part 2 (CLI `--analytics`, `/renmark:usage` + `/renmark:analytics` commands+skills, orchestrate/loop/finish/resume integration, gitignore) is NOT built yet — feature-level verify runs after Part 2.
- Pre-existing 39 ruff errors in other `tests/` files were untouched (not introduced by this feature).

## [2026-06-09] — PRD updated (REQ-15 / REQ-16: local reporting, analytics, usage status + usage-aware pause/resume)
**Request:** `/renmark:feature reporting-and-usage-analytics` flagged PRD drift; reconcile the new local observability surface into the PRD before planning.
**Built:** Reconciled Requirements, Scope boundaries, and Open questions of `PRD.md`. Added `REQ-15` (local-only reporting/analytics/usage status — on-disk JSON/JSONL, `/renmark:usage` + `/renmark:analytics`, no external telemetry/DB) and `REQ-16` (usage-aware safe pause/resume on rate/quota limits — extends REQ-3/10/12). Registered `usage` + `analytics` in the in-scope skill list and added the reporting/analytics/usage layer to the in-scope clause. Resolved the long-standing "minimum viable telemetry" open question. `last_reviewed` already 2026-06-09.
**Files changed:**
- `PRD.md` — added REQ-15 + REQ-16; in-scope skills/layer; resolved telemetry open question
**Do not change:**
- Reporting/analytics is **observed-local only** — no external telemetry, no database, stdlib JSON/JSONL only; account-limit output must carry "Observed local usage only. Provider-side account limits may differ." unless a provider source is explicitly available.
- Orchestrator never reads raw JSONL into context (REQ-5); all renmark writes stay under `.renmark/` (REQ-6).
- MVP must NOT poll for quota or auto-schedule retries; usage limits pause-not-fail for later `/renmark:resume`.

## v0.7.8 — 2026-06-09 (Release version snapshot — `.renmark/version/`)

**Release of the canonical local version-snapshot protocol.** Bumped 0.7.7 → 0.7.8 across
all 7 version locations. Shipped on `main` via `--no-ff` merge of
`feature/release-version-snapshot` (verified 7/7; full codex codereview 1 Critical /
3 Major / 2 Minor / 1 Nit — all fixed on-branch + independently re-probed; 593 tests +
mypy + lint_all clean). **This release dogfoods itself** — packaged via the new
`python -m renmark.release snapshot`.

- **`renmark/release.py`** — new `build_version_snapshot()` writes BOTH a portable zip
  (`<basename>-v<VERSION>.zip`) AND an unpacked, browsable `v<VERSION>/` snapshot
  (`manifest.json` + `release.md` + `verification.md` + `files-changed.txt`) under the new
  canonical home `.renmark/version/`. `build_package` default home baks→version (`.renmark/baks/`
  retained, legacy-readable). New `snapshot` CLI subcommand (`--dest`/`--name` supported).
  Reuses `PACKAGE_EXCLUDES`/`_is_excluded` (self-excludes `.renmark` → no recursion).
- **Security:** release packaging now SKIPS symlinks (closes a host-secret-leak vector
  where a repo-local symlink would be dereferenced into the zip/snapshot — also fixed in
  the pre-existing `build_package`).
- `verification.md` is matched to the release's HEAD sha; CHANGELOG section matched by
  exact version token (`1.2.3` ≠ `v1.2.30`).
- `renmark/init.py` scaffolds `.renmark/version/` into the gitignore set; `/renmark:finish`
  §4 documents the new protocol + timing contract (snapshot is the last LOCAL step, before
  remote publish). 44 release tests.

## [2026-06-09] — release-version-snapshot (verified + codereview-hardened)

**Request:** Codereview + fix pass on the release-version-snapshot feature before finish.
**Built:** Full codex review (1 Critical / 3 Major / 2 Minor / 1 Nit) → all findings fixed on-branch.
**Files changed:**
- `renmark/release.py` — CRITICAL: skip symlinks in `build_package` + snapshot copy (no host-secret leak via a repo-local symlink); changelog section matched by exact version token (`1.2.3` ≠ `v1.2.30`); `verification.md` selected by current HEAD sha; `build_version_snapshot` gained `dest_dir`/`archive_stem`/`verification_path`; `snapshot` CLI parses `--dest`/`--name`; robust snapshot-dir cleanup. +5 tests (44 in file).
- `plugin/skills/finish/SKILL.md` — `[r]` menu + override note baks→version; `--dest`/`--name` documented accurately; timing reworded to "last LOCAL artifact step (before remote publish 4d)".
**Do not change:**
- Release packaging MUST skip symlinks (never dereference a repo-local symlink into the zip/snapshot) — this was a real secret-leak vector.
- `verification.md` in a snapshot is matched to the release's HEAD sha, not the lexicographically-last artifact.
- Verified 7/7; full suite 593 pass (+5 fix tests); mypy + lint_all clean.

## [2026-06-09] — release version snapshot (.renmark/version) — orchestrate complete, pre-verify

**Request:** On finish/release, version the app and create a local snapshot under `.renmark/version/` as part of the release protocol.
**Built:** 7 tasks across 2 waves, all PASS (588 tests, +13; mypy + lint_all clean).
**Files changed:**
- `renmark/release.py` — `VERSION_SUBDIR=".renmark/version"`; `build_package` default home baks→version (baks retained, legacy-readable); new `build_version_snapshot(repo,*,version,now)` writes a zip + unpacked `v<VER>/` (manifest.json, release.md, verification.md, files-changed.txt), reusing `build_package`/`PACKAGE_EXCLUDES`/`_is_excluded` (self-excludes `.renmark` → no recursion); new `snapshot` CLI subcommand.
- `tests/test_release_snapshot.py` (13 tests) + `tests/test_release_drift.py` (baks→version expectation).
- `renmark/init.py` — `.renmark/version` added to the gitignore-scaffold set.
- `plugin/skills/finish/SKILL.md` + `plugin/commands/finish.md` — §4 release protocol → `release snapshot`; timing contract (snapshot only after merge approval → merge → verify → tag).
- `.gitignore` — ignore `.renmark/version/`.
**Do not change:**
- `.renmark/version/` is the canonical release home; `.renmark/baks/` is legacy (readable, never written by new releases). No artifact duplication across the two.
- The snapshot self-excludes `.renmark` (incl. version/ and baks/), `.git`, `node_modules`, caches — reuse `_is_excluded`, never hand-roll a second exclude set.
- The snapshot is the LAST release step — only after merge approval → merge to main → final verify passes → version/tag known.

## v0.7.7 — 2026-06-09 (Backlog-driven loop execution — `/renmark:backlog`)

**Release of the backlog intake + approval-buffer feature (REQ-13/REQ-14).** Bumped
0.7.6 → 0.7.7 across all 7 version locations. Shipped on `main` via `--no-ff` merge of
`feature/backlog-driven-loop-execution` (verified 5/5; full codex codereview 0 Critical /
6 Major / 2 Minor — all fixed on-branch + independently re-probed; 575 tests + mypy +
lint_all clean).

- **`/renmark:backlog`** — interactive intake + approval buffer: a list view
  (title/status/source/risk/pending decision) → per-item detail (summary/source/evidence/
  recommended action/risk/status/served reqs) → actions (Approve and build / Research more /
  Split / Reject / Back). "Approve and build" launches **bounded Loop Mode internally**
  (max 5 iterations hardcoded, no user-facing budget/iteration/ID flags) on a managed
  branch, gates on human merge approval, and guarantees every managed branch ends
  merged-deleted / abandoned-deleted / kept (no orphans).
- **`renmark/backlog.py`** — never-raise `BacklogItem` ledger under `.renmark/state/backlog/`:
  `BL-NNNN` ids (atomic `O_EXCL` reservation), path-traversal-safe read/write, id integrity
  (filename authoritative), `managed_branch_name` (ref-safe), exact `completion_report`
  ("N/5") wording, `DISPOSITIONS`, `status_for_outcome`. 24 tests.
- **`plugin/skills/backlog/SCHEDULED-QA.md`** — design-only read-only scheduled-QA proposer
  lane (REQ-14); may inspect/check/research/report/propose, never executes.
- Registered `backlog` in lifecycle (build domain / aux class); tooling row mirrored to
  CLAUDE.md + AGENTS.md; project map refreshed.

## [2026-06-09] — backlog-driven loop execution (verified + codereview-hardened)

**Request:** Codereview + fix pass on the backlog feature before finish.
**Built:** Full codex review (0 Critical / 6 Major / 2 Minor) → all findings fixed on-branch.
**Files changed:**
- `renmark/backlog.py` — path-traversal guard (`_is_safe_item_id` `^BL-\d+$`), true never-raise on serialize, id integrity (filename authoritative), branch-name sanitization, atomic `next_id` reservation (O_CREAT|O_EXCL retry). +5 tests (24 total).
- `plugin/skills/backlog/SKILL.md` — awaiting-merge documented as a tracked resumable interim state (not an orphan); Step 0 resume scans in-progress items + stored `loop_id`; blocked outcome drives `/renmark:debug`.
**Do not change:**
- `next_id` now RESERVES atomically (side effect: writes a `needs review` placeholder); intake/split callers must `write_item` to fill it. `read_item`/`write_item` refuse non-canonical ids (return None).
- A managed branch's disposition is terminal-only; awaiting-merge is interim/resumable, never an orphan.
- Verified 5/5 behaviors; full suite 575 pass (+5 from new fix tests); mypy + lint_all clean. The 39 `ruff check` errors remain pre-existing (v0.7.6 baseline), zero added.

## [2026-06-09] — backlog-driven loop execution (orchestrate complete, pre-verify)

**Request:** Add a vibe-coder `/renmark:backlog` intake + approval-buffer that, on "Approve and build", runs bounded Loop Mode (max 5, no flags) on a managed branch with no-orphan-branch lifecycle; reserve a design-only scheduled-QA read-only lane.
**Built:** 8 tasks across 3 waves, all PASS (570 tests pass, +19 new; mypy + lint_all clean).
**Files changed:**
- `renmark/backlog.py` — never-raise BacklogItem ledger (`.renmark/state/backlog/`), BL-NNNN ids, `managed_branch_name`, `completion_report` (exact "N/5" wording), `DISPOSITIONS` no-orphan invariant, `status_for_outcome`. (REQ-13)
- `tests/test_backlog.py` — 19 tests (round-trip, never-raise on corrupt, id increment, exact wording, dispositions).
- `plugin/skills/backlog/SKILL.md` + `plugin/commands/backlog.md` — interactive list+detail skill; Approve-and-build → bounded Loop Mode (max 5 hardcoded) → human merge gate → merge/re-verify/delete OR blocked+keep/abandon. (REQ-13)
- `plugin/skills/backlog/SCHEDULED-QA.md` — design-only read-only proposer lane seam. (REQ-14)
- `renmark/lifecycle.py` — registered `backlog` (build domain, aux class).
- `CLAUDE.md` / `AGENTS.md` — `/renmark:backlog` tooling row (mirrored).
**Do not change:**
- Backlog is a thin intake/decision layer — does NOT replace feature/plan/orchestrate/verify/finish.
- Approve-and-build hardcodes max 5 iterations; NO user-facing budget/iteration/ID flags; budget escalation + merge stay human-gated.
- Every managed branch ends in exactly one disposition (merged-deleted / abandoned-deleted / kept) — no orphans.
- Scheduled QA lane is read-only/design-only: never edits code/commits/merges/releases/edits PRD/escalates budget/auto-executes.
- The 39 repo-wide `ruff check` errors are PRE-EXISTING (present at v0.7.6 baseline ebcd009); this feature adds zero new ruff errors.

## [2026-06-09] — PRD updated

**Request:** PRD-alignment for the `backlog-driven-loop-execution` feature returned DRIFT — reconcile the backlog/intake + scheduled-QA concepts into the PRD before planning.
**Built:** Reconciled the Requirements, a new "Backlog & lanes" section, and Scope boundaries of PRD.md; bumped last_reviewed.
**Files changed:**
- `PRD.md` — added `REQ-13` (`/renmark:backlog` interactive intake + approval buffer; bounded Loop Mode on a managed branch, default 5 iterations, no orphan branches, human-gated merge) and `REQ-14` (scheduled QA/Deep-QA reserved as a read-only proposer lane — design only, never executes); added the "Backlog & lanes" section (four-lane model + one-code-writing-loop-per-tree parallelism rule); added `/renmark:backlog` to in-scope and narrowed the Deferred "scheduled loops" line to autonomous scheduled *execution* only.
**Do not change:**
- Backlog is a thin intake/decision layer — it must NOT replace `/renmark:feature`, `/renmark:plan`, `/renmark:orchestrate`, `/renmark:verify`, or `/renmark:finish`.
- The scheduled QA lane is read-only: it may inspect/research/check/report/propose, but MUST NOT edit code, commit, merge, release, edit `PRD.md`, escalate budget, or auto-execute.
- Only one code-writing loop may run per working tree; default backlog Loop Mode is capped at 5 iterations; budget escalation stays human-gated.

## v0.7.6 — 2026-06-09 (Loop Mode MVP — bounded resumable agentic loops)

**Release of Loop Mode (MVP).** Bumped 0.7.5 → 0.7.6 across all 7 version locations.
Shipped on `main` via `--no-ff` merge of `feature/loop-mode` (codereview: full codex
— 5 Major + 2 Minor + 1 Nit, all fixed + independently re-verified + regression tests;
551 tests + mypy + lint_all clean). Realizes PRD REQ-9..12 + the Loop Mode section.

- **`renmark/loop.py`** — deterministic, never-raise loop state machine: `loop.json`
  under `.renmark/loops/<id>/`, `parse_budget` (tokens **or** `$`), `build_decision`
  (derives `next_action` from verify evidence so the loop ITERATES on failure),
  `stop_reason` (done / budget-hit / max-iter / awaiting-approval / stalled),
  `should_continue_budget` (preflights budget BEFORE each dispatch — never overshoots),
  `refresh_spent`. Defaults: max-iterations 5, budget 300k tokens.
- **`state.usage_by_run_id`** — aggregates ledger token spend per run (decode-tolerant,
  clamps negatives) — the budget-gate primitive.
- **`/renmark:loop "<goal>"`** (`--goal/--verify/--budget/--max-iterations`) — single
  upfront approval gate, then autonomous orchestrate→verify→decide iterations with a
  bounded per-iteration progress line; commits each passing iteration to the branch,
  STOPS for approval before merge/release (REQ-12). Vibe coders reach it via
  `/renmark:start` (never see "loop"); `/renmark:resume` recovers an in-flight loop.
- Codereview caught the loop's worst bug pre-merge: it would have **stalled on the
  first failed verify** (an automation, not a loop) — fixed.

## [2026-06-09] — project scope: loop-mode (MVP)

**Request:** Implement Loop Mode — bounded, verified, cost-aware, resumable agentic loops as the execution engine (per ChatGPT design + approved PRD REQ-9..12).
**Tech stack:** Python ≥3.10 stdlib + markdown — **no new deps**. New `renmark/loop.py` driver + a `usage_by_run_id` ledger helper; reuses `state.py` (usage.jsonl), verify/orchestrate/resume skills, the plan cost model.
**Deployment:** Claude Code plugin (unchanged).
**MVP boundary:** loop.json state under `.renmark/loops/<id>/`; `/renmark:loop` wrapper (orchestrate→verify→decision per iteration); budget + max-iterations bounds; `/renmark:resume` recovery; goal-backward verify each iteration; `/renmark:start` vibe-coder wiring. **Out of scope:** indefinite autonomous loops; scheduled/PR-triggered loops; per-iteration prompting; loop state in lifecycle.json.
**Decisions (locked):**
- Budget accepts BOTH a token count and a `$` amount; tracked in tokens (the measurable ledger unit) with a `$` estimate shown.
- SINGLE upfront approval (goal+budget+max-iter+verify cmd+cost preview), then autonomous to a terminal state — no per-iteration prompts (single-dispatch-gate doctrine).
- Loop commits each passing iteration to the branch (safe/revertable); STOPS for approval before merge/release/PR/budget-escalation/destructive (REQ-12).
- Loop runtime state in `loop.json` (NOT lifecycle.json — G12); spend enforced against `usage.jsonl` by run_id. Defaults: max-iterations 5, budget 300k tokens (tunable).

## [2026-06-09] — PRD updated: Loop Mode
**Request:** Feature `loop-mode`'s drift gate proposed adding Loop Mode (bounded, verified, cost-aware, resumable agentic loops as the execution engine; new `/renmark:loop`, hidden behind `/renmark:start`). Human-approved with one wording edit.
**Built:** Added REQ-9..12, a new `## Loop Mode` section, and Loop Mode entries to Scope boundaries (in-scope: `loop` + `.renmark/loops/`; deferred: indefinite autonomous + scheduled/PR-triggered loops). Bumped last_reviewed → 2026-06-09. Phrase reworded per user: "not a separate product or standalone mode."
**Files changed:**
- `PRD.md` — Loop Mode requirements + section + scope (human-gated, approved via /renmark:prd)
**Do not change:**
- Loop Mode MVP is bounded + human-gated; indefinite/scheduled/PR-triggered loops are explicitly deferred. Loops never run unbounded; human approval before PRD edit/merge/release/budget-escalation/destructive change (REQ-12).

## v0.7.5 — 2026-06-08 (modularity / scalability health lens)

**Release of the modularity-health-lens feature.** Bumped 0.7.4 → 0.7.5 across all 7
version locations. Shipped on `main` via `--no-ff` merge of
`feature/modularity-health-lens` (codereview: full codex — 3 Major + 2 Minor
metric-accuracy/suppression findings, all fixed + independently re-verified; 483
tests + mypy + lint_all clean). Completes the user's original three-part request
(init front-door pipeline + acceptance criteria + this).

- **`renmark/modularity.py`** — pure-`ast`, zero-dep, never-raise analyzer. 5
  metrics, each two bands: module LOC, function length, cyclomatic branch count,
  import fan-out (coupling), nesting-weighted cognitive complexity. Thresholds
  mirror pylint/mccabe/SonarQube. False-positive suppression: `tests/`, comment-
  header generated files, `__init__.py` fan-out.
- **`/renmark:init` standards-health** now surfaces advisory modularity gaps — the
  `HEALTH:` stdout line stays a bounded summary; full detail (capped) goes to
  `.renmark/memory/dev-standards.md`. Advisory / never blocking / never auto-refactors.
- Self-scan on this repo surfaced 121 advisory gaps (20 major / 101 warn) — the
  lens working on day one.

## [2026-06-08] — project scope: modularity-health-lens

**Request:** Advisory modularity/scalability health lens — renmark enforces modularity at plan-time but never measures it on the shipped codebase. (User asked to research how other tools do it + reuse what renmark already has.)
**Tech stack:** Python ≥3.10 stdlib + markdown — **no new deps**. New `renmark/modularity.py` is a pure-`ast` analyzer; reuses `init.py`'s standards-health pipeline + `sizing.py` style.
**Deployment:** Claude Code plugin (unchanged).
**MVP boundary:** new `renmark/modularity.py` (5 ast metrics — module LOC, function length, cyclomatic branch count, import fan-out, nesting-weighted cognitive complexity; two bands each; FP suppression) → merged into `init.py` `evaluate_health` → `dev-standards.md` + `HEALTH:` line; one-line `init/SKILL.md` note; tests. ADVISORY / never blocking / never auto-refactors.
**Out of scope:** a separate `/renmark:hygiene` surface; blocking the pipeline; third-party metric deps (radon/pylint); auto-refactor.

**Locked decisions:**
- Ship all 5 metrics (LOC, fn length, cyclomatic, import fan-out [coupling/scalability], cognitive complexity); thresholds mirror pylint/mccabe/SonarQube defaults
- Surfaces ONLY through init's existing standards-health (no new /hygiene surface); reuses init's Gap dataclass + HEALTH pipeline
- Pure stdlib `ast`, zero-LLM, never raises (skip unparseable files); advisory — init still exits 0
- FP suppression mandatory: skip tests/generated/__init__ fan-out/data; count code lines not raw

## v0.7.4 — 2026-06-08 (proportional pipeline — cost ∝ feature size/risk)

**Release of the proportional-pipeline feature.** Bumped 0.7.3 → 0.7.4 across all 7
version locations. Shipped on `main` via `--no-ff` merge of
`feature/proportional-pipeline` (codereview: full codex — 2 Critical + 2 Major + 1
Minor *false-lite* holes, all fixed + independently re-verified + 11 regression
tests; 437 tests + mypy + lint_all clean).

- **`renmark/sizing.py`** — deterministic, zero-LLM tier classifier:
  `classify_plan` / `classify_diff` → `lite | standard | full`. Code-suffix always
  wins (no false-lite from a "template" substring); validates task shape; degrades
  to `standard` on any uncertainty (never accidentally `lite`). `resolve_override`:
  `--full` always escalates, `--lite` only narrows a `standard` classification
  (refused on hard/core/full).
- **Size-tier lite lane** (`/renmark:feature`): tiny features land on `main`, skip
  the codex review + release ceremony — but **always** run plan-validation + verify.
- **Proportional codereview** (`/renmark:codereview`): lite/doc diff → built-in
  cheap `/review` by default + one-keystroke escalate to full codex; standard/full
  → full codex. `--full` / `--skip` flags. Never silently skips.
- Makes small features cheap by default (the steady-stream complaint) while keeping
  full rigor where it matters — proven when the feature's own diff self-tiered
  `full` and the codex review caught real classifier bugs.

## [2026-06-08] — project scope: proportional-pipeline (C+A)

**Request:** Pipeline cost should be proportional to feature size/risk, not a fixed per-feature toll (a 2-task feature cost ~340k tokens, ~40% a 120–160k codex codereview run once regardless of size).
**Tech stack:** Python ≥3.10 stdlib + markdown — **no new deps**. New `renmark/sizing.py` (deterministic, zero-LLM) reuses `parser.Task` signals + git diff stat.
**Deployment:** Claude Code plugin (unchanged).
**MVP boundary:** `sizing.classify_plan/classify_diff` → tier (lite/standard/full); feature-router lite lane (lite features land on `main`, skip codex/release, keep verify+plan-validate); proportional codereview (cheap built-in `/review` default on tiny/doc + one-key escalate to codex; `--full`/`--skip`); tier surfaced in cost preview; `--full`/`--lite` overrides; tests.
**Out of scope:** roadmap-batch execution (B — deferred next); modularity health lens (deferred); not spawning subagents for trivial edits (future micro-lever); new runtime deps.

**Locked decisions:**
- Cheap built-in `/review` by default on tiny/doc diffs + one-key escalate to full codex — NOT silent-skip (this session a "doc-only" feature had 2 real codex findings)
- Lite features land straight on `main` (per single-branch-rule); standard/full keep branch→PR/release
- verify + plan-validation ALWAYS run regardless of tier (REQ-7); classifier degrades to `standard` on uncertainty
- Build C+A now; B (batch) + modularity lens deferred (ADR this session)

## v0.7.3 — 2026-06-08 (optional acceptance criteria in the PRD)

**Release of the acceptance-criteria feature.** Bumped 0.7.2 → 0.7.3 across all 7
version locations. Shipped on `main` via `--no-ff` merge of
`feature/acceptance-criteria` (codereview: 0 critical, 1 Major + 1 Minor — a
cross-file format inconsistency — both fixed; 416 tests + lint_all clean).

- **Optional per-`REQ-n` acceptance criteria** in the PRD: a single indented
  `- *Acceptance:* done when (outcome); done when (outcome).` bullet (1–3
  semicolon-separated clauses), product-level OUTCOME criteria.
- **`plugin/templates/PRD.md.template`** documents the format + example + a note
  distinguishing per-REQ acceptance from project-wide Success metrics.
- **`/renmark:prd`** CREATE asks for them one-REQ-at-a-time (skippable); UPDATE
  edits them via the reconcile→diff→approval flow; always human-gated; a PRD with
  zero criteria stays valid.
- Altitude held (ADR-005): criteria are NOT plan task verifiers and do NOT
  re-introduce the deferred `verify --coverage`.

## v0.7.2 — 2026-06-08 (init front-door pipeline + serves parser fix)

**Release of the init-pipeline feature + accumulated fixes.** Bumped 0.7.1 → 0.7.2
across all 7 version locations. Shipped on `main` via `--no-ff` merge of
`feature/init-pipeline` (codereview: 0 critical, 4 Major + 1 Minor all fixed +
independently re-verified; 416 tests pass, mypy + ruff + lint_all clean).

- **`/renmark:init` is now the non-destructive front door** — scaffolds missing
  `CLAUDE.md`/`AGENTS.md`/`CHANGELOG.md`/`.renmark/` (via `bootstrap`) instead of
  the old exit-1 dead-end, deterministically back-fills missing `BEGIN/END` rule
  blocks byte-verbatim, scans/maps, reports standards health, then hands off to
  `/renmark:roadmap` gap discovery. Works with or without a pre-existing CLAUDE.md.
- **`merge_rule_blocks()`** (zero-LLM, in `init.py`) — corruption-safe: tightened
  marker regex to full `<!-- BEGIN:name -->` own-line comments; pre-validates
  balanced markers and SKIPS a malformed file (`MarkerCorruptionError` → exit 2)
  rather than corrupting it. Shared `iter_rule_blocks`/`validate_rule_markers` with lint.
- **`/renmark:setup`** is now a thin rule-block-refresh alias of init (PRD REQ-8
  updated + human-approved).
- **`serves` plan field** now parses (`parser.py` + `Task` + `_build_task`) —
  closes the documented-but-rejected traceability field.
- PRD REQ-8 + Scope boundaries reconciled to init-as-front-door.

## [2026-06-08] — init-pipeline: marker hardening + corruption-safe back-fill

**Request:** Fix 5 verified codereview findings in the init-pipeline feature; core safety property — `merge_rule_blocks` must NEVER corrupt a file (SKIP malformed input, never insert).
**Built:**
- **#1** Tightened `_BEGIN_RE`/`_END_RE` (lint.py) to match ONLY a full managed-marker HTML comment on its own line (`^[ \t]*<!--[ \t]*BEGIN:name[ \t]*-->[ \t]*$`, MULTILINE) — bare prose `BEGIN:example` is no longer a marker. Horizontal-only whitespace classes keep block boundaries exact.
- **#2/#3** `merge_rule_blocks` now pre-validates each target's markers (new `lint.validate_rule_markers`) BEFORE inserting; malformed (orphan END, unclosed BEGIN, duplicate, out-of-order) → file SKIPPED, never written, collected into new `init.MarkerCorruptionError`.
- **#4** Scoped out AGENTS rule-block back-fill/mirroring in docstring + init/SKILL.md + setup/SKILL.md (AGENTS.md.template has no managed markers).
- **#5** `run()` maps `MarkerCorruptionError` → exit **2** (user-fixable corruption), other RuntimeError → exit **1**, success → **0**; documented in module docstring + init/SKILL.md.
**Files changed:**
- `renmark/lint.py` — tightened marker regexes; added `validate_rule_markers`.
- `renmark/init.py` — `MarkerCorruptionError`; pre-insert balance gate in `merge_rule_blocks`; exit-2 mapping in `run()`; honest docstrings.
- `plugin/skills/init/SKILL.md`, `plugin/skills/setup/SKILL.md` — dropped AGENTS-mirroring claims; documented skip-on-corruption + exit codes.
- `tests/test_init_pipeline.py` — replaced old unclosed-BEGIN test (asserted the OLD vulnerable behavior) with skip+raise; added orphan-END, exit-2, prose-marker tests.
- `tests/test_lint.py` — fixtures use real `<!-- BEGIN:name -->` form; added prose-marker non-match test.
**Do not change:**
- Markers are ONLY the `<!-- BEGIN:name -->` / `<!-- END:name -->` comment form — the regexes must use `[ \t]*` (not `\s*`) so MULTILINE `^`/`$` don't eat the preceding newline (would corrupt `iter_rule_blocks` block boundaries).
- `MarkerCorruptionError` subclasses `RuntimeError`; in `run()` it MUST be caught BEFORE the generic `RuntimeError` handler or exit-2 collapses to exit-1.
- There is NO CLAUDE.md↔AGENTS.md rule-block mirroring — AGENTS.md.template has no managed markers; `merge_rule_blocks` always reports `AGENTS.md: 0`.

## [2026-06-08] — project scope: init-pipeline

**Request:** Make `/renmark:init` the front-door "initialize renmark here" pipeline (scaffold-if-missing → back-fill rule blocks → scan/map → standards → roadmap gap discovery), folding `/renmark:setup`'s bootstrap in; fix the exit-1-when-CLAUDE.md-absent bug.
**Tech stack:** Python ≥3.10 stdlib + markdown — **no new deps**. Reuses `bootstrap.py`, `memory.template_dir()`, and lint's BEGIN/END marker logic.
**Deployment:** Claude Code plugin (unchanged).
**MVP boundary:** init.py scaffold phase (delegating to `bootstrap(init_git=False)` + CHANGELOG create) + new deterministic `merge_rule_blocks()` back-fill; init/SKILL.md redefined as the 6-step pipeline; setup/SKILL.md → thin alias; tests. Roadmap-at-end is inherited from ADR-009 (already wired).
**Out of scope:** removing `/renmark:setup`; any LLM call in init.py; new runtime deps.

**Locked decisions:**
- Tech stack + deployment locked for this plan
- Rule-block merge is **deterministic Python** (Option A) — best for context hygiene AND accuracy (canonical marker-delimited blocks inserted byte-verbatim, unit-tested), not agent/markdown
- `init.py` stays **zero-LLM**; roadmap `--gaps` hand-off stays SKILL-level (ADR-009)
- Non-destructive: existence-skip on create, byte-skip on managed blocks, never overwrite hand-written content

## [2026-06-08] — PRD updated
**Request:** Feature `init-pipeline`'s drift gate proposed consolidating `/renmark:setup` into `/renmark:init` as the front-door adoption pipeline; REQ-8 named setup explicitly.
**Built:** Reconciled REQ-8 + Scope boundaries of PRD.md — `/renmark:init` is now the named non-destructive adoption front door; `/renmark:setup` is recorded as its rule-block-refresh alias. last_reviewed already 2026-06-08.
**Files changed:**
- `PRD.md` — REQ-8 reworded; Scope-boundaries skill list reflects init-as-front-door + setup-as-alias
**Do not change:**
- PRD is human-owned; this edit was human-approved through the /renmark:prd gate. `setup` is an alias of `init`, not a separate adoption command.

## [2026-06-08] — fix: plan parser accepts the documented `serves` field
**Request:** Fix the `serves:` parser bug surfaced by gap discovery (Open Q1 / bugs.md).
**Built:** `renmark/parser.py` now accepts `serves` (parser keys + `Task.serves` field + `_build_task` pass-through), so plans using the documented `serves: REQ-n` traceability field parse instead of aborting with "unknown field serves".
**Files changed:**
- `renmark/parser.py` — accept `serves` end-to-end
- `tests/test_parser.py` — +2 tests (serves parses to Task.serves; absent → None)
- `.renmark/memory/bugs.md` — moved serves bug Open → Fixed
**Do not change:**
- Keep `parser.py` accepted-keys in lockstep with `plan/SKILL.md`'s format example — a documented field is only real if the parser accepts it.

## v0.7.1 — 2026-06-08 (next-step-engine: guided hand-offs + roadmap gap discovery)

**Release of the next-step-engine feature.** Bumped 0.7.0 → 0.7.1 across all 7
version locations. Shipped on `main` via `--no-ff` merge of
`feature/next-step-engine` (codereview: 0 critical, 3 major + 1 minor all
fixed+tested; 401 tests pass, mypy + ruff + lint_all clean).

- **`_shared/next-steps.md`** — umbrella hand-off contract: every skill ends by
  recommending a state-derived next step (lifecycle.json + pipeline.json), so no
  interaction dead-ends. References the existing `handoff-menu.md` gate sub-menu.
- **`lifecycle.next_steps(repo, skill)`** — pure stdlib helper returning the
  structured next-step set (pipeline/gate/aux classes); reuses NEXT_BY_STAGE /
  next_recommended; never raises (tolerates malformed input).
- **All 19 skills** now cite the contract — enforced by a new class-aware
  `lint_next_steps_citation` (pipeline/aux must cite next-steps.md; gate skills
  may cite handoff-menu.md) wired into `lint_all`.
- **`/renmark:roadmap` gap-discovery mode** (ADR-009) — PRD-vs-shipped gap
  analysis with tiered cost gating (T0 deterministic / T1 local / T2 web research
  opt-in), advisory + human-gated; never writes PRD. `/renmark:finish` and
  `/renmark:init` route into it so picking the next feature is guided.
- 28 new tests (`test_next_steps.py`, `test_lint_next_steps.py`).
- Pipeline: prd → feature → brainstorm → plan(×2, 21 tasks) → orchestrate →
  verify (6/6 smoke) → codereview → finish.

## [2026-06-08] — project scope: next-step-engine

**Request:** Make every renmark interaction guided — each skill recommends a state-derived next step; finishing a feature flows into PRD-vs-shipped gap discovery to suggest what to build next.
**Tech stack:** Python ≥3.10 stdlib + markdown (Claude Code plugin) — no new runtime deps. Optional Tier-2 web research uses Claude Code's own tools, not a Python dependency.
**Deployment:** Claude Code plugin (unchanged).
**MVP boundary:** all 7 components land in this feature — `_shared/next-steps.md` umbrella contract; `lifecycle.next_steps()` helper; refit of all 19 skills' hand-off; `/renmark:roadmap` gap-discovery (T0/T1/T2, T2 opt-in); `/renmark:finish` + `/renmark:init` wiring into gap mode; tests + lint drift guard.
**Out of scope:** a standalone `/renmark:next` skill (extends roadmap instead); web research on-by-default; auto-writing PRD/roadmap; per-skill bespoke menus.

**Locked decisions:**
- Tech stack and deployment target above are locked for this plan
- Changing them requires a new project scope entry
- Gap discovery extends `/renmark:roadmap` (supersedes the deferred roadmap view in ADR-005); it stays read-only/advisory/human-gated and never becomes a second PRD writer
- Reuse `NEXT_BY_STAGE` / `next_recommended()` and the existing `handoff-menu.md` — generalize, do not rebuild

## [2026-06-08] — PRD created
**Request:** Create the project's PRD via `/renmark:prd`.
**Built:** Created PRD.md as the project's product source of truth (synthesized-from-docs — distilled from CLAUDE.md, .renmark/memory/, specs, and CHANGELOG since renmark is a mature project).
**Files changed:**
- `PRD.md` — new product definition (what/who/why/capabilities/non-goals/success criteria)
**Do not change:**
- PRD.md is human-owned. Automated stages may PROPOSE edits but never write it without approval.
- Product-level non-goals (plugin-not-app, no own model, stdlib-only runtime, renmark≠legacy-plugin) live in PRD; a single build's MVP cut belongs in the scope contract, not the PRD (ADR-005).

## v0.7.0 — 2026-06-05 (blueprint: prototype/schematic step)

**Release of the blueprint milestone.** Bumped 0.6.0 → 0.7.0 across all 7 version
locations. Shipped on `main` via merge of `feature/blueprint` (codereview: 0 critical,
4 major fixed; 374 tests pass).

- **`/renmark:blueprint`** — generates a living `SCHEMATIC.md` (always, Mermaid) and
  `PROTOTYPE.html` (UI builds only, self-contained HTML/CSS), synthesized from
  `.renmark/memory/project-map.md` via a hybrid `<!-- RENMARK:GENERATED:*:START/END -->`
  marker update. Standalone command + embedded touchpoints in `start` and `feature`.
- **`renmark/blueprint.py`** — `splice_generated_block` (idempotent, marker-injection
  guarded via `MarkerInjectionError`), `detect_ui` (parses canonical `**Frontend:**`
  forms), marker builders/constants.
- **Guardrails** — blueprint is an artifact touchpoint, NOT a lifecycle stage;
  `project-map.md` is the sole architecture source (never rescans); `/renmark:init`
  writes map/stack only, blueprint is sole writer of the two artifacts.
- 22→31 unit tests; pipeline ran brainstorm → plan (12 tasks) → orchestrate (1
  codex→sonnet escalation) → verify (8/8) → codereview → finish.


## [2026-06-05] — blueprint feature built (12 tasks)

**Request:** Implement `/renmark:blueprint` — the Phase-3 prototype/schematic pipeline step.
**Built:** Orchestrated 12 atomic tasks across 3 waves (sonnet/haiku/opus Agents + 1 escalation):
- `renmark/blueprint.py` — marker-splice helper (`splice_generated_block`, `MarkerNotFoundError`), UI detection (`detect_ui`), marker builders/constants.
- `plugin/templates/{SCHEMATIC.md,PROTOTYPE.html}.template` — skeletons with `RENMARK:GENERATED:*` marker blocks.
- `plugin/skills/blueprint/SKILL.md` + `plugin/commands/blueprint.md` — the skill (freshness gate → UI gate → synthesize → splice → lifecycle touchpoint) and command entry.
- Wiring: `start` (onboarding offer), `feature` (delta touchpoint), `help`, `DOMAIN_BY_SKILL` (build), CLAUDE.md/AGENTS.md tooling table.
- `tests/test_blueprint.py` — 22 unit tests (splice byte-preservation, idempotency, human-edit preservation, missing-marker abort, `detect_ui` branches, source_sha).
**Files changed:** see commits 8a1ddc7..51601e1 on `feature/blueprint`.
**Gates:** 365 passed / 28 skipped; ruff clean on changed code. All 12 task verifiers PASS.
**Do not change:**
- T6 was escalated codex→sonnet: `renmark-execute --task` ran read-only in this env and didn't write the file. See `learnings.md`.
- The `serves:` field in plan files breaks `renmark-execute` (parser drift) — logged Open in `bugs.md`; stripped from this plan.

## [2026-06-05] — project scope: blueprint (prototype/schematic step)

**Request:** Add a renmark pipeline step (`/renmark:blueprint`) that generates a
living architecture **schematic** (always) and a visual UI **prototype** (only
when the build has a UI), updated as the project evolves like the PRD.
**Tech stack:** Python ≥3.10 + Claude Code plugin markdown — existing renmark stack, **no new deps**.
**Deployment:** local plugin install (WSL + Windows), unchanged.
**MVP boundary:** schematic + conditional prototype + hybrid marker-based update + pipeline wiring (start/feature/standalone).
**Out of scope:** deterministic language parsers (deferred), full 4-level C4 (Container level only), image/SVG export, full-repo rescan.

**Locked decisions:**
- Command slug `/renmark:blueprint`; artifacts `SCHEMATIC.md` (always) + `PROTOTYPE.html` (UI only) at project root, like `PRD.md`.
- Schematic = Mermaid in Markdown; prototype = self-contained static HTML/CSS.
- `project-map.md` is the ONLY architecture source — blueprint synthesizes, never rescans the repo.
- Hybrid update: regenerate only content between `<!-- RENMARK:GENERATED:*:START/END -->` markers; preserve human prose; single current-state artifact.
- Blueprint is an artifact **touchpoint like PRD, NOT a lifecycle stage** — must not advance the `init→…→released` chain.
- `source_sha` in a generated block = hash of `project-map.md`, not an implied repo scan.

**Do not change:**
- Do not add deterministic parsers in this phase — explicitly deferred.
- Do not clobber an existing artifact that lacks markers — abort instead.
- Do not let blueprint fabricate architecture when `project-map.md` is missing/stale — route to `/renmark:init`.

## v0.6.0 — 2026-06-05 (PRD source of truth)

**Release of the PRD source-of-truth milestone.** Bumped 0.5.9 → 0.6.0 across all
7 version locations. Shipped on `main` via merge of `feature/prd-source-of-truth`
(codereview: 0 critical).

- **`/renmark:prd`** — create/update skill for a per-project `PRD.md`, the
  human-owned source of truth; every write human-gated.
- **WRITE / ALIGN / NOTHING touchpoint policy** (ADR-005) — one writer
  (`/renmark:prd`), one read-only align contract (`_shared/prd-alignment.md`),
  nothing for everyone else. Guards against PRD duplication/over-engineering.
- **Pipeline wiring** — `start` offers PRD create; `feature` runs the alignment
  drift gate; `brainstorm` runs read-only alignment (+ no-PRD nudge); `plan`
  carries `serves: REQ-n` traceability; `help` lists the command.
- Codereview pass fixed 6 doc-consistency findings (approve-skill framing, the
  5-line budget contradiction, PRD artifact-governance exemption, etc.).

Gates: 368 passed; ruff + plugin lint clean. 3 pre-existing stale `approve`-gate
tests remain (separate follow-up; not introduced here). Local release (no remote).

## 2026-06-05 — PRD branch codereview fixes (pre-merge)

**Request:** Codex review of `main..HEAD` before merging prd-source-of-truth; fix
the doc-consistency findings.

**Built:** Codex pass = 0 Critical / 3 Major / 2 Minor / 1 Nit (all
doc-consistency, no runtime bugs; review at
`.renmark/reviews/2026-06-05-3eb9b02…review.md`). Fixed all 6:
- `_shared/prd-alignment.md` — clarified the ≤5-line budget applies to the
  orchestrator-visible `verdict`+`reason`; `proposed_prd_addition` is a separate
  bounded snippet routed to `/renmark:prd`, not counted against it (resolved the
  contract's internal contradiction).
- `plugin/skills/prd/SKILL.md` — `/renmark:approve` reframed as *planned* (not
  shipped); manual gate is the current path. Read-only "what does the PRD say"
  use case clarified as UPDATE-mode's read step. G6 row states the PRD's
  human-owned **exemption** from generated-artifact provenance fields.
- `plugin/templates/PRD.md.template` — header comment documents the same exemption.
- `plugin/skills/start/SKILL.md` — "[b] Skip" copy no longer claims it always
  goes to the build plan (start can route to brainstorm).
- `plugin/skills/help/SKILL.md` — dropped the hardcoded "six commands" count.

**Do not change:**
- `/renmark:approve` is **not shipped** — `lifecycle.next_recommended()` (line ~289)
  intentionally surfaces a manual gate. Docs must not present approve as shipped.
- 3 pre-existing test failures (`test_cold_start_recovery`,
  `test_smoke_full_lifecycle`) assert `/renmark:approve` in `next_recommended()`
  output — they are **stale** (code is correct by design). Separate follow-up on
  main; not introduced by this branch.

## 2026-06-05 — PRD touchpoint policy + brainstorm alignment

**Request:** Analyze where the PRD overlaps across renmark skills, prevent
duplication/over-engineering, and keep a single source of truth — then implement
the one change that pays for itself.

**Built:** Codified the **WRITE / ALIGN / NOTHING** PRD-touchpoint policy (one
writer = `/renmark:prd`; one read-only align contract = `_shared/prd-alignment.md`;
NOTHING for everyone else) and wired `brainstorm` into ALIGN:
- `.renmark/memory/decisions.md` — ADR-005 records the policy, the rejected-as-bloat
  list (brainstorm-as-writer, `verify --coverage`, roadmap progress view,
  init/document PRD pointers, orchestrate reading the PRD), and the altitude rule.
- `plugin/skills/_shared/prd-alignment.md` — new "PRD touchpoint policy" section
  (the durable guard, co-located with the alignment contract skill authors read).
- `plugin/skills/brainstorm/SKILL.md` — new Step 1b: read-only PRD alignment via
  the shared subagent when `PRD.md` exists; a non-blocking "no PRD yet" nudge when
  it doesn't; **no write path**. Step 6 gains an altitude note (spec non-goals are
  feature-scoped; product non-goals live in the PRD).
- `plugin/templates/PRD.md.template` + `plugin/skills/_shared/scope-contract.md` —
  reciprocal altitude notes: product-level non-goals → PRD; a build's MVP cut →
  scope contract. Cross-reference, never copy.

**Do not change:**
- **brainstorm must never write `PRD.md`** — it ALIGNs (read-only) and routes drift
  to `/renmark:prd`. One writer only (ADR-005).
- The brainstorm PRD check uses the `_shared/prd-alignment.md` subagent — it MUST
  NOT read the PRD body into the skill's context.
- `plan`'s `serves: REQ-n` is a light ID read, deliberately *not* a full ALIGN;
  this is why `verify --coverage` stays unbuilt (coverage flows plan→tasks→verify).
- Pre-existing unrelated test failures (3) live in lifecycle approval-routing
  (`test_cold_start_recovery`, `test_smoke_full_lifecycle`); not caused by and not
  in scope of this doc/skill change.

## 2026-06-05 — PRD source of truth + `/renmark:prd` (built)

**Request:** Centralized per-project source of truth (a PRD), informed by studying TaskMaster; ship the skill, wire it into the pipelines, add a hygiene-preserving drift check.

**Built:** 14-task plan executed (10 Claude via Agent, 4 codex via renmark-execute):
- `plugin/skills/prd/SKILL.md` — `/renmark:prd` create/update modes, human-gated living updates, Governance-compliance section.
- `plugin/skills/_shared/prd-alignment.md` — drift-check subagent contract; router passes only feature description + file scope, gets a ≤5-line `verdict`, never reads the PRD body.
- `plugin/commands/prd.md` — command shim.
- `plugin/templates/PRD.md.template` — lean sections (vision/users/goals+non-goals/REQ-n/metrics/scope/open-questions) + provenance header.
- `renmark/lifecycle.py` — `prd` registered in `DOMAIN_BY_SKILL` (build).
- `start` offers PRD create for new projects; `feature` dispatches the alignment subagent; `plan` carries an optional `serves: REQ-n` traceability note; `help` lists the command.
- Plain-text PRD pointers added to `CLAUDE.md`/`AGENTS.md` + both templates (never `@import`).
- `tests/integration/test_plugin_install.py` — enforces `prd` in the documented-skill set; excludes `_shared/` from the skills↔commands parity check.

**Files changed:** see plan `.renmark/plans/2026-06-05-prd-source-of-truth.plan.md`. Full suite: 343 passed, 28 skipped; ruff clean on `renmark/` (34 pre-existing repo-wide ruff errors untouched).

**Do not change:**
- PRD pointers in CLAUDE.md/AGENTS.md/templates MUST stay **plain text — never `@PRD.md` import** (an import auto-loads the whole PRD into every session, breaking context hygiene).
- The orchestrator/router/`feature` MUST NOT read `PRD.md` into context — always dispatch the `_shared/prd-alignment.md` subagent and consume only its bounded verdict.
- PRD writes are **human-gated**; automated stages propose, they never write the PRD without approval.
- Integration tests gate on `RENMARK_SMOKE=1` — run with it set, or real failures stay hidden as skips.
- The prototype/schematic pipeline step is the **next** feature (recorded in memory), intentionally not built here.

## 2026-06-05 — project scope: PRD source of truth + `/renmark:prd`

**Request:** Add a per-project PRD as the durable source of truth (peer to CLAUDE.md), informed by a study of TaskMaster; ship a `/renmark:prd` skill, wire it into `start`/`feature`, and add a lightweight, hygiene-preserving PRD↔work drift check.
**Tech stack:** Python >=3.10 + Claude Code plugin (markdown skills/commands) — unchanged; this is a feature inside renmark itself.
**Deployment:** N/A — distributed as the renmark Claude Code plugin.
**MVP boundary:** PRD artifact + `/renmark:prd` (create/update, human-gated) + start/feature wiring + subagent-based drift flag + plan traceability note.
**Out of scope:** prototype/schematic pipeline step (next, separate feature); REQ-ID coverage enforcement in verify; hard PRD↔plan gating; TaskMaster status-taxonomy / dependency-integrity tooling.

**Locked decisions:**
- PRD lives at the **project root** (`PRD.md`), committed — confirmed free of context cost (only CLAUDE.md/AGENTS.md auto-load).
- The orchestrator/router **never reads the PRD body**; all alignment reading happens in an isolated subagent returning a bounded summary.
- CLAUDE.md/AGENTS.md pointer is **plain text, never `@import`** (an import would auto-load the PRD every session).
- Spec: `.renmark/specs/2026-06-05-prd-source-of-truth.spec.md`; research: `.renmark/research/2026-06-05-prd-taskmaster.research.md`.

## v0.5.9 — 2026-06-04 (fix: finish deletes merged branch + correct release routing)

**Request:** "Once a release is created, the branch should get merged and deleted — but I keep seeing the feature branch left behind." Check the finish/release skill.

**Built:** Fixed two real gaps in `plugin/skills/finish/SKILL.md`:
1. **Branch cleanup** — the `[m] Merge` step merged into main but never deleted the branch `/renmark:feature` created, so every finish left the feature branch behind. It now runs `git branch -d <branch>` (the *safe* form — refuses to delete unmerged work) after a clean merge, plus `git push origin --delete` when a remote exists. Release packaging is cut from `main` after the merge, so the branch is already gone by release time.
2. **Stale release routing** — line 23 claimed PR/merge logic "moves to `/renmark:release`", a command that does not exist (`lifecycle.NEXT_BY_STAGE` routes `ready-to-release` to a manual fallback; `/renmark:release` lives only in `NEXT_BY_STAGE_PLANNED`). Corrected to state merge/release logic lives in finish itself, and added a guard so a re-run never downgrades a `released` feature back to `ready-to-release`.

**Files changed:**
- `plugin/skills/finish/SKILL.md` — `[m] Merge` deletes the merged branch; final-step lifecycle guard + accurate "no /renmark:release skill" note.

**Do not change:**
- **Use `git branch -d` (lowercase), never `-D`,** in the merge step — the safe form can never discard unmerged work. `-D` only on explicit user request.
- **Finish must not downgrade `released → ready-to-release`** on a re-run — guard the final-step lifecycle write on the current stage.
- There is no `/renmark:release` skill; don't re-introduce references to it as if it were implemented.

## v0.5.8 — 2026-06-04 (QA flow memory + QA bootstrap)

**Release of the qa-flow-memory feature** (detailed per-change entry below). Bumped from 0.5.7 across all 7 version locations.

- **QA flow memory:** new committed `.renmark/memory/qa-flows.md` playbook store. `/renmark:verify --qa` / `--deep-qa` read it before choosing a browser flow and promote a passing one-off flow into it; degrades to today's synthesize-from-plan behavior when the file is missing or empty.
- **QA bootstrap:** `/renmark:verify --qa --bootstrap` seeds the playbook with the project's top critical flows (no third browser flag — rides the existing `--qa` parser).
- **Recommendation triggers:** `/renmark:verify` and `/renmark:orchestrate` now recommend (never auto-run) browser QA for user-visible/browser-facing changes; shell smoke stays the default.

Gates: plugin lint clean, `pytest` 343 passed / 0 failed. Codex review: 0 findings on the feature diff. Local release only (no remote configured).

## v0.5.7 — 2026-06-04 (browser QA, dual channel, interactive menus, lifecycle identity)

**Release bundling the four changes shipped on 2026-06-04** (detailed per-change entries below). Bumped from 0.5.6 across all 7 version locations.

- **Browser QA refinement** (`/renmark:verify --qa` / `--deep-qa`): visual/layout integrity checks (overlapping/clipped/off-screen controls), before/after UI-change tracking, explicit stop-and-report-on-break, and a "when to use which mode" guide. Default shell smoke preserved; browser QA stays opt-in.
- **Dual browser channel:** Chrome DevTools MCP (default; the only option under WSL — targets Windows-host Chrome) or native `claude --chrome` when connected; environment-detected with graceful install-hint + shell-smoke fallback.
- **Interactive hand-off menus:** arrow-selectable `AskUserQuestion` pickers as the primary presentation (numbered markdown demoted to fallback), with a hard guarantee that a hand-off never ends on a choiceless prompt. Supersedes the earlier numbered-markdown rule.
- **Lifecycle identity fix:** `lifecycle.begin_feature()` — `/renmark:feature` now persists feature/branch identity at entry, so stage writes no longer inherit the prior feature's identity.

Gates: `ruff`/`mypy`/plugin lint clean, `pytest` 337 passed. Local release only (no remote configured).

## [2026-06-04] — QA flow memory + QA bootstrap

**Request:** Add a lightweight, markdown-based QA flow memory layer so `/renmark:verify --qa` / `--deep-qa` reuse known-good browser flows instead of re-inventing tests each run, centered on a new `.renmark/memory/qa-flows.md` playbook.

**Built:** New committed QA playbook store (`qa-flows.md`) with a seeded EXAMPLE/TEMPLATE flow (Flow name, URL, Preconditions, Actions, Expected — incl. no overlapping/clipped controls + no console errors, selectors, Evidence, Known risks, related bugs). `/renmark:verify` now reads it BEFORE choosing a QA flow (degrades to today's synthesize-from-plan behavior when the file is "missing or empty"), promotes a passing one-off flow into it on PASS, and gains a `--qa --bootstrap` path (no third flag) plus `--qa`/`--deep-qa` recommendation triggers. `/renmark:orchestrate` Step 8 now recommends (does NOT auto-run) browser QA after a clean run touching browser-facing surfaces. INDEX.md registers the new file. 6 content-presence tests added.

**Files changed:**
- `.renmark/memory/qa-flows.md` — new QA playbook store (seeded template).
- `plugin/skills/verify/SKILL.md` — flow selection from memory, `--qa --bootstrap`, promote-on-pass, recommendation triggers, Deep-QA reuse pointer.
- `.renmark/memory/INDEX.md` — registered `qa-flows.md` in the memory table.
- `plugin/skills/orchestrate/SKILL.md` — Step 8 browser-QA recommendation note (not automatic).
- `tests/test_qa_flows.py` — 6 tests covering the store, verify wiring, and the INDEX row.

**Do not change:**
- **Shell smoke stays the default; browser QA stays opt-in** via `--qa`/`--deep-qa` — never automatic. No third browser flag (bootstrap rides `--qa`).
- **Existing QA must work when `qa-flows.md` is missing or empty** — that literal phrase is the load-bearing fallback guarantee; don't remove it.
- **Context-hygiene (G3/G5):** screenshots/DOM/console/network stay on disk + artifact body; chat sees only the ≤5-line verdict.
- Preserve the dual browser-channel selection (WSL→MCP precedence) and the interactive `AskUserQuestion` hand-off menus.

## [2026-06-04] — interactive (arrow-selectable) hand-off menus via AskUserQuestion

**Interaction-layer change, not menu formatting.** The earlier "numbered, forced-choice markdown menu" change only made menus *print* as `1. [x] Option` text — readable, but still a static list with no arrow-key selection. This change makes hand-off gates present an actual arrow-key-navigable picker via Claude Code's **`AskUserQuestion`** tool when available, with the printed numbered list demoted to a graceful fallback. It **supersedes** the numbered-markdown-as-primary rule.

**Request:** Render hand-off menus through the interactive question/choice component (arrow keys + Enter) when available; fall back to the printed numbered list (number or bracket-letter input) in non-interactive contexts. Don't invent an API — use the supported mechanism.

**Built:** Verified the mechanism first (via Claude Code docs): `AskUserQuestion` is the supported interactive picker — 1–4 questions/call, **2–4 options per question (hard cap of 4)**, label + description + ≤12-char header, blocking (no default, which enforces the required-choice gate), free-text always accepted; **unavailable in subagents and in headless / `-p` / piped / CI** sessions. SKILL.md can't call tools — it instructs the agent to call `AskUserQuestion`.
- `_shared/handoff-menu.md`: rules 6–7 rewritten. **Rule 6 (PRIMARY): present survivors via `AskUserQuestion`** — one choice per option (`label` = action + `[x]` code, `description` = gloss). **4-option-cap handling:** ≤4 survivors → all selectable; >4 → surface the 4 highest-priority (defined order, `[n]` always kept) AND print the full numbered list so overflow stays reachable by typed number/letter (free-text). **Rule 7 (FALLBACK): printed numbered list** for non-interactive / unavailable / error, and as the reference beneath an overflow picker. Rule 8: explicit choice always required.
- Static gates updated to interactive-primary + numbered-fallback: `plan`, `check-plan`, `finish`, `brainstorm`, `setup`, `orchestrate` (preview note), `codereview` (combined `[o]/[fix]`+gate menu, overflow path), `verify` (dispatch wording + citation).
- Discovery questions updated likewise: `start` (Q1/Q2), `_shared/scope-contract.md` (Q1–Q3; 5-option questions use top-4 + free-text). `brainstorm` already used `AskUserQuestion` for discovery.

**Follow-up (same branch) — choiceless-prompt hardening.** Closed a failure mode where `AskUserQuestion` rendered only the header (`What's next?`) with no visible options, or was declined/errored, leaving the user stuck. New rule 9 (hard guarantee): a hand-off MUST end in exactly one of two visible states — the picker showing selectable choices, OR the printed numbered list — **never the bare question with no choices**. Rule 6 now mandates options be passed as real `options[]` entries (never embedded in the `question` text — that's what renders header-only), and broadens the fallback trigger to fire immediately on *any* non-rendering reason: unavailable, errored, **declined/rejected/interrupted**, no valid selection, or header-only. The static gates' fallback clause was broadened to match. "When in doubt, print the fallback."

**Files changed:**
- `plugin/skills/_shared/handoff-menu.md` — interactive-primary rules 6–8, citation snippet, canonical-menu intro.
- `plugin/skills/{plan,check-plan,finish,brainstorm,setup,orchestrate,codereview,verify,start}/SKILL.md` — gate/dispatch wording.
- `plugin/skills/_shared/scope-contract.md` — Presentation directive + sub-question wording.

**Do not change (supersedes the prior numbered-menu guard):**
- **Interactive `AskUserQuestion` is the PRIMARY presentation; the numbered markdown list is ONLY the fallback.** Do not revert to "numbered list is the solution" — that earlier rule is intentionally superseded.
- **The 4-option cap is a real API constraint, not a style choice.** Menus with >4 filtered options must surface the top 4 as choices and keep the rest reachable via the printed fallback + free-text. Don't try to cram >4 options into one `AskUserQuestion`.
- **Never auto-proceed.** The required-choice gate holds in both modes; `AskUserQuestion` enforces it by blocking, the text fallback by re-asking on no match.
- Option **filtering rules (1–5) are unchanged** — interactivity is purely the presentation layer on top of the same filtered survivor set.

## [2026-06-04] — fix: /renmark:feature now persists feature identity to lifecycle.json

**Request:** Fix the lifecycle-identity bug found during the browser-QA finish: a feature started via `/renmark:feature` never wrote its identity, so `lifecycle.json` kept the prior feature's `feature`/`branch` and finish's ADR was wrong. Keep it tightly scoped; add a verifier; don't touch the browser-QA work.

**Built:** New `lifecycle.begin_feature(repo, *, feature, branch)` establishes a clean lifecycle for a new feature — resets to stage `init` with empty `stages_completed`/`artifacts` and the correct identity. `/renmark:feature` Step 1 now calls it immediately after creating/switching to the branch. Two focused tests prove `lifecycle.json` reflects the current feature/branch after entry and that a new feature does not inherit prior stage history or artifact pointers.

**Files changed:**
- `renmark/lifecycle.py` — added `begin_feature` (DRY: `clear_lifecycle` + `write_lifecycle(stage="init", …)`, so the 1KB byte-budget guard still applies).
- `plugin/skills/feature/SKILL.md` — Step 1 now writes feature identity via `begin_feature` right after branch creation, with rationale.
- `tests/test_lifecycle.py` — `test_begin_feature_writes_identity`, `test_begin_feature_resets_prior_feature_state`.
- `.renmark/memory/bugs.md` — moved the identity bug Open → Fixed.

**Do not change:**
- **The router owns identity; stage skills only advance `stage`.** `begin_feature` must run at feature entry (after the branch exists) — before plan/orchestrate/verify/finish, which only write `stage`/artifacts and would otherwise inherit stale identity.
- `begin_feature` intentionally **resets** `stages_completed` and `artifacts` — a new feature starts clean. Don't change it to a partial overwrite, or cross-feature artifact pointers leak back in.

## [2026-06-04] — verify browser QA refinement (`--qa` / `--deep-qa`)

**Request:** Make `/renmark:verify --qa`/`--deep-qa` do real browser-based QA (load pages, drive controls, exercise workflows, report visible + console/runtime bugs) — opt-in, not the default — and document when to use it; prefer `--deep-qa` for deeper runtime/visual checks that track UI changes, catch overlapping/broken interface layout, and stop/flag when a flow breaks or can't finish.

**Built:** Audit found browser QA already existed (Chrome DevTools MCP: navigate/click/fill/wait_for/screenshot, console + network criteria, opt-in flags, degrade-to-shell). This refinement closes four gaps in `plugin/skills/verify/SKILL.md`: (1) a `### When to use which mode` decision guide (shell smoke vs `--qa` vs `--deep-qa`); (2) a new HARD visual/layout integrity criterion catching overlapping interactive elements / clipped / off-screen content, detected via snapshot + screenshot + `getBoundingClientRect`; (3) before/after screenshot capture with an agent-observed diff note (evidence to disk only); (4) explicit stop-and-report-on-break semantics (hang, uncaught exception, broken layout, can't-finish) wired into the existing `log_bug` / artifact / learnings flow.

Follow-up (same branch): the QA applicability gate now selects between **two browser channels** so renmark works on both WSL and the Windows/desktop app — **Chrome DevTools MCP** (default; the only option under WSL, can target Windows-host Chrome) and the **native Claude-in-Chrome** extension (`claude --chrome`, used when on the Windows/desktop app with the extension connected). Detection precedence: WSL → MCP; Windows/desktop app with native channel connected → native; otherwise default CLI → MCP. If the chosen channel is unavailable it prints the environment-matched install hint (MCP `claude mcp add` command, or extension + `claude --chrome`) and degrades to shell smoke — never blocks. Pass criteria, evidence handling, and the hygiene contract are identical across channels.

**Files changed:**
- `plugin/skills/verify/SKILL.md` — added when-to-use guide, visual/layout hard criterion (`--qa` + strengthened `--deep-qa`), before/after UI-change tracking, stop-on-break semantics; frontmatter description lightly extended. (+33/−7)

**Do not change:**
- **Shell smoke (default mode) stays untouched and stays the default** — browser QA must remain opt-in via `--qa`/`--deep-qa`; the applicability gate (web project? browser MCP available?) and degrade-to-shell fallback are load-bearing.
- **Context-hygiene contract (G3/G5) is non-negotiable** — screenshots, DOM trees, console/network dumps, and before/after diff data go to disk + artifact body only; chat sees only the ≤5-line verdict. Do not inline images or paste diffs.
- **No third browser flag** — the refinement lives inside the existing two flags by design.
- **Browser-channel precedence is load-bearing:** WSL must always resolve to Chrome DevTools MCP (native messaging cannot cross the WSL boundary); the native `claude --chrome` channel is only for the Windows/desktop app. Do not reorder so that WSL attempts the native extension. Both channels share identical pass criteria / evidence / hygiene — keep them in lockstep.
- The hand-off menu blocks and dispatch-on-number-or-letter wording were deliberately NOT touched (see prior numbered-menu guard).

## [2026-06-04] — numbered, forced-choice hand-off menus

**Request:** Make the bracketed option menus (`[qa]`, `[d]`, etc.) numbered `1. 2. 3. 4.` so the user can answer by number, and require an explicit choice to continue on every prompt.

**Built:** Every renmark interactive menu now renders as a numbered list while keeping its `[x]` bracket code (e.g. `1. [d] Dispatch …`). The number is the primary selector; the bracket letter still works. Each prompt now states a choice is required and must never auto-proceed on an empty answer.

**Files changed:**
- `plugin/skills/_shared/handoff-menu.md` — added rendering rule 6 (number survivors after filtering) and rule 7 (a choice is required; accept number or letter; re-ask on no match); updated the citation snippet.
- `plugin/skills/verify/SKILL.md` — dispatch now keys on "number or letter" and requires an explicit choice.
- `plugin/skills/plan/SKILL.md`, `check-plan/SKILL.md`, `finish/SKILL.md`, `brainstorm/SKILL.md`, `setup/SKILL.md` — static gates numbered; dispatch keyed on `N / letter`; added "choice required" line.
- `plugin/skills/orchestrate/SKILL.md` — numbered the verify-menu preview.
- `plugin/skills/codereview/SKILL.md` — numbered the `[o]`/`[fix]` actions; appended hand-off menu continues the numbering into one list.
- `plugin/skills/_shared/scope-contract.md` — Q1/Q2/Q3 discovery questions numbered.

**Do not change:** — ⚠️ **SUPERSEDED** by the interactive-menu entry above (2026-06-04). Numbered markdown is now only the *fallback*; the primary presentation is the `AskUserQuestion` picker. The notes below apply only to the fallback list:
- The handoff menu numbering is a **render-time** rule, not hardcoded in the canonical list — items are filtered first (rules 1–5), then numbered. Don't bake fixed numbers into the canonical `[x]` block in `handoff-menu.md`; omitted gates would leave gaps.
- Keep the `[x]` bracket code on every fallback menu line — letters are still valid selectors and several dispatch instructions reference them.

## v0.5.6 — 2026-05-29 (lifecycle hygiene — decision log enforcement, artifact GC, memory prune, resume validation)

**Patch release — closes the gap between renmark's artifact-first doctrine and its actual enforcement. The `stale_after` / `created_at` / `source_sha` metadata schema in `renmark/summary.py` and `memory.log_decision()` in `renmark/memory.py` were both designed in earlier releases but had no consumer wired in. v0.5.6 builds the sweepers and enforcers that close the loop — turning aspirational metadata into operational hygiene.**

The driving idea: artifacts decay. Decisions get forgotten across `/clear`. Escalations happen silently inside `_engine.py` and leave no trail. The schema fields were already there — what was missing was the code that READS them and acts. v0.5.6 ships that code: a hygiene CLI, a resume-time validator, an idempotent decision logger, and a finish-time ADR write.

**What shipped:**

- **`memory.log_decision()` is now idempotent on `(title, date)`.** New helpers in `renmark/memory.py`: `dedupe_memory_log` (collapses duplicate ADR sections in curated files), `age_out_memory_log` (archives entries older than N days from append-only logs), and `log_escalation_decision` (writes a structured ADR when an executor escalates). Same `(title, date)` short-circuits — so rerunning the same plan on the same day no longer duplicates every ADR.
- **`lifecycle.validate_artifact_refs(repo, state=None)`** cross-checks paths + `source_sha` + `stale_after` for every artifact tracked in `lifecycle.json`. Returns a list of BLOCK / WARN findings with explicit reasons. `hygiene` added to `DOMAIN_BY_SKILL` as `meta` — diagnostic, not a pipeline stage.
- **New `renmark/hygiene.py` module + `python -m renmark.hygiene` CLI** with `scan | prune | all` subcommands and `--apply / --ttl-days / --memory-days / --include-memory` flags. Archives stale artifacts to `.renmark/archive/YYYY-MM/` preserving repo-relative paths under the archive root. Default dry-run; writes are opt-in via `--apply`. Refuses any `archive_root` outside the project tree (raises `ValueError`).
- **`_record_escalation` in `renmark/cli/_engine.py`** now accepts `escalated_to: str | None = None`. When non-None, it calls `memory.log_escalation_decision()` best-effort (try/except: pass — never breaks orchestrate). Every meaningful executor escalation now leaves an ADR in `decisions.md` — the WHY survives `/clear`.
- **New `/renmark:hygiene` skill + `plugin/commands/hygiene.md` dispatcher.** Thin command stub; the skill invokes `python -m renmark.hygiene` and relays its output. **`/renmark:resume` now runs `validate_artifact_refs` as Step 1.5** and emits BLOCK/WARN lines; exits `SystemExit(2)` when any BLOCK is present. Ghost references are caught before re-entry, not after.
- **`/renmark:finish` documents (and runs) a single `log_decision()` write at branch close** — captures feature name, branch, stage transition, and completed stages. Idempotent on `(title, date)`, so re-running finish on the same day is safe.

**Why this matters for vibe coders:** `decisions.md` becomes the persistent WHY across `/clear` — re-entering a project two weeks later, the ADRs are still there and the reasoning isn't lost. `.renmark/` no longer grows unbounded — `python -m renmark.hygiene prune --apply` archives stale plan/spec/review/verification artifacts into `.renmark/archive/YYYY-MM/`. `/renmark:resume` catches dangling artifact pointers (deleted plans, renamed specs, stale-after-deadline reviews) before they cause downstream confusion. And executor escalations — previously a silent fact about a run — now leave an audit trail. Together they make renmark's promise of "artifacts over conversation" enforced, not aspirational.

**Acceptance gates:**

- ✅ pytest: 64 new tests + all existing tests passing (total 335 + 28 skipped)
- ✅ ruff check + ruff format: clean
- ✅ mypy strict: 0 errors (38 source files)
- ✅ plugin lint: OK
- ✅ 5/5 pre-commit gates OK

**Codex codereview pass applied before merge (4 Major fixes):**

A `/renmark:codereview` over the feature branch surfaced 4 Major findings. All were fixed on the same branch before merge; v0.5.6 ships with the helpers actually working on real renmark memory files (not just the synthetic shapes the original tests covered).

- **`renmark/memory.py`** — `dedupe_memory_log` and `age_out_memory_log` rewired to parse the REAL on-disk schemas: `### YYYY-MM-DD — Title` entries under H2 section headers for `features.md` / `bugs.md`, and `- ` bullets under H2 sections for `learnings.md`. The original H2-only parser worked on synthetic tests but was a no-op on production files. Tests now produce entries via the writer functions (`log_feature`, `log_bug`, `append_learning`) so readers round-trip with writers. Bullet parser also tightened to stop at paragraph breaks (`(Empty — will fill…)` placeholders no longer get absorbed into the last bullet's signature). Migrated `dt.utcnow()` → `dt.now(timezone.utc)` along the way (kept on `datetime.timezone.utc` rather than `dt.UTC` for Python 3.10 compatibility).
- **`renmark/hygiene.py`** — lifecycle artifact refs normalized via `Path.resolve()` before comparison. Absolute paths and repo-relative paths now match consistently; a verify run that stored `str(absolute_path)` is no longer mis-detected as unreferenced and prematurely archived. Ghost-ref counting uses the same normalization.
- **`renmark/lifecycle.py`** — `validate_artifact_refs` now emits `WARN` with `kind="out_of_tree"` for any artifact path that resolves outside the project subtree (absolute paths, `..`-escapes). `/renmark:resume` can no longer be tricked into trusting files outside `.renmark/` via a crafted `lifecycle.json` ref. Existing `BLOCK`/`WARN` semantics for missing/stale/unreachable artifacts and the BLOCK-first stable ordering are preserved.
- **Tests** — updated/added across `test_memory.py`, `test_hygiene.py`, `test_lifecycle.py`: real-schema dedupe + age-out cases via writer functions, absolute-path lifecycle ref regression, out-of-tree boundary cases. 6 new tests on top of the original 58, plus 3 existing prune tests rewritten against real schemas.

The Minor finding (#5 — escalation hook dead code in `_record_escalation`) is by design: the `escalated_to: str | None = None` kwarg is opt-in to avoid breaking existing call sites; real callers land as escalation contexts get fleshed out in a follow-up.

**Codereview lens — `--focus optimize` / `--focus standards` (same skill, different prompt):**

The driving idea: codereview's default lens is correctness — does this diff do what it claims, safely. Sometimes the question is different. Sometimes it's "is this fast?" or "does this look like the rest of the package?" Both deserve a review pass, neither deserves a second skill, a second module, or a second artifact path. `--focus` swaps the prompt template only. Same dispatcher, same sandbox, same `.renmark/reviews/YYYY-MM-DD-<sha>.review.md` output path. Zero new context cost, zero new modules, one new flag.

- **`--focus optimize`** — performance / idiom lens. Allocations, complexity, hot-loop work, blocking calls inside async paths, resource lifecycle (file handles, subprocesses, network sessions). Out-of-scope correctness bugs spotted in passing are listed as ASIDEs at the bottom of the report rather than mixed into the main findings — keeps the lens honest.
- **`--focus standards`** — UNWRITTEN-standards lens. Compares the diff against sibling files in the same package for conventions that aren't enforced by `tools/precommit.sh` (ruff/mypy/format already gate the written standards). Looks at pathlib vs os.path mixing, helper duplication, naming drift, error-handling shape, type-annotation density. The point is to catch the conventions a linter cannot see.
- **Default (no flag)** — unchanged. Same prompt body, same output, same artifact path. The summary line now reads `Review at <path> (focus: <mode>)` only for non-default modes — default invocations stay terse and exactly as they were.

**What did NOT ship and why.** `--focus prior-art` was considered and explicitly dropped. Prior-art lookup — "is there a stdlib module or well-known library that does this better than the hand-rolled version in the diff?" — is research, not review. It would require codex to reach beyond the diff and consult external knowledge or the web, which violates the read-only-sandbox shape of codereview and conflates two different jobs. That work belongs on `/renmark:brainstorm` (as a prior-art mode) or on a dedicated `/renmark:prior-art` skill if real usage justifies the slot. Future contributors should not re-add it to codereview without revisiting this trade-off.

**Do not change:**

- **The idempotency check in `log_decision`.** Same `(title, date)` short-circuits and returns without writing. Removing it floods `decisions.md` on re-runs — the same plan rerun on the same day would duplicate every ADR, defeating the purpose of the decision log.
- **`hygiene` is `meta` domain.** It MUST NOT advance `lifecycle.json` stage — hygiene is diagnostic, not a workflow stage. Moving it into the `build` domain breaks the workflow router (it would be treated as a pipeline stage and confuse `/renmark:resume`).
- **The `try/except: pass` inside `memory.log_escalation_decision`** (and the optional-kwarg pattern in `_record_escalation`). Decision logging is best-effort. A failure to write `decisions.md` must NEVER break orchestrate's escalation path — escalation is the load-bearing behavior, ADR write is the audit trail.
- **Hygiene's `dry_run=True` default.** Writes are opt-in via `--apply`. Flipping the default would silently rewrite project state on the first `python -m renmark.hygiene scan` — exactly the kind of surprise the artifact-first doctrine exists to prevent.
- **Hygiene's refusal to write outside `.renmark/`.** The `ValueError` guard against a caller-supplied `archive_root` outside the project tree is what keeps the "writes stay in the project" memory honest. Loosening it would let one project's hygiene run leak into `$HOME` or the global plugin install.
- **The curated memory-file set in `dedupe_memory_log` / `age_out_memory_log`.** `decisions.md`, `project.md`, `stack.md`, `architecture.md`, `conventions.md`, `routing.md`, `dev-standards.md`, `MEMORY.md`, `project-map.md`, `INDEX.md` are curated and MUST NOT be auto-pruned. Only `learnings.md`, `bugs.md`, `features.md` are treated as append-only logs subject to age-out.
- **BLOCK-only severity for missing `plan` / `spec` artifacts in `validate_artifact_refs`.** Other missing artifacts (review, verification, research) WARN. Promoting all missing artifacts to BLOCK would make `/renmark:resume` too noisy to use; demoting plan/spec to WARN would let users continue with structurally broken pipelines.

## v0.5.5 — 2026-05-28 (codereview fixes — 4 findings from v0.5.4 review applied)

**Patch release — fixes 4 findings (2 Major, 2 Minor) raised by `/renmark:codereview` on the v0.5.4 strict-mypy commit. Codex caught real semantic bugs that the type-checker rubber-stamped because the casts were unchecked or the migration broke backward compat invisibly. These are the kind of catches that justify running adversarial review after a mechanical refactor.**

The driving observation: mypy strict says "no errors" but doesn't guarantee runtime safety. v0.5.4's strict-mode pass got the count to zero by adding `cast()` calls and migrating data classes — both legitimate moves, but each created a new class of risk that codex flagged correctly in the post-commit review.

**Fixes for the 2 Major findings:**

- **`renmark/state/pipeline.py`** — v0.5.4 migrated `completed_tasks`/`failed_tasks` from `None + __post_init__ coercion` to `field(default_factory=list)`. Clean Python idiom, but it silently dropped the backward-compat path for legacy `pipeline.json` files (pre-v0.5.4) that stored those fields as `null`. On resume, those legacy files would crash at the first `in self.completed_tasks` or `self.failed_tasks.append(...)` call in `write_pipeline_state()`. v0.5.5 restores the safety net by **normalizing in the loader** instead of the dataclass: `read_pipeline_state()` strips `None`-valued list fields from the deserialized dict so the constructor receives clean defaults. The dataclass stays mypy-clean (no `# type: ignore` lies); the legacy compat lives where it belongs (at the I/O boundary). Also added `isinstance(data, dict)` guard for the deserialized JSON itself — a malformed pipeline.json containing a JSON array would have hit the `data.items()` call.

- **`pyproject.toml [[tool.mypy.overrides]]`** — v0.5.4 added `module = "requests.*"` to ignore missing stubs. But `providers/nim.py` and `providers/openai_compat.py` use bare `import requests`, and mypy's `requests.*` pattern doesn't match the top-level package — only its submodules. So v0.5.4's "0 mypy errors" claim was environment-dependent: on a clean install without `types-requests` cached locally, mypy would have reported import errors. Fixed to `module = "requests"` (bare), which matches the actual import statements. The `requests.*` glob is unused (renmark only does top-level imports) so omitting it removes the corresponding "unused section" mypy note.

**Fixes for the 2 Minor findings:**

- **`renmark/doctor.py:_load_json()`** — v0.5.4 wrapped `return json.loads(path.read_text(...))` in `cast(dict[str, Any], ...)` to satisfy `-> dict[str, Any]`. But `json.loads()` can validly return any JSON type — list, scalar, null. A non-object JSON file would type-check through the cast but crash at the first `.get()` or `.setdefault()` downstream, with the type system saying everything was fine. Now: parse into `obj`, validate `isinstance(obj, dict)`, return `{}` for non-objects, then `cast()` only the verified-dict path.

- **`renmark/init.py:_package_json()`** — same unchecked-cast pattern. A `package.json` that's structurally valid JSON but not an object would type-check through and crash at downstream `pkg.get("scripts", {})` calls. Same fix: `isinstance(obj, dict)` guard before the cast.

**Lesson recorded:**

> `cast()` is a promise to the type checker that you've verified the shape. If you haven't verified it, you're lying. v0.5.4 made 5 of these promises with `cast(dict[str, Any], json.loads(...))` and codex flagged the 2 that didn't validate. The fix isn't to remove cast — it's to do the validation cast claims you already did. Pattern locked in: `json.loads → isinstance(dict) guard → cast → return`.

**All 5 pre-commit gates green:** 298 pytests passing, ruff clean, ruff format clean, mypy strict 0 errors, plugin lint clean. Pre-commit hard-fails on mypy as of v0.5.4 — that gate is enforcing.

**Do not change:**

- The `isinstance(obj, dict)` guards in `doctor.py:_load_json` and `init.py:_package_json`. These exist specifically because `cast()` was lying without them. Removing the guards re-introduces the v0.5.4 silent-failure mode.
- The legacy-state normalization in `read_pipeline_state()`. Moving it to `__post_init__` reintroduces the mypy `unreachable` warnings v0.5.4 was trying to avoid AND lies to the type checker. Loader-level normalization keeps both invariants honest.
- The `module = "requests"` override (bare, not `requests.*`). Renmark's code only does top-level `import requests`. Adding `requests.*` back generates an "unused section" note on every mypy run.

## v0.5.4 — 2026-05-28 (full strict mypy — 59 → 0, pre-commit gate flipped to hard-fail)

**Patch release — closes the mypy backlog from v0.5.3. `tool.mypy` flipped from lenient to `strict = true`; all 59 strict-mode errors resolved; `tools/precommit.sh` step 5 promoted from informational soft-warn to hard-fail. Renmark's source tree now enforces full strict mypy on every commit.**

The driving idea: v0.5.3 shipped the infrastructure with mypy in soft-warn mode and 20 known errors. v0.5.4 closes that gap so the gates are real, not aspirational. Every commit from this point forward MUST pass strict type-checking — the discipline that catches real bugs at edit time instead of at runtime.

**Real bugs caught by strict mypy (now fixed in source):**

- **`renmark/release.py:332`** — `for i in issues` shadowed an outer `i = 0` int counter from an earlier loop, then was used as a string in the inner loop body. `[assignment]` error caught a genuine variable shadowing bug. Renamed to `for issue in issues`.
- **`renmark/dispatch.py:75`** — clever list-comp using `set.add()` as a side-effect was relying on `set.add` returning None (falsy). `[func-returns-value]` flagged it as a likely mistake; refactored to an explicit for-loop with clear intent.
- **`renmark/cli/_engine.py:488-495`** — three `Task | None` accesses past early-return guards. mypy couldn't narrow across multiple if-return branches. Added an `assert failed_task is not None` at the join point so the type narrowing is explicit. (Also documents the invariant for future readers.)
- **`renmark/doctor.py:373`** — `c.fix_fn()` called on `Optional[object]` field; mypy's `[operator]` error correctly flagged "object not callable". Field typed as `Callable[[], str] | None` instead.
- **`renmark/state/pipeline.py:33-41`** — `__post_init__` None-check on dataclass fields that were typed as `list[int]` (with `# type: ignore[assignment]` lying about the default value). mypy correctly reported the post-init branches as `[unreachable]`. Refactored to `field(default_factory=list)` — the idiomatic Python pattern for mutable defaults. The `# type: ignore` lies are gone.
- **`renmark/init.py:579`** — Python 3.10 syntax error fixed in v0.5.3 (backslash in f-string subexpression). Confirmed clean.

**Bulk mechanical fixes (no runtime behavior change):**

- **33 `[type-arg]` resolved** — bare `dict` and `tuple` in type position parameterized as `dict[str, Any]` and `tuple[Any, ...]`. Applied across 15 files via a regex pass with careful isolation (the script avoided `isinstance(x, dict)` calls, which would have been an illegal `isinstance(x, dict[str, Any])` and broke runtime). 4 files needed manual repair after the regex pass (`__future__` imports got bumped, fixed). Tests stayed green throughout.
- **6 `[no-untyped-def]` resolved** — added explicit `Task`, `Callable[[Task, Path], TaskResult]`, and `"_dispatch.TaskResult"` annotations to `_task_signature`, `_memory_log_outcome`, `_runner`, `dispatch_wave.run_task`, `_run_one.run_task`, `dispatch_task_isolated.subagent_runner`.
- **5 `[no-any-return]` resolved** — `return json.loads(...)` patterns wrapped in `cast(dict[str, Any], ...)` to preserve runtime behavior while satisfying the declared return type. Added `from typing import cast` where needed.
- **4 `[unreachable]` from subprocess.TimeoutExpired** — bytes/str disjoint-base checks in `verifier.py` and `providers/codex.py`. Added `# type: ignore[unreachable]` on those specific lines (the code IS unreachable when `text=True`, but the defensive branch handles a hypothetical caller that disables `text=True` later).
- **2 `[import-untyped]`** — added `[[tool.mypy.overrides]]` for `requests.*` with `ignore_missing_imports = true` (avoids a `types-requests` dev dependency for a transitive-only import in providers).

**`tools/precommit.sh` flipped to hard-fail:**

- Step 5 header renamed `5/5 mypy (type check)` → `5/5 mypy (strict type check)` to reflect the new posture.
- Old soft-warn branch (`say "WARN — type errors detected (informational)"`) removed.
- Replaced with hard-fail: `fail=1` on any mypy error, just like the other 4 steps. No way to commit through a broken type-check without `--no-verify`.

**Updated `pyproject.toml [tool.mypy]`:**

- `strict = false` → `strict = true`.
- Removed the `check_untyped_defs = true` line (subsumed by `strict`).
- Added `[[tool.mypy.overrides]] module = "requests.*"` with `ignore_missing_imports = true` (replaces the dropped tests.* override which was generating an "unused section" warning since `tests/` is in `exclude`).

**Acceptance criteria:**

> Step 5/5 of `tools/precommit.sh` says `OK`, not `WARN`, when run from a clean tree.

Status after v0.5.4:
- ✅ 298 pytests passing
- ✅ ruff check: 0 errors (after final `--unsafe-fixes` clean-up + `ruff format`)
- ✅ ruff format: 0 reformat needs
- ✅ **mypy strict: 0 errors** (was 59)
- ✅ plugin lint clean
- ✅ drift check clean
- ✅ pre-commit: 5/5 OK in ~3s

**Do not change:**

- The `cast(dict[str, Any], json.loads(...))` pattern at the json.loads return sites. `json.loads()` is typed as returning `Any`, which is fine in most callers but defeats the purpose of typed function returns. cast() preserves the typed surface without runtime overhead. Don't refactor to `# type: ignore` — that hides the seam.
- The `assert failed_task is not None` in `cli/_engine.py:482`. Looks redundant because the preceding if-return branches GUARANTEE non-None, but mypy can't narrow across multi-branch returns. The assert serves both as type narrowing AND as a runtime invariant (cheap; only fires if we ever break the narrowing).
- The hard-fail in `tools/precommit.sh` step 5. Backing off to soft-warn would let regressions slip in. If a strict mypy error blocks an urgent commit, fix the type — don't relax the gate.
- The `# type: ignore[unreachable]` markers in `verifier.py` and `providers/codex.py`. The bytes branch of the TimeoutExpired stdout/stderr handling is technically dead when `text=True`, but exists as defense in depth if `text=True` is ever removed. Deleting the bytes branch would silently lose the protection.

## v0.5.3 — 2026-05-28 (self-host — dev standards tightened: ruff strict, mypy lenient, GitHub Actions CI, 5-step pre-commit)

**Patch release — renmark adopts its own dev-standards prescriptions. Closes the 4 warn-level gaps surfaced when `/renmark:init` first ran against the renmark source repo at v0.5.2. The infrastructure now matches what renmark recommends to managed projects: linter + formatter + type-checker + CI + pre-commit, all wired into a single `tools/precommit.sh` script.**

The driving idea: a vibe-coder-targeted tool's first impression is its `dev-standards.md` report. v0.5.2 made that report visible; v0.5.3 makes it green. Each fix in this release was driven by reading renmark's own scanner output, then choosing strict-where-possible and pragmatic-where-intentional.

**New dev-standards infrastructure:**

- **`.github/workflows/test.yml`** (NEW) — 6-cell CI matrix: ubuntu+macos+windows × Python 3.10+3.13. Each cell runs `pip install -e .[dev]`, `ruff check`, `ruff format --check`, `mypy`, `pytest -q`, `renmark.release check`, `renmark.lint`. `fail-fast: false` so one cell's failure doesn't cancel the others — when something breaks we want to see if it's OS-specific or Python-version-specific, not get cells canceled. The Windows cell is the only place that exercises the same code paths `install.ps1` users hit, so without it Windows install regressions would ship blind.
- **`tools/precommit.sh`** (UPDATED) — augmented from 3 steps (pytest, drift, plugin lint) to 5 (added ruff lint+format, added mypy as informational warn). Mypy is soft-warn at the v0.5.3 baseline; once the 20 known mypy errors are cleaned up, flip the `fail=1` line to make mypy a hard-fail.
- **`pyproject.toml [tool.ruff]`** (NEW) — `target-version = "py310"`, `line-length = 120` (industry standard for modern Python), `select = ["E", "W", "F", "I", "B", "UP", "SIM", "RUF"]`, `ignore = ["E402", "RUF001", "RUF003"]` (E402 mid-file imports are intentional; RUF001/003 unicode-ambiguity rules flag renmark's deliberately stylized comments). Per-file ignores for `tests/**` (E501, F841, B011 — pytest patterns) and `renmark/init.py` (E501 — long template strings for project-map.md rendering).
- **`pyproject.toml [tool.mypy]`** (NEW) — lenient-strict baseline: `strict = false`, but enables `warn_return_any`, `warn_unreachable`, `warn_redundant_casts`, `check_untyped_defs`. Catches actual bugs (Any returns, dead code, None-handling violations) without flagging every internal helper that lacks a return annotation. v0.5.3 sets this baseline; the path to `strict = true` is tracked in a follow-up plan after the 20 remaining strict-mode warnings are cleaned up.
- **`pyproject.toml [project.optional-dependencies] dev`** — added `ruff>=0.6.0` and `mypy>=1.11` alongside the existing `pytest>=8.0.0`.

**Real bug fixes surfaced by the new gates:**

- **207-line dead-code deletion in `renmark/cli/_engine.py`** — ruff's `F821 Undefined name` caught a dead NIM-executor block (lines 521-727 in the pre-edit file). The block was preserved "for reference" after the NIM executor was removed in v0.2.0, but it referenced `client`, `NIMQuotaError`, `NIMRateLimitError`, `NIMError` — all undefined since v0.2.0. Function returned unconditionally at line 520, so the entire block was unreachable. Deleted; all 298 tests still pass.
- **Python 3.10 syntax fix in `renmark/init.py`** — `f"... {desc.replace('|', '\\|') if desc else '—'} ..."` used a backslash inside an f-string subexpression, which is a Python 3.12+ syntax feature. On the declared minimum Python 3.10, this would syntax-error at module import. Tests didn't catch it because the dev box runs Python 3.13. The new Windows-CI cell at Python 3.10 would have caught it on the first PR; ruff caught it locally. Extracted the conditional to a separate variable before the f-string.
- **Removed unused imports** — `format_reminder_prompt` and `retry_prompt` in `_engine.py` became unused after the NIM dead-code deletion. Ruff's `F401` flagged them; pruned.
- **97 auto-fixed ruff issues** — `typing.X` → `collections.abc.X` migrations (UP rule), unused locals, simplifiable comprehensions, etc. All auto-applied, no behavior change.
- **10 unsafe-fix transforms** — SIM rules (use `contextlib.suppress` for try/except/pass patterns, collapse nested if statements, use ternaries for simple else-return). Applied with `--unsafe-fixes`, verified by full test re-run.
- **37 files reformatted** by `ruff format` — purely cosmetic, no behavior change. Format is now stable.

**Manual surgical fixes:**

- Three long-line wrappings — `cli/_engine.py:811` (argparse help text), `lifecycle.py:284` (long error message return), `providers/codex.py:80-82` (multi-line prompt template). All wrapped at 120 chars without semantic change.
- Two SIM rule fixes — `lifecycle.py:209` (collapsed nested `if`), `memory.py:212` (replaced multi-branch if/else with ternary). Semantic equivalents.
- Cleaned up `_engine.py` import block — removed two imports made unused by the dead-code deletion.

**What's deliberately deferred to follow-up:**

- The 20 lenient-strict mypy warnings: 3 union-attr (Task | None access), 4 no-any-return (typed function returning Any), 2 unreachable, others. All real catches; all warrant fixing. Tracking issue: cleanup pass to land `strict = true`.
- No-op `model = _choose_model(task, cfg)` removed from the dead block — that helper is no longer reachable. Could be deleted from `_engine.py` entirely; preserved for now in case the NIM executor ever returns.

**Acceptance criteria (from spec):**

> A vibe coder running `python -m renmark.init` on this repo should see HEALTH: 0 gaps.

Status after v0.5.3:
- ✅ Test framework: pytest (configured + 298 tests passing)
- ✅ Linter: ruff (configured + clean)
- ✅ Formatter: ruff format (configured + clean)
- ✅ Type checker: mypy (configured + lenient-strict baseline; soft-warn in pre-commit until backlog clears)
- ✅ CI: GitHub Actions (6-cell matrix; will pass once pushed to a GitHub remote)
- ✅ Pre-commit hooks: `tools/precommit.sh` (already wired via `install.sh --dev`)

**Do not change:**

- The "lenient-strict" mypy baseline. Going straight to `strict = true` would BLOCK pre-commit on 20 errors and grind contributions to a halt while the cleanup ships. The two-step path (lenient now, strict later) keeps the door open for incremental commits.
- The mypy soft-warn in `tools/precommit.sh`. Hard-failing mypy at v0.5.3 baseline would mean every commit ships under `--no-verify`, defeating the purpose. Once the 20-error backlog is cleaned up, flip to hard-fail.
- The line-length = 120 setting. 100 generated 39 E501 warnings (mostly unavoidable long signatures and template strings); 110 still left 17; 120 is the modern Python community standard and produces zero noise without forfeiting the lint budget that catches genuinely-too-long lines.
- The `RUF001`/`RUF003` ignores. Renmark deliberately uses unicode (`×`, `ℹ`, `⚠`, `→`) in stylized output and comments. Re-enabling these rules would generate hundreds of false positives across the codebase.
- The 207-line dead-block deletion in `cli/_engine.py`. It was non-executing dead code referencing a removed subsystem (NIM, deleted v0.2.0). Resurrecting it requires bringing back the NIM provider AND fixing the references; both are deliberate decisions, not accidents.

## v0.5.2 — 2026-05-28 (distribution readiness — LICENSE, install.ps1, Codex prompt, vibe-coder README)

**Patch release — makes the zip safely distributable to vibe coders on any of the three OS paths (Mac/Linux/WSL, native Windows). Closes the four real distribution blockers identified during the v0.5.1 audit: missing LICENSE file, no Windows installer, stale README, no Codex handling.**

**Reason for shipping now:** the audience is non-technical vibe coders sharing the zip hand-to-hand. They won't manually copy folders into `%USERPROFILE%\.claude\plugins\` and they won't hand-edit `settings.json`. Without `install.ps1`, Windows users would hit the same silent failure WSL did before v0.5.1 — installer "succeeds" but `/renmark:*` commands never appear. v0.5.2 closes that gap so every supported OS has a single command that produces a working install.

**New: LICENSE file (legal blocker for redistribution):**

- **`LICENSE`** (NEW) — MIT License text at repo root. `pyproject.toml` already declared MIT but the actual license text was missing from both the repo and the release zip. MIT redistribution requires the text shipped alongside the code; without it, anyone who pulls the zip can't legally redistribute. v0.5.2 ships the LICENSE file in the zip.

**New: `install.ps1` (Windows PowerShell installer):**

- **`install.ps1`** (NEW) — Mirrors `install.sh` for native Windows. Uses NTFS **junctions** (directory aliases that don't require admin/elevation) instead of symlinks, with a copy-fallback if junctions fail (uncommon — usually a corporate AppLocker policy). Performs the same 4 steps as the bash version: plugin install → `pip install -e .` → Codex prompt → `python -m renmark.doctor --fix` for registry/settings.json registration.
- **`-Uninstall` flag** — removes everything bash uninstall does: junction/copy, cache directory, settings.json entries, installed_plugins.json entries.
- **`-NoCodex` flag** — for scripted/non-interactive installs that should skip the Codex prompt.

**New: Codex CLI detection + offer-to-install (both installers):**

- **`install.sh`** — after the pip install step, detects whether `codex` is on PATH. If missing AND stdin is a terminal AND npm is available, prompts: *"Install Codex CLI now via npm? [Y/n]"*. On Y, runs `npm install -g @openai/codex` and prints the `codex login` reminder. On N or non-interactive, prints the manual install steps. If npm itself is missing, prints the Node.js install URL + manual steps. Codex is OPTIONAL — without it, `executor: codex` tasks fall back to Sonnet automatically, so the prompt is a recommendation not a hard requirement.
- **`install.ps1`** — same logic in PowerShell. Same prompt, same fallbacks, same package name (`@openai/codex` — Codex CLI bundles per-platform binaries, so the npm command is identical on all three OSes).

**README rewrite for vibe-coder audience:**

- **`README.md`** — replaced the stale `unzip ai-system-renmark-v0.3.0-*.zip` example with a version-agnostic `v*` glob. Rewrote the Windows section from "manually copy folders into `%USERPROFILE%\.claude\plugins\renmark\` (which won't work — the silent-failure bug)" to `.\install.ps1`. Added a dedicated **Codex CLI** section explaining when to install it and the one-line install command. Added **Troubleshooting** section explaining what to do if `/renmark:*` commands don't appear (`python -m renmark.doctor --fix`).
- **WSL-vs-Windows-native note** — explicit callout: if Claude Code is running inside WSL Ubuntu, use `install.sh` not `install.ps1`. PowerShell installer only registers with `%USERPROFILE%\.claude\` which Claude Code under WSL doesn't read.

**Do not change:**

- **The `@openai/codex` npm package name.** Codex CLI uses an optional-platform-dependencies pattern that bundles per-OS binaries (`@openai/codex-linux-x64`, `@openai/codex-darwin-arm64`, `@openai/codex-win32-x64`) — the parent `@openai/codex` package resolves the right binary at install time. One install command works on every supported OS.
- **The junction-then-copy fallback in install.ps1.** Junctions don't need admin, copies don't either, but copies break the "edit source → see changes" workflow. We prefer junction so dogfooding stays live; the copy is only a last resort when corporate policy blocks junctions entirely.
- **`-NoCodex` as opt-out (not opt-in).** Defaulting to "ask about Codex" is the vibe-coder-friendly behavior; CI/scripted callers can pass `-NoCodex` to suppress the prompt. Flipping the default would silently skip a recommended dependency for most users.

## v0.5.1 — 2026-05-28 (/renmark:doctor + install.sh self-registers with Claude Code)

**Patch release — fixes the silent-install failure mode discovered during v0.5.0 dogfooding. The canonical `install.sh` only created symlinks; Claude Code requires THREE additional entries in `~/.claude/settings.json` and `~/.claude/plugins/installed_plugins.json` before slash commands appear. Without them, `/renmark:*` silently doesn't show up — the worst-possible UX for a vibe-coder-targeted tool whose first impression depends on a clean install.**

**New command — `/renmark:doctor`:**

- **`plugin/commands/doctor.md`**, **`plugin/skills/doctor/SKILL.md`** (NEW) — thin command stub + skill dispatcher. The skill invokes `python -m renmark.doctor` and relays its checklist output; agents do no diagnosis work themselves.
- **`/renmark:doctor`** — runs 9 health checks: CLI on PATH, Python package importable, VERSION file present, plugin manifest version parity, Claude Code registry registration, settings.json marketplace registration, settings.json plugin-enabled flag, cache install path resolves to source, convenience symlink. Each check prints a ✓ / ✗ / ! glyph, a one-line detail, and (for failures) a `fix:` line.
- **`/renmark:doctor --fix`** — applies safe auto-fixes for the four known-remediable failures (add to `extraKnownMarketplaces`, set `enabledPlugins[…] = true`, register in `installed_plugins.json`, create the cache version symlink). Every modified file gets a timestamped `.doctor.bak.<unix-time>` backup first.
- **`/renmark:doctor --json`** — machine-readable output for scripting (CI, integration with editor extensions, etc.).

**New Python module — `renmark/doctor.py`:**

- 9 deterministic checks. Read-only by default; `--fix` writes only to `~/.claude/settings.json`, `~/.claude/plugins/installed_plugins.json`, and `~/.claude/plugins/cache/renmark-local/<version>/`.
- Each `Check` carries: name, status (`pass` / `fail` / `warn`), one-line detail, optional `fix_cmd` for users to run manually, and (when auto-fixable) a callable that applies the fix idempotently.
- Detects 4 specific drift modes that cause silent load failure: (1) version mismatch between VERSION file and installed_plugins.json registry, (2) missing `extraKnownMarketplaces.renmark-local` (cache file `known_marketplaces.json` is regenerated from this — editing only the cache doesn't stick), (3) missing `enabledPlugins["renmark@renmark-local"] = true`, (4) cache symlink pointing to a non-existent or wrong-version directory.

**`install.sh` now self-registers:**

- After the symlink and pip-install steps, calls `python -m renmark.doctor --fix` to write the three required registry entries automatically. Same Python logic that `/renmark:doctor` uses to repair broken installs — DRY, with backups always taken before writes.
- `install.sh --uninstall` now also removes the renmark entries from `settings.json` and `installed_plugins.json`, and wipes `~/.claude/plugins/cache/renmark-local/`. Pre-v0.5.1 uninstalls left dangling registry entries that surfaced as "Plugin not found in marketplace" warnings in the `/plugin` UI.
- Post-install banner adds `/renmark:doctor` to the skill list.

**Background — why this matters:**

A directory-marketplace Claude Code plugin needs THREE moving parts to surface its slash commands:

1. `~/.claude/plugins/installed_plugins.json` — registry entry under `<plugin>@<marketplace>`, with `version` matching the marketplace's current version (drift causes silent skip), and `installPath` pointing to an existing directory.
2. `~/.claude/settings.json` → `extraKnownMarketplaces.<marketplace-name>` — tells Claude Code where the marketplace lives. The cache file `~/.claude/plugins/known_marketplaces.json` is *derived* from this; editing only the cache doesn't survive a reload.
3. `~/.claude/settings.json` → `enabledPlugins["<plugin>@<marketplace>"] = true` — Claude Code requires explicit enable for directory marketplaces. Without this, the plugin loads (no error) but commands don't appear in the slash menu.

A plain `install.sh` that only writes symlinks misses #2 and #3 entirely, and the resulting failure is silent — `/reload-plugins` reports "1 error during load" without naming the plugin. v0.5.1 closes that gap.

**Other changes:**

- **`plugin/skills/help/SKILL.md`** — `/renmark:doctor` added to the command catalog with a hint about when to use it.

**Do not change:**

- The doctor module's "read-only by default" stance. Making it edit settings.json without `--fix` would surprise users who run it for diagnosis.
- The `.doctor.bak.<timestamp>` naming convention for backups. The integration tests and rollback procedures assume that pattern.
- The decision to delegate install-time registry writes to `python -m renmark.doctor --fix`. Pulling the JSON-edit logic into raw bash inside install.sh would duplicate it and re-create the maintenance burden v0.5.1 was designed to eliminate.

## v0.5.0 — 2026-05-28 (/renmark:init — codebase map + dev-standards/health scanner)

**Minor release — renmark gains its own analog to Claude Code's native `/init`, but designed around context-window hygiene from day one. Walk into any project (greenfield or production) and get a verdict: what the code looks like, what standards the project enforces, and where the standards are loose enough to break things.**

The driving observation: CLAUDE.md is loaded into the system prompt on every turn of every conversation, forever. Embedding a 2-3k-token project map in CLAUDE.md would be paid permanently as context tax — worse than re-running `find` + `grep` on demand. So the design splits content by access pattern: tiny stub in always-loaded context (~200-300 tokens), full payload in on-demand files (`.renmark/memory/project-map.md`, `.renmark/memory/dev-standards.md`).

**New command — `/renmark:init`:**

- **`plugin/commands/init.md`**, **`plugin/skills/init/SKILL.md`** (NEW) — thin command stub + skill dispatcher. The skill's only job is to invoke `python -m renmark.init` and relay the one-line summary; agents do no scanning, no regex, no rendering. Token cost per invocation: near-zero (just script stdout).
- **`/renmark:init --deep`** — opt-in flag for slower checks: samples last 20 git commits for conventional-commits style. Reserved for future expensive checks (GitHub branch-protection lookups, test-naming inference). Baseline scan runs without the flag.
- **`/renmark:init scan`** — diagnostic mode; prints what would be detected, writes nothing.

**New Python module — `renmark/init.py`:**

- **Project map scanner.** Walks the repo respecting `.gitignore` (excludes `.git`, `node_modules`, `.venv`, `dist`, `build`, `.next`, `target`, `.renmark/state`, `.renmark/debug`, etc.). Detects stack from `pyproject.toml` / `package.json` / `go.mod` / `Cargo.toml` / Claude Code plugin manifest. Extracts public symbols from the top-20 largest source files for Python, JS/TS, Go, Rust, Ruby. Caps modules table at 40 rows, symbols-per-file at 6, top-level layout at 7 dirs. No file bodies, no docstring transcripts.
- **11 dev-standard detectors.** Test (pytest/jest/vitest/cargo/go), lint (ruff/flake8/eslint/rubocop/clippy), formatter (black/ruff format/prettier/rustfmt/gofmt), type-checker (mypy/pyright/tsc-strict), CI (GitHub Actions/GitLab/CircleCI — extracts workflow names), pre-commit (`.pre-commit-config.yaml` hooks + Husky), env schema (`.env.example` key names only, never values), database/migrations (alembic/prisma/drizzle/knex), local-dev startup (npm scripts/Makefile/docker-compose), code style (`.editorconfig`), dep policy (dependabot/renovate/lockfiles).
- **11 standards-health gap checks** with severity ranking. 🚨 danger: `.env` committed without `.gitignore` entry; multiple JS package-manager lockfiles concurrently. ⚠ warn: no linter; no type checker (or tsconfig without `"strict": true`); no tests in a >10-file project; test framework configured but zero test files; linter not wired to pre-commit OR CI; no CI on a multi-file project; pre-commit AND CI both missing; missing lockfile when `package.json` exists. ℹ info: no `.gitignore`; no README. Each gap carries a *tighten-this* recommendation pointing to the exact remediation.
- **Byte-equality skip on every artifact.** If the rendered stub body matches the existing `<!-- BEGIN:project-stub -->` block in CLAUDE.md, the file is not rewritten — no prompt-cache bust. Same check for `project-map.md` and `dev-standards.md` (stripping the timestamp header line so the freshness stamp doesn't trigger spurious rewrites).

**Three artifacts, three access patterns:**

- **CLAUDE.md / AGENTS.md stub** (always-loaded, ~250 tokens) — stack one-liner, top-level layout, `Dev gates:` line listing test/lint/typecheck/CI commands when detected, and pointers to the on-demand files. The gates line is conditional: greenfield projects with no detected standards produce a stub with no gates line at all.
- **`.renmark/memory/project-map.md`** (on-demand, opt-in payload) — full directory tree, modules table with symbols, user-facing commands catalog. Read by agents that need to navigate the codebase.
- **`.renmark/memory/dev-standards.md`** (on-demand, opt-in payload) — detected-standards table + standards-health section with severity-ranked gaps and recommendations. Read by agents about to make non-trivial changes.

**Auto-refresh hooks wired into the pipeline:**

- **`/renmark:setup`** — step 5.5 seeds the project map and dev-standards on first run (skipped if `project-map.md` already exists). One-time bootstrap.
- **`/renmark:finish`** — step 1.5 refreshes both artifacts after verifiers pass but before the branch summary. If the byte-equality skip says nothing changed (e.g. feature only fixed bugs, no shape change), no files are written, no commit is made, no cache is busted. If anything changed, files are staged and committed as `docs: refresh project map` so the refresh ships with the feature.
- **`/renmark:init`** — manual escape hatch for hand-edited or out-of-pipeline changes.
- **Explicitly NOT hooked into `/renmark:orchestrate` or `/renmark:debug`** — those run too frequently for the cost-to-value ratio. Per-task or per-fix refreshes would bust the CLAUDE.md cache 5-15 times per feature for the same information value finish would refresh once.

**stdout contract — what the agent sees:**

```
OK  stub=<created|refreshed|unchanged> agents=<…|skipped> map=<…> standards=<…> modules=N commands=N langs=py,ts,… ref=YYYY-MM-DD@<git-sha>
HEALTH: N gaps (X danger, Y warn, Z info) — see `.renmark/memory/dev-standards.md`
```

The HEALTH line only appears when at least one gap exists. A clean project produces just the OK line.

**Other changes:**

- **`plugin/skills/help/SKILL.md`** — `/renmark:init` added to the command catalog.
- **`.claude-plugin/marketplace.json`** — skills list updated to include `init`.

**Do not change:**

- Changelog format — renmark reads and appends to this file automatically; the `## [date] — [title]` heading shape is parsed by the version-drift gate and the release-notes generator.
- The byte-equality skip logic in `renmark.init` — without it, every `/renmark:finish` would rewrite CLAUDE.md and bust the prompt cache for every conversation in the project. The skip is what makes the auto-refresh strategy affordable.
- The "stub vs payload" split — moving full module/symbol detail back into CLAUDE.md would re-introduce the context-tax problem this release was designed to solve.

## v0.4.0 — 2026-05-28 (verify --qa / --deep-qa: live-browser E2E verification)

**Minor release — verification grows a second lens. Smoke proves the happy path *responds*; QA proves it *works in a browser*; Deep QA proves it *fails gracefully at the edges*. All three are reachable from each other in one keystroke via a shared hand-off menu.**

The driving goal: stop the loop of "ask to fix → find it's still broken → surgically fix what QA should have caught." Live-browser E2E that runs automatically-on-request and produces specific, reproducible findings makes the fix loop converge. Spec lived as draft at `.renmark/specs/2026-05-27-verify-qa-browser-e2e.spec.md` since v0.3.3; this release implements it as skill prose with zero new Python deps.

**New shared file:**

- **`plugin/skills/_shared/handoff-menu.md`** (NEW) — single source of truth for the quality-gate hand-off menu, referenced by `verify`, `verify --qa`, `verify --deep-qa`, and `codereview`. Same `_shared/` pattern as `scope-contract.md` (already excluded from the plugin linter as of v0.3.3). Documents the four canonical gate letters (`[s]` Smoke, `[qa]` QA, `[dq]` Deep QA, `[c]` Code review) plus the terminal actions, and the five rendering rules (omit the gate just run; show `[dq]` only after `--qa` passes; show `[d]` only on failure; etc.). Adding a future gate (perf, security) is now a one-file edit.

**`verify --qa` — one live-browser happy-path flow:**

- **Applicability gate.** Web project (per `.renmark/memory/stack.md` / `package.json`) + Chrome DevTools MCP reachable (`list_pages` probe). Non-web project → "N/A, no browser surface." MCP unavailable → degrade to shell smoke with a one-line note. Never crash, never block.
- **Server lifecycle.** Detect-or-boot the dev server via the run command from `CLAUDE.md § Testing` / `stack.md`; record `qa_started_server` so we tear down only what we booted, never a server the user is using.
- **Single happy-path flow** derived goal-backward from the spec's #1 user-visible behavior; driven via `navigate_page` / `take_snapshot` / `click` / `fill` / `wait_for` / `take_screenshot` / `list_console_messages` / `list_network_requests`.
- **Pass criteria (5 hard, 2 soft).** Hard: page loads (not blank/500), no uncaught console errors, no 4xx/5xx on the path, expected result element renders (`wait_for`), no error UI. Soft: persistence + latency. Each failure names *which* criterion broke so the verdict line is specific.
- **Context-hygiene contract — non-negotiable.** Screenshots go to `.renmark/reviews/qa/<feature>/step-N.png`; console + network dumps go into the artifact body; accessibility snapshots are used transiently to find selectors and then discarded. The orchestrator sees only the ≤5-line verdict block + artifact pointer.
- **Artifact:** `.renmark/reviews/YYYY-MM-DD-<sha>.qa.md` via `summary.write_artifact(artifact_type="qa", generator="verify-qa", ...)`.

**`verify --deep-qa` — 3 risk-ranked edge-case flows:**

- **Hard gate behind a passing `--qa`.** Refuses unless a `.qa.md` artifact exists for the current sha with `completion_state="complete"` and `generator="verify-qa"`. Edge cases on a broken happy path are noise.
- **Plan phase — risk-rank, then pick 3 (no browser yet).** Reads the diff (bounded — never pasted into chat), the feature behaviors, and `bugs.md` entries whose `files:` overlap, then ranks failure modes by likelihood using a 6-category checklist (empty/missing, boundary/size, malformed/hostile, error path, state/sequence, authz). Surfaces top 3 + one-line rationale each for user approval before opening a browser.
- **Runs them serially**, in risk order, in the singleton main-agent browser. Pass condition is **graceful handling**: no uncaught console exception, no crash, no corrupt state, either tolerates the input OR rejects with a clear visible error — not silent no-op, not infinite spinner.
- **Artifact:** `.renmark/reviews/YYYY-MM-DD-<sha>.deep-qa.md`; per-case evidence under `.renmark/reviews/qa/<feature>/deep/case-N/`.
- **Why serial-in-main, not subagents:** at 1+3 flows that each dump evidence to disk and return only verdict lines, the main context never holds heavy payloads — subagent fan-out buys nothing against a singleton browser and adds coordination cost.

**Three gates, mutually reachable:**

- `verify` (smoke), `verify --qa`, `verify --deep-qa`, and `codereview` all now render the menu from `_shared/handoff-menu.md`, omitting the gate just run and showing `[dq]` only after `--qa` passes for the current sha and `[d]` only on a failure. Re-testing a feature from a different angle is one keystroke at any point.
- `codereview`'s hand-off was extended: in addition to its existing `[o] Open` / `[fix] Fix` actions, it now offers Smoke + QA + (conditionally) Deep QA + Debug + Finish + Nothing.

**Convergence loop (the certainty mechanism):**

- Every `--qa` / `--deep-qa` failure calls `memory.log_bug` with a reproducible finding — symptom + console/error + file:line if discoverable + repro steps. A later `verify --qa` re-runs the failing flow plus the `bugs.md` regression set; the fix loop converges. No "still broken" surprises downstream.
- Every run (pass or fail, any mode) calls `memory.append_learning` (G8 compounding).

**No Python module changes required.** The browser MCP session is the main agent's; `renmark/` Python stays as-is. `summary.write_artifact` accepts `artifact_type="qa"` / `"deep-qa"` via its existing generic field; no signature changes.

**Lifecycle:** `--qa` / `--deep-qa` do NOT add new stages. Both run at stage `verified` (or re-run there). The verification artifact pointer is updated via `lifecycle.write_lifecycle(artifact_update=("qa", ...))` / `("deep-qa", ...)`, but `stage` stays `verified` — codereview / finish remain the next recommended steps.

**Files touched:**

- New: `plugin/skills/_shared/handoff-menu.md`.
- Modified: `plugin/skills/verify/SKILL.md` (smoke hand-off rewritten to use shared menu; full `--qa` and `--deep-qa` sections added), `plugin/skills/codereview/SKILL.md` (hand-off appends shared menu), `plugin/commands/verify.md` (description + `argument-hint` + mode-selection notes), `.renmark/specs/2026-05-27-verify-qa-browser-e2e.spec.md` (`status: draft` → `implemented` + `related_release: v0.4.0`), all 7 canonical version locations, this changelog.

**Do not change:**

- The hand-off menu text lives in `_shared/handoff-menu.md` and nowhere else. If you find yourself pasting the menu into a SKILL.md, stop and reference the shared file instead — drift across skills was the exact problem this directory was added to solve.
- The Deep QA gate (`--deep-qa` refuses unless a passing `.qa.md` exists for the current sha) is load-bearing. Removing it means edge cases run against a happy path that doesn't work, producing meaningless noise.
- The context-hygiene contract for `--qa` / `--deep-qa` (screenshots/console/network → disk; orchestrator sees only the ≤5-line verdict) is non-negotiable. If a future change makes the orchestrator ingest browser payloads, the whole point of running this in the singleton main agent is defeated — split it into a subagent flow first.
- The browser MCP session is a singleton owned by the main agent. Do not introduce a subagent-driven browser flow; that path (subagent fan-out for many journeys) was explicitly deferred.

**Verification:** 298 unit tests pass (no Python changes, no test changes), plugin lint clean, drift check clean (all 7 version locations at v0.4.0). The new skill prose is text-only and exercised by the existing lint test that checks every SKILL.md has matching frontmatter + paired command shim.

## v0.3.3 — 2026-05-27 (pipeline streamlining + research + write boundary)

**Fewer commands, more done per command. The day-to-day path is now four steps (brainstorm → plan → orchestrate → finish) because validation and verification auto-run inside the steps they belong to. brainstorm gained research; the project-write boundary is now a hard rule.**

**Distribution packaging (new — `/renmark:finish` § Release):**

- **`renmark.release.build_package()`** — pure-Python (no rsync/zip CLI, no new deps) builder that zips the distributable into the **project's** `.renmark/baks/<name>-v<version>.zip`, version-anchored to match the git tag `v<version>`. Honors the project-write-boundary rule (writes only inside the project) and excludes `.git`, `.venv`, `__pycache__`, `.env`, `.renmark/`, `PLAN.md`, etc. CLI: `python -m renmark.release package`. (+5 tests)
- **`/renmark:finish` gains an `[r] Release` option:** drift-gate → build the local bak (always, offline) → tag `v<version>` → **if** a git remote + `gh` exist, offer to push the tag and `gh release create` with the zip attached; otherwise report the local bak + tag as a complete offline release. One version string across bak filename, git tag, and GitHub release — never drifting. The local `.renmark/baks/` copy is the offline fallback when you don't want to pull from GitHub.
- `.renmark/baks/` is gitignored (regenerable; the GitHub release is the shareable canonical copy).
- **`--dest` / `--name` overrides** on `release package` (and `build_package(dest_dir=, archive_stem=)`) — a maintainer escape hatch to package renmark's OWN release to a sibling dir with a custom name (e.g. `~/projects/ai-system-renmark-v<version>-<date>.zip`), rather than into a managed project's `.renmark/baks/`. Managed-project releases still default to `.renmark/baks/`.

**Pipeline auto-chaining (commands stay standalone-callable):**

- **`/renmark:plan` auto-runs `/renmark:check-plan`.** After writing the plan, validation runs automatically before the dispatch gate. BLOCK loops back to fix; PASS/WARN advances the lifecycle to `plan-validated` and shows the cost-approval gate. The critical cost gate stays in `plan` — auto-validation never silently dispatches. `/renmark:check-plan` remains callable on any plan.
- **`/renmark:orchestrate` auto-runs `/renmark:verify`.** A fully clean run (all tasks pass) flows straight into goal-backward verification, which advances the stage to `verified` and presents the review/finish hand-off. On any task failure the run pauses and does NOT auto-verify. `/renmark:verify` remains callable standalone.

**brainstorm upgrades:**

- **Research phase (new).** Before proposing approaches, brainstorm researches best practices, prior art (existing software that solves the problem), and live GitHub reference implementations via `WebSearch` / `WebFetch` / Context7. Findings are written to a `.renmark/research/` artifact; only a ≤5-line summary enters the conversation (G3/G6). The design is now informed, not invented. (Folds in the previously-planned `/renmark:research` gap.)
- **Owns the scope contract.** brainstorm now runs the stack/deployment/MVP questions and writes the records (`stack.md` + CHANGELOG scope entry), so `/renmark:plan` detects them and skips re-asking.

**Single source of truth:**

- **`scope-contract.md` moved to `plugin/skills/_shared/`** and is now referenced by both `brainstorm` and `plan`. The stack/deployment/MVP questions live in exactly one place and can't drift. The plugin linter now skips `_`-prefixed shared dirs (they're reference files, not skills). (+1 lint test)

**Hard rule — project-write boundary:**

- **renmark must never write outside the project.** All specs, plans, reviews, research, logs, and memory go under the project's `.renmark/` subtree (or project-root docs). The global plugin install (`${CLAUDE_PLUGIN_ROOT}`, `~/.claude/...`) is read-only — reading templates/reference files from it is fine, writing to it is forbidden. Codified as `project-write-boundary-rule` in `CLAUDE.md.template` and mirrored in `AGENTS.md.template`.

**Verification:** 292 unit tests pass (+1 lint test), 28 integration skipped, shadow baselines clean, plugin lint clean. These are skill-prose + linter changes; the lifecycle stage machine already supported the auto-chained flow, so no Python state changes were required beyond the linter.

## v0.3.2 — 2026-05-27 (context-hygiene + maintainability audit)

**Patch release — seven audit fixes hardening the isolation boundary, spend reporting, and module structure. No breaking changes; the public import surface is preserved.**

**Context-hygiene fixes:**

- **G3 char-cap leak closed** — `SubagentOutput.__post_init__` (`dispatch.py`) now enforces the ≤1200-char-per-line cap and a non-string guard, not just the ≤5-line count. A 5-line × 5000-char payload can no longer slip through `parse_subagent_response`. The cap matches `schemas.py` and `summary.py`. (+3 tests)
- **Lifecycle dead-pointers fixed** — `NEXT_BY_STAGE` no longer routes to unimplemented skills (`/renmark:document`, `/release`, `/approve`, etc.). `next_recommended()` resolves through a new `IMPLEMENTED_SKILLS` set and falls back to manual hints; aspirational routing preserved in `NEXT_BY_STAGE_PLANNED`. A regression test iterates every canonical stage. (lifecycle.py)
- **Agent-call spend ledgered** — new `state.log_agent_call()`; the orchestrate skill records every haiku/sonnet/opus Agent return so `/renmark:roadmap` reports real spend. `roadmap.py` now prices opus at ~$0.015/kT (was treated as free) and includes haiku.
- **Honest cost preview** — `plan/SKILL.md` bakes the ~10k Agent-call overhead into the displayed total instead of footnoting it; the dry-run footer was corrected to match.
- **Step-0 boilerplate consolidated** — new `lifecycle.skill_preamble(repo, skill)` replaces the duplicated `context_budget_check` + `record_skill_invocation` block across all 14 SKILL.md files. Domain resolves centrally from `DOMAIN_BY_SKILL`, so per-skill drift is impossible.
- **Artifact-dir rotation** — new `state.rotate_dir()` caps `wave-summaries/` (50), `logs/` (50), and `escalations/` (20), archiving overflow to `.renmark/state/archive/<stamp>/`. Best-effort; never breaks a running orchestrate. (+4 tests)

**Maintainability:**

- **`state.py` (538 lines) → `state/` package** — eight cohesive submodules (`_core`, `usage`, `pause`, `pipeline`, `logs`, `commits`, `skills`) behind a re-exporting `__init__.py`. Rotation caps are read via `_core` at call-time so they stay monkeypatchable.
- **`cli.py` (982 lines) → `cli/` package** — execution engine (`_engine.py`) split from the self-contained subcommand handlers (`commands.py`); re-exporting `__init__.py` keeps `cli.main` / `cli.cmd_task` / `cli.execute_plan` intact.

**Verification:** 291 unit tests pass (+10 new), 28 integration skipped (codex/network-gated), shadow baselines re-accepted (lifecycle `case-full-walk`), functional smoke green (`--usage`/`--roadmap`/`--logs`/dry-run). Independent codex review was unavailable (account model limitation); reviewed via diff + runtime invariant checks.

## v0.3.1 — 2026-05-21 (integration testing + guardrails)

**Patch release — the framework now defends itself against regressions.**

Three layers of test discipline land in v0.3.1: per-commit guardrails (fast), per-release integration smoke (thorough), and per-task shadow tests (regression detection on load-bearing subsystems). Every layer is opt-in or gated so day-to-day work stays fast.

**New modules:**

- **`renmark/schemas.py`** (NEW, 24 tests) — zero-dependency structural validators for `lifecycle.json`, `pipeline.json`, `SubagentOutput` JSON, and `ArtifactMetadata`. G11 isolation enforcement catches transcript/diff/reasoning leakage at the schema layer. G3 summary boundary enforced (≤5 lines, ≤1200 chars per line). G12 lifecycle byte budget enforced. CLI: `python -m renmark.schemas {lifecycle|pipeline|subagent|artifact} <path>`.
- **`renmark/lint.py`** (NEW, 25 tests) — plugin contract linter. Verifies every SKILL.md has valid frontmatter with matching `name:`, every `commands/<name>.md` has a paired `skills/<name>/SKILL.md` (and vice versa — no orphan commands, no unreachable skills), CLAUDE.md.template has balanced `BEGIN:` / `END:` rule-block markers, and `plugin.json` has required fields. CLI: `python -m renmark.lint [--plugin-dir DIR]`.
- **`renmark/release.py`** (NEW, 20 tests) — version-file drift detection pulled forward from the v0.4.0 release skill. `VERSION_FILES` catalogs the 7 locations that carry the canonical version (VERSION, pyproject.toml, `renmark/__init__.py`, plugin.json, marketplace.json metadata + plugins[0], README.md header). `python -m renmark.release check` exits 1 on any disagreement. Bump/tag/zip operations stay deferred to v0.4.0 — this module is read-only at v0.3.1.
- **`renmark/shadow.py`** (NEW, 22 tests) — record-and-replay regression framework. Per-subsystem `replay(case_dict) → output_dict` functions registered via `@shadow.register("name")`. `run` replays every case and diffs against the committed baseline; `accept --subsystem X -m "msg"` re-records baselines and prepends a `CHANGES.md` entry. Initial subsystems: `dispatch`, `lifecycle`, `summary` (9 baselined cases total, including adversarial leakage scenarios).

**New tooling:**

- **`tools/precommit.sh`** — 30-second pre-commit guard: pytest, drift check, plugin lint. Three-step output, fails loud on any issue. Total budget for the renmark repo today: ~3s warm.
- **`install.sh --dev`** — opt-in flag that symlinks `tools/precommit.sh` to `.git/hooks/pre-commit`. Existing hooks are moved aside with a timestamped `.bak.` suffix, never overwritten. `--uninstall` removes the dev hook alongside the plugin.

**Integration smoke suite:**

- **`tests/integration/`** (NEW, 27 tests, gated behind `RENMARK_SMOKE=1`) — five end-to-end tests against a synthetic fixture project: full-lifecycle round-trip with schema validation at every stage, cold-start recovery via subprocess (simulates `/clear`), dispatch isolation E2E with realistic adversarial responses (transcript / generated_code / diff / reasoning / conversation / raw_output / trace leakage all blocked), codex-fallback behavior when codex CLI is absent, plugin install.sh round-trip in a fake `$HOME`. `conftest.py` auto-skips integration tests unless `RENMARK_SMOKE=1` so unit-test runs stay at ~2.5s.
- Fixtures: `repo_root`, `fixture_project` (initialized git repo with baseline `.renmark/` tree), `fixture_plan` (writes a one-task plan into the fixture).

**Shadow framework specifics:**

- Baseline files live at `tests/shadow/baselines/<subsystem>/case-*.json` (committed, ~few KB total). Cases live at `tests/shadow/cases/<subsystem>/case-*.json`.
- Replay functions are deterministic — `lifecycle.last_updated` (timestamp) and `summary.created_at` are stripped or fixed to keep baselines stable.
- `accept` requires a non-empty `-m MESSAGE` explaining the change. Prepends to `tests/shadow/CHANGES.md` below the header so the most recent change is on top.
- Shadow framework's own correctness tested by `tests/test_shadow.py` using `monkeypatch` to redirect `_shadow_root` at a tmpdir — 22 unit tests verify drift detection, missing-baseline handling, accept idempotency, deterministic replay, CLI flag handling.

**Test counts:**

- Unit tests: **283 passed, 28 skipped** in 2.56s (smoke gated off)
- Full suite: **311 passed** in 18.13s (`RENMARK_SMOKE=1`)
- Net new tests in v0.3.1: **+113** (schemas 24 + lint 25 + release 20 + shadow 22 + integration 22 = exactly the additions; 261 → 283 unit, +28 integration = +50 not counting the bumps from shadow framework's own tests)

**Risk-reduction posture:**

- Three independent regression nets now exist. A bug in one is caught by another: schema drift catches structural breakage, drift check catches version desync, lint catches plugin-contract rot, smoke catches integration breakage, shadow catches behavioral drift in load-bearing modules.
- Pre-commit hook is opt-in by design — `bash install.sh --dev` activates it. Default install path stays as fast as v0.3.0.
- Future v0.4.0 `/renmark:release` will invoke shadow + smoke + drift as its preflight checks before tagging.

**Files touched:**

- New: `renmark/schemas.py`, `renmark/lint.py`, `renmark/release.py`, `renmark/shadow.py`, `tools/precommit.sh`, `tests/test_schemas.py`, `tests/test_lint.py`, `tests/test_release_drift.py`, `tests/test_shadow.py`, `tests/integration/__init__.py`, `tests/integration/conftest.py`, `tests/integration/test_smoke_full_lifecycle.py`, `tests/integration/test_cold_start_recovery.py`, `tests/integration/test_dispatch_isolation_e2e.py`, `tests/integration/test_codex_fallback.py`, `tests/integration/test_plugin_install.py`, `tests/shadow/cases/{dispatch,lifecycle,summary}/case-*.json` (9 files), `tests/shadow/baselines/{dispatch,lifecycle,summary}/case-*.json` (9 files), `tests/shadow/CHANGES.md`.
- Modified: `install.sh` (added `--dev` flag), `VERSION`, `pyproject.toml`, `renmark/__init__.py`, `plugin/.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `README.md` (version bump only).

---

## v0.3.0 — 2026-05-19 (framework MVP — context death is survivable)

**Minor release — the foundation that makes renmark a development framework, not just a plugin.**

The core innovation this release: **AI workflows that survive context death.** Cold start from any `/clear` or `/compact` is one file read. Heavy work runs in isolated subagent contexts. The orchestrator is now structurally incapable of merging generated code into its conversation — the parser refuses it.

**Load-bearing new infrastructure** (the MVP five):

- **`renmark/summary.py`** (NEW, 323 LOC, 19 tests) — `write_artifact`, `emit_pointer`, `read_metadata`, `is_stale`, `verifier_tail`, `hash_artifact`, `git_head_sha`. Enforces G3 (5-line summary cap, ~300 tokens per line), G6 (provenance + freshness metadata on every artifact), G9 (`completion_state` / `confidence` / `validation_status` / `retry_count` / `parser_success` / `schema_compliance` transparency fields). Every auditor skill funnels through this module.
- **`renmark/lifecycle.py`** (NEW, 251 LOC, 18 tests) — workflow state for the seven-stage lifecycle. `read_lifecycle`, `write_lifecycle`, `clear_lifecycle`, `next_recommended`, `domain_of`, `is_cross_domain_transition`. Strict 1KB byte budget; runtime cruft is rejected with `LifecycleBloatError` to keep lifecycle.json separate from pipeline.json. G12 codified.
- **`renmark/state.py`** (extended +200 LOC, 15 new tests) — pipeline.json (`read_pipeline_state`, `write_pipeline_state`, `clear_pipeline_state`, `pipeline_is_resumable`), `.renmark/state/wave-summaries/wave-N.json` aggregation (`write_wave_summary`, `read_wave_summary`, `list_wave_summaries`), and `last-skill.json` for cross-domain detection (`record_skill_invocation`, `last_skill_invocation`, `context_budget_check`).
- **`renmark/dispatch.py`** (extended +190 LOC, 19 new tests) — G11 task isolation contract. `SubagentInput` (the ONLY fields a subagent receives) and `SubagentOutput` (the ONLY fields it emits) are frozen dataclasses. `parse_subagent_response` raises `IsolationViolation` on any extra field (transcript, diff, generated_code, reasoning). `dispatch_task_isolated` is the injection point — wraps subagent runners under strict I/O bounds.
- **`renmark/cli.py`** (+110 LOC, 6 new tests) — `--task SPEC --output ARTIFACT` ad-hoc Codex mode. Emits SubagentOutput-shaped JSON to stdout; the generated body lives in the artifact file, never the conversation. Falls back cleanly when codex CLI is missing.
- **`plugin/skills/resume/SKILL.md`** (NEW, 112 lines) — `/renmark:resume`. Zero LLM calls. Reads `lifecycle.json`, prints stage + next recommended command + any pending human approval gate. The cold-start recovery surface.

**Skill behavior changes:**

- All 13 existing skills gained a **Step 0 — Context check** preflight that calls `state.context_budget_check` (for cross-domain `/clear` recommendations) and `state.record_skill_invocation` (for next-skill detection). Skills with stage semantics (start, brainstorm, plan, check-plan, finish) now also write `lifecycle.json` on completion.
- `/renmark:orchestrate` rewritten to honor G11 task isolation: builds dependency context only from prior wave's `dependency_notes` (never the full output), dispatches each task in isolation via `dispatch_task_isolated`, aggregates `SubagentOutput` dicts into `.renmark/state/wave-summaries/wave-N.json`, refuses to merge subagent responses that contain forbidden fields. Pipeline state machine tracked at wave boundaries; `lifecycle.write_lifecycle(stage='created')` on completion.
- `/renmark:check-plan` gained 5 new hygiene + isolation BLOCK/WARN rules: heavy-read check (G5), transcript-leak phrase denylist (G11), dependency-graph hygiene (G11), verifier output bound check (G3), spec length WARN.
- `/renmark:verify` strengthened to goal-backward mode: reads plan goal via `parser.parse_plan`, cross-references open bugs from `.renmark/memory/bugs.md` for regression coverage (G8 compounding), runs commands via `summary.verifier_tail` (bounded output), emits a `.verification.md` artifact via `summary.write_artifact`, appends to `learnings.md` on every run and `bugs.md` on failures. Refuses if pipeline state is dirty.

**New rule blocks in `plugin/templates/CLAUDE.md.template`:**

- `context-budget-rule` — `/compact` at 60%, `/clear` on cross-domain transitions. Domain taxonomy: debug, build, audit, meta.
- `lifecycle-rule` (G12) — every stage transition writes lifecycle.json; cold start is one file read; strict separation from pipeline.json; human approval gates carried in `human_review_required` / `human_review_completed` / `human_review_for` fields.

`plugin/templates/AGENTS.md.template` gained two one-liner mirrors. `plugin/skills/setup/SKILL.md` merge table extended from 15 to 17 blocks.

**`renmark/__init__.py` version drift fixed.** Was stuck at `0.2.0` since the package was forked from ai-inference; now in sync at `0.3.0`.

**Tests:** 192 → 192 passing. 77 new tests added across summary, lifecycle, pipeline state, isolation, and CLI task mode. Zero regressions.

**Files changed:**
- `renmark/summary.py` — NEW
- `renmark/lifecycle.py` — NEW
- `renmark/state.py` — extended (pipeline + wave-summaries + skill invocations)
- `renmark/dispatch.py` — extended (SubagentInput/Output, IsolationViolation, dispatch_task_isolated, parse_subagent_response, build_subagent_input)
- `renmark/cli.py` — `--task` / `--output` ad-hoc Codex mode
- `renmark/__init__.py` — version sync 0.2.0 → 0.3.0
- `plugin/skills/resume/SKILL.md` — NEW
- `plugin/skills/orchestrate/SKILL.md` — full rewrite
- `plugin/skills/verify/SKILL.md` — full rewrite
- `plugin/skills/check-plan/SKILL.md` — hygiene + isolation BLOCKs added
- `plugin/skills/{start,brainstorm,plan,finish,feature,debug,codereview,setup}/SKILL.md` — Step 0 + lifecycle hooks added
- `plugin/templates/CLAUDE.md.template` — `context-budget-rule` + `lifecycle-rule` blocks
- `plugin/templates/AGENTS.md.template` — 2 one-liner mirrors
- `plugin/skills/setup/SKILL.md` — merge table extended to 17 blocks
- `tests/test_summary.py`, `test_lifecycle.py`, `test_state_pipeline.py`, `test_dispatch_isolation.py`, `test_cli_task_mode.py` — all NEW
- `VERSION`, `pyproject.toml`, `plugin/.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `README.md` — version sync

**Do not change:**
- `SubagentOutput` and `SubagentInput` are the **boundary contract**. Adding fields requires updating `SUBAGENT_OUTPUT_FIELDS` (in `dispatch.py`) AND updating every Agent prompt template (in `prompts.py`) AND extending the test `test_subagent_output_fields_match_dataclass`. Drift here is silent corruption.
- `IsolationViolation` is intentionally fail-loud. Do not swallow it with try/except in dispatch paths — that defeats G11. If a real subagent legitimately needs to send a new field, add it to the schema with explicit tests.
- `lifecycle.json` byte budget (1KB) is a forcing function, not a suggestion. If `LifecycleBloatError` fires, the answer is to move fields to `pipeline.json`, not raise the limit.
- The 5-line summary cap in `write_artifact` and `SubagentOutput.summary_lines` is the G3 enforcement. Raising it requires editing `MAX_SUMMARY_LINES` in `summary.py` AND `summary_lines` validation in `dispatch.py.SubagentOutput.__post_init__` AND updating the rule prose in CLAUDE.md.template. All three or none.
- `renmark/__init__.py.__version__` MUST stay synced with `VERSION` and `pyproject.toml`. v0.4.0's `/renmark:release` skill will automate this — until then, bump by hand and run `grep -R 0\\.X\\.Y plugin/templates/ pyproject.toml plugin/.claude-plugin/ .claude-plugin/ README.md renmark/__init__.py VERSION` to confirm.

**Next release: v0.3.1 — `/renmark:document` (post-feature doc sync).** See `/home/renmark/.claude/plans/cheerful-drifting-seal.md` for the full v0.3.x → v0.4.0 rollout.

---

## v0.2.5 — 2026-05-18 (governance charter codification)

**Patch release — documentation only, no code or skill behavior changes.**

The orchestrator (Sonnet 200k typical) is now treated as a degrading systems resource. Nine new governance rules codify how every renmark skill must behave to protect orchestration integrity against context rot. The rules ship as `BEGIN/END` blocks in CLAUDE.md.template so `/renmark:setup` merges them into existing projects without overwriting.

**New CLAUDE.md rule blocks** (9, all in `plugin/templates/CLAUDE.md.template`):
- `orchestrator-role-rule` — coordinator, not memory container
- `canonical-state-rule` — truth lives in `.renmark/` and CHANGELOG, not conversation
- `summary-boundary-rule` — orchestrator-visible output ≤ 5 lines or ≤ 300 tokens
- `context-contamination-rule` — cross-domain skill changes recommend `/clear` (domains: debug, build, audit, meta)
- `artifact-governance-rule` — every artifact carries provenance + freshness metadata
- `compact-semantics-rule` — `/compact` preserves goals, blockers, pipeline state, artifact refs, verification status
- `failure-transparency-rule` — outputs carry `completion_state` / `confidence` / `validation_status` / `retry_count` / `parser_success` / `schema_compliance`
- `workflow-recovery-rule` — multi-step workflows resumable from `.renmark/state/pipeline.json`, not conversational reconstruction
- `task-isolation-rule` — `/renmark:orchestrate` runs each task in an isolated subagent context; subagent transcripts and generated code never re-enter the orchestrator

**AGENTS.md.template:** 9 corresponding one-liner mirrors, each pointing at the longer block in CLAUDE.md.

**`/renmark:setup`:** merge table extended from 6 to 15 blocks. Existing projects get the new rules merged on next setup run without overwriting custom content.

**New file `plugin/skills/CONTRIBUTING.md`:** governance acceptance bar for new skills — 9-rule compliance checklist (G2–G11). A new skill that cannot tick all 9 boxes does not merge. Includes the canonical SKILL.md structure with the `Governance compliance` table every new skill must include.

**Files changed:**
- `plugin/templates/CLAUDE.md.template` — 9 new rule blocks inserted between `verify-before-done-rule` and the tooling table
- `plugin/templates/AGENTS.md.template` — 9 one-liner mirrors added between `Verification before completion` and `Conventions`
- `plugin/skills/setup/SKILL.md` — merge table updated with 9 new entries
- `plugin/skills/CONTRIBUTING.md` — new file
- `VERSION` — bumped `0.2.4` → `0.2.5`

**Do not change:**
- The 9 rule blocks ship as one cohesive set; do not split them into separate releases. Each rule reinforces the others (e.g., G6 artifact metadata depends on G3 summary boundaries; G10 recovery depends on G2 canonical state).
- AGENTS.md mirrors stay one-liners that reference the long-form block in CLAUDE.md — do not duplicate the full rule text in AGENTS.md.
- Block names use the `<topic>-rule` suffix convention. Do not rename existing blocks; downstream merge logic depends on the names.
- The `task-isolation-rule` block describes a contract that Phase 1 code (next release v0.3.0) will enforce. Rules ship first so plans drafted against v0.2.5 already obey them — the code that mechanically blocks violations comes in v0.3.0.

---

## v0.2.4 — 2026-05-15 (vibe coder entry point)

**New skill:**
- `/renmark:start` — plain-English entry point for vibe coders. Asks what you want to build, infers stack and scope from the description, asks at most 2 follow-up questions (reach and lifespan), presents a confirmation summary with a brief best-practices mention, then routes to `/renmark:plan` (simple requests) or `/renmark:brainstorm` (complex/multi-feature). Best practices (error handling, README, .env, .gitignore, smoke test) are woven into task specs automatically — no separate tasks, no jargon exposed to the user.

**plugin.json:** version bumped to 0.2.4; description updated to lead with vibe coder framing; added `vibe-coder` keyword.

**install.sh:** `/renmark:start` added as first skill in success message; start message updated to show `start` as the entry point for new users.

**CLAUDE.md template:** `/renmark:start` added as first row in tooling table.

**Do not change:**
- The 2-question cap in `start` — more questions break the adaptive/frictionless contract
- Stack inference happens silently — never prompt the user to choose a framework

---

## v0.2.3 — 2026-05-15 (setup skill + install.sh rewrite)

**New skill:**
- `/renmark:setup` — prepares any existing project for renmark workflow. Detects tech stack from project files, creates or merges missing CLAUDE.md rule blocks (using BEGIN/END markers), syncs AGENTS.md, creates CHANGELOG.md if absent, scaffolds `.renmark/` directory tree with seed memory files, adds `.gitignore` entries, offers optional `git init`. Safe to re-run — merge-only, never overwrites existing content. Prompts to continue to brainstorm or plan on completion.

**install.sh rewrite:**
- Added `--uninstall` flag (`bash install.sh --uninstall`)
- Removed stale `/orchestrator` cleanup step (ai-inference project artifact)
- Added optional `pip3 install -q -e` step for Python editable package
- Success message now lists all 12 skills with descriptions
- VERSION read dynamically from `./VERSION` file

**VERSION:** bumped `0.1.5` → `0.2.3`

**Do not change:**
- `install.sh` symlinks are idempotent — stale symlinks are removed and recreated; non-symlink collisions abort with an error rather than overwriting

---

## v0.2.2 — 2026-05-14 (skill quality gates + CLAUDE.md discipline rules)

Skills-only release — no Python module changes.

**New skills:**
- `/renmark:check-plan` — lightweight plan validator (task count ≤ 15, verifier presence, parallel group safety). Invoked automatically by orchestrate pre-flight. Returns PASS / WARN / BLOCK.
- `/renmark:verify` — goal-backward smoke test after orchestrate. Reads plan context paragraph, runs one functional command per stated behavior, reports N/M requirements verified. Never reads source files.
- `/renmark:finish` — branch close wrapper. Re-runs verifiers, shows git log summary, offers [p] PR / [m] merge / [n] nothing.

**Skill updates:**
- `orchestrate`: pre-flight now invokes `/renmark:check-plan`; step 7 re-runs all verifiers before reporting done; hand-off menu adds `[v] Verify` and `[f] Finish` options.
- `debug`: Iron Law cross-references CLAUDE.md § Root cause before any fix; step 6 has explicit gate requiring root cause sentence before any code change.

**Template updates (CLAUDE.md.template + AGENTS.md.template):**
- Added `## Context hygiene` — never read generated file contents into conversation
- Added `## Executor dispatch rules` — codex → renmark-execute only, never Agent calls
- Added `## Root cause before any fix` — no code changes without written root cause
- Added `## Verification before completion` — re-run verifiers fresh before claiming done
- Added 3 new commands to tooling table (check-plan, verify, finish)
- AGENTS.md: added absolute paths, single-file scope, root cause, verify-before-done rules

**plugin.json:** version bumped to 0.2.2; description updated (NIM removed, new skills listed); keywords updated.

**Do not change:**
- CLAUDE.md.template rule blocks use BEGIN/END comment markers for tooling that parses them — preserve the `<!-- BEGIN:x -->` / `<!-- END:x -->` wrapper format

---

## v0.2.1 — 2026-05-14 (dispatch routing fix + scope contract + subscription language)

Skills-only release — no Python module changes.

**Fixed:**
- `orchestrate` overview: corrected dispatch table — `codex` → `renmark-execute` (Codex subscription quota), `haiku/sonnet/opus` → Agent calls (Claude Code subscription quota). Added RED FLAG to Step 3 explicitly forbidding codex tasks from being dispatched as Agent calls (was the root cause of all agents running on Sonnet 4.6 in test).
- `orchestrate` overview: replaced "OpenAI credits / Anthropic credits" language with "Codex account / Claude Code account" — both are subscription-based, not API billing.

**Added:**
- `/renmark:plan` Step 0 Scope Contract: 3-question discovery phase (tech stack with inference rules, deployment target, MVP boundary) before any task decomposition. Writes locked decisions to `CHANGELOG.md` and `.renmark/memory/stack.md`. Explicit confirmation gate — no silence-as-confirmation.
- `debug` Step 6: root-cause gate added — must write root cause sentence before drafting any fix.

**Do not change:**
- Scope Contract confirmation gate language: "Do not rely on silence, lack of objection, or ambiguous replies as confirmation" — this wording was specifically required

---

## v0.2.0 — 2026-05-14 (NIM executor removal — multi-executor architecture)

**Breaking change:** NIM executor removed. All NIM references replaced with multi-executor architecture (Haiku / Codex / Sonnet / Opus).

**Python changes:**
- `cli.py`: removed `NIMClient.from_env()` pre-flight block (was blocking all non-dry-run execution without `NVIDIA_NIM_API_KEY`); renamed `NIM_*` env vars → `RENMARK_*`; git tags `nim-run-*` → `renmark-run-*`; commit prefix `[nim]` → `[renmark]`; cleared stale Mistral model defaults to `""`
- `state.py`: `_COMMIT_TASK_RE` updated to match `renmark|codex|nim|manual` prefixes (nim kept for backward-compat with existing git history)
- `roadmap.py`: git log pattern updated; `COST_PER_KT` adds `haiku: 0.0001`
- `debug.py`: `suggest_inspector()` returns `"haiku"` for cheap intents (was `"nim"`)
- `parser.py`: default `executor` changed from `"nim"` to `"codex"`
- `__init__.py`: version bumped to `0.2.0`; description updated to list Haiku/Codex/Sonnet/Opus
- `apply.py`: module docstring updated to generic "agent output"

**Skill updates:**
- `orchestrate`: NIM pre-flight removed; refactor safety check + changelog check added; haiku added to Agent dispatch section; NIM error codes removed
- `plan`: executor list updated (NIM → Haiku); CHANGELOG.md integration added; routing table updated

**Tests:**
- `test_dispatch.py`: default executor `"nim"` → `"codex"`
- `test_debug.py`: `inspector="nim"` → `inspector="haiku"`; `suggest_inspector` assertions updated
- `test_state.py`: 3 new commit variants (`[renmark]`, `[codex]`, bare `renmark`) added; 113 tests pass

**Do not change:**
- `_COMMIT_TASK_RE` still matches `nim` — required for backward-compat with git history from pre-v0.2.0 runs
- `RENMARK_PREFER_SMALL_MODEL` and `RENMARK_BIG_MODEL` env var defaults are intentionally `""` — let users set them explicitly

---

## v0.1.5 — 2026-05-12 (Phase 3: /renmark:debug helper module)

Adds `renmark/debug.py` — file-format helpers + executor-suggestion routing for the debug loop. The skill now has a real backend instead of being a pure playbook.

- `debug.new_session(repo, symptom)` — creates `.renmark/debug/<id>/session.md` with H2 sections (Symptom / Hypotheses / Investigation log / Root cause / Fix / Verification)
- `debug.add_hypothesis(session, idx, title, likely)` — ranked list under Hypotheses
- `debug.log_investigation(session, hypothesis, inspector, finding, rules_out=False)` — append step with which model inspected it
- `debug.set_root_cause(session, text)` — replace the placeholder
- `debug.close_session(session, repo, ...)` — finalize and write a structured entry to `.renmark/memory/bugs.md` (with auto-cross-post to `learnings.md`)
- `debug.latest_session(repo)` — resume the most recent debug session (survives `/clear`)
- `debug.suggest_inspector(intent)` — returns the cheapest executor for a step:
  - `nim` for grep / file-read / line-count / regex
  - `codex` for multi-file-trace / find-usages / context-gather / api-check
  - `opus` for reasoning / race-condition / architecture
- `/renmark:debug` SKILL.md updated to point at these helpers

7 new tests. 111 passing (104 before + 7 debug tests).

**Still pending (lower priority):**
- `dispatch.py` calling `resolve_provider` to route non-nim/codex executors through the new Phase 4 providers
- `/renmark:codereview` writing review findings into `bugs.md`/`decisions.md` automatically

## v0.1.4 — 2026-05-12 (Phase 4: native multi-provider clients)

Adds three native providers + a resolver. Zero new third-party deps.

- `renmark/providers/openai_compat.py` — generic OpenAI-compatible client. Speaks `/chat/completions` against any base URL with a bearer token. Retry on 429/503, fail on 401, parse `choices[0].message.content` + `usage.{prompt,completion}_tokens`.
- `renmark/providers/ollama.py` — delegates to `openai_compat` against `http://localhost:11434/v1` by default. Executor: `ollama_chat/<model>` (e.g. `ollama_chat/qwen2.5-coder:7b`).
- `renmark/providers/openrouter.py` — delegates to `openai_compat` against `https://openrouter.ai/api/v1`. Executor: `openrouter/<provider>/<model>`. Reads `OPENROUTER_API_KEY` from env.
- `renmark/providers/__init__.py` — new `resolve_provider(executor)` function maps any executor string to `(module_name, model_arg)`. Unknown `<prefix>/<model>` strings fall through to `openai_compat` so Together / Anyscale / Groq / etc. work with the right env vars.
- 13 new tests for resolver + each provider (all mocked HTTP).

Executor strings that now work:

| Executor | Routes to |
|---|---|
| `nim` | NIM client (existing) |
| `codex` | Codex CLI (existing) |
| `opus`, `sonnet` | Agent tool — skill must dispatch |
| `ollama_chat/<model>` | Local Ollama (default `:11434`) |
| `openrouter/<provider>/<model>` | OpenRouter gateway |
| `openai_compat/<model>` | Any OpenAI-compatible API (needs `OPENAI_COMPAT_BASE_URL` + `OPENAI_COMPAT_API_KEY`) |
| `<unknown>/<model>` | Falls through to openai_compat |

104 tests pass (91 before + 13 provider tests).

**Still pending:**
- Wiring `resolve_provider` into `dispatch.py`'s actual call path (right now `dispatch.dispatch_wave` only knows nim/codex/opus/sonnet)
- `/renmark:debug` per-step routing
- `/renmark:debug` and `/renmark:codereview` writing to `bugs.md` automatically

## v0.1.3 — 2026-05-12 (cost preview + --no-commit + routing-memory + perm snippet)

Phase 1 polish landed:

- **Cost preview in `--dry-run`**: per-task line shows executor + complexity + estimated tokens + estimated $; totals at the bottom. Uses `est_tokens` / `est_cost_usd` from the plan if present, falls back to complexity heuristic. NIM = free, codex ≈ $0.05/kT, sonnet ≈ $0.003/kT, opus = in-context.
- **`renmark-execute --no-commit`** runtime now wired through `_NO_COMMIT_MODE` module flag. `_git_commit` returns `"(no-commit)"` sentinel; the skill batches commits per wave.
- **Routing memory auto-updates**: after each task completes (passed/failed), `_memory_log_outcome` appends to `routing.md` with the task signature (`target=*.py, complexity=medium, mode=A`), executor, and outcome. Failed tasks also append to `learnings.md` with the failure note. Future `/renmark:plan` runs read these to inform auto-routing.
- **Permission-allowlist snippet** added to README — paste-in `.claude/settings.local.json` block that eliminates Bash prompts for `renmark-execute *` calls.

91 tests pass (no regressions from these changes — pure additions).

**Still pending:**
- `providers/ollama.py`, `openrouter.py`, `openai_compat.py` — Phase 4
- `/renmark:debug` per-step routing — Phase 3

## v0.1.2 — 2026-05-12 (cli uses dispatch.py — parallel waves live)

**Headline:** `renmark-execute` now uses `dispatch.py` for wave-based parallel execution. Tasks sharing a `parallel_group` run concurrently on separate threads; tasks with `executor: opus | sonnet` are marked `needs_agent` and surfaced so the `/renmark:orchestrate` skill can dispatch them via the Agent tool.

Changes:
- `cli.py`:
  - Module-level `_GIT_LOCK = threading.Lock()` serializes `_git_tag`, `_git_commit`, `_git_restore_target` across parallel task threads (git index isn't multi-thread-safe).
  - `execute_plan` refactored to use `dispatch.group_tasks_by_wave` + `validate_wave` + `dispatch_wave` instead of a flat per-task loop. Existing `_execute_task` is now invoked through a `_runner` adapter that returns `dispatch.TaskResult`.
  - End-of-run summary now reports `needs-agent` count and wave count.
  - If a wave validation fails (overlapping targets, context-into-target conflicts), the plan is rejected with exit 2 before any LLM call.
- `dispatch.py` tests (11) already covered the parallel semantics; cli.py integration verified by the existing 91-test suite — all still pass.

**LiteLLM dropped from roadmap.** Per user decision: native providers cover all realistic use cases. Future providers go in as one-file `providers/*.py` modules following the `openai_compat.py` pattern.
- PLAN.md "Phase 5" struck through with rationale
- CHANGELOG pending-list updated
- "What to steal from" table notes LiteLLM was considered and rejected

**Still pending (v0.1.3+):**
- `--no-commit` runtime behavior (argparse flag accepted, not yet effective in the commit path — would let skills batch-commit per wave manually)
- Cost preview in `--dry-run` (per-task estimate before any LLM call)
- Routing memory auto-updates from run outcomes
- `/renmark:debug` per-step routing actually wired
- Additional native providers (Ollama, OpenRouter, OpenAI-compat) — Phase 4

91 tests pass.

## v0.1.1 — 2026-05-12 (logs dir + codereview simplified to codex-only)

**Added: `.renmark/logs/`** for per-invocation troubleshooting logs (gitignored). One log file per command run named `<command>-<run_id>.log`.

- `renmark/state.py`:
  - New constants: `LOGS_SUBDIR = "logs"`
  - `logs_dir(repo)`, `open_log(repo, command, run_id=None)`, `append_log(path, *messages)`, `recent_logs(repo, n=10)`
  - 6 tests
- `renmark-execute --logs` — lists the n most-recent log files with size + mtime
- `renmark-execute --logs-n <N>` — adjust the count (default 10)
- `bootstrap.py` updated: `.gitignore` template now includes `.renmark/logs/`
- `plugin/templates/memory/INDEX.md.template` updated to reference all `.renmark/` subdirs (specs, plans, reviews, state, debug, logs)

**Changed: `/renmark:codereview` is now single-pass (codex-only)**, no Sonnet/Opus passes.

The earlier multi-pass design put code into the conversation, which defeats the context-hygiene goal renmark is built for. Codex stays in its own sandbox; Opus only reads the severity summary. Output format and storage path unchanged (`.renmark/reviews/YYYY-MM-DD-<sha>.review.md`). Recommended cadence: end-of-plan, not per-task.

Tests: 91 passing (up from 85).

**Still pending (v0.1.2+):**

- CLI `execute_plan` integration with `dispatch.group_tasks_by_wave` + `dispatch_wave` — parallel waves not yet wired into the live loop
- `--no-commit` runtime behavior (flag accepted, not yet effective)
- Cost preview in `--dry-run`
- Routing memory auto-updates from run outcomes
- `/renmark:debug` per-step routing actually wired
- Additional native providers (Ollama, OpenRouter, OpenAI-compat) — Phase 4
- ~~LiteLLM plug-in slot — Phase 5~~ (dropped — native providers cover the realistic use cases)

## v0.1.0 — 2026-05-12 (Phase 1 module landing + roadmap reporter)

**First minor release.** The Phase 1 modules are all in place with tests; the CLI's `execute_plan` loop still uses the v0.0.x single-task code path. Integrating that loop with the new dispatcher is the v0.1.1 work.

**New modules (with tests):**

- `renmark/dispatch.py` — wave-based parallel dispatcher. `group_tasks_by_wave`, `validate_wave`, `dispatch_wave` (concurrent for nim/codex/litellm, `needs_agent` marker for opus/sonnet). 11 tests including a timing assertion that two slow tasks in the same wave finish in under the serial total.
- `renmark/providers/claude_agent.py` — composer for the Agent-tool prompt when a task is `executor: opus` or `executor: sonnet`. Skill issues the Agent call; this module owns the prompt format and constraints.
- `renmark/bootstrap.py` — empty-folder helper. `is_empty_project(repo)`, `bootstrap(repo, project_name=...)` creates CLAUDE.md / AGENTS.md / `.renmark/` from plugin templates, runs `git init`. Idempotent. 6 tests.
- `renmark/roadmap.py` — synthesizer that builds a per-task `task | llm | status | tokens | $ | commit` table from `features.md` + `usage.jsonl` + git log. `write_roadmap_md(repo)` snapshots to `.renmark/memory/roadmap.md`. 7 tests.

**Parser extensions (v0.0.3+, fully tested):**

- New optional task fields: `complexity` (simple|medium|hard), `parallel_group` (int), `est_tokens` (int), `est_cost_usd` (float).
- `executor` now accepts `opus`, `sonnet`, or any `<provider>/<model>` string (e.g., `ollama_chat/qwen2.5-coder:7b`).
- 9 new tests covering defaults, type validation, and rejection of invalid values.

**New skills:**

- `/renmark:roadmap` — prints the status table; also writes the snapshot to `.renmark/memory/roadmap.md` so it's committed.
- `/renmark:help` (added in v0.0.3) — lists all skills with one-sentence descriptions.

**Wizard-style hand-offs:**

- `/renmark:brainstorm` now ends with an explicit `Y/n/wait` prompt to continue to `/renmark:plan`.
- `/renmark:plan` shows a summary (task count + cost preview) and prompts `[r]eview / [d]ispatch / [e]dit / [n]o` — Dispatch only triggers `/renmark:orchestrate` after explicit user approval.
- `/renmark:orchestrate` offers `[c]ode-review / [s]moke / [n]one` after a clean run.

**CLI:**

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
