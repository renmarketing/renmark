<!--
artifact_type: plan
schema_version: 1
created_at: 2026-06-23
source_sha: 4e259ad
related_plan: 2026-06-23-auto-routing-default
generator: opus
feature: auto-routing-default
branch: feature/auto-routing-default
-->

# Plan — auto-routing default (renmark as the default for build/dev work)

**Context:** Make renmark the default path for plain-English build/dev requests so the user doesn't have to remember `/renmark:*` commands, without removing manual control. Three levers: (a) broaden pipeline trigger vocabulary so descriptions match natural dev verbs; (b) a `routing-preference-rule` block shipped via the CLAUDE.md/AGENTS.md templates + back-filled by `init`; (c) a `/renmark:doctor`-managed global `~/.claude/CLAUDE.md` routing rule (detect → create-if-missing / append-if-present / skip-if-there), human-gated, idempotent, backed up, never clobbering. Surfaced from `init` (one-time offer) and `start` (light nudge). Honest framing: auto-routing is a model-followed instruction (not a hard interlock), explicit `/renmark:` always wins, takes effect next session, renmark never silently writes outside the project (the global write is always user-approved).

Reuse check: N/A — this extends renmark's own skills/runtime; no existing equivalent. `renmark/global_routing.py` is a new module that reuses `lint.iter_rule_blocks` + the `merge_rule_blocks` append pattern.

---

### Task 1: broaden pipeline trigger descriptions
- **mode:** B
- **target:** plugin/skills/start/SKILL.md
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 1
- **est_tokens:** 800
- **est_cost_usd:** 0.03
- **verifier:** python -m renmark.audit | grep -q "description-drift=0"
- **serves:** REQ-1
- **spec:**
  Edit ONLY the `description:` frontmatter of these SIX files so they match plain-English dev verbs (develop, implement, add, make, create, build out, code up, fix, change) in ADDITION to the current phrasings — do NOT remove existing triggers, do NOT touch bodies: `plugin/skills/start/SKILL.md`, `plugin/skills/feature/SKILL.md`, `plugin/skills/debug/SKILL.md`, and their shims `plugin/commands/start.md`, `plugin/commands/feature.md`, `plugin/commands/debug.md`. Each SKILL.md description and its shim description must stay near-identical (high token overlap) so `audit description_drift` stays 0. Keep the pipeline-name framing already present ("New Build pipeline", "Feature pipeline", "Debug pipeline"). This is the single multi-file mechanical-consistency task — all six descriptions edited together to guarantee pairwise drift stays clean. Run `python -m renmark.audit` after; description-drift MUST be 0.

