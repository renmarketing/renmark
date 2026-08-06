---
artifact_type: rethink-external-benchmark
schema_version: 1
created_at: 2026-08-06T00:00:00Z
source_sha: da164692c2ebb9f5094497cfc9ddca9e5217b169
related_plan: cross-host-native-tool-leverage
generator: sonnet
stage_status: complete
dependency_refs: []
---

# External Benchmark — Cross-Host Native-Tool Leverage

Stage 4 of `/renmark:rethink`. Research via WebSearch (live, dated Aug 2026). All findings from search-result snippets, not fetched full pages — flagged as such below.

## 1. Claude Code native surface

- **Task tracking**: `TodoWrite` is deprecated/removed. As of TypeScript Agent SDK 0.3.142 / Claude Code v2.1.142, and Python SDK v0.2.82 (2026-05-15), sessions use structured `TaskCreate` / `TaskUpdate` / `TaskGet` / `TaskList` tools. Introduced as the "Tasks" primitive in Claude Code v2.1.16 (2026-01-22). Tasks persist across context compaction and can be claimed/completed by subagents.
  SOURCE: code.claude.com/docs/en/agent-sdk/todo-tracking; clauder-navi.com TodoWrite deprecation article; claudelog.com "What are Tasks". ACCESS DATE: 2026-08-06. **verified fact** (multiple corroborating sources, version-numbered).
  **recommendation**: renmark's REQ-31 native-task-tracking contract (`plugin/skills/.shared/task-tracking.md`) should map onto `TaskCreate/TaskUpdate/TaskGet/TaskList`, not a hand-rolled equivalent — confirm current plugin code isn't still targeting a `TodoWrite`-era shape.

- **Git worktree tools**: `EnterWorktree` / `ExitWorktree` are native Claude Code tools (introduced v2.1.72). `EnterWorktree` creates/switches into an isolated worktree under `.claude/worktrees/`; can chain to another worktree without exiting first. As of v2.1.206, `EnterWorktree` prompts for confirmation before entering a worktree outside `.claude/worktrees/`. Resuming an Agent-SDK session inside a worktree returns you to that worktree.
  SOURCE: code.claude.com/docs/en/worktrees; github.com/anthropics/claude-code issue #29436 (ExitWorktree request/added). ACCESS DATE: 2026-08-06. **verified fact**.
  **inference**: renmark's own worktree management (`renmark/worktree.py`, `EnterWorktree`/`ExitWorktree` already appear as deferred tools in this very session) is likely already riding the native primitive rather than shelling out to `git worktree` — worth confirming which mode is active.

- **Structured output for subagent calls**: `query()` accepts `outputFormat` (TS) / `output_format` (Python) with a JSON Schema; Claude Code internally wraps it as a synthetic `StructuredOutput` tool call and validates + retries against the schema, erroring out if retries are exhausted.
  SOURCE: code.claude.com/docs/en/agent-sdk/structured-outputs. ACCESS DATE: 2026-08-06. **verified fact**.
  **Gap** (open GitHub issue #20625, still open per search snippet): subagents declared in Markdown/`settings.json` **cannot yet declare their own structured-output contract** — only the top-level `query()` call can. Multi-agent pipelines wanting typed per-role payloads (planner/critic/analyzer) still need an orchestration layer around the CLI to enforce shape.
  SOURCE: github.com/anthropics/claude-code issue #20625. ACCESS DATE: 2026-08-06. **verified fact** (issue exists; unclear if resolved — search snippet doesn't confirm current status beyond "there's currently a feature request").
  **recommendation**: renmark's "artifacts carry provenance/freshness metadata" and "artifact existence != correctness" rules (`completion_state`, `confidence`, etc.) are effectively hand-rolling schema enforcement per-subagent because native support for per-subagent schemas doesn't exist yet. This is validated, not obsolete — keep it.

- **Multi-agent fan-out / orchestration**: "Dynamic Workflows" (per one blog source, June 2026) lets a lead agent plan and fan out "tens to hundreds" of parallel subagents in one session. Subagents are isolated Claude instances with their own context window, tool permissions, and model.
  SOURCE: totalum.app "Claude Code subagents: 2026 production playbook"; shipyard.build blog. ACCESS DATE: 2026-08-06. **inference-leaning** — these are blog/marketing sources, not code.claude.com docs; treat the "Dynamic Workflows" claim as **unverified** until confirmed against official docs (flagged in Unknowns).

- **Scheduled/cron agent execution**: not found in official docs via this search pass. renmark's own `schedule` skill (loaded in this session's skill list) and Claude's "Managed Agents" (one blog mentions "a scheduler, dreaming pass, rubric-based grading" sitting under Agent SDK in 2026) suggest scheduling exists as a *product* feature (claude.ai scheduled agents) but no evidence found that it's a *plugin-invokable primitive* inside Claude Code CLI itself.
  SOURCE: totalum.app Agent SDK guide. ACCESS DATE: 2026-08-06. **inference** — insufficiently sourced, flagged in Unknowns.

