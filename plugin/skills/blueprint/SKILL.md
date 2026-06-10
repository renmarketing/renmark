---
name: blueprint
description: Use when the user wants a visual blueprint of the project — typed as /renmark:blueprint or phrases like "diagram this architecture", "draw the system", "show me a schematic", "mock up the UI", "make a prototype". Synthesizes a Container-granularity Mermaid architecture diagram (SCHEMATIC.md) and, when the build has a UI, a self-contained HTML/CSS mockup (PROTOTYPE.html) — both spliced into human-owned root docs without clobbering hand-written sections. Reads architecture ONLY from `.renmark/memory/project-map.md` (never rescans the repo) and halts to `/renmark:init` when that map is missing or stale. The diagram body is the LLM's job; the marker-splice mechanics live in `renmark/blueprint.py`.
---

# blueprint

## Overview

`/renmark:blueprint` turns the project's recorded architecture into two visual artifacts at the repo root: a **SCHEMATIC.md** (a Container-granularity Mermaid flowchart of the system) and — only when the build has a user interface — a **PROTOTYPE.html** (a self-contained HTML/CSS mockup body). It is a **touchpoint, not a lifecycle stage**: you can run it at any point once the project map exists, as often as you like.

This skill **orchestrates**; it does not implement the splice. The marker grammar, idempotent block replacement, and the "never clobber human content" guard all live in `renmark/blueprint.py`. The skill's job is the LLM-side synthesis (the Mermaid graph, the mockup body) plus the gates (freshness, UI) and the write-boundary contract. Architecture is read from **one source only** — `.renmark/memory/project-map.md` — and is **never** reconstructed by rescanning the repo.

## When to Use

- "Diagram this project's architecture" / "draw the system" / "make a schematic"
- "Mock up what the UI could look like" / "build me a prototype page"
- After `/renmark:init` has produced a fresh `project-map.md` and you want a visual companion to it
- To refresh SCHEMATIC.md / PROTOTYPE.html after the architecture changed and the map was re-run

**Do NOT use:**
- To document the project map itself — that's `/renmark:init` (the SOLE writer of `project-map.md` and `stack.md`).
- To author the product definition — that's `/renmark:prd` (`PRD.md`).
- To decompose work into tasks — that's `/renmark:plan`.
- To rescan the repository for structure — blueprint NEVER rescans; if the map is missing/stale it routes to `/renmark:init` instead of fabricating architecture.

### Write-boundary guardrail (load-bearing)

The map and the visuals have **disjoint, single-writer ownership** — do not cross them:

- `/renmark:init` writes **only** `.renmark/memory/project-map.md` and `.renmark/memory/stack.md`. It never touches the visuals.
- `/renmark:blueprint` is the **SOLE writer** of `SCHEMATIC.md` and `PROTOTYPE.html`. It never writes the map or stack; it only **reads** them.

Blueprint treats `project-map.md` as read-only upstream truth and the two root visuals as its exclusive downstream output. Any write outside `SCHEMATIC.md` / `PROTOTYPE.html` from this skill is a bug.

## Steps

**Step 0 — Context check.** Call `lifecycle.skill_preamble(repo, 'blueprint')`. If it returns a non-None hint, surface it as a one-line note. Do NOT block — the user decides whether to `/compact` or `/clear`.

### Step 1 — Freshness gate (architecture source of truth)

Read `.renmark/memory/project-map.md`. This is the **only** architecture source — do NOT rescan the repo, and NEVER fabricate architecture from memory or guesswork.

- **If the file is missing → HALT.** Route the user to `/renmark:init`:
  > *"No project map yet — `/renmark:blueprint` reads architecture from `.renmark/memory/project-map.md`. Run `/renmark:init` first to generate it, then re-run blueprint."*
- **If present, check freshness** using the same pattern `dev-standards.md` uses. The map carries a header line `<!-- Last refreshed: <date> @ <sha> -->`. Compare that `<sha>` against the current `git rev-parse HEAD`:
  ```bash
  git rev-parse HEAD
  ```
  If the recorded sha does not match current HEAD, the map is **stale** → HALT and route to `/renmark:init`:
  > *"Project map is stale (refreshed @ `<old-sha>`, HEAD is `<new-sha>`). Re-run `/renmark:init` so the diagram reflects current architecture, then re-run blueprint."*

