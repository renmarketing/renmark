---
artifact_type: research
schema_version: 1
created_at: 2026-06-14T17:35:44+00:00
source_sha: e14ab253cd12d878df0065c60db8cd6d40ddacaf
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

# REQ-14 Scheduling & Access Model Research
## Claude Code Scheduling, Headless Execution, and Permission Model

**Research date:** 2026-06-14
**Context:** Designing REQ-14 "proposer lane" — a scheduled, read-only renmark command
**Sources:** docs.code.claude.com (authoritative)

---

## 1. Scheduling Primitives — Local Repo Access Analysis

### Three scheduling options (official comparison matrix from docs)

| Option | Runs on | Local files | Requires machine on | Requires open session |
|--------|---------|-------------|--------------------|-----------------------|
| `/loop` (in-session) | Your machine | Yes — full working tree | Yes | Yes |
| Desktop scheduled task | Your machine | Yes — full working tree | Yes (app open) | No |
| Cloud Routine (`/schedule`) | Anthropic cloud | **NO — fresh clone** | No | No |

**Critical finding for REQ-14: Cloud Routines do NOT have access to the local `.renmark/` directory.** They clone the repo from GitHub. Any artifact written by a cloud routine goes into a `claude/`-prefixed branch pushed to GitHub — not to the local `.renmark/` tree. This **rules out cloud routines** for REQ-14 unless the repo is public/accessible and artifact output is acceptable in a git branch rather than local disk.

**Local repo access requires:** `/loop` (in-session) OR Desktop scheduled tasks (app must be open). Both run from the actual working directory including uncommitted state.

Sources:
- https://code.claude.com/docs/en/scheduled-tasks
- https://code.claude.com/docs/en/desktop-scheduled-tasks
- https://code.claude.com/docs/en/routines

---

## 2. Slash Command / Plugin Skill Invocation in Non-Interactive (`-p`) Mode

**Finding (authoritative from headless docs):**

> "User-invoked skills and custom commands work in `-p` mode: include `/skill-name` in the prompt string and Claude Code expands it before running. Built-in commands that open an interactive dialog, such as `/config` and `/login`, are not available in `-p` mode."

**Concrete invocation pattern:**

```bash
claude -p "/renmark:propose" \
  --permission-mode dontAsk \
  --tools "Read,Bash,Grep,Glob" \
  --allowedTools "Read,Bash(git log *),Bash(git diff *),Bash(git status *),Grep,Glob" \
  --cwd /home/renmark/projects/ai-system
```

**Caveats on slash commands in `-p` mode:**
- Skills that invoke interactive dialogs (e.g. `/config`) do not work headlessly — skills that just read/write files and emit text are fine
- `--bare` mode SKIPS plugin/skill discovery — do NOT use `--bare` for `/renmark:propose` invocations since the plugin must load
- Plugin must be loaded: either installed (enabledPlugins) or passed via `--plugin-dir`

Sources:
- https://code.claude.com/docs/en/headless (headless docs)
- https://code.claude.com/docs/en/cli-reference

---

## 3. Permission/Access Model — Read-Only Enforcement

### Available mechanisms, ranked by enforcement strength

#### A. `--tools` flag (STRONGEST — capability removal)

```bash
claude -p "/renmark:propose" --tools "Read,Bash,Grep,Glob"
```

> "Restrict which built-in tools Claude can use. Use `""` to disable all, `"default"` for all, or tool names like `"Bash,Edit,Read"`. MCP tools are not affected."

This removes Edit and Write from the model's context entirely. Claude literally cannot see or call them. This is a hard capability boundary, not a permission boundary. **For MCP tools, add `--disallowedTools "mcp__*"` to also strip those.**

#### B. `--disallowedTools` with bare tool names (STRONG — context removal)

```bash
claude -p "/renmark:propose" --disallowedTools "Edit,Write,mcp__*"
```

> "A bare tool name removes the matching tools from the model's context: `Edit` removes Edit, `*` removes every tool, `mcp__*` removes every MCP tool."

Bare-name deny rules strip the tool definition before the permission evaluation loop, so the model never receives the tool schema. Cannot be overridden by allow rules.

#### C. `--permission-mode dontAsk` (STRONG — deny-on-prompt)

```bash
claude -p "/renmark:propose" --permission-mode dontAsk
```

> "Converts any permission prompt into a denial. Tools pre-approved by `allowed_tools`, `settings.json` allow rules, or a hook run as normal. Everything else is denied without calling `canUseTool`."

Paired with `--allowedTools "Read,Bash(git log *),Bash(git diff *),Bash(git status *),Grep,Glob"`, this creates a fixed, explicit tool surface. Anything not explicitly allowed is denied.

#### D. `--permission-mode plan` (MODERATE — prompts on writes, not denied)

> "Claude explores and produces a plan without editing your source files. File edits are NEVER auto-approved in plan mode, even when an allow rule matches. They prompt through your `canUseTool` callback instead."