### Task 2: routing-preference-rule in templates
- **mode:** B
- **target:** plugin/templates/CLAUDE.md.template
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 1
- **est_tokens:** 650
- **est_cost_usd:** 0.03
- **verifier:** python -c "from renmark import lint; from pathlib import Path; t=Path('plugin/templates/CLAUDE.md.template'); assert lint.lint_template_rule_blocks(t)==[], lint.lint_template_rule_blocks(t); assert any(n=='routing-preference-rule' for n,_ in lint.iter_rule_blocks(t.read_text())); a=Path('plugin/templates/AGENTS.md.template').read_text(); assert 'renmark pipelines' in a"
- **serves:** new
- **spec:**
  Add a new `<!-- BEGIN:routing-preference-rule -->` … `<!-- END:routing-preference-rule -->` marker block to `plugin/templates/CLAUDE.md.template` (place it near the top behavioral rules, e.g. right after `response-style-rule`), with a `## ` heading like `## Default to renmark for build/dev work`. Body: route build / feature / debug / ship work through the renmark pipelines (`/renmark:start`, `/renmark:feature`, `/renmark:debug`, `/renmark:roadmap`, `/renmark:finish`); use other skill frameworks (superpowers, etc.) only when named explicitly. State it is a DEFAULT not a lock — explicit `/renmark:` always wins; it still pauses at the Pause-Policy gates. Add the prose-format mirror (`**Default to renmark for build/dev work.** …`) to `plugin/templates/AGENTS.md.template` under its Core rules. Must pass `lint.lint_template_rule_blocks` (well-formed markers + heading) and be back-fillable by `init.merge_rule_blocks` (no code change needed there — it's generic over blocks). This task edits ONLY the two template files.

### Task 3: mirror routing-preference-rule into repo CLAUDE.md + AGENTS.md
- **mode:** B
- **target:** CLAUDE.md
- **complexity:** simple
- **executor:** sonnet
- **parallel_group:** 1
- **est_tokens:** 400
- **est_cost_usd:** 0.03
- **verifier:** grep -q "BEGIN:routing-preference-rule" CLAUDE.md && grep -q "Default to renmark for build/dev work" AGENTS.md
- **serves:** new
- **spec:**
  Mirror the SAME `routing-preference-rule` block (byte-identical body to the template from Task 2) into this repo's own `CLAUDE.md` (marker block) and `AGENTS.md` (prose `**rule.**` mirror), same placement convention as the existing `response-style-rule`. This task edits ONLY `CLAUDE.md` and `AGENTS.md` at the repo root. Keep CLAUDE↔AGENTS in sync (same commit). Do not touch any skill/template files.

### Task 4: global-routing helper module
- **mode:** A
- **target:** renmark/global_routing.py
- **complexity:** hard
- **executor:** opus
- **parallel_group:** 1
- **est_tokens:** 1500
- **est_cost_usd:** 0.17
- **verifier:** python -c "import renmark.global_routing as g; assert hasattr(g,'detect_global_rule') and hasattr(g,'install_global_rule')"
- **serves:** new
- **spec:**
  New deterministic, zero-LLM module managing a `renmark-routing` rule block in the GLOBAL `~/.claude/CLAUDE.md` (the per-user, every-session file — NOT a project file). Reuse `renmark.lint.iter_rule_blocks` for marker detection. Public functions: `detect_global_rule(home: Path|None=None) -> Literal['missing','present-without-rule','present-with-rule']` and `install_global_rule(home=None) -> dict` that: if file missing → create `~/.claude/CLAUDE.md` containing a `<!-- BEGIN:renmark-routing --> … <!-- END:renmark-routing -->` block; if file exists WITHOUT the block → append the block (preserve all existing content verbatim); if block already present → no-op. ALWAYS write a `<file>.bak` backup before modifying an existing file. Idempotent (second call = no-op, returns a status). NEVER overwrite unrelated content. Accept an injectable `home` param (default `Path.home()/'.claude'`) so tests can point at a tmp dir. Include a `WINDOWS_HOME_NOTE` constant / docstring noting the Windows home is `%USERPROFILE%\.claude` (separate from WSL `~/.claude`) so a future caller can handle both. The routing-block body = the same plain-English routing rule text used in Task 2 (keep a single canonical string constant in this module; Task 5/6 reference it). Pure file IO + return dicts; raise nothing on the happy paths; mirror renmark's existing helper style (type hints, `from __future__ import annotations`). This task creates ONLY `renmark/global_routing.py`.

### Task 5: wire global-routing into /renmark:doctor
- **mode:** B
- **target:** renmark/doctor.py
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 2
- **est_tokens:** 700
- **est_cost_usd:** 0.03
- **verifier:** python -c "import renmark.doctor" && python -m renmark.doctor >/dev/null 2>&1; test $? -le 1
- **serves:** new
- **spec:**
  Wire `renmark.global_routing` (Task 4) into `renmark/doctor.py`: add a NON-FAILING informational check that calls `global_routing.detect_global_rule()` and reports one of: `[i] global auto-routing rule present` / `[ ] global auto-routing rule not set — run with --fix to add it (writes ~/.claude/CLAUDE.md, backed up)`. In `--fix` mode, call `global_routing.install_global_rule()` and report what it did (created / appended / already-present). This check must be ADVISORY only — never flip doctor's overall pass/fail (the global rule is optional, opt-in). Match doctor's existing check/▢/✓ output style and `--fix` backup-then-write convention. Do not regress existing doctor checks. Edits ONLY `renmark/doctor.py`.

### Task 6: surface from init (offer) + start (nudge) + document in doctor skill
- **mode:** B
- **target:** plugin/skills/init/SKILL.md
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 2
- **est_tokens:** 750
- **est_cost_usd:** 0.03
- **verifier:** grep -qi "auto-routing\|~/.claude/CLAUDE.md\|global routing" plugin/skills/init/SKILL.md && grep -qi "doctor\|auto-routing\|default everywhere" plugin/skills/start/SKILL.md && grep -qi "global\|routing\|~/.claude" plugin/skills/doctor/SKILL.md
- **serves:** new
- **spec:**
  Three doc edits (this task owns all three since they're the user-facing surfacing of the same feature): (1) `plugin/skills/init/SKILL.md` — add a one-time, NON-BLOCKING offer step mirroring its existing PRD-offer pattern: after the map/standards step, if `global_routing.detect_global_rule()` is `missing`/`present-without-rule`, offer once: "Want renmark to be the default for build/dev work in every project on this machine? I can add a routing rule to ~/.claude/CLAUDE.md (backed up, never overwrites your other rules)." On yes → call doctor's --fix path / `install_global_rule`. Skip silently if already present. (2) `plugin/skills/start/SKILL.md` — add a SINGLE light one-line nudge (not a prompt, no blocking) shown only when the global rule is missing: "tip: `/renmark:doctor --fix` makes renmark the default everywhere." Do NOT nag mid-build. (3) `plugin/skills/doctor/SKILL.md` — document the new advisory check + `--fix` behavior and the honest constraints (model-followed instruction, explicit `/renmark:` wins, next-session, never silent / always user-approved, per-machine: WSL `~/.claude` vs Windows `%USERPROFILE%\.claude`). Note: `start/SKILL.md` was description-edited in Task 1 (frontmatter) — this task edits its BODY; runs in a later wave so no collision.

### Task 7: tests for global-routing helper + drift guard
- **mode:** A
- **target:** tests/test_global_routing.py
- **complexity:** medium
- **executor:** codex
- **parallel_group:** 3
- **est_tokens:** 1200
- **est_cost_usd:** 0.03
- **verifier:** python -m pytest -q tests/test_global_routing.py
- **serves:** new
- **spec:**
  New pytest module for `renmark.global_routing` using a tmp `home` dir (inject via the `home` param — never touch the real `~/.claude`): (1) missing → `install_global_rule` CREATES `~/.claude/CLAUDE.md` with the `renmark-routing` block and `detect` then returns `present-with-rule`; (2) exists-without-block → `install` APPENDS the block AND preserves prior content verbatim AND writes a `.bak`; (3) already-present → `install` is a no-op (returns an already-present status, file byte-unchanged, no duplicate block); (4) no-clobber: pre-existing unrelated user content survives an install; (5) idempotency: two installs in a row leave exactly one block. Use `lint.iter_rule_blocks` to assert exactly one `renmark-routing` block. Keep tests hermetic (tmp_path), no network, no real-home writes. Depends on Task 4 (module) existing.

---

## Cost preview

| Task | executor | complexity | est_tokens (incl. ~10k overhead) | est_cost |
|---|---|---|---|---|
| 1 broaden triggers | sonnet | medium | ~10.8k | $0.03 |
| 2 templates rule | sonnet | medium | ~10.7k | $0.03 |
| 3 repo mirror | sonnet | simple | ~10.4k | $0.03 |
| 4 helper module | opus | hard | ~11.5k | $0.17 |
| 5 doctor wiring | sonnet | medium | ~10.7k | $0.03 |
| 6 init/start/doctor docs | sonnet | medium | ~10.7k | $0.03 |
| 7 tests | codex | medium | ~1.2k (no overhead) | $0.03 |

**Total: ~7 tasks, 3 waves, ~66k tokens, ~$0.35.**
Executors: sonnet×5, opus×1, codex×1. (fable: none — no escalation signal.)

**Waves (parallel groups):**
- Wave 1 (parallel — disjoint files): T1 (skill+shim descriptions), T2 (templates), T3 (repo CLAUDE/AGENTS), T4 (new helper module).
- Wave 2 (parallel — disjoint files, after T4): T5 (doctor.py), T6 (init/start/doctor SKILL bodies).
- Wave 3: T7 (tests — needs T4).
