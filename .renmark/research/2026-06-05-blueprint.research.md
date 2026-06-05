---
artifact_type: research
schema_version: 1
created_at: 2026-06-05T18:41:08+00:00
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

# Research — prototype/schematic pipeline step (`/renmark:blueprint`)

## Q1 — Marker-based generated-block injection (the hybrid update model)

The "regenerate machine-owned blocks, preserve human prose" pattern is well-established prior art:

- **markdown-magic** (DavidWells/markdown-magic) — formats/regenerates markdown content between HTML-comment marker blocks. Comments are invisible in rendered HTML. Exactly the `<!-- RENMARK:GENERATED:SCHEMATIC:START -->` / `:END -->` model the user specified.
- **embedme** (zakhenry/embedme) — narrower: embeds external code snippets into fenced blocks keyed by a leading comment.

**Build-vs-reuse call: BUILD (trivially).** Neither is a Python lib and both are general-purpose Node tooling. The mechanic — find `START`/`END` marker pair, replace the span between them, leave everything else byte-identical — is ~30 lines of Python regex/splice. No dependency. Reuse the *pattern* (HTML-comment fences, idempotent re-run, invisible-in-render), not the package.

Sources:
- https://github.com/davidwells/markdown-magic
- https://github.com/zakhenry/embedme

## Q2 — Living architecture diagrams (the schematic half)

- **Diagrams-as-code / docs-as-code**: Mermaid in markdown, versioned in git, regenerated as code evolves, reviewed via normal diff in the same PR. This is precisely renmark's model — validates SCHEMATIC.md + Mermaid.
- **C4 model** is the idiomatic abstraction ladder: Context → Container → Component → Code. Consensus from multiple sources: **Context + Container levels are sufficient for most teams**; only add Component/Code when they earn their keep. Mermaid supports C4 natively (`C4Context`, `C4Container`) but plain `flowchart`/`graph` is more portable and renders everywhere.
- **Known maintenance risk**: keeping multiple C4 levels *consistent with each other* over time is the hard part. Direct implication for our design: the generated schematic should default to **one or two levels (Container-ish)**, not a full four-level C4 set — fewer views to keep in sync, less drift surface. Coding agents (Claude Code) parsing a repo to emit Mermaid is now an established workflow, so auto-generation from the project map is realistic.

Sources:
- https://www.tiagovalverde.com/posts/diagram-as-code-with-mermaid
- https://www.docsie.io/blog/articles/technical-diagrams-docs-as-code-2026/
- https://mermaideditor.com/blog/c4-model-diagrams-with-mermaid
- https://medium.com/@prabhu.ajay/code-designs-that-stay-in-sync-why-mermaid-coding-agents-work-so-well-4fea5d3869c4

## Implications for the spec
1. Hybrid marker update = build in-house, ~30 LOC splice helper; reuse markdown-magic's comment-fence pattern.
2. Schematic = Mermaid `flowchart`/`graph` (portable) at Container-ish granularity; do NOT auto-emit full 4-level C4 (sync cost).
3. Diagram content can be derived from the existing `.renmark/memory/project-map.md` rather than re-scanning the repo from scratch — reuse renmark's own map artifact as the source.

## Summary

- marker injection: reuse markdown-magic PATTERN, build ~30-LOC Python splice (no dep)
- schematic: Mermaid flowchart/graph at Container granularity — NOT full 4-level C4 (sync cost)
- diagram source: derive from existing .renmark/memory/project-map.md, don't rescan repo
- docs-as-code validates living SCHEMATIC.md in git, regenerated + diff-reviewed in PR
- stack confirmed idiomatic: yes — Python + markdown, no new deps
