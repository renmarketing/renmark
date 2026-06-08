---
artifact_type: research
schema_version: 1
created_at: 2026-06-08T19:25:11+00:00
source_sha: null
related_plan: null
generator: brainstorm-research
stale_after: null
dependency_refs: []
completion_state: complete
confidence: medium
validation_status: unvalidated
retry_count: 0
parser_success: true
schema_compliance: true
---

# Research — folding /renmark:setup bootstrap into /renmark:init

## Context
Designing a front-door pipeline where /renmark:init scaffolds CLAUDE.md/AGENTS.md/
CHANGELOG.md/.renmark/ when missing (currently init hard-errors and tells the user
to run /renmark:setup first), then scans, then hands off to roadmap --gaps.

---

## 1. init.py structure for the fold

**Hard-error location.** `run(repo, ...)` at init.py:1293. First thing it does
(lines 1295-1297):

    claude_md = repo / "CLAUDE.md"
    if not claude_md.exists():
        return 1, "FAIL  CLAUDE.md not found. Run /renmark:setup first ..."

Everything downstream (scan_repo, scan_standards, merge_stub_into x2,
write_full_map, write_standards_md) assumes CLAUDE.md exists. merge_stub_into
itself returns 'skipped' for a non-existent file rather than creating it
(init.py:617-618) — so init never creates CLAUDE.md/AGENTS.md today; it only
edits them if present.

**Cleanest injection point.** A scaffold-if-missing phase belongs at the very top
of run(), BEFORE the line-1295 existence check — i.e. scaffold first, then let
the existing check pass. This is the single chokepoint; both the module CLI
(main -> run) and the skill (`python -m renmark.init`) flow through it.

