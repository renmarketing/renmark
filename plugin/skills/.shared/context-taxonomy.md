# Context Taxonomy — Reference (single source of truth)

**Shared by every skill that loads instructions or dispatches subagents:**
`orchestrate`, `feature`, `start`, `finish`, `verify`, `codereview`, and any
skill that resolves a `_shared/*.md` fragment on demand. This is the one place
renmark's four kinds of context — and the load policy that governs each — are
defined, so skills cite this pointer instead of re-explaining what may be
pre-loaded versus fetched on demand. Operationalizes REQ-5 (context hygiene)
and REQ-20 (dynamic skill loading).

---

## The four kinds of context

renmark treats context as four disjoint kinds. Anything the orchestrator or a
subagent holds is exactly one of these — nothing is "just floating."

| Kind | Source | Persistence | Load policy |
|---|---|---|---|
| **static** | `CLAUDE.md` / `AGENTS.md` rule blocks | always present (whole session) | injected by the harness at session start; never fetched, never dropped |
| **dynamic** | skill bodies (`SKILL.md`) + `_shared/*.md` fragments | on demand; released after use | **metadata upfront only** — full body loaded via `load_skill_body` / `load_fragment` when a skill actually runs |
| **memory** | `.renmark/memory/*` (`INDEX.md`, `project.md`, `routing.md`, logs) | durable; survives `/clear` and `/compact` | read by pointer/summary when a workflow needs prior decisions; never bulk-loaded |
| **task-local** | the per-subagent dispatch packet | ephemeral; dies with the subagent | assembled per dispatch; carries task spec + required-skill metadata, never a full skill body |

---

## Metadata upfront, bodies on demand

The load-bearing rule for **dynamic** context: a skill's or fragment's
**metadata** (name, description, and cite pointers) is exposed upfront through
the `skillmeta` registry — surfaced programmatically via
`renmark.context.skill_metadata`. The full **instructions/body** load ONLY on
demand, via `renmark.context.load_skill_body` (for a `SKILL.md`) or
`load_fragment` (for a `_shared/*.md`).

Dynamic bodies are **never pre-loaded into the orchestrator**. The orchestrator
knows a skill *exists* and what it's *for* (metadata) without paying for its
prose until the moment that skill runs — and it releases the body afterward.

---

## The dispatch-packet contract

Every scoped subagent receives ONLY:

- **task-local context** — its task spec, required file paths, upstream artifact
  pointers (paths, never contents), dependency summaries.
- **required-skill metadata** — the name + cite pointer of any skill it needs,
  never that skill's full body. The subagent loads the body itself on demand if
  it runs the skill.

This is enforced in production, not by convention:
`renmark.dispatch.build_subagent_input` builds the packet, carries
`required_skills` as **metadata** through `renmark.context`, and is guarded by
`assert_metadata_only` — which raises if a full skill/fragment body is ever
smuggled into a dispatch packet. A body reaching a subagent through dispatch is
a bug, not a shortcut.

---

## Why a shared file

Earlier drafts had each skill inline its own description of "what's loaded when."
The wording drifted, and one skill implied bodies were always resident.
Centralizing here means:

- One edit point. The four kinds and the load policy are defined once; every
  skill and the `renmark.context` code path cite the same taxonomy.
- Linter-friendly. `plugin/skills/.shared/` is skipped by `renmark.lint` (it's a
  reference dir, not a skill), so this file never trips the command-pair check.
- Symmetric with `_shared/reasoning-contract.md` and `_shared/handoff-menu.md` —
  same pattern, same precedent.

When citing this taxonomy in a SKILL.md or rule block, write:

> *Honor the context taxonomy in
> `${CLAUDE_PLUGIN_ROOT}/skills/.shared/context-taxonomy.md`: static rules are
> always present; dynamic skill/fragment bodies load on demand (metadata
> upfront only); memory is durable and read by pointer; the per-subagent
> dispatch packet carries task-local context + required-skill metadata, never a
> full body.*

Do not paste the taxonomy table into the calling SKILL.md — cite this file.

---

## Context hygiene gates

Renmark resolves host capabilities through `renmark.hosts.capabilities_for`
(explicit host → `RENMARK_HOST` → Codex process marker → Claude-compatible default)
before emitting either hygiene gate. Claude Code uses its manual context
controls; Codex does not expose a compatible `/clear` + `/renmark:resume` pair,
so Codex records the domain transition and continues without asking the user to
run unsupported commands.

**Clear gate (Python-enforced, Claude Code only):** `skill_preamble` → `context_budget_check` returns `"clear"` on cross-domain transition → host supports clear/resume → `persist_compact_checkpoint(repo, skill, reason="clear")` called → returns `CONTEXT_GATE_CLEAR:`-prefixed string → CLAUDE.md rule triggers `AskUserQuestion`. Bypass skills (advisory only): `finish`, `approve`, `resume`. On Codex or an unknown host, the preamble records the invocation and emits no clear/resume gate.

**Compact gate (rule-enforced, hosts with manual compact only):** Threshold in `config.json["compact_gate_tokens"]` (default 120k, 0 = disabled). CLI helper: `renmark-execute --compact-checkpoint`. Enforced by host rule at ≥120k tokens only when `supports_compact` is true; Python provides persist + CLI helper only. Codex relies on host-managed compaction and must not be blocked on an unavailable `/compact`, `/clear`, or resume command.

**`persist_compact_checkpoint(repo, skill, reason, host=None)`:** writes `.renmark/state/compact_checkpoint.json` with `{skill, reason, resume_cmd, timestamp}`. `resume_cmd` is `/renmark:resume` only when the resolved host supports it; otherwise it is null. Never raises.
