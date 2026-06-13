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
