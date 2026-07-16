# Reuse-Check Subagent — Contract Reference (single source of truth)

**Shared by `/renmark:brainstorm` and `/renmark:plan` — any skill that is about
to propose a custom build.** This is the one place the reuse-check dispatch
pattern lives so skills can't drift. The rule is simple: before a skill proposes
building something new, a cheap subagent checks whether the capability **already
exists** — in a loaded skill, an available MCP tool, a prior spec/plan, or a
shipped feature — and the orchestrator/router reads ONLY the bounded `reuse`
verdict, never the searched bodies (REQ-5).

This is the "don't reinvent the wheel" guard.

---

## Why a subagent

The search surface — the full skill/command registry, the live MCP connector
list, every spec under `.renmark/specs/`, every plan under `.renmark/plans/`,
and the shipped-features log — is a large context consumer. Loading all of it
into the orchestrator to answer one question ("does this already exist?") would
violate the G11 / "orchestrator coordinates, does not accumulate" rule and bloat
the routing context for all subsequent waves. Instead, a single-purpose,
**cheap** subagent absorbs the search surface in its own context, reasons over
it, and returns a compact verdict.

The reuse-check is the cheapest gate in the pipeline: dispatch on
**`model: "haiku"`** by default — pattern-matching a request against an existing
inventory is haiku-grade work. **Escalate to `model: "sonnet"`** only when the
search surface is large (many dozens of specs/plans, or a wide MCP tool list)
where a haiku scan risks missing a real match — a missed match defeats the whole
purpose of the gate.

---

## Hard rule — orchestrator context boundary

> **The router/orchestrator MUST NOT read the searched bodies** — not the skill
> registry dump, not the MCP tool schemas, not any spec/plan body, not
> `features.md`. It passes only the request description to the subagent and
> receives only the ≤5-line `reuse` verdict. Period.

This is an enforcement point for the G11 contract and REQ-5. Violations —
reading spec/plan content inline, summarizing the registry in orchestrator
reasoning, or pasting MCP tool descriptions into the routing context — are
treated as bugs, not optimizations.

---

## What the skill dispatches (subagent inputs)

The skill invokes an **Agent tool call** (not a Bash subprocess) pinned to
**`model: "haiku"`** by default — without the pin the subagent inherits the
session tier and every reuse-check runs at top-tier pricing — and passes ONLY:

| Field | Content |
|---|---|
| `request_description` | Plain-text description of what the skill is about to build (≤200 words) |

**Size escalation:** when the search surface is large (many dozens of
specs/plans, or a wide MCP tool list), dispatch on `model: "sonnet"` instead.

The skill does **not** pass: the registry body, any spec/plan excerpt, MCP tool
schemas, or prior conversation context about existing features.

---

## What the subagent does (in its own context)

It searches, IN ITS OWN CONTEXT, the four reuse sources:

1. **Loaded renmark skills + commands** — the registry / plugin command surface
   (does a `/renmark:*` skill or command already do this?).
2. **MCP connectors / tools available in the session** (does a connected MCP
   server already expose this capability?).
3. **Prior specs under `.renmark/specs/` and plans under `.renmark/plans/`**
   (has this already been specced or planned?).
4. **`.renmark/memory/features.md`** — already-shipped features (has this
   already been built?).

The subagent's own prompt MUST carry the reasoning-contract citation — consider
interpretations, list assumptions, then act — per
`${CLAUDE_PLUGIN_ROOT}/skills/.shared/reasoning-contract.md`.

The subagent does NOT modify any file. It reads and reasons only.

---

## Bounded return format

The subagent returns EXACTLY the following — no prose, no reasoning dump,
≤5 lines total:

```
reuse: found | none
pointer: <one-line name-or-path of the existing skill / MCP tool / spec / feature that already covers the request>
```

`reuse` is the required field. `pointer` is included only when `reuse: found`,
and is exactly one line: the **name or path** of the matching skill, MCP tool,
spec, or feature — never the matched body. The orchestrator reads ONLY this
verdict (REQ-5).

---

## Examples

**Found case** (the capability already exists):

```
reuse: found
pointer: /renmark:blueprint already renders a Mermaid architecture diagram (SCHEMATIC.md)
```

**None case** (nothing covers the request — a custom build is warranted):

```
reuse: none
```

---

## What the consuming skill does with the verdict

The skill **surfaces the verdict**, then reports findings before proposing
custom work:

| Verdict | Skill action |
|---|---|
| `found` | Surface the `pointer`. **Default to reuse** — recommend the existing skill / MCP tool / spec / feature instead of a custom build, unless there is a clear, stated reason the existing thing doesn't fit. |
| `none` | Proceed to propose the custom build as normal. |

The bias is toward reuse: a `found` verdict is a recommendation to *not* build,
overridden only by an explicit reason the existing capability is insufficient.
Report the finding first; propose custom work second.

---

## Dispatch reference (for skill authors)

When citing this contract in a SKILL.md, write:

> *Before proposing any custom build, dispatch the reuse-check subagent from
> `${CLAUDE_PLUGIN_ROOT}/skills/.shared/reuse-check.md`: Agent tool call
> (`model: haiku`; `sonnet` for a large search surface), passing ONLY
> `request_description`. The subagent searches loaded skills/commands, session
> MCP tools, `.renmark/specs/` + `.renmark/plans/`, and
> `.renmark/memory/features.md` in its own context, and returns ONLY the ≤5-line
> `reuse: found | none` verdict (+ a one-line pointer when found). Surface the
> verdict and default to reuse; do NOT read the searched bodies in the
> orchestrator context (REQ-5).*

Do not paste the subagent logic or examples into the calling SKILL.md.

**Consumers:** `/renmark:brainstorm` (before propose-approaches),
`/renmark:plan` (before decomposition).

---

## Why a shared file

A per-skill reuse check would drift the moment a second skill needed it — and
brainstorm and plan need the identical contract. Centralizing here means:

- One edit point. Both consumers (and any future skill that proposes builds)
  read the same contract.
- Linter-friendly. `plugin/skills/.shared/` is skipped by `renmark.lint` (it's
  a reference dir, not a skill).
- Symmetric with `_shared/prd-alignment.md`, `_shared/scope-contract.md`, and
  `_shared/handoff-menu.md` — same pattern, same precedent.