## 2. Codex CLI native surface

- **Plugin maturity**: As of Aug 5, 2026 the latest release is `rust-v0.146.1`. Plugin system has matured substantially in 2026: remote plugins enabled by default, npm marketplace sources, bundled-hooks visibility, plugin sharing/discoverability. Enterprise admins can allowlist plugin suggestions; install/uninstall state syncs remotely for fleets.
  SOURCE: releasebot.io/updates/openai/codex; havoptic.com codex release tracker. ACCESS DATE: 2026-08-06. **verified fact** (dated, version-numbered).
  **recommendation**: this is a materially different (and newer-feeling) plugin surface than what renmark's own dogfooding hit — worth a fresh compatibility check against `codex plugin list --json` rather than assuming the earlier 0.133.0 gap still holds at 0.146.1.

- **Multi-agent orchestration**: OpenAI shipped a standalone "Codex app" (Feb 2, 2026) that centralizes/orchestrates multiple coding agents. In March 2026 Codex added "first-class plugins, path-based sub-agents, and structured messaging," transforming it into "a workflow layer for multi-agent software delivery." Codex CLI supports parallel fan-out (one source: "up to 6 threads by default").
  SOURCE: intuitionlabs.ai; aibuilderhub.dev "Codex Plugins and Multi-Agent Workflows"; firecrawl.dev "Multi-Agent Orchestration With Codex". ACCESS DATE: 2026-08-06. **inference-leaning** — blog/aggregator sources, not openai.com/docs directly; treat specifics (thread counts, exact plugin API shape) as unverified pending direct doc fetch.

- **Breaking-change cadence**: confirmed churn — `codex login --api-key` deprecated in favor of `--with-api-key` (stdin-based); `mcp` subcommand replaced by `mcp-server` starting 0.43.0-alpha.5, breaking upgraders; `--profile` became the primary profile selector (~May 2026) with legacy profile configs rejected pending migration.
  SOURCE: smartscope.blog Codex CLI 0.45/0.46 guide; gradually.ai changelog; hexdocs.pm codex_sdk changelog. ACCESS DATE: 2026-08-06. **verified fact** — this directly corroborates this session's own observation that `codex plugin list --json` isn't supported on 0.133.0: Codex CLI's plugin/CLI surface has a demonstrated pattern of subcommand renames and flag replacements between minor/alpha versions, not just missing features on old versions.

- **Structured output / task tracking**: no official Codex-CLI-native equivalent to Claude's `TaskCreate/TaskUpdate` or JSON-schema `outputFormat` found in this search pass. Codex's internal architecture reportedly separates by ownership boundary ("cli_subprocess_core owns subprocess-backed lifecycle, codex_sdk keeps app-server/MCP/realtime/voice semantics") per one Phase-4 release-note summary, but no task-tracking-equivalent primitive surfaced.
  SOURCE: (Phase 4 boundary note found via generic search, exact origin unclear — likely a Codex SDK changelog). ACCESS DATE: 2026-08-06. **inference**, flagged in Unknowns for direct verification.

## 3. Comparable cross-host patterns

- **codex-plugin-cc**: described by one source as "OpenAI's official cross-provider bridge for Claude Code" — i.e., a Codex-authored plugin that runs *inside* Claude Code, delegating specific work (reviews, investigations, fixes) to Codex while Claude retains orchestration/conversation/context. This matches renmark's own `codex:` plugin pattern (`renmark-execute` subprocess dispatch, `executor: codex` rule already in this project's CLAUDE.md) almost exactly.
  SOURCE: codex.danielvaughan.com "codex-plugin-cc: OpenAI's Official Cross-Provider Bridge for Claude Code" (2026-04-12). ACCESS DATE: 2026-08-06. **verified fact** (dated, specific) but from a third-party blog, not openai.com — treat as **medium confidence**, not primary-source-verified.
  **recommendation**: renmark already implements the pattern this article describes as "official" (Claude orchestrates, Codex executes bounded work via subprocess, inherits local auth/rate-limits). This is direct external validation that renmark's existing `executor: codex` dispatch design is aligned with the wider ecosystem's converged pattern — not a gap to close, but worth citing as validation.

