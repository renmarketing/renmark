---
name: inventory
description: "Use to harvest a flat inventory of every renmark command and skill — typed as /renmark:inventory or \"list all commands\", \"inventory the skills\". Alias of /renmark:audit --inventory-only."
disable-model-invocation: false
---

# inventory

## Overview

`/renmark:inventory` is a **thin alias** of `/renmark:audit --inventory-only`,
following the `setup`→`init` delegation pattern. It does not run the audit's
drift/lint passes — it only harvests the per-command inventory (name, shim path,
skill path, description, argument-hint, domain, class, line counts) by parsing
the plugin tree's frontmatter, and writes it to `.renmark/audits/`.

The harvest logic lives in `renmark/audit.py` (`build_inventory` /
`write_inventory`) — zero LLM, pure parsing. For the full health audit (registry
drift, lint, version parity, modularity), use **`/renmark:audit`** directly.

## When to Use

- You want a quick table of every command/skill and how they're classified.
- You're checking which commands lack a backing SKILL.md.

For drift detection and contract checks, use `/renmark:audit`.

## Steps

**Step 0 — Context check.** Call `lifecycle.skill_preamble(repo, 'inventory')`.
Inventory is `audit` domain; surface the returned hint if non-None.

### 1. Run the engine (inventory-only)

```bash
python -m renmark.audit --inventory-only
```

Pass the bounded stdout through to the user **verbatim** — it reports the command
count and the `.renmark/audits/inventory-<date>.md` + `.json` artifact paths. Do
not paraphrase; the format is the contract. Point the user at the `.md` artifact
for the full table.

### 2. Hand off

inventory is an **aux / terminal skill** (class 3 in
`${CLAUDE_PLUGIN_ROOT}/skills/.shared/next-steps.md`).

> *End by calling `renmark.lifecycle.next_steps(repo, "inventory")` and render per
> `${CLAUDE_PLUGIN_ROOT}/skills/.shared/next-steps.md` (class 3 — resume-pipeline
> + 1–2 local actions). The in-flight feature's next command is `(Recommended)`;
> add the skill's local follow-ups. Render via `AskUserQuestion`
> (`${CLAUDE_PLUGIN_ROOT}/skills/.shared/handoff-menu.md` rules 6–9); require an
> explicit choice.*

The natural local follow-up is **`/renmark:audit`** (the full health audit this
aliases). Do not paste the rendering rules or the gate menu — cite the files.

## Governance compliance

- **G3 (bounded output)** — relays the engine's ≤5-line stdout verbatim; reads no
  artifact body.
- **G6 (provenance)** — the inventory artifact is written via
  `summary.write_artifact`, so provenance metadata is automatic.
- Read-only: advances no stage (G7/G12 stage rules N/A); emits no dispatch
  (G9/G11 N/A).

See `CLAUDE.md` governance rules for definitions.
