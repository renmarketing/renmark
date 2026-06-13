---
artifact_type: research
schema_version: 1
created_at: 2026-06-13T03:21:19+00:00
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

# Playwright Python: Session Persistence + Optional-Dep Packaging
## Research date: 2026-06-12
## Sources
- https://playwright.dev/python/docs/auth (authoritative, fetched)
- https://www.browserstack.com/guide/playwright-storage-state
- https://www.browserstack.com/guide/playwright-persistent-context
- https://github.com/microsoft/playwright-python/issues/2502

---

## 1. storageState vs. persistent context (user-data-dir)

### storageState

**What it captures:**
- Cookies (all origins)
- localStorage (all origins)
- IndexedDB (all origins)

**What it does NOT capture:**
- sessionStorage — scoped per tab/page, not persisted to disk. Can be hacked in via `add_init_script()` that injects JS to populate it on page load, but this is fragile.
- Full browser cache (HTTP cache, compiled JS, image cache)
- Service workers and their caches (registrations and cached responses)
- Browser extension state
- DevTools Protocol state

**Save idiom:**
```python
# After login flow completes:
context.storage_state(path="playwright/.auth/state.json")
```

**Reuse idiom:**
```python
context = browser.new_context(storage_state="playwright/.auth/state.json")
```

**When storageState breaks (token-refresh edge cases):**
- If the app uses short-lived access tokens stored ONLY in memory (React state, JS heap) and refreshes them via a silent iframe or a service worker, storageState won't capture the in-memory token — only the refresh token (if stored in a cookie or localStorage). On first reuse the access token will be stale; the app must trigger a refresh before scraping, or the flow fails immediately.
- Service worker intercepts: some SPAs cache auth responses in service worker caches. storageState does not persist SW caches, so even with valid cookies the SW may return a stale or missing token on replay.
- HttpOnly cookie-based auth (classic session cookies): storageState DOES capture these because they live in the browser cookie jar, not in JS-accessible storage. This is the most reliable case.
- Sites using device-fingerprinting or IP pinning will reject replayed storageState from a different process context, regardless of what was saved.

**Assumption:** IndexedDB capture works for Chromium; Playwright docs confirm it for cross-browser state sharing, but behavior on Firefox/WebKit with complex IDB schemas has occasional bugs in older Playwright versions — test explicitly if targeting non-Chromium.

### Persistent context (user_data_dir)

**What it captures — everything storageState misses:**
- Full browser profile on disk (Chromium profile directory)
- Service worker registrations and their caches
- Full HTTP cache (avoids network hits on replay)
- Extension state (if extensions are loaded)
- IndexedDB, localStorage, cookies (superset of storageState)
- Compiled V8 bytecode caches

**Launch idiom:**
```python
context = await playwright.chromium.launch_persistent_context(
    user_data_dir="/path/to/profile",
    headless=False,   # some sites block headless
)
# context IS the BrowserContext; no separate browser.new_context() call
```

**Tradeoffs vs storageState:**
| Dimension | storageState | persistent context |
|---|---|---|
| Portability | Single JSON file, easy to copy/backup | Directory tree, GB-scale possible |
| Parallelism | Many contexts from one file, each isolated | One live context per user_data_dir at a time (Chrome profile lock) |
| Freshness | Snapshot — stale after token expiry | Live — browser renews tokens naturally |
| Service workers | Not captured | Fully captured |
| MCP reuse | Easy (pass path to new_context) | Harder (MCP server must own the persistent context lifecycle) |
| Secret surface area | One JSON file to protect | Whole directory to protect |

**Recommendation for renmark-browser:** Use storageState as the PRIMARY export format (portable, single file, easy to gitignore, suitable for both deterministic scripted flows AND MCP context creation). Fall back to persistent context only if the target site relies on service workers or SW-cached auth tokens. The `login` step should always end with `context.storage_state(path=...)` to produce the canonical artifact.

---

## 2. Optional-dependency packaging

### pip extras pattern

In `pyproject.toml` (or `setup.cfg`):
```toml
[project.optional-dependencies]
browser = [
    "playwright>=1.40.0",
]
```

Install with:
```
pip install renmark[browser]
```

This installs the `playwright` Python package but NOT the browser binaries. That requires a separate step:
```
python -m playwright install chromium
```

**Critical packaging nuance:** The `playwright install` step is a CLI command that downloads ~150–300 MB of browser binaries to `~/.cache/ms-playwright/`. It cannot be expressed as a pip extra dependency because pip only handles Python packages, not arbitrary binary downloads. This is a known gap — see https://github.com/microsoft/playwright-python/issues/2502 (open as of 2024, not resolved).

**Implication for renmark:** The `renmark[browser]` extra installs the Python bindings; a post-install step `renmark-browser install` (or a CLI wrapper around `playwright install chromium`) must be documented and ideally invoked automatically on first use.

### Runtime availability detection

Two-layer guard needed:

