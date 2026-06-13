---
artifact_type: research
schema_version: 1
created_at: 2026-06-13T03:21:30+00:00
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

# Playwright MCP — Session Persistence & Chrome DevTools MCP Comparison

## Research scope

This document covers `@playwright/mcp` (Microsoft's official Playwright MCP server) with a focus on:
1. Session persistence flags and how a pre-saved `storageState` JSON is loaded
2. Dependency footprint vs the Chrome DevTools MCP that renmark currently uses
3. Reuse fit for renmark's `/renmark:verify --qa` hybrid layer

---

## 1. Installation

### @playwright/mcp
- **Install command**: `npx @playwright/mcp@latest` — no global install required; works as an npx one-liner in Claude Code MCP config
- **Node requirement**: Node.js 18 or newer
- **Browser binaries**: Not mentioned as a separate step in official docs; Playwright bundles its own Chromium. In practice, running `npx @playwright/mcp@latest` for the first time will trigger a Playwright browser install if browsers are not already present in `~/.cache/ms-playwright/`. This is a one-time cost, not per-session.
- **MCP config example**:
```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": ["@playwright/mcp@latest", "--storage-state=.renmark/state/browser/auth.json"]
    }
  }
}
```

### Chrome DevTools MCP (current renmark usage)
- Already installed; talks to an existing Chrome/Chromium instance via CDP on port 9222 (or the OS MCP bridge). No new browser install required — it drives a running browser.

---

## 2. Session persistence: flags and behavior

### Flag reference

| Flag | Behavior |
|---|---|
| `--storage-state=<path>` | Loads cookies + localStorage from a Playwright `storageState` JSON at startup; session starts authenticated. Works in `--isolated` mode. |
| `--user-data-dir=<path>` | Points the browser profile at a custom directory; ALL browser state (cookies, IndexedDB, extension state) persists between server restarts. |
| `--isolated` | Each new MCP session starts with a clean context. Combine with `--storage-state` to start authenticated but otherwise fresh. |
| `--headless` | Run without a visible window (default in server contexts). |
| `--browser=` | `chrome`, `firefox`, `webkit`, `msedge`. Default: Chromium. |

### Persistent (default) mode
When neither `--isolated` nor `--user-data-dir` is supplied, Playwright MCP stores the profile in the platform cache under `ms-playwright/mcp-{channel}-{workspace-hash}`. Login state, cookies, and localStorage persist between server restarts automatically. This is fine for single-user single-session QA but **cannot be shared across parallel runs**.

### Isolated + storageState (recommended for renmark QA)
```json
"args": ["@playwright/mcp@latest", "--isolated", "--storage-state=.renmark/state/browser/auth.json"]
```
- Browser starts with no profile cruft, but cookies and localStorage from the saved file are injected immediately.
- The session IS authenticated at first navigation.
- Multiple parallel instances can use the same read-only `auth.json` (reads at startup, does not lock the file).
- To refresh the auth file mid-session: the LLM can call `browser_storage_state { path: ".renmark/state/browser/auth.json" }` (save) then reload.

### Path note: can the storage-state path live inside the project?
**Yes, with no known restriction.** The flag accepts any resolvable path relative to the MCP server's cwd (which is the project root when launched from Claude Code). Pointing it at `.renmark/state/browser/auth.json` is idiomatic and consistent with renmark's state layout. The file should be gitignored (contains session tokens).

---

## 3. Tool surface exposed to the LLM

### @playwright/mcp (~21 tools)
Categories: Navigation, click/type/fill/select, form interaction, keyboard & mouse, tab management, dialogs, waiting, network inspection & API mocking, storage/authentication (save/load storageState), console log access, screenshots, code execution (evaluate), tracing, assertions, PDF export, video recording.

**Notable for renmark**: `browser_storage_state` (save) and `browser_set_storage_state` (load) are first-class tools the LLM can invoke mid-session — no need to restart the server to refresh auth.

### Chrome DevTools MCP (~26–29 tools)
Categories: navigation, input, debug (CDP-level), network inspection, performance tracing, Lighthouse audits, accessibility snapshot, screenshots, console, heap snapshots.

**Chrome DevTools MCP is the ONLY one with built-in performance tracing and Lighthouse** — relevant if renmark QA ever needs Web Vitals. It operates at the CDP protocol level (lower abstraction) and drives an already-running Chrome instance.

---

## 4. Dependency footprint comparison

| Dimension | @playwright/mcp | Chrome DevTools MCP |
|---|---|---|
| Node requirement | Node 18+ | Node 16+ (usually) |
| Browser install | Playwright bundles Chromium; first-run auto-install (~300 MB) | Drives an already-running Chrome — no extra install |
| Protocol layer | High-level Playwright API over CDP | Direct CDP |
| Multi-browser | Chromium, Firefox, WebKit, Edge | Chromium only |
| Token cost (tool defs) | Lower (~21 tools) | Higher (~26–29 tools; one source claims 18k tokens for tool defs alone) |
| Session persistence | First-class (`--storage-state`, `--user-data-dir`) | Inherits from the running Chrome profile; no flag-level control |
| Parallel instances | Easy with `--isolated` | Harder; shares the running Chrome process |

**Key asymmetry**: Chrome DevTools MCP assumes a browser is already open (you point it at `localhost:9222`). Playwright MCP manages its own browser lifecycle. For a CI/headless QA scenario where no browser is pre-running, `@playwright/mcp` is self-contained; Chrome DevTools MCP requires an external Chrome launch step.

---

## 5. Reuse vs build assessment

renmark already ships Chrome DevTools MCP integration. The proposed hybrid adds Playwright MCP for:
- Pre-authenticated sessions via `--storage-state` (no LLM-driven login ceremony)
- Headless QA in environments without a running Chrome
- Parallel isolated sessions per test run

**Reuse path (recommended)**: Add `@playwright/mcp` as a second MCP server in the renmark `--qa` profile. Configure it with `--isolated --storage-state=.renmark/state/browser/auth.json`. Keep Chrome DevTools MCP for performance tracing and Lighthouse (its exclusive capabilities). This is additive — no removal of existing tooling.

**Build path**: Writing a custom session-state injector over CDP is redundant; Playwright's `storageState` is already the Playwright-native format and the MCP flag accepts it directly.

---

## 6. Key gotchas

1. **storageState is Playwright format**: The JSON saved by `page.context().storageState()` includes `cookies` and `origins[].localStorage`. If renmark generates this file from a non-Playwright login flow (e.g., manual browser or Puppeteer), the schema must match exactly. Chrome DevTools MCP has no equivalent save tool.

2. **Persistent profile: one instance at a time**: Default (non-isolated) mode locks the profile dir. Two simultaneous MCP server instances against the same profile will conflict. Always use `--isolated` for parallel QA runs.

3. **First-run browser download**: On a fresh machine (e.g., CI), `npx @playwright/mcp@latest` triggers a Chromium download (~300 MB). Cache it in CI. Can be pre-seeded with `npx playwright install chromium`.

4. **cwd-relative paths**: The `--storage-state` path resolves relative to the directory from which the MCP server process is started. Claude Code MCP servers inherit the workspace root as cwd, so `.renmark/state/browser/auth.json` is safe — but document this assumption in the renmark MCP config template.

5. **Token overhead**: Playwright MCP exposes ~21 tools (~3k–5k tokens for definitions, estimated). Chrome DevTools MCP's ~26–29 tools are reported heavier (one claim: 18k tokens). Running both in the same session doubles the tool-definition overhead — consider using separate MCP server profiles (`--qa` vs `--debug`) to avoid paying both costs simultaneously.

---

## Sources

- https://playwright.dev/docs/getting-started-mcp
- https://playwright.dev/mcp/configuration/user-profile
- https://mastalerz.it/comparing-playwright-mcp-vs-chrome-devtools-mcp-what-they-are-how-to-use-them-and-configuration-details/
- https://www.test-lab.ai/blog/chrome-devtools-mcp-vs-playwright-mcp-cli
- https://mcpservers.org/servers/microsoft/playwright-mcp

## Summary

- playwright MCP storage flags: --storage-state=<path> (preload auth JSON) + --user-data-dir + --isolated; all path-relative to server cwd
- can preload storageState (start authed): YES — combine --isolated --storage-state=.renmark/state/browser/auth.json; LLM can also save/load mid-session via browser_storage_state tool
- dependency footprint vs chrome-devtools MCP: heavier first-run (Chromium ~300 MB auto-install); lighter token overhead (~21 tools vs ~26-29); self-contained vs requires running Chrome on CDP
- reuse vs build call: REUSE — add @playwright/mcp as second MCP server alongside existing Chrome DevTools MCP; additive, no removal; Playwright handles auth sessions, Chrome DevTools MCP keeps perf/Lighthouse
- key gotcha: storageState format is Playwright-native (cookies+origins.localStorage); persistent mode locks profile to one instance — always use --isolated for parallel QA runs