Capture the map's recorded sha (the `@ <sha>` value) — it becomes the `source_sha` recorded on every spliced block in Step 4, so each generated block is provenance-stamped to the exact map revision it was synthesized from.

### Step 2 — UI gate (schematic always; prototype only when UI)

Read `.renmark/memory/stack.md` and pass its text to the detector:

```python
from renmark import blueprint
ui = blueprint.detect_ui(stack_md_text)   # -> True | False | None
```

Branch on the result:

- **`True`** → the build likely has a UI. Confirm with a one-line override prompt before committing to a prototype:
  > *"stack.md suggests a UI — generate PROTOTYPE.html too? [Y/schematic-only]"*
  Default to generating both if no objection.
- **`False`** or the user declines the override → **schematic only**. Skip the prototype entirely (no PROTOTYPE.html write).
- **`None`** (detector can't tell) → ask the user directly:
  > *"Does this build have a UI? [y/n]"*
  `y` → both; `n` → schematic only.

The schematic is **always** produced (assuming the freshness gate passed). Only the prototype is gated on UI.

### Step 3 — Synthesize (LLM-side)

From `project-map.md` alone, the LLM produces:

- **Schematic** — a **Container-granularity** Mermaid `flowchart`/`graph` (NOT a full 4-level C4 model). One node per major container/module/service the map records, edges for the data/control flow between them. Keep it to the system's real top-level structure — do not invent components the map doesn't list.
- **Prototype** (only when UI confirmed in Step 2) — a **self-contained** HTML/CSS mockup **body** (markup + inline styles, no external assets, no JS dependencies) representing the primary UI surface the project describes.

These are the only two pieces of content the LLM generates; everything else is mechanics in `blueprint.py`.

### Step 4 — Splice & write (mechanics in `renmark/blueprint.py`)

For **each** artifact to write — `SCHEMATIC.md`, and `PROTOTYPE.html` when UI — apply this decision per root file. Use the marker-id constants `blueprint.MARKER_SCHEMATIC` (`"SCHEMATIC"`) and `blueprint.MARKER_PROTOTYPE` (`"PROTOTYPE"`). The `source_sha` is the project-map.md sha captured in Step 1.

1. **Root file absent** → create it from the template (`${CLAUDE_PLUGIN_ROOT}/templates/SCHEMATIC.md.template` / `${CLAUDE_PLUGIN_ROOT}/templates/PROTOTYPE.html.template`), substituting `{{PROJECT_NAME}}` / `{{DATE}}`. The template already carries the `RENMARK:GENERATED:<id>:START…END` markers around its `## Current Architecture` block, so after creating it you splice the generated content into those markers exactly as in case 2.
2. **Root file exists WITH markers** → splice in place, replacing only the generated block and preserving every human-owned section:
   ```python
   new_text = blueprint.splice_generated_block(
       existing_text,
       blueprint.MARKER_SCHEMATIC,        # or MARKER_PROTOTYPE
       generated_content,
       source_sha=project_map_sha,        # from Step 1
   )
   ```
3. **Root file exists WITHOUT markers** → **ABORT for that artifact. Never clobber human content.** `splice_generated_block` raises `blueprint.MarkerNotFoundError` in this case — catch it to distinguish a human-authored, marker-free file from an internal error, and report clearly:
   > *"`SCHEMATIC.md` exists but has no RENMARK generated markers — it looks hand-authored. Refusing to overwrite. Add the marker block (see the template) or move the file aside to let blueprint manage it."*

Write the spliced text back to the root file. The splice is idempotent: re-running blueprint replaces the block content and re-stamps `source-sha=<sha>` on the start marker without disturbing anything outside the markers.

### Final step — Lifecycle (touchpoint, not a stage)

Record the artifact pointers in lifecycle state. **Do NOT pass a `stage=` argument** — blueprint is a touchpoint and must not advance the lifecycle stage:

```python
from renmark import lifecycle
lifecycle.write_lifecycle(repo, artifact_update=("schematic", "SCHEMATIC.md"))
# only when the prototype was actually written:
lifecycle.write_lifecycle(repo, artifact_update=("prototype", "PROTOTYPE.html"))
```

Emit a bounded verdict to the user — what was written/created-vs-spliced, the recorded `source_sha`, and whether the prototype was generated or skipped. Keep it within the renmark output cap (≤5 lines / ≤300 tokens). NEVER paste the Mermaid graph, the HTML body, or full file contents into the conversation — report paths and counts only.

Sample verdict:

```
blueprint: <project>  (source-sha 8b5f07e)

✅ SCHEMATIC.md — spliced Container diagram (12 nodes) into existing markers
✅ PROTOTYPE.html — created from template + mockup body (UI confirmed)
```

## What's next

Blueprint is a **touchpoint, not a lifecycle stage** — it must not advance the
stage. But it must still hand off rather than dead-end. As a class-1 pipeline
skill (per `${CLAUDE_PLUGIN_ROOT}/skills/_shared/next-steps.md`), end the run by
deriving the next step from durable state so the refresh resumes the in-flight
feature's next stage:

> *End by calling `renmark.lifecycle.next_steps(repo, "blueprint")` and render the
> result per `${CLAUDE_PLUGIN_ROOT}/skills/_shared/next-steps.md` (class 1 —
> Tier-0 stage routing). Present via `AskUserQuestion` (handoff-menu.md rules
> 6–9); the state-derived next command is the `(Recommended)` option. Require an
> explicit choice — never auto-proceed.*

Because the next step is read from `lifecycle.json` (not the conversation), the
recommendation resumes whatever stage the in-flight feature stopped at. If no
feature is in flight, `next_steps` falls back to `/renmark:roadmap` gap mode.
This hand-off does NOT change blueprint's artifact-touchpoint behavior — the
final step still records artifact pointers with **no `stage=`** argument.

## Governance compliance

| # | Rule | How this skill complies |
|---|---|---|
| G2 | Canonical state | Architecture truth lives on disk in `.renmark/memory/project-map.md`; the two visuals are durable root files; the artifact pointers persist in `.renmark/state/lifecycle.json`. Nothing relies on conversation memory. |
| G3 | Summary boundary | Only a ≤5-line verdict (paths + node counts + source-sha + skip/created/spliced) crosses into the conversation. The Mermaid graph, the HTML body, and full file contents are NEVER read into chat. |
| G5 | Executor isolation | Heavy reads (`project-map.md`, `stack.md`, templates) happen inside this dedicated invocation; the orchestrator never loads diagram or markup bodies. |
| G6 | Artifact governance | Every generated block is provenance-stamped via `source-sha=<project-map.md sha>` on its start marker through `splice_generated_block(..., source_sha=...)`. The templates carry `artifact_type` / `schema_version` / `created_at` headers and `source-sha=PENDING` placeholders that get filled on first splice. |
| G7 | Compact semantics | The map, the templates, and the spliced files are on disk; after `/compact` mid-skill the freshness gate + UI gate + splice can be re-derived from files with no transcript dependency. |
| G9 | Failure transparency | A missing/stale map HALTS and routes to `/renmark:init` rather than fabricating architecture. A marker-free human file ABORTS (caught `MarkerNotFoundError`) rather than clobbering. A skipped prototype is reported honestly, never claimed written. |
| G10 | Workflow recovery | Idempotent and self-locating: re-running re-detects the map state and re-splices the generated block in place without duplicating human content; the source-sha stamp makes re-runs verifiable. |
| G11 | Task isolation | This skill runs first-person (its reads are in-invocation, no subagent fan-out); the splice mechanics are a deterministic library call (`renmark/blueprint.py`), not delegated reasoning. |
| G12 | Lifecycle persistence | Records artifact pointers via `lifecycle.write_lifecycle(repo, artifact_update=...)` with **no `stage=`** — blueprint is a touchpoint, so it never advances the canonical lifecycle stage. |

*Mirror any rule-affecting change to this skill in `AGENTS.md`/`CLAUDE.md` guidance per the workspace sync convention.*