**Layer 1 — Python import guard:**
```python
try:
    from playwright.sync_api import Playwright, sync_playwright
    _PLAYWRIGHT_AVAILABLE = True
except ImportError:
    _PLAYWRIGHT_AVAILABLE = False

def require_playwright():
    if not _PLAYWRIGHT_AVAILABLE:
        raise RuntimeError(
            "Playwright is not installed. Run: pip install renmark[browser]"
        )
```

**Layer 2 — browser binary guard:**
Even with playwright installed, binaries may be missing (pip install without `playwright install`). Detection:
```python
import subprocess, sys

def _browser_installed(browser: str = "chromium") -> bool:
    """Check if playwright browser binary is available."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "playwright", "install", "--dry-run", browser],
            capture_output=True, text=True, timeout=10
        )
        # exit 0 if already installed; non-zero or specific message if not
        return result.returncode == 0
    except Exception:
        return False
```

NOTE: `--dry-run` flag availability varies by Playwright version. A more reliable check is to attempt `sync_playwright().start()` and call `p.chromium.executable_path()` — if the path doesn't exist on disk, it raises. Wrap in try/except and surface a clear error:
```python
import os
from playwright.sync_api import sync_playwright

def assert_browser_ready(browser: str = "chromium") -> None:
    with sync_playwright() as p:
        exe = getattr(p, browser).executable_path()
        if not os.path.exists(exe):
            raise RuntimeError(
                f"Playwright browser binary not found at {exe}. "
                f"Run: python -m playwright install {browser}"
            )
```

**Graceful degradation:** Any renmark command that requires the browser layer should:
1. Call `require_playwright()` at the top of the command handler.
2. Call `assert_browser_ready()` before launching.
3. Surface actionable install instructions, not a raw ImportError or FileNotFoundError.
Commands that don't need browser (plan, orchestrate, verify, etc.) must NEVER import from `playwright` at module load time — only inside the browser subcommand module.

### pyproject.toml example for renmark
```toml
[project.optional-dependencies]
browser = ["playwright>=1.40.0"]
dev    = ["pytest", "ruff", "mypy"]
```

---

## 3. Secret-safety: storageState files contain auth tokens

The Playwright auth docs (fetched) state explicitly:
> "The browser state file may contain sensitive cookies and headers that could be used to impersonate you or your test account."
> "We strongly discourage checking them into private or public repositories."

**Recommended gitignore pattern (official):**
```bash
mkdir -p playwright/.auth
echo '\nplaywright/.auth' >> .gitignore
```

**For renmark:** storageState artifacts must:
- Live under `.renmark/state/browser-sessions/<profile>/` (already gitignored per .renmark/state/ convention).
- Never be logged to stdout, never appear in task summaries or wave-summary files.
- Never be passed as inline content to any subagent — only the path.
- Be excluded from any artifact export or ZIP release.

---

## 4. Pitfalls / pushback on obvious approaches

1. **"Just use persistent context for everything"** — pitfall: profile lock. Chromium holds an exclusive lock on user_data_dir; two concurrent flows on the same profile will fail. For parallel scripted flows (a renmark strength), storageState + multiple isolated new_context() calls is the only safe pattern.

2. **"storageState is always fresh enough"** — pitfall: SPA token refresh. If the access token TTL is shorter than the time between `login` and actual browser flow execution, the flow will start with an expired token. Mitigation: add a post-login wait or a token-check probe before saving storageState; OR save storageState just before the actual flow rather than right after login.

3. **"One playwright install covers all tools"** — pitfall: version mismatch. If `playwright` Python package is upgraded without re-running `playwright install`, the binaries are mismatched. The Python package and browser binaries must be installed at compatible versions. Recommend pinning `playwright>=1.40.0,<2` and documenting this.

4. **"Import playwright at module top level"** — pitfall: breaks stdlib-only import for users without the extra. All playwright imports must be deferred behind the `require_playwright()` guard.

## Summary

- best practice: use storageState (JSON snapshot) as primary session export — portable, parallelism-safe, easy to gitignore; fall back to persistent context only when SW-cached auth is required
- storageState vs user-data-dir: storageState captures cookies+localStorage+IndexedDB (not SW cache, not sessionStorage); user-data-dir captures full profile but locks to one process — storageState is correct for parallel scripted+MCP reuse
- optional-dep packaging: add playwright>=1.40.0 under [project.optional-dependencies] browser; pip install renmark[browser] installs Python bindings only — browser binaries require a separate `python -m playwright install chromium` step that cannot be expressed as a pip extra
- key risk surfaced: SPA short-lived access tokens may expire between login and flow execution if stored only in memory — save storageState immediately before the actual flow, not just after login; also: Chromium profile lock prevents parallel persistent-context use
- secret-safety: storageState JSON contains live auth cookies/headers — must live under .renmark/state/browser-sessions/ (gitignored), never logged, never passed inline to subagents, excluded from release ZIPs