**THE KEY FINDING: scaffolding already exists — renmark/bootstrap.py.**
There is NO renmark/setup.py (setup is pure markdown: skills/setup/SKILL.md +
the thin commands/setup.md shim). But `renmark/bootstrap.py::bootstrap(repo, *,
project_name=None, init_git=True)` ALREADY does exactly the proposed scaffold,
non-destructively and idempotently:
  - CLAUDE.md   from plugin/templates/CLAUDE.md.template  (only if not exists)
  - AGENTS.md   from plugin/templates/AGENTS.md.template  (only if not exists)
  - .gitignore  (create, or append renmark lines if missing)
  - .renmark/memory/* via memory.ensure_memory  (idempotent, per-file skip)
  - .renmark/README.md from renmark-readme.md
  - .renmark/{specs,plans,reviews}/.gitkeep
  - optional `git init -b main` + scaffold commit
It substitutes {{PROJECT_NAME}} and {{DATE}}. Returns BootstrapResult(created,
git_initialized). It is `is_empty_project`-gated by its current caller
(brainstorm), but bootstrap() itself is safe to call on a non-empty repo — every
write is existence-guarded.

**bootstrap() does NOT create:** CHANGELOG.md, and it does NOT merge renmark rule
blocks into a pre-existing CLAUDE.md (it only creates a fresh one from template).
Those two are the gap vs. setup/SKILL.md (see #2).

**Template path resolution at runtime.** Yes, there is a helper:
`memory.template_dir()` honors $RENMARK_TEMPLATES then walks up from __file__ for
`plugin/templates/memory/`; bootstrap derives `plugin_tdir = tdir.parent`. So
init.py can locate templates the same way (import memory; or just call
bootstrap()). Templates are readable from the install — install.sh symlinks the
plugin dir; bootstrap raises RuntimeError if the symlink is missing.

**Recommendation for a `scaffold_missing(repo)`:** do NOT re-implement template
copying in init.py. Either (a) `from . import bootstrap` and call
`bootstrap.bootstrap(repo, init_git=False)` at the top of run(), or (b) add a thin
`scaffold_missing(repo)` wrapper in init.py that delegates to bootstrap() and then
additionally creates CHANGELOG.md from CHANGELOG.md.template (the one file
bootstrap omits). Byte/existence-skip semantics are already guaranteed by
bootstrap + memory.ensure_memory.

---

## 2. Scaffold inventory (what setup/SKILL.md creates, deterministically)

Files created (all merge-only / never overwrite):
  - CLAUDE.md   <- CLAUDE.md.template (or merge missing rule blocks if present)
  - AGENTS.md   <- AGENTS.md.template (mirror, one-liner per rule)
  - CHANGELOG.md <- CHANGELOG.md.template (single setup entry; left as-is if exists)
  - .gitignore  (create w/ .renmark/state|debug|logs, or append missing lines)
  - .renmark/{memory,plans,specs,state,debug,logs,reviews}/
  - memory seed files: stack.md, INDEX.md, project.md, features.md, bugs.md,
    decisions.md, routing.md, learnings.md, conventions.md, architecture.md
    (templates exist under plugin/templates/memory/*.md.template; the canonical
    set is renmark.memory.MEMORY_FILES, copied by memory.ensure_memory)
  - .renmark/README.md <- renmark-readme.md
  - Then runs `python -m renmark.init` (step 5.5) to seed project-map.md — but
    ONLY first-time (skip if project-map.md exists).

Rule blocks merged into CLAUDE.md (17, in order, by <!-- BEGIN:x --> marker):
  changelog-rule, refactor-safety-rule, context-hygiene-rule,
  executor-dispatch-rule, root-cause-rule, verify-before-done-rule,
  orchestrator-role-rule, canonical-state-rule, summary-boundary-rule,
  context-contamination-rule, artifact-governance-rule, compact-semantics-rule,
  failure-transparency-rule, workflow-recovery-rule, task-isolation-rule,
  context-budget-rule, lifecycle-rule
  + the `## Tooling — renmark workflow` section if absent.
These blocks live in CLAUDE.md.template and are merged by the *agent* (markdown
logic), NOT by Python — there is no Python rule-merge function today. This is the
part that cannot be made fully deterministic without new code: a fresh
template-copy gets all blocks for free; merging-into-an-existing-CLAUDE.md is
agent work.

Templates present in plugin/templates/: CLAUDE.md.template, AGENTS.md.template,
CHANGELOG.md.template, PRD.md.template, PROTOTYPE.html.template,
SCHEMATIC.md.template, renmark-readme.md, memory/{decisions,conventions,project,
features,routing,INDEX,bugs,learnings,stack,architecture}.md.template.

---

## 3. setup-as-alias + lint

lint_command_shims (lint.py:139) requires a bijection: every commands/<n>.md
needs skills/<n>/SKILL.md and vice versa; AND each commands/<n>.md text must
contain the literal string `skills/<n>/SKILL.md`. So to keep lint green, KEEP
both skills/setup/SKILL.md and commands/setup.md. A thin SKILL.md that just
delegates to init is fine — there is no lint rule on SKILL.md *body* content
beyond frontmatter + the next-steps citation.

next-steps citation lint (lint_next_steps_citation, lint.py:91): setup is class
'aux' (lifecycle AUX_SKILLS includes 'setup'; DOMAIN_BY_SKILL maps setup ->
'meta'). Aux skills MUST contain the literal 'next-steps.md'. So the alias
SKILL.md must still cite _shared/next-steps.md or lint fails. (gate-only skills
may cite handoff-menu.md instead — setup is not gate.)

Other lint passes that touch setup: lint_skill_files requires frontmatter
name==dir ('setup') + non-empty description. All satisfiable by a thin alias.

No lint rule would break from making setup delegate to init, provided: both
files stay, command shim still references skills/setup/SKILL.md, frontmatter
intact, and the SKILL.md keeps the 'next-steps.md' string.

---

## 4. roadmap-at-end / zero-LLM

init.py is strictly zero-LLM and deterministic (module docstring lines 11-14;
also re-stated in init/SKILL.md). It must STAY zero-LLM. Therefore step-5
`/renmark:roadmap --gaps` MUST be a SKILL-level hand-off, never code in init.py.

How init/SKILL.md ends today (section "4. What's next", lines 73-89): it already
routes into roadmap gap-discovery mode (per ADR-009). It calls
`renmark.lifecycle.next_steps(repo, "init")`, renders via the class-3
next-steps contract, and names `/renmark:roadmap` (gap mode) as the PRIMARY
recommended action, with the in-flight feature resume step (or /renmark:start)
as alternate, plus Nothing. It never auto-proceeds — explicit AskUserQuestion
choice required. So the roadmap-at-end behavior the design wants is ALREADY the
documented init hand-off; the fold just inherits it.

setup/SKILL.md ends with its own class-3 hand-off (prd / start / roadmap) — if
setup becomes a thin alias, that menu would be superseded by init's.

---

## 5. Idempotency / non-destructive (byte-equality skip)

Two distinct mechanisms:

(a) merge_stub_into / write_full_map / write_standards_md use BYTE-EQUALITY skip:
they render the new body, compare against the existing managed-block body
(stripping the timestamp header so the volatile date does not force a rewrite),
and return 'unchanged' without writing if equal — avoiding prompt-cache busts.
See _render_stub_body vs _existing_stub_body (init.py:468/590), and
_strip_header_lines (init.py:652) for the map/standards files. These only ever
touch the managed `<!-- BEGIN:project-stub -->` block, never hand-written prose.

(b) bootstrap()/ensure_memory use EXISTENCE skip (`if not target.exists()`):
files are created only when absent; existing files are never read or rewritten.
This is the right primitive for scaffold-if-missing — 'never overwrite existing
files' is satisfied structurally. CHANGELOG.md should follow the same
existence-skip rule (create from template only if absent; setup/SKILL.md already
mandates 'if exists, leave as-is').

So scaffold-if-missing preserves non-destruction for free: scaffold via
existence-skip (bootstrap), then the existing init scan uses byte-equality-skip
for the managed blocks. No new invariant needed.

## Summary

- renmark/bootstrap.py::bootstrap() ALREADY scaffolds CLAUDE.md/AGENTS.md/.gitignore/.renmark/ non-destructively from templates (existence-skip); no renmark/setup.py exists (setup is pure markdown). Gaps vs setup: bootstrap omits CHANGELOG.md and does NOT merge rule blocks into a pre-existing CLAUDE.md.
- init.run() hard-errors at init.py:1295-1297 (CLAUDE.md missing -> exit 1); cleanest fold is a scaffold-if-missing call at the TOP of run() before that check, delegating to bootstrap(init_git=False) + a CHANGELOG.md create. Templates resolve via memory.template_dir() — reuse, do not reimplement.
- setup-as-alias keeps lint green IF both skills/setup/SKILL.md + commands/setup.md stay, shim references skills/setup/SKILL.md, frontmatter name=='setup', and SKILL.md keeps literal 'next-steps.md' (setup is aux class -> citation required by lint_next_steps_citation).
- init.py is strictly zero-LLM and must stay so; roadmap --gaps hand-off is already SKILL-level (init/SKILL.md sec 4 routes to /renmark:roadmap gap mode per ADR-009) — the fold inherits it.
- Non-destruction is structural: bootstrap/ensure_memory use existence-skip (create only if absent); init scan uses byte-equality-skip on managed BEGIN:project-stub blocks only. The 17 rule-block merges into an existing CLAUDE.md remain agent/markdown work — no Python merge function exists.
