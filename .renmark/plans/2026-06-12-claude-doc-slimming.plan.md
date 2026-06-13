---
artifact_type: plan
schema_version: 1
created_at: 2026-06-12T17:15:00+00:00
source_sha: HEAD
related_spec: .renmark/specs/2026-06-12-claude-doc-slimming.spec.md
generator: fable
dependency_refs: [.renmark/specs/2026-06-12-claude-doc-slimming.spec.md]
---

# claude-doc-slimming — terse-rewrite CLAUDE/AGENTS to ≤200 lines

**Goal:** get all four onboarding docs ≤200 lines via in-place terse-rewrite —
compress the 23 governance rule blocks (keep names/markers/load-bearing clauses)
and the non-block sections (→ memory pointers). See the spec for the full
must-preserve clause list. **Byte-identity contract:** the CLAUDE template is the
authoritative source of block content; this repo's CLAUDE.md must reproduce the
template's terse blocks BYTE-FOR-BYTE (only its project-stub/glance differ), or
`merge_rule_blocks` (missing-only back-fill) and the audit's template-integrity
check would see drift. That forces order: template first, live files copy from it.

### Task 1: terse-rewrite the CLAUDE template (authoritative)
- **mode:** B
- **target:** plugin/templates/CLAUDE.md.template
- **complexity:** hard
- **executor:** sonnet
- **parallel_group:** 1
- **est_tokens:** 2600
- **est_cost_usd:** 0.038
- **verifier:** test $(wc -l < plugin/templates/CLAUDE.md.template) -le 200 && python3 -m renmark.lint 2>&1 | tail -1
- **serves:** REQ-5
- **spec:**
  Rewrite plugin/templates/CLAUDE.md.template to ≤200 lines. For EACH of the 23
  `<!-- BEGIN:name -->`…`<!-- END:name -->` blocks: keep the `## Heading`, BOTH
  markers, the block NAME unchanged, and the imperative load-bearing clause(s);
  cut examples, restated rationale, and filler — target ~6 lines/block incl.
  heading+markers. MUST-PRESERVE clauses (per spec, grep-findable after):
  codex RED-FLAG (never Agent-dispatch codex) + fable `model:"fable"` override
  escalation-only + the codex→sonnet usage-limit reroute exception
  (executor-dispatch-rule); the ≤5-line/≤300-token caps + 60%/80% thresholds
  (summary-boundary + context-budget); the receives-ONLY/writes-ONLY/aggregates
  -ONLY three lists (task-isolation); canonical stage order + lifecycle.json-vs
  -pipeline.json split + human-review fields (lifecycle); provenance field list
  (artifact-governance); never-write-outside-project + artifact-home list
  (project-write-boundary); the fable + reasoning-contract + reuse-check pointer
  lines (executor-preferences). Non-block sections → memory pointers: Tooling
  table → one line + `see /renmark:help`; Executor preferences → one line +
  `see .renmark/memory/routing.md`; at-a-glance/module tree → stack one-liner +
  `see .renmark/memory/project-map.md`; Code conventions/Testing → dev-gate
  one-liner + `see .renmark/memory/dev-standards.md`; File conventions → path
  list only. Preserve `{{PROJECT_NAME}}`/`{{DATE}}` placeholders, the line-3
  note, and the frontmatter exactly. Do NOT rename, merge, remove, or reorder
  any block. Run the verifier (≤200 lines AND lint clean) before returning.

### Task 2: rewrite this repo's CLAUDE.md to match
- **mode:** B
- **target:** CLAUDE.md
- **complexity:** hard
- **executor:** sonnet
- **parallel_group:** 2
- **est_tokens:** 2400
- **est_cost_usd:** 0.036
- **verifier:** test $(wc -l < CLAUDE.md) -le 200 && python3 -m renmark.lint 2>&1 | tail -1
- **serves:** REQ-5
- **spec:**
  Rewrite the repo-root CLAUDE.md to ≤200 lines, matching the now-terse template
  (Task 1, committed). CRITICAL byte-identity: for every `BEGIN:name`…`END:name`
  block, copy the template's terse block content VERBATIM (read
  plugin/templates/CLAUDE.md.template and reproduce each block byte-for-byte,
  including the `## Heading`) — the live file's blocks must equal the template's
  so `merge_rule_blocks` (missing-only) and the audit template-integrity check
  see no drift. Author ONLY the non-block, project-specific sections yourself
  (the "What this project is" description, project-at-a-glance → keep stack
  one-liner + project-map pointer, Tooling/File-conventions/Executor-prefs/
  Code/Testing → same memory-pointer treatment as the template). Keep this
  repo's real project description (don't replace with the template placeholder).
  Mirror-pair note: the same terse rule prose lands in AGENTS.md (Task 4) — keep
  shared wording identical. Run the verifier before returning.

### Task 3: terse-rewrite the AGENTS template (prose mirror)
- **mode:** B
- **target:** plugin/templates/AGENTS.md.template
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 2
- **est_tokens:** 900
- **est_cost_usd:** 0.033
- **verifier:** test $(wc -l < plugin/templates/AGENTS.md.template) -le 200 && grep -qi 'codex' plugin/templates/AGENTS.md.template
- **serves:** REQ-5
- **spec:**
  AGENTS.md.template has NO `BEGIN:` markers — it's plain-prose mirror of the
  same rules. Rewrite it so its rule prose matches the terse wording Task 1 gave
  the CLAUDE template's blocks (same rules, same brevity), and apply the same
  non-block memory-pointer compression. It's already 113 lines; the goal is
  consistency with the terse CLAUDE template, not just length. Preserve the
  sync-note (CLAUDE↔AGENTS parallel rule set), `{{PROJECT_NAME}}`/`{{DATE}}`
  placeholders, and frontmatter. Do not add `BEGIN:` markers (AGENTS is
  intentionally marker-free — merge_rule_blocks reports it as 0 blocks).

### Task 4: rewrite this repo's AGENTS.md to match
- **mode:** B
- **target:** AGENTS.md
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 3
- **est_tokens:** 900
- **est_cost_usd:** 0.033
- **verifier:** test $(wc -l < AGENTS.md) -le 200 && grep -qi 'codex' AGENTS.md
- **serves:** REQ-5
- **spec:**
  Rewrite repo-root AGENTS.md to ≤200 lines, mirroring the terse AGENTS template
  (Task 3, committed) and keeping shared rule prose byte-identical with the terse
  CLAUDE.md (Task 2) per the sync-note discipline. Keep this repo's real project
  specifics (not the template placeholder). Same memory-pointer compression for
  non-rule sections. Run the verifier before returning.

## Cost preview

| # | Task | Executor | est_tokens | est cost |
|---|---|---|---|---|
| 1 | CLAUDE template (authoritative) | sonnet | 2600 | $0.038 |
| 2 | CLAUDE.md (match template) | sonnet | 2400 | $0.036 |
| 3 | AGENTS template (prose mirror) | sonnet | 900 | $0.033 |
| 4 | AGENTS.md (match) | sonnet | 900 | $0.033 |

Haiku/sonnet costs include the ~10k-token Agent overhead per task (honest accounting).
**Total: ~$0.14 · ~47k tokens incl. overhead · 4 tasks (wave 1: task 1 → wave 2: tasks 2,3 parallel → wave 3: task 4). Byte-identity forces template-before-live ordering.**
