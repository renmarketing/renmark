"""---
artifact_type: code_module
schema_version: 1
created_at: 2026-06-13T13:35:00-04:00
source_sha: ad7f21141b4056d55db4f84df580d7c6cc2b62bc
related_plan: null
generator: sonnet
stale_after: null
dependency_refs:
  - /home/renmark/projects/ai-system/CHANGELOG.md
  - /home/renmark/projects/ai-system/renmark/browser.py
completion_state: complete
confidence: high
validation_status: validated
retry_count: 1
parser_success: true
schema_compliance: true
---

Argparse CLI for persisted browser-session management.

## Findings

Blocking:
- The module must import cleanly without the optional Playwright extra, so every
  Playwright import stays inside the `login` execution path.
- repo_root must be resolved ONCE via browser._repo_root() and threaded through
  every browser.* call so running from a subdirectory uses the correct sessions dir.
- Playwright launch errors (missing Chromium, sandbox failures) must be caught at
  the boundary and mapped to the documented remediation path, never a traceback.
- Profile names from argv must be validated via browser._safe_profile_name() at
  the CLI boundary; ValueError must be caught and turned into a clean one-line error.

Deferrable:
- The current public browser API exposes storage-state and metadata helpers, but
  no public user-data-dir helper; forget-mode therefore performs best-effort
  cleanup of conventional sibling directories only.

## Assumptions

- Session metadata lives beside each profile JSON as `<name>.meta.json`.
- A headed login flow may start on `about:blank`; the human can navigate to the
  target site manually before confirming.
- `active.json` is not profile-owned state and should not be removed by
  `forget <profile>`.

## Edge Cases

- Missing or malformed metadata should never print secrets; status/list degrade
  to `unknown` fields plus stale detection from `renmark.browser.is_stale`.
- Forget is idempotent: absent files/directories do not fail the command.
- Playwright missing or Chromium not installed returns a non-zero exit after
  printing the exact remediation commands, with no auto-install side effects.
- Invalid profile names (traversal, special chars) print a clean one-line error
  and exit non-zero without a traceback or any file deletion.

## Recommendations

- If a future wave adds first-class persistent user-data-dir support, expose a
  public path helper in `renmark.browser` so `forget` can delete exactly that
  path instead of using conventional-name cleanup.

## Summary

- Resolves repo_root ONCE per CLI invocation and threads it through all browser.* calls.
- Wraps Playwright chromium.launch and context creation in try/except; any launch
  error prints remediation and exits non-zero — never a traceback.
- Validates profile names at CLI boundary via browser._safe_profile_name(); catches
  ValueError and prints a clean error (protects `forget` and all other commands).
- Keeps Playwright optional: all playwright imports stay inside `login`.
- Never prints cookie values or other session secrets.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import shutil
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from renmark import browser


def _print_playwright_remediation() -> None:
    print("pip install renmark[browser]", file=sys.stderr)
    print("python -m playwright install chromium", file=sys.stderr)


def _sessions_dir(repo_root: Path) -> Path:
    return browser.active_path(repo_root=repo_root).parent


def _profile_names(repo_root: Path) -> list[str]:
    root = _sessions_dir(repo_root)
    if not root.exists():
        return []

    names: list[str] = []
    for path in root.glob("*.json"):
        if path.name == "active.json" or path.name.endswith(".meta.json"):
            continue
        names.append(path.stem)
    return sorted(set(names))


def _load_meta(name: str, repo_root: Path) -> dict[str, Any]:
    path = browser.meta_path(name, repo_root=repo_root)
    if not path.exists():
        return {}

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

    if not isinstance(raw, dict):
        return {}
    return raw


def _status_fields(name: str, repo_root: Path) -> tuple[str, str, bool]:
    meta = _load_meta(name, repo_root)
    saved_at = str(meta.get("saved_at", "unknown"))
    mode = str(meta.get("mode", "unknown"))
    stale = browser.is_stale(name, repo_root=repo_root)
    return saved_at, mode, stale


def _user_data_dir_candidates(name: str, repo_root: Path) -> list[Path]:
    root = _sessions_dir(repo_root)
    return [
        root / name,
        root / f"{name}.user-data",
        root / f"{name}.user-data-dir",
        root / f"{name}.userdata",
        root / f"{name}-user-data",
        root / f"{name}-user-data-dir",
    ]


def _validate_profile_name(name: str) -> str:
    """Validate profile name at CLI boundary; print error and exit on failure."""
    try:
        return browser._safe_profile_name(name)
    except ValueError as exc:
        print(f"Invalid profile name: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


def cmd_login(args: argparse.Namespace, repo_root: Path) -> int:
    _validate_profile_name(args.profile)

    if not browser.is_playwright_available():
        _print_playwright_remediation()
        return 1

    from playwright.sync_api import sync_playwright  # type: ignore[import-not-found]

    with sync_playwright() as playwright:
        try:
            launched = playwright.chromium.launch(headless=False)
        except Exception as exc:
            print(
                f"Chromium launch failed: {exc}",
                file=sys.stderr,
            )
            _print_playwright_remediation()
            return 1

        try:
            context = launched.new_context()
        except Exception as exc:
            print(f"Failed to create browser context: {exc}", file=sys.stderr)
            _print_playwright_remediation()
            with contextlib.suppress(Exception):
                launched.close()
            return 1

        try:
            page = context.new_page()
            page.goto("about:blank")
            print(
                f"Complete login for profile {args.profile!r} in the opened Chromium window.",
                file=sys.stderr,
            )
            input("Press Enter immediately after login is complete to save the session: ")
            saved = browser.save_storage_state(args.profile, context, repo_root=repo_root)
        finally:
            with contextlib.suppress(Exception):
                context.close()
            with contextlib.suppress(Exception):
                launched.close()

    print(saved)
    return 0


def cmd_list(_: argparse.Namespace, repo_root: Path) -> int:
    names = _profile_names(repo_root)
    if not names:
        print("No saved browser profiles.")
        return 0

    for name in names:
        saved_at, _mode, stale = _status_fields(name, repo_root)
        stale_label = "stale" if stale else "fresh"
        print(f"{name}\tsaved_at={saved_at}\t{stale_label}")
    return 0


def cmd_status(args: argparse.Namespace, repo_root: Path) -> int:
    _validate_profile_name(args.profile)

    profile = browser.profile_path(args.profile, repo_root=repo_root)
    if not profile.exists():
        print(f"Profile not found: {args.profile}", file=sys.stderr)
        return 1

    saved_at, mode, stale = _status_fields(args.profile, repo_root)
    print(f"profile={args.profile}")
    print(f"saved_at={saved_at}")
    print(f"mode={mode}")
    print(f"stale={'yes' if stale else 'no'}")
    return 0


def cmd_forget(args: argparse.Namespace, repo_root: Path) -> int:
    _validate_profile_name(args.profile)

    removed_any = False

    for path in (
        browser.profile_path(args.profile, repo_root=repo_root),
        browser.meta_path(args.profile, repo_root=repo_root),
    ):
        if path.exists():
            path.unlink()
            removed_any = True

    for path in _user_data_dir_candidates(args.profile, repo_root):
        if path.is_dir():
            shutil.rmtree(path)
            removed_any = True

    if removed_any:
        print(f"Forgot profile {args.profile}.")
        return 0

    print(f"Profile not found: {args.profile}", file=sys.stderr)
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m renmark.browser_cli")
    subparsers = parser.add_subparsers(dest="command", required=True)

    login_parser = subparsers.add_parser("login", help="Create or refresh a saved login profile.")
    login_parser.add_argument("profile")
    login_parser.set_defaults(func=cmd_login)

    list_parser = subparsers.add_parser("list", help="List saved login profiles.")
    list_parser.set_defaults(func=cmd_list)

    status_parser = subparsers.add_parser("status", help="Show non-secret profile metadata.")
    status_parser.add_argument("profile")
    status_parser.set_defaults(func=cmd_status)

    forget_parser = subparsers.add_parser("forget", help="Delete a saved login profile.")
    forget_parser.add_argument("profile")
    forget_parser.set_defaults(func=cmd_forget)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    func = getattr(args, "func", None)
    if func is None:
        parser.print_help(sys.stderr)
        return 2

    # Resolve repo root ONCE; thread it through every command.
    repo_root = browser._repo_root()
    return int(func(args, repo_root))


if __name__ == "__main__":
    raise SystemExit(main())
