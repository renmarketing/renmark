---
artifact_type: host_parity_audit
schema_version: "1.0"
created_at: "2026-07-15T19:58:22Z"
source_sha: "b59fefa7f4edcae1c13e3c479cc7f80026324ea9"
related_plan: null
generator: "codex"
stale_after: "2026-08-15T00:00:00Z"
dependency_refs:
  - ".codex-plugin/plugin.json"
  - "plugin/.claude-plugin/plugin.json"
  - "plugin/skills/_shared/handoff-menu.md"
  - "plugin/skills/orchestrate/SKILL.md"
  - "renmark/lifecycle.py"
  - "renmark/loop.py"
completion_state: complete
confidence: high
validation_status: validated
retry_count: 0
parser_success: true
schema_compliance: true
---

# Codex / Claude Code parity audit

## Verdict

Renmark is **not yet host-parity complete**. Its deterministic workflow core is
healthy and most skills are discoverable by natural language, but the interactive
and orchestration layers remain Claude-native. The Codex package currently exposed
to the desktop app is also an older `renmark-ai` v0.36.0 cache, not this `renmark`
v0.37.0 source tree.

The highest-risk failure is silent degradation: on Codex, a skill that asks for
Claude's `AskUserQuestion` can be classified as headless and auto-pick or print a
fallback even though a human is present. A second high-risk failure is orchestration:
the skill body routes non-Codex tasks through Claude `Agent`/`Workflow` tools, while
the Codex-native routing helper and custom-agent files are not wired into that path.

## Scorecard

| Capability | Verdict | Evidence |
|---|---|---|
| Deterministic audit/lint | PASS | Full audit: 0 structural issues; 30 skills clean |
| Lifecycle, loop, pause, resume state | PASS/PARTIAL | Runtime state is host-neutral and focused tests pass; no live Codex trajectory proves it |
| Natural-language skill matching | PARTIAL | Trigger-shaped descriptions exist; exact `plan this` and `dispatch this` prompts are absent |
| Recommended option first | FAIL | Plan, finish, guide, and dynamic quality menus can place the recommendation later or omit the label |
| Native interactive selector | FAIL | Skills reference `AskUserQuestion`; no Codex `request_user_input` contract exists |
| Pipeline/subagent execution on Codex | FAIL | Orchestrate is written around Claude `Agent` and `Workflow`; Codex routing is unused |
| Codex install/update/version parity | FAIL | Codex manifest is stale and is not part of installer, doctor, or release drift checks |
| Cross-host behavior proof | FAIL | Current behavior fixtures validate deterministic text, not host tool schemas or live implicit routing |

## What already works

1. All 30 shipped skills have trigger-shaped frontmatter and pass `skillgen --check`.
   Codex can implicitly activate skills from their descriptions, so the basic design
   is compatible with Codex progressive disclosure.
2. `.codex-plugin/plugin.json` exists, points at the shared skill tree, and the repo
   has Codex custom-agent TOML files plus `renmark/codex_routing.py`.
3. `renmark.lifecycle`, `renmark.loop`, pipeline state, wave summaries, pause state,
   and resume logic are deterministic Python and do not intrinsically depend on Claude.
4. The focused parity slice passed: 211 tests passed and 11 skipped. The deterministic
   behavior suite passed 4/4. The full structural audit passed with zero issues.

## P0 findings

### P0.1 — No host-neutral choice contract

`plugin/skills/_shared/handoff-menu.md` names `AskUserQuestion` as the primary
renderer and assumes Claude's four-option cap. The source and installed Codex copy
contain no `request_user_input` instructions. Codex's current native selector has a
different schema and, in this app session, is available only in Plan mode. Treating
the absent Claude tool as `headless` conflates **interactive Codex Default mode** with
**non-interactive execution**.

Recommended design:

- Add a host-neutral `Choice` contract with stable id, label, description,
  recommended flag, danger class, and aliases.
- Normalize every choice set before rendering: the single recommended option is
  always index 0 and its label is suffixed `(Recommended)`.
- Claude adapter: `AskUserQuestion`, up to four visible options.
- Codex adapter: `request_user_input`, two to three visible options per question.
- Capability fallback: numbered choices with the recommendation first. Tool absence
  is `selector_unavailable`, not automatically `headless`; headless detection remains
  a separate TTY/config decision.
- Validate every menu through a deterministic helper before a skill renders it.

Product constraint: exact native-picker parity in Codex Default mode is not possible
with the selector tool exposed in the audited session. The practical parity contract
is **native picker when the host exposes one; identical recommended-first numbered
fallback otherwise**. A custom UI/app would be a separate, larger product feature.

### P0.2 — Recommended-first is not an invariant

- Plan shows Review before its recommended Dispatch action.
- Finish can show the recommended lane as a duplicated fifth item.
- Guide selects a recommendation based on the answer but does not move it to index 0.
- Quality-menu priority is action-class based and does not guarantee that the
  state-derived recommendation is first or even labeled.

Fix this in one normalizer, not by manually reordering prose in 30 skills. Add a lint
that fails when a static menu lacks exactly one recommendation or puts it anywhere
other than index 0; add behavior tests for dynamic menus.

### P0.3 — Codex distribution is not installing this plugin

Canonical source is v0.37.0, while `.codex-plugin/plugin.json` says v0.36.0.
`renmark/release.py::VERSION_FILES` omits the Codex manifest, so the normal drift
guard reports green. `install.sh`, `install.ps1`, doctor, and README install only the
Claude registry. The active desktop cache is `personal/renmark-ai/0.36.0`, so audit runs
in Codex are not exercising the current renmark source.

