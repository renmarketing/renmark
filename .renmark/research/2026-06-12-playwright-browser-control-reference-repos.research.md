---
artifact_type: research
schema_version: 1
created_at: 2026-06-13T03:21:50+00:00
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

# Browser-Control Reference: Multi-Channel Abstraction + Auth-Once Reuse

## Research Scope
Two angles: (1) reference projects/patterns for abstracting over Playwright vs CDP/MCP channels with capability detection + runtime selection; (2) pitfalls of "login once, reuse storageState" across channels and in CI/headless environments.

---

## 1. Reference Implementations

### browserstate-org/browserstate
- **URL:** https://github.com/browserstate-org/browserstate
- **What it does:** Persistent browser session management across machines and automation environments. Captures and restores full browser context (cookies, localStorage, IndexedDB, service workers). Python + Node.js parity.
- **Architecture to borrow:**
  - **Mount/unmount pattern:** sessions mounted to a temp dir before launch, unmounted after; the profile path is always ephemeral from the automation side, never held open.
  - **Pluggable storage backends:** local disk / Redis / S3 / GCS — the "profile" is just a portable tarball moved between backends.
  - **`userId` as logical session key:** decouples the profile name from the filesystem path.
  - **launchPersistentContext integration:** for Playwright, it resolves the temp dir and passes it to `launchPersistentContext`; the lib owns the lifecycle, not the caller.
- **Python support:** yes, feature-parity with Node.js.
- **Channel abstraction:** implicit (the lib does not do auto-detect); it surfaces to the framework-specific launch call. The channel-select layer would sit above it.
- **Source:** https://github.com/browserstate-org/browserstate

### microsoft/playwright-mcp (issue #983)
- **URL:** https://github.com/microsoft/playwright-mcp/issues/983
- **What it does:** Open issue requesting storageState support when connecting via CDP endpoint (the MCP channel). Currently, storageState loading only works with direct Playwright launch, not CDP-attach mode.
- **Key finding for renmark:** the two channels are NOT symmetric for storageState. Playwright-direct supports `browser.new_context(storage_state=...)` natively; CDP-attach does not (as of mid-2026). This is the primary cross-channel parity gap to design around.

### browser-use/browser-use (issue #702)
- **URL:** https://github.com/browser-use/browser-use/issues/702
- **What it does:** AI browser agent; issue discusses reusing `storage_state` in `BrowserContextConfig`. Community workaround: serialize storageState on Playwright side, then inject cookies manually into CDP-attached context via `add_cookies`.
- **Pattern to borrow:** when channel=MCP/CDP, fall back to cookie injection from the saved JSON rather than native storageState load.

### Playwright CLI storage-state command (knightli.com, 2026)
- **URL:** https://knightli.com/en/2026/04/14/playwright-cli-storage-state-commands/
- **Pattern:** `playwright open --save-storage=auth.json <url>` for headed login bootstrap; subsequent runs pass `--load-storage=auth.json`. Directly maps to `renmark-browser login <profile>` → writes `~/.renmark/profiles/<profile>/auth.json`.

---

## 2. Channel-Abstraction Pattern

**Recommended layering (from synthesized patterns):**

```
BrowserChannel (abstract)
  .launch(profile_path) -> BrowserContext
  .is_available() -> bool          # capability check

PlaywrightChannel(BrowserChannel)
  is_available(): try importlib.util.find_spec("playwright"); launch browser binary check
  launch(): playwright.launch() or launchPersistentContext(temp_dir)

MCPChannel(BrowserChannel)
  is_available(): check MCP server reachable (CDP endpoint probe)
  launch(): attach via CDP; inject cookies from storageState JSON manually

AutoChannel
  selects: PlaywrightChannel if available, else MCPChannel, else raise NoBrowserError
```

The critical insight: **storageState is not symmetric**. Design the `launch()` method to accept a `ProfileState` (parsed JSON), and let each channel implementation decide how to apply it (native `storage_state=` arg vs `add_cookies` injection).

---

## 3. Auth-Once / storageState Reuse Pitfalls

### 3.1 Staleness and Token Expiry
- Session cookies set `Expires` or `Max-Age`; some apps also expire server-side sessions independently.
- storageState captures point-in-time state; there is no TTL signal in the JSON itself.
- **Mitigation:** store `saved_at` timestamp alongside the auth.json; treat as stale after configurable TTL (default: 24 h for CI, longer for dev). Regenerate via `renmark-browser login --refresh <profile>`.

