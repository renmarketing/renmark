---
artifact_type: research
schema_version: 1
created_at: 2026-06-26T13:54:40+00:00
source_sha: e06da633f9bd2585fc7d13e960cb83539a947c5c
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


# P10 Headless-Session Detection Research

**Research question:** What concrete signals can a renmark skill observe to detect
non-interactive / headless execution in Claude Code, so the skill can suppress
AskUserQuestion calls and adjust its gate behavior?

---

## 1. `claude -p` / `--print` headless mode — env-var signals

### What `-p` does
`-p` / `--print` runs Claude Code as a single-turn non-interactive "Agent SDK" invocation.
It prints stdout and exits. All interactive UI elements are absent (no REPL, no
TUI, no permission dialogs unless `--permission-prompt-tool` is configured).

### Documented env vars set BY Claude Code itself

From the official env-vars reference (code.claude.com/docs/en/env-vars, fetched 2026-06-26):

| Variable | Value | Set by | Scope |
|---|---|---|---|
| `CLAUDECODE` | `1` | Claude Code runtime | ALL subprocesses: Bash, PowerShell, tmux, hooks, status-line cmds, stdio MCP servers. IDE extensions also set it in integrated terminals. |
| `CLAUDE_CODE_CHILD_SESSION` | `1` | Claude Code runtime (v2.1.172+) | Subprocesses via Bash/PowerShell/Monitor tools, hook commands, status-line commands. **NOT** set for stdio MCP servers. Distinguishes nested interactive sessions from top-level claude. |

### Key negative finding
There is **no documented `CLAUDE_CODE_IS_HEADLESS`, `IS_PRINT_MODE`, or analogous
single variable** that Claude Code sets to indicate the session was launched with `-p`.

### Variables referenced in gist but NOT in official docs
The mculp gist (v2.1.104) mentions `CLAUDE_CODE_SIMPLE`, `CLAUDE_CODE_ENTRYPOINT`,
`CLAUDE_CODE_REMOTE`, and `CLAUDE_CODE_COORDINATOR_MODE` but the official env-vars
reference page does not define them. The CLI reference confirms `--bare` sets
`CLAUDE_CODE_SIMPLE` (with a cross-link to env-vars), but the env-vars page itself
omits the entry. These appear to be internal variables not intended as stable API.

### What CAN be used from a hook or subprocess
- `CLAUDECODE=1` → "I am running inside any Claude Code subprocess" (reliable, documented).
- `CLAUDE_CODE_CHILD_SESSION=1` → "I am a subprocess started by an already-running
  Claude Code session" (nested/background — not a direct headless signal).
- Standard Unix `CI` → widely set in CI environments (GitHub Actions, GitLab CI,
  CircleCI, etc.) but NOT set by Claude Code itself; user/CI pipeline must set it.
- `TERM=dumb` or absence of a TTY (`[ -t 0 ]` etc.) → traditional Unix TTY detection,
  but Claude Code does not document relying on this.

### `--bare` mode
`--bare` sets `CLAUDE_CODE_SIMPLE` (per CLI reference). It is designed for scripted
calls where reproducibility matters. The headless page notes it will become the
default for `-p` in a future release. If renmark can require callers to use `--bare`,
that variable becomes detectable — but it is undocumented in the env-vars reference
so should be treated as unstable.

---

## 2. AskUserQuestion availability — subagents and `-p` mode

### Confirmed behavior (as of v2.1.76, issue #34592, closed 2026-03)

AskUserQuestion is **completely absent** from sub-agent environments. This was
confirmed via tool enumeration in multiple sub-agent contexts:

| Context | AskUserQuestion present? |
|---|---|
| Main interactive session | Yes |
| Agent tool dispatch (foreground) | No |
| Skill with `context: fork` | No |
| ToolSearch inside sub-agent | Returns "no matching deferred tools found" |

The official docs stated foreground subagents pass through AskUserQuestion, but
this was contradicted by actual behavior and confirmed as a known issue. GitHub
issue #34592 was **closed as "not planned"** — meaning the absence is intentional,
not a bug to be fixed.

### AskUserQuestion in `-p` / print mode (main session, not subagent)
The headless/CLI docs do NOT explicitly state whether AskUserQuestion is available
in the main `-p` session (as opposed to a subagent). The `-p` docs say "built-in
commands that open an interactive dialog, such as /login, are not available in -p
mode." AskUserQuestion is similar: it pauses for user input. In a headless pipeline
no human is watching stdout to respond, so even if the tool were technically available,
calling it would stall the run indefinitely. No documentation explicitly says the
tool is removed in `-p` mode; the practical effect is equivalent to unavailable.

### Reliability as a detection tier
- **Absence of AskUserQuestion from the tool list** → reliable signal that you are
  in a subagent context. Can be tested via ToolSearch at skill startup.
- **Absence of AskUserQuestion in `-p` main session** → NOT confirmed by docs as
  guaranteed; do not rely on this alone.

---

