---
artifact_type: plan
schema_version: 1
created_at: 2026-06-13
source_sha: aeacf97
related_review: .renmark/reviews/2026-06-13-aeacf9771d0e535f51b2fa87cebc276743aaa854.review.md
generator: codereview-fix
---

# Plan — playwright-browser-control review fixes

Fixes the codex review's 1 Critical + 6 Major + 1 Minor on feature/playwright-browser-control.
Locked decision — canonical channel contract: `resolve_channel(override=None)` →
`{"playwright"|"chrome-devtools"|"native"}`; overrides accept
`playwright|chrome-devtools|native|auto` + `mcp` (back-compat alias → playwright);
`auto` → playwright if available else chrome-devtools; native explicit-only.

### Fix A: renmark/browser.py (Critical + Major) — sonnet, group 1
- Path-traversal guard (Critical): a `_safe_profile_name(name)` that rejects anything not matching `^[A-Za-z0-9._-]+$` (and bare `.`/`..`); profile_path/meta_path call it; resolve-check computed paths stay under the sessions root.
- is_stale(): catch TypeError too; missing/invalid/naive/non-string saved_at → treat as stale, never raise.
- activate(): call validate_storage_state(src) before copying; refuse on schema failure (and on traversal name).
- Channel API: resolve_channel accepts {playwright,chrome-devtools,native,auto,mcp-alias}, returns {playwright,chrome-devtools,native}; auto → playwright if available else chrome-devtools.
- Repo-root: add `_repo_root()` (nearest .git/.renmark upward); path helpers default repo_root to it, NOT Path.cwd().
- verifier: py_compile + import without playwright + ruff.

### Fix B: renmark/browser_cli.py (Major) — sonnet, group 2 (depends on A)
- Use sanitized profile names (reject traversal early with a clear error + nonzero exit).
- login: catch Playwright launch errors (chromium missing / launch fail) → print remediation + exit nonzero, never crash.
- Resolve repo root once and thread repo_root through all browser.* calls.
- verifier: py_compile + import without playwright + ruff.

### Fix C: plugin/skills/verify/SKILL.md (Major) — haiku, group 3
- Correct examples to real signatures: `resolve_channel(override=None)` (not `(repo, args)`) and `activate(name, repo_root=None)` (not `(repo, profile=)`); channel values playwright|chrome-devtools|native.
- verifier: grep -q 'resolve_channel(override' plugin/skills/verify/SKILL.md

### Fix D: tests/test_browser.py (Minor) — codex, group 3
- Align channel expectations to the canonical contract; add negative tests: traversal profile names rejected; malformed/naive/non-string saved_at treated as stale (no crash); activate refuses foreign-schema JSON.
- verifier: pytest -q tests/test_browser.py