### 3.2 Headed Login → Headless Reuse (the macOS/Chrome persistent-context bug)
- Confirmed Playwright issue #35466: `launchPersistentContext` in headless mode fails to read cookies written by a prior headed session using the **same** `userDataDir`. The headless process also fails to release lock files on close, corrupting the SQLite profile databases.
- **Root cause:** headless Chrome does not fully honor the profile's SQLite WAL finalization on exit.
- **Mitigation for renmark:** use **storageState JSON** (not `launchPersistentContext` with a shared dir) as the cross-mode hand-off format. The headed login step does `context.storage_state(path=auth.json)`; the headless reuse step loads from that file into a **fresh ephemeral context** (`browser.new_context(storage_state=auth.json)`). Never reuse the raw userDataDir across headed/headless boundaries.

### 3.3 Profile / userDataDir Locking
- Chrome/Chromium locks the userDataDir with a `SingletonLock` file; a second process attempting to open the same dir is rejected or silently creates a new temp dir (losing state).
- **In CI with parallelism:** if N workers load the same profile dir, only one wins; others run unauthenticated and fail silently.
- **Mitigation:** the mount/unmount pattern from browserstate-org/browserstate is the correct answer — copy the profile to a per-worker temp dir on mount, write back on unmount. storageState JSON sidesteps this entirely (it's a plain file, multiple readers OK).

### 3.4 Incomplete Session Data Capture
- `context.storage_state()` captures: cookies, localStorage, optionally IndexedDB.
- It does NOT capture: sessionStorage (tab-local, not persisted), service worker registrations, in-flight WebSocket state.
- Apps that store auth tokens only in sessionStorage will not survive storageState reuse.
- **Detection:** if login page reappears after state load, suspect sessionStorage-only auth.

### 3.5 CDP / MCP Channel Gap (storageState injection)
- CDP-attached contexts (MCP channel) do not support Playwright's `storage_state=` init arg.
- **Workaround:** parse auth.json, call `context.add_cookies(state["cookies"])` and `page.evaluate(js_inject_localstorage, state["origins"])` manually after attach.
- This is less reliable than native load (order of operations matters; SameSite=Strict cookies may not apply correctly via injection).
- **Risk:** if the MCP-channel target is an already-open browser with an existing session, injecting cookies may conflict or be silently ignored.

### 3.6 CI Caching Gotcha
- storageState files cached in CI (GitHub Actions cache, etc.) survive across runs; if the app rotates session secrets between deploys, the cached file is silently invalid.
- **Mitigation:** key the cache on a deploy fingerprint (e.g., app version hash), or always regenerate in the setup job.

---

## 4. Assumptions and Missing Context

- Assumed "MCP channel" means the Chrome DevTools MCP server (playwright-mcp or equivalent) accessed via CDP endpoint; if it's a higher-level MCP tool abstraction, the storageState gap analysis changes.
- No direct reference found for a Python CLI tool that performs runtime Playwright-vs-MCP capability detection + fallback in a single binary — the pattern must be synthesized from the above primitives.
- The browserstate-org/browserstate Python library was not evaluated for active maintenance status (last commit date not confirmed).

---

## Sources
- https://github.com/browserstate-org/browserstate
- https://github.com/microsoft/playwright-mcp/issues/983
- https://github.com/browser-use/browser-use/issues/702
- https://playwright.dev/python/docs/auth
- https://github.com/microsoft/playwright/issues/35466
- https://knightli.com/en/2026/04/14/playwright-cli-storage-state-commands/
- https://www.browserstack.com/guide/playwright-storage-state
- https://qaskills.sh/blog/playwright-storagestate-authentication-reference
- https://www.checklyhq.com/blog/speed-up-playwright-tests-with-storage-state/

## Summary

- reference repo: browserstate-org/browserstate — mount/unmount pattern, userId-keyed profiles, pluggable backends; borrow the temp-dir lifecycle and storage abstraction layer
- channel-abstraction pattern: BrowserChannel ABC with is_available() + launch(ProfileState); PlaywrightChannel uses native storage_state=; MCPChannel falls back to add_cookies injection from parsed JSON
- auth-once reuse pitfall: storageState is point-in-time JSON with no TTL signal; store saved_at alongside auth.json and regenerate on staleness check (24 h CI default)
- headed-login/headless-reuse: never share userDataDir across modes (Playwright #35466 lock/corruption); always hand off via storageState JSON into a fresh ephemeral context
- profile-lock / staleness risk: userDataDir SingletonLock blocks parallel workers (silent fallback to temp dir, loses auth); CDP channel cannot load storageState natively — requires manual cookie+localStorage injection