In headless `-p` mode with no `canUseTool` callback, a write attempt would result in a permission prompt that can't be answered — but this stalls rather than hard-denies. **Do not rely on `plan` mode for guaranteed read-only in headless runs.** In headless non-interactive mode, repeated blocks abort the session; but `plan` mode is described as prompting, not denying.

#### E. Hooks via `PreToolUse` / `PermissionRequest` (FINE-GRAINED — but complex)

Hooks run BEFORE deny/allow rules. A `PreToolUse` hook can deny a tool call outright. This is the most configurable mechanism but also the most complex to set up and maintain.

### STRONGEST COMBINATION for REQ-14 read-only guarantee:

```bash
claude -p "/renmark:propose" \
  --tools "Read,Bash,Grep,Glob" \           # strips Edit/Write from context entirely
  --disallowedTools "Edit,Write,mcp__*" \   # belt-and-suspenders context removal
  --allowedTools "Read,Bash(git log *),Bash(git diff *),Bash(git status *),Bash(git show *),Grep,Glob" \
  --permission-mode dontAsk \               # deny-on-prompt for anything else
  --append-system-prompt "You are in read-only mode. You MUST NOT edit, write, commit, or push any files. You may only read, inspect, and report."
```

**Key insight from docs warning:**
> "`allowed_tools` does NOT constrain `bypassPermissions`. Setting `allowed_tools=["Read"]` alongside `permission_mode="bypassPermissions"` still approves every tool, including Bash, Write, and Edit."

So `bypassPermissions` MUST NOT be used for REQ-14. `dontAsk` is the correct mode.

**Deny rules vs allow rules precedence:**
- Deny rules (bare name) → strips tool from model context (step 2 in evaluation)
- Allow rules → evaluated at step 5, after deny
- `dontAsk` → evaluated at step 6 (canUseTool skipped, denied instead)

Protected paths (`.git`, `.gitconfig`, shell rc files, `.mcp.json`, etc.) are NEVER auto-approved in any mode except `bypassPermissions`. The renmark dirs `.renmark/` are NOT in the protected list, so write access to `.renmark/` must be controlled by the flags above.

Sources:
- https://code.claude.com/docs/en/agent-sdk/permissions
- https://code.claude.com/docs/en/permission-modes
- https://code.claude.com/docs/en/cli-reference

---

## 4. Headless Caveats: Auth, MCP, Working Directory

### Authentication in cron/WSL

**Without interactive browser, these options work:**

1. **`CLAUDE_CODE_OAUTH_TOKEN`** (recommended for cron/WSL subscription users):
   ```bash
   # One-time setup (interactive):
   claude setup-token
   # Store output as CLAUDE_CODE_OAUTH_TOKEN in ~/.profile or cron env
   export CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat01-...
   ```
   - Requires Pro/Max/Team/Enterprise subscription
   - One-year expiry
   - **CAVEAT:** Does NOT work with `--bare` mode

2. **`ANTHROPIC_API_KEY`** (console/API key auth):
   ```bash
   export ANTHROPIC_API_KEY=sk-ant-api03-...
   ```
   - Works in `--bare` mode and all non-bare modes
   - Note: API key auth does NOT enable cloud Routines (`/schedule` requires claude.ai subscription login)

3. **Linux credentials file**: `~/.claude/.credentials.json` (mode 0600) — stored by `/login`, read automatically. Works as-is if `/login` was previously run interactively in WSL.

**WSL2 note:** Interactive login in WSL2 prints a login URL for manual browser navigation. After that, credentials persist in `~/.claude/.credentials.json`. For cron without re-login, use `CLAUDE_CODE_OAUTH_TOKEN` or `ANTHROPIC_API_KEY`.

### MCP availability in headless runs

- **`-p` (non-bare) mode:** reads `.mcp.json` and MCP configs from the project and `~/.claude/` — MCP servers load as in interactive mode
- **`--bare` mode:** MCP servers are skipped unless explicitly passed via `--mcp-config`
- **For REQ-14 (needs git read, no MCP):** non-bare is appropriate (plugin must load), MCP should be explicitly stripped: `--disallowedTools "mcp__*"` and `--strict-mcp-config` without `--mcp-config` (no MCP servers load)

### Working directory

`claude -p` runs from the shell's `cwd` at invocation time. For OS cron, must explicitly set `cwd`:

```bash
# In crontab:
0 9 * * * cd /home/renmark/projects/ai-system && claude -p "/renmark:propose" [flags]
# OR use --cwd if available (not documented; use cd instead)
```

For Desktop scheduled tasks: the task creation form requires selecting a working folder — this is set at task creation and used on every run.

### No-`--bare` requirement for plugin skills

The headless docs note:
> "Add `--bare` to reduce startup time by skipping auto-discovery of hooks, skills, plugins, MCP servers, auto memory, and CLAUDE.md."

Since `/renmark:propose` is a plugin skill, `--bare` CANNOT be used — the plugin must load. This means full startup time but correct skill resolution.

---

## 5. REQ-14 Recommended Implementation Strategy

### Best-fit scheduling option for REQ-14: Desktop scheduled task