- **Bidirectional MCP**: both Claude Code and Codex CLI reportedly now act as MCP *servers* (not just clients), exposing their own capabilities to each other over the same JSON-RPC/stdio channel — a general basis for cross-tool orchestration beyond the CLI-subprocess pattern renmark currently uses.
  SOURCE: codex.danielvaughan.com "Claude Code ↔ Codex CLI: Bidirectional MCP Integration" (2026-03-26). ACCESS DATE: 2026-08-06. **inference** (single third-party source, not cross-checked against official docs) — flagged in Unknowns as a possible future migration path off subprocess dispatch.

- **`orch` (kninetimmy/orch)**: a GitHub project explicitly described as a "cross-host development orchestrator for Codex CLI and Claude Code CLI" — i.e., a third party independently built the same category of tool as renmark (cross-host abstraction over both CLIs). No adoption/maturity signal found beyond the repo existing.
  SOURCE: github.com/kninetimmy/orch. ACCESS DATE: 2026-08-06. **verified fact** (repo exists) / **inference** on relevance (unknown maturity, unknown whether it's a serious competitor or a toy).

## 4. Migration gotchas

- **API churn is real and corroborated on both hosts**, not just this session's dogfooding artifact:
  - Claude Code: `TodoWrite` → `TaskCreate/TaskUpdate/TaskGet/TaskList` was a hard removal (not a deprecation-with-shim) as of Python SDK 0.2.82 (2026-05-15) — any renmark code still calling/emulating `TodoWrite` shape would silently mismatch the current native tool.
  - Codex CLI: `mcp` → `mcp-server` subcommand rename broke upgraders at 0.43.0-alpha.5; `--profile` flag/config format changed ~May 2026 with old configs rejected; this session independently found `codex plugin list --json` unsupported on 0.133.0 (current per this search: 0.146.1) — consistent with a CLI whose plugin/CLI-flag surface renames/removes rather than only additively extends.
  SOURCE: multiple, listed above. ACCESS DATE: 2026-08-06. **verified fact**.
  **recommendation**: renmark's existing "never assume a native primitive is stable across a Codex minor version" instinct (implied by this session's own workaround) is correct and should be made explicit as a written guard: pin/detect CLI version before relying on any Codex plugin subcommand shape, and re-check Claude Code's Task-tool names against the SDK version actually installed rather than hardcoding tool names from memory.
- **Structured-output gap is asymmetric**: Claude Code has schema enforcement at the top-level `query()` call but explicitly not yet at the individual-subagent level (open issue #20625); Codex CLI shows no evidence of an equivalent primitive at all. renmark's own `completion_state`/`confidence`/`validation_status` contract on every subagent output is therefore not redundant scaffolding — it's covering a real, currently-unfilled gap on both hosts, at the level (per-subagent) neither host guarantees natively.
- **Third-party "official" claims need discounting**: several strong claims here (Dynamic Workflows fan-out size, Codex's 6-thread default, "codex-plugin-cc" being OpenAI's "official" bridge) come from blog aggregators, not code.claude.com or openai.com/docs directly. Treat as directional, not load-bearing, until confirmed by a direct WebFetch of the primary doc.

## Unknowns (require a bounded spike, not further open-web search)

1. Whether "Dynamic Workflows" (tens-to-hundreds parallel subagent fan-out) is an actual shipped Claude Code/Agent-SDK feature or marketing framing of existing subagent parallelism — needs a direct fetch of code.claude.com/docs release notes.
2. Whether Codex CLI has *any* native task-tracking or structured-output-enforcement primitive comparable to Claude's Task tools / `outputFormat` — this search pass found none, but coverage was thin; needs a direct fetch of the Codex CLI / Codex SDK official docs (not aggregator blogs).
3. Current status of Claude Code issue #20625 (per-subagent structured-output contracts) — open, in progress, or shipped since the issue was filed.
4. Whether "bidirectional MCP" (both CLIs as MCP servers to each other) is real, shipped, and stable enough to be a viable alternative to renmark's current subprocess-dispatch pattern for `executor: codex` — single third-party source only.
5. Exact current behavior of `codex plugin list --json` (or equivalent) on Codex CLI 0.146.1 — this session confirmed a gap at 0.133.0; unclear if since fixed. A local `codex --version` + `codex plugin list --json` probe (deterministic, no web search) would resolve this in under a minute and should be run before trusting any doc claim about current Codex plugin CLI shape.