There is also a layout mismatch: the legacy-compatible marketplace points at
`./plugin`, but the Codex manifest is at the repository root. Make `plugin/` the
shared plugin root by adding its Codex manifest there (or change the Codex marketplace
source to the repository root), then add a real repo/personal Codex marketplace entry.
Include the Codex manifest and marketplace metadata in version drift and release
snapshots. Add an explicit `renmark-ai` to `renmark` migration/removal step so both cannot
compete in skill matching.

### P0.4 — Orchestration is Claude-bound

`plugin/skills/orchestrate/SKILL.md` routes `haiku|sonnet|opus|fable` through Claude
`Agent` calls and multi-item waves through `Workflow`. `renmark.dispatch` classifies
these as `needs_agent`, explicitly meaning Claude agent dispatch. On Codex,
`renmark.codex_routing.route_for_task` and `.codex/agents/*.toml` exist but are not
used by production orchestration.

Add a host dispatch adapter:

- Claude: preserve `Agent`/`Workflow` behavior and native role files.
- Codex: use Codex subagent spawning/waiting, map role/complexity through
  `route_for_task`, and preserve the same `SubagentInput`/`SubagentOutput`, wave,
  ledger, verifier, and state contracts.
- Keep deterministic/codex-CLI tasks on the existing subprocess path only when that
  is intentionally cheaper than a Codex subagent; do not recursively shell out by
  accident when Codex is already the host.
- Replace `${CLAUDE_PLUGIN_ROOT}` dependencies with a host-neutral fragment loader or
  an installed-plugin-root resolver.

The `.codex/agents` files in the source repo are project-scoped configuration; they
are not currently installed into consumer projects by the plugin installer. Either
make Codex orchestration work with built-in agents plus bounded prompts, or explicitly
install/update the custom agents as a separately governed component.

## P1 findings

### P1.1 — Natural routing is broad but not proven

Skill descriptions cover most verbs, and Codex officially performs implicit matching
from `description`. However, the exact owner phrases `plan this` and `dispatch this`
are absent, the persistent global routing helper writes only `~/.claude/CLAUDE.md`,
and `--set-proactive` only persists config—it does not enforce a Codex entry-point
decision.

Add a compact trigger matrix to frontmatter and tests:

| Prompt | Expected pipeline |
|---|---|
| `plan this` | plan |
| `dispatch this` / `run these tasks` | orchestrate |
| `loop until this passes` | loop |
| `fix this failure` | debug |
| `add/change this` | feature |
| `build this from scratch` | start |
| `what is next?` | roadmap |
| `ship this` | finish |

Front-load these phrases so they survive Codex's initial skill-description budget.
Mirror the global routing block into `~/.codex/AGENTS.md` through an opt-in installer
step, and define how `proactive=false` suppresses auto-routing without disabling
explicit skill invocation.

### P1.2 — Tests prove structure, not host behavior

The audit, lint, and behavior suites are green because they do not cover:

- Claude vs Codex selector payload schemas;
- recommended-first across every static and dynamic menu;
- source manifest vs installed Codex cache identity/version;
- implicit prompt-to-skill routing on either host;
- Codex subagent fan-out for a full plan;
- loop pause, `/clear`/resume, and terminal disposition on Codex.

Add deterministic contract tests first, then opt-in live trajectory tests for both
hosts. A passing structure audit must not be labeled host parity.

## Implementation sequence

1. **Distribution truth** — unify plugin root/name/version, Codex marketplace install,
   doctor checks, release drift, and `renmark-ai` migration.
2. **Interaction adapter** — host-neutral choice schema, recommended-first normalizer,
   Codex/Claude renderers, fallback, and headless separation.
3. **Natural routing** — exact phrase matrix, Codex global `AGENTS.md` rule, proactive
   semantics, and discovery tests.
4. **Dispatch adapter** — host-native subagents, role/model mapping, fragment loading,
   cost ledger, and wave behavior.
5. **End-to-end proof** — plan → dispatch → verify → handoff; bounded loop → pause →
   resume → finish; run once on Claude and once on Codex.

Because this touches more than three files and changes routing/orchestration, execute it
as a refactor-grade feature: clean-tree check, checkpoint commit, fresh baseline, small
passing commits, and final full verification. Do not combine distribution migration and
runtime dispatch in one commit.

## Acceptance criteria

Parity is complete only when all of the following are true:

1. The same released version/name is installed and reported by both hosts.
2. Every menu has exactly one recommendation at index 0, visibly labeled.
3. Both hosts render a native selector when available and the same ordered numbered
   fallback when not available; interactive Codex is never mistaken for headless.
4. The exact natural prompts in the trigger matrix invoke the correct skill without a
   slash command.
5. A validated plan executes all waves using host-native subagents, preserves bounded
   outputs, and auto-verifies.
6. A loop survives interruption and resumes from persisted state on both hosts.
7. Claude and Codex live behavior transcripts pass the same golden outcomes.

## Verification evidence

- `python -m renmark.audit`: PASS, 0 structural issues, 30 commands.
- `python -m renmark.skillgen --check`: PASS, 30 skills.
- `renmark-execute --behavior`: PASS, 4/4 deterministic fixtures.
- Focused lifecycle/loop/headless/routing/install suite: 211 passed, 11 skipped.
- Full suite: 1,423 passed, 28 skipped in 127.05 seconds.

## Official Codex contracts used

- Plugins require `.codex-plugin/plugin.json`; marketplaces determine the installed
  cache and enabled plugin presented to the desktop app.
- Codex implicitly invokes skills by matching user tasks to concise, front-loaded
  skill descriptions.
- Codex supports project/global custom agents and instruction-driven subagent workflows,
  but those must be wired explicitly; Claude `Agent`/`Workflow` prose is not a Codex
  dispatch implementation.