## 3. Subagent context vs main interactive loop — observable differences

From official docs (sub-agents page, SDK overview, CLI reference):

| Signal | Main session | Spawned subagent | `-p` session |
|---|---|---|---|
| `AskUserQuestion` in tool list | Present | Absent (confirmed) | Unknown/effectively absent |
| `CLAUDECODE` env var | Available in subprocesses | Available in subprocesses | Available in subprocesses |
| `CLAUDE_CODE_CHILD_SESSION` | Not set | Set in Bash/hook subprocesses | Not set directly |
| Can spawn sub-subagents (Agent tool) | Yes | Unclear (issue #19077) | Yes |
| Interactive UI (TUI, prompts) | Yes | No | No |
| `--max-turns` applies | No | Yes (per-Task limit) | Yes |
| Output goes to parent orchestrator | No | Yes | No (goes to stdout) |

### What a skill markdown file can observe
Skills run as model instructions in the model context — they cannot directly read
env vars. Reliable detection methods available to the model:

1. **ToolSearch for AskUserQuestion**: if the result is empty → confirmed subagent.
2. **System prompt inspection**: Claude Code injects different system prompt sections
   in `-p` vs interactive mode (the `--exclude-dynamic-system-prompt-sections` flag
   exists specifically because this differs per invocation).
3. **Prompt content hints**: callers can pass explicit flags (e.g.
   `RENMARK_HEADLESS=true` in the prompt or `--append-system-prompt`).
4. **Bash to read env var**: a skill can emit a Bash call `echo $CLAUDECODE` to
   test subprocess context, or `echo ${CLAUDE_CODE_CHILD_SESSION:-unset}` to detect
   nested session. This is the only way to read env vars from within a skill.

---

## 4. Plugin/skill convention for headless vs interactive

No official convention was found in the docs for plugins/skills to detect headless
mode. The SDK documentation recommends `--bare` for scripted calls but provides no
model-observable flag. The implicit convention from the docs:

- **For CI/scripted callers**: use `--bare -p --dangerously-skip-permissions` (or a
  permission mode) and set `CI=true` in the environment.
- **For subagent-aware skills**: check AskUserQuestion availability as the headless
  gate signal.
- **No official plugin convention** for a skill to auto-detect and adapt behavior
  — renmark would need to define its own.

---

## 5. Recommended detection tiers for renmark P10 headless contract

Based on evidence:

| Tier | Signal | Reliability | Notes |
|---|---|---|---|
| T1 | ToolSearch("select:AskUserQuestion") empty | HIGH | Subagent confirmed; docs closed "not planned" → stable negative |
| T2 | `CI=true` env var (Bash probe) | MEDIUM | Standard but must be set by pipeline; not set by Claude Code |
| T3 | `CLAUDE_CODE_CHILD_SESSION=1` (Bash probe) | MEDIUM | v2.1.172+ only; signals nested not headless-at-top-level |
| T4 | `CLAUDE_CODE_SIMPLE=1` (Bash probe) | LOW | Undocumented in official env-vars reference; --bare sets it |
| T5 | Explicit caller flag in prompt/system prompt | HIGH | Most reliable overall; requires caller discipline |

**Recommended design for P10:** combine T1 (AskUserQuestion probe) + T5 (explicit
caller flag in `--append-system-prompt` or prompt prefix). T1 covers the subagent
case automatically; T5 covers the `-p` main-session case where T1 may not trigger.

---

## Sources

- https://code.claude.com/docs/en/cli-reference (fetched 2026-06-26)
- https://code.claude.com/docs/en/env-vars (fetched 2026-06-26)
- https://code.claude.com/docs/en/headless (fetched 2026-06-26)
- https://github.com/anthropics/claude-code/issues/34592 (AskUserQuestion in subagents, closed "not planned")
- https://gist.github.com/mculp/e6a573f2a45ef7dbbf30f6a8574c7351 (env var gist v2.1.104)
- https://github.com/anthropics/claude-code/issues/12890 (AskUserQuestion subagent bug)
- https://github.com/anthropics/claude-code/issues/18721 (AskUserQuestion docs gap)

## Summary

- Env-var signal: CLAUDECODE=1 is set in all subprocesses (documented, stable); no CLAUDE_CODE_IS_HEADLESS or IS_PRINT_MODE exists.
- CLAUDE_CODE_SIMPLE set by --bare (undocumented in env-vars ref, unstable); CLAUDE_CODE_CHILD_SESSION=1 signals nested session (v2.1.172+, not a direct -p signal).
- AskUserQuestion ABSENT in all subagent contexts (confirmed, closed 'not planned' #34592); reliable T1 subagent detection signal via ToolSearch.
- AskUserQuestion in -p main session: no explicit doc removal, but effectively unavailable (stalls); do not rely on presence as interactive confirmation.
- Recommended P10 tiers: T1=AskUserQuestion probe (subagent), T5=explicit caller flag in system-prompt (covers -p main session); T2-T4 are supplemental Bash probes.