**Rationale:**
- Cloud Routines = no local `.renmark/` access → disqualified
- `/loop` = requires open session → too fragile for production scheduling
- Desktop scheduled task = local files, no open session required, configurable permission mode per task, minimum 1-minute interval

**Desktop scheduled task setup:**
1. In Desktop app → Routines → New routine → Local
2. Instructions = `/renmark:propose` + read-only constraint text
3. Permission mode selector: set to `dontAsk`
4. Working folder: `/home/renmark/projects/ai-system` (requires Desktop to trust this folder)
5. Schedule: configure desired cadence

**WSL2 caveats for Desktop scheduled tasks:**
- Desktop app runs on Windows; accessing WSL2 filesystem from Windows Desktop app is possible via `\\wsl$\Ubuntu\home\renmark\...` but the tooling behavior (git, Python) may differ from running natively in WSL
- **Safer option for WSL2:** OS cron in WSL2 calling `claude -p` directly — no Desktop app dependency

### Recommended WSL2 cron approach:

```bash
# ~/.claude/.credentials.json must exist from prior /login, OR:
export CLAUDE_CODE_OAUTH_TOKEN=... # set in cron env or ~/.profile

# Add to WSL2 crontab (crontab -e):
0 9 * * 1-5 cd /home/renmark/projects/ai-system &&   claude -p "/renmark:propose"     --tools "Read,Bash,Grep,Glob"     --disallowedTools "Edit,Write,mcp__*"     --allowedTools "Read,Bash(git log *),Bash(git diff *),Bash(git status *),Bash(git show *),Grep,Glob"     --permission-mode dontAsk     --append-system-prompt "Read-only proposer run. Do not edit, commit, or push any files."     >> /home/renmark/projects/ai-system/.renmark/logs/propose-cron.log 2>&1
```

---

## 6. Ambiguities and Missing Context

### Ambiguous: `plan` mode in headless `-p` with no canUseTool callback

The docs say `plan` mode "prompts through canUseTool" for writes. In `-p` mode with no callback, the behavior is described as: "repeated blocks abort the session." It is NOT documented as a guaranteed hard deny — it depends on the prompt/block cycle behavior. **Do not rely on `plan` mode for headless read-only enforcement.** Use `--tools` + `dontAsk` instead.

### Ambiguous: Plugin loading with `--tools` restriction

It is not confirmed whether restricting `--tools "Read,Bash,Grep,Glob"` affects the tool set available to plugin skill invocations internally vs. the model's tool call context. The `--tools` flag is documented as restricting "which built-in tools Claude can use" — likely the model context, not the Python subprocess level. Renmark skills that use `Agent` subagents would inherit the parent's permission mode.

### Missing: WSL2 Desktop scheduled task filesystem mapping behavior

Whether the Desktop app (running on Windows) correctly resolves WSL2 paths and runs WSL2 tools (Python, git, claude CLI) for scheduled tasks is not documented. Testing required.

### Missing: `CLAUDE_CODE_OAUTH_TOKEN` token rotation/expiry handling

The token has a 1-year expiry. No documented auto-refresh in cron context. Must be manually rotated annually.

### Missing: `--plugin-dir` interaction with permission restriction

If the plugin is installed via `enabledPlugins` (the standard install), skills load at session start. If loaded via `--plugin-dir`, it must be passed explicitly in the cron invocation. Docs confirm `--plugin-dir` works in `-p` mode.

---

## Sources

- CLI reference: https://code.claude.com/docs/en/cli-reference
- Headless/programmatic: https://code.claude.com/docs/en/headless
- Permission modes: https://code.claude.com/docs/en/permission-modes
- Agent SDK permissions: https://code.claude.com/docs/en/agent-sdk/permissions
- Scheduled tasks (/loop): https://code.claude.com/docs/en/scheduled-tasks
- Desktop scheduled tasks: https://code.claude.com/docs/en/desktop-scheduled-tasks
- Routines (cloud): https://code.claude.com/docs/en/routines
- Authentication: https://code.claude.com/docs/en/authentication

## Summary

- LOCAL-REPO ACCESS: Only /loop (in-session) and Desktop scheduled tasks run against the real working tree; cloud Routines use a fresh GitHub clone — rules them out for .renmark/ writes.
- SLASH COMMANDS IN -p: Include /skill-name in the prompt string; skills expand before execution. Do NOT use --bare (strips plugins). Example: `claude -p "/renmark:propose" [flags]`.
- STRONGEST READ-ONLY: Combine `--tools "Read,Bash,Grep,Glob"` (strips Edit/Write from context) + `--disallowedTools "Edit,Write,mcp__*"` + `--permission-mode dontAsk`; plan mode only prompts, does not hard-deny in headless.
- AUTH FOR CRON: `claude setup-token` → `CLAUDE_CODE_OAUTH_TOKEN` env var (1-year, works in WSL2 cron; NOT compatible with --bare). API key also works. Credentials persist in ~/.claude/.credentials.json after /login.
- MISSING CONTEXT: WSL2 Desktop scheduled task filesystem behavior unconfirmed (Windows app vs WSL2 paths); `plan` mode headless deny behavior ambiguous; plugin+--tools interaction not explicitly documented.
