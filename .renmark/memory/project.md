# Project

(Auto-maintained by `/renmark:brainstorm`. Edit freely.)

## Tech stack

- (Language + version)
- (Framework)
- (Notable dependencies)

## File layout

```
(Top-level structure)
```

## Runtime environment

- (Where it runs — local, container, edge, etc.)
- (Required services)

## Notable facts

- 2026-06-12: renmark gained an OPTIONAL Playwright browser-control layer with
  session memory (`feature/playwright-browser-control`, PRD REQ-19). It
  authenticates once via `renmark-browser login <profile>`, persists the session
  under gitignored `.renmark/state/browser-sessions/`, and reuses it across
  verify runs through both a Python scripted path and an `@playwright/mcp` live
  channel — falling back to the pre-existing Chrome DevTools MCP (cold session)
  when Playwright is absent. This is the project's first optional runtime dep;
  the core runtime stays stdlib-only.
- 2026-06-15: REQ-14 scheduled read-only QA proposer lane spec'd as
  `/renmark:scan` (spec: `.renmark/specs/2026-06-15-req14-scan-proposer.spec.md`).
  Decision: scheduling stays **external** to renmark (Option 1) — renmark ships
  the worker + `--emit-cron` printer; the trigger is the user's WSL cron / Task
  Scheduler. Cloud Routines (`/schedule`) ruled out (fresh-clone, no local repo
  access). Read-only is **enforced** (restricted tool-list + `dontAsk` +
  PreToolUse Bash-denylist hook), not conventional. Lands deduped `source="qa"`
  backlog items via the REQ-13 `SCHEDULED-QA.md` seam — never executes.
