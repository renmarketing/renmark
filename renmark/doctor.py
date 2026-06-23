"""renmark.doctor — diagnose Claude Code plugin install health.

Checks that renmark is properly registered with Claude Code and surfaces
remediation commands for anything broken. Pure diagnostic by default;
``--fix`` mode applies the obvious safe fixes (add to settings.json,
register in installed_plugins.json, refresh cache symlink).

CLI:
    python -m renmark.doctor          # check + report, exit 1 if any issue
    python -m renmark.doctor --fix    # apply safe auto-fixes, then re-check
    python -m renmark.doctor --json   # machine-readable output

Exit codes:
    0  all checks pass
    1  one or more checks failed (or fixes still needed)
    2  bad usage

Why this exists: directory-marketplace Claude Code plugins need THREE
moving parts to surface their slash commands, and the canonical
``install.sh`` only addresses one of them. This module catches the
other two (and a few related drift modes) before the user discovers
the failure by typing ``/renmark:*`` and seeing nothing.
"""

from __future__ import annotations

import datetime as _dt
import json
import shutil
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

from . import global_routing

# ── Where renmark expects to live ─────────────────────────────────────────────

# Resolve the renmark source dir from this file's location.
# /home/renmark/projects/ai-system/renmark/doctor.py  →  /home/renmark/projects/ai-system
RENMARK_ROOT = Path(__file__).resolve().parent.parent
PLUGIN_SOURCE = RENMARK_ROOT / "plugin"
VERSION_FILE = RENMARK_ROOT / "VERSION"

CLAUDE_DIR = Path.home() / ".claude"
SETTINGS_JSON = CLAUDE_DIR / "settings.json"
PLUGINS_DIR = CLAUDE_DIR / "plugins"
INSTALLED_PLUGINS_JSON = PLUGINS_DIR / "installed_plugins.json"
KNOWN_MARKETPLACES_JSON = PLUGINS_DIR / "known_marketplaces.json"
SYMLINK_PATH = PLUGINS_DIR / "renmark"

MARKETPLACE_NAME = "renmark-local"
PLUGIN_KEY = "renmark@renmark-local"  # `<plugin>@<marketplace>` per CC convention


@dataclass
class Check:
    """One diagnostic check result."""

    name: str
    status: str  # "pass", "fail", "warn"
    detail: str
    fix_cmd: str = ""  # shell command the user can run to remediate
    auto_fixable: bool = False  # whether --fix can resolve this
    fix_fn: Callable[[], str] | None = None  # callable that applies the fix (set by checker)


@dataclass
class DoctorReport:
    checks: list[Check] = field(default_factory=list)

    def failed(self) -> list[Check]:
        return [c for c in self.checks if c.status == "fail"]

    def warned(self) -> list[Check]:
        return [c for c in self.checks if c.status == "warn"]

    def ok(self) -> bool:
        return not self.failed()


# ── Helpers ──────────────────────────────────────────────────────────────────


def _current_version() -> str | None:
    if not VERSION_FILE.exists():
        return None
    return VERSION_FILE.read_text(encoding="utf-8").strip() or None


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    # Guard against valid non-object JSON (lists, scalars, null) — downstream
    # callers use .get()/.setdefault() and would crash otherwise.
    if not isinstance(obj, dict):
        return {}
    return cast(dict[str, Any], obj)


def _backup(path: Path) -> Path | None:
    if not path.exists():
        return None
    bak = path.with_suffix(path.suffix + f".doctor.bak.{int(_dt.datetime.now().timestamp())}")
    shutil.copy2(path, bak)
    return bak


# ── Individual checks ────────────────────────────────────────────────────────


def check_cli_on_path() -> Check:
    cli = shutil.which("renmark-execute")
    if cli:
        return Check("CLI on PATH", "pass", f"`renmark-execute` resolves to {cli}")
    return Check(
        "CLI on PATH",
        "warn",
        "`renmark-execute` is not on PATH. The plugin still works, but ad-hoc CLI usage won't.",
        fix_cmd=f"bash {RENMARK_ROOT}/install.sh",
    )


def check_python_package() -> Check:
    try:
        import renmark

        loc = Path(renmark.__file__).resolve()
        v = getattr(renmark, "__version__", "<no __version__>")
        return Check("Python package", "pass", f"`renmark` v{v} importable from {loc.parent}")
    except ImportError as exc:
        return Check(
            "Python package",
            "fail",
            f"`import renmark` failed: {exc}",
            fix_cmd=f"pip install -e {RENMARK_ROOT}",
            auto_fixable=False,  # involves package install — leave to user
        )


def check_version_file() -> Check:
    v = _current_version()
    if not v:
        return Check("VERSION file", "fail", f"{VERSION_FILE} missing or empty")
    return Check("VERSION file", "pass", f"v{v}")


def check_plugin_manifest() -> Check:
    manifest = PLUGIN_SOURCE / ".claude-plugin" / "plugin.json"
    if not manifest.exists():
        return Check("Plugin manifest", "fail", f"{manifest} missing")
    data = _load_json(manifest)
    v = data.get("version")
    src_v = _current_version()
    if v and src_v and v != src_v:
        return Check(
            "Plugin manifest version",
            "fail",
            f"manifest at v{v} but VERSION says v{src_v} — version drift",
            fix_cmd="python -m renmark.release check",
        )
    return Check("Plugin manifest", "pass", f"plugin.json at v{v}")


def check_settings_marketplace() -> Check:
    settings = _load_json(SETTINGS_JSON)
    mkt = settings.get("extraKnownMarketplaces", {}).get(MARKETPLACE_NAME)
    if not mkt:
        return Check(
            "Marketplace registered (settings.json)",
            "fail",
            f"`extraKnownMarketplaces.{MARKETPLACE_NAME}` missing — Claude Code doesn't know where to find renmark.",
            fix_cmd="python -m renmark.doctor --fix",
            auto_fixable=True,
            fix_fn=_fix_add_marketplace,
        )
    src = mkt.get("source", {})
    path = src.get("path")
    if path != str(RENMARK_ROOT):
        return Check(
            "Marketplace registered (settings.json)",
            "warn",
            f"marketplace registered but path is {path!r}, not {str(RENMARK_ROOT)!r}",
            fix_cmd="python -m renmark.doctor --fix",
            auto_fixable=True,
            fix_fn=_fix_add_marketplace,
        )
    return Check("Marketplace registered (settings.json)", "pass", f"`{MARKETPLACE_NAME}` → {path}")


def check_settings_enabled() -> Check:
    settings = _load_json(SETTINGS_JSON)
    enabled = settings.get("enabledPlugins", {}).get(PLUGIN_KEY)
    if not enabled:
        return Check(
            "Plugin enabled (settings.json)",
            "fail",
            f"`enabledPlugins[{PLUGIN_KEY!r}]` is not set to true — slash commands won't appear.",
            fix_cmd="python -m renmark.doctor --fix",
            auto_fixable=True,
            fix_fn=_fix_enable_plugin,
        )
    return Check("Plugin enabled (settings.json)", "pass", f"`{PLUGIN_KEY}` = true")


def check_installed_plugins_registry() -> Check:
    data = _load_json(INSTALLED_PLUGINS_JSON)
    entries = data.get("plugins", {}).get(PLUGIN_KEY)
    if not entries:
        return Check(
            "Claude Code registry",
            "fail",
            f"`installed_plugins.json` has no entry for `{PLUGIN_KEY}`.",
            fix_cmd="python -m renmark.doctor --fix",
            auto_fixable=True,
            fix_fn=_fix_register_plugin,
        )
    entry = entries[0] if isinstance(entries, list) else entries
    registered_v = entry.get("version")
    src_v = _current_version()
    if src_v and registered_v != src_v:
        return Check(
            "Claude Code registry",
            "fail",
            f"registry says v{registered_v} but source is v{src_v} — version drift will cause silent skip.",
            fix_cmd="python -m renmark.doctor --fix",
            auto_fixable=True,
            fix_fn=_fix_register_plugin,
        )
    install_path = Path(entry.get("installPath", ""))
    if not install_path.exists():
        return Check(
            "Claude Code registry",
            "fail",
            f"registry installPath `{install_path}` does not exist on disk.",
            fix_cmd="python -m renmark.doctor --fix",
            auto_fixable=True,
            fix_fn=_fix_register_plugin,
        )
    return Check("Claude Code registry", "pass", f"v{registered_v} at {install_path}")


def check_cache_install_path() -> Check:
    """The cache path that installed_plugins.json points to must resolve to the plugin dir."""
    src_v = _current_version()
    if not src_v:
        return Check("Cache install path", "warn", "VERSION missing — can't check cache")
    cache_path = PLUGINS_DIR / "cache" / MARKETPLACE_NAME / "renmark" / src_v
    if not cache_path.exists():
        return Check(
            "Cache install path",
            "fail",
            f"`{cache_path}` doesn't exist — Claude Code won't find the plugin source.",
            fix_cmd="python -m renmark.doctor --fix",
            auto_fixable=True,
            fix_fn=_fix_cache_symlink,
        )
    if cache_path.is_symlink():
        target = cache_path.resolve()
        if target != PLUGIN_SOURCE.resolve():
            return Check(
                "Cache install path",
                "warn",
                f"`{cache_path}` is a symlink to {target}, not the current plugin source {PLUGIN_SOURCE}",
                fix_cmd="python -m renmark.doctor --fix",
                auto_fixable=True,
                fix_fn=_fix_cache_symlink,
            )
    # Either symlink to right place, or a real dir — both fine
    return Check("Cache install path", "pass", f"{cache_path}")


def check_plugin_symlink() -> Check:
    """The convenience symlink ~/.claude/plugins/renmark → source/plugin/."""
    if not SYMLINK_PATH.exists():
        return Check(
            "Convenience symlink",
            "warn",
            f"`{SYMLINK_PATH}` missing — not required for plugin load, but install.sh creates it.",
            fix_cmd=f"bash {RENMARK_ROOT}/install.sh",
        )
    if SYMLINK_PATH.is_symlink() and SYMLINK_PATH.resolve() != PLUGIN_SOURCE.resolve():
        return Check(
            "Convenience symlink",
            "warn",
            f"`{SYMLINK_PATH}` points to {SYMLINK_PATH.resolve()}, not {PLUGIN_SOURCE}",
            fix_cmd=f"bash {RENMARK_ROOT}/install.sh",
        )
    return Check("Convenience symlink", "pass", str(SYMLINK_PATH))


def check_global_routing_rule() -> Check:
    """ADVISORY-ONLY: is the optional global auto-routing rule installed?

    The renmark routing rule in ``~/.claude/CLAUDE.md`` is opt-in, so this check
    never reports ``fail``/``warn`` — it uses the informational ``"info"`` tier,
    which is excluded from both the failure and warning tallies. It can never
    change doctor's overall pass/fail exit status.
    """
    state = global_routing.detect_global_rule()
    path = global_routing.global_claude_path()
    if state == "present-with-rule":
        return Check("Global auto-routing rule", "info", f"global auto-routing rule present ({path})")
    return Check(
        "Global auto-routing rule",
        "info",
        f"global auto-routing rule not set — run `python -m renmark.doctor --fix` to add it "
        f"(writes {path}, backed up)",
        fix_cmd="python -m renmark.doctor --fix",
        auto_fixable=True,
        fix_fn=_fix_install_global_routing_rule,
    )


CHECKS = [
    check_cli_on_path,
    check_python_package,
    check_version_file,
    check_plugin_manifest,
    check_installed_plugins_registry,
    check_settings_marketplace,
    check_settings_enabled,
    check_cache_install_path,
    check_plugin_symlink,
    check_global_routing_rule,
]


def run_checks() -> DoctorReport:
    return DoctorReport(checks=[c() for c in CHECKS])


# ── Fix functions (callable when --fix is passed) ────────────────────────────


def _fix_add_marketplace() -> str:
    SETTINGS_JSON.parent.mkdir(parents=True, exist_ok=True)
    _backup(SETTINGS_JSON)
    s = _load_json(SETTINGS_JSON)
    s.setdefault("extraKnownMarketplaces", {})[MARKETPLACE_NAME] = {
        "source": {"source": "directory", "path": str(RENMARK_ROOT)}
    }
    SETTINGS_JSON.write_text(json.dumps(s, indent=4))
    return f"added {MARKETPLACE_NAME} → {RENMARK_ROOT} to extraKnownMarketplaces"


def _fix_enable_plugin() -> str:
    SETTINGS_JSON.parent.mkdir(parents=True, exist_ok=True)
    _backup(SETTINGS_JSON)
    s = _load_json(SETTINGS_JSON)
    s.setdefault("enabledPlugins", {})[PLUGIN_KEY] = True
    SETTINGS_JSON.write_text(json.dumps(s, indent=4))
    return f"set enabledPlugins[{PLUGIN_KEY!r}] = true"


def _fix_register_plugin() -> str:
    INSTALLED_PLUGINS_JSON.parent.mkdir(parents=True, exist_ok=True)
    _backup(INSTALLED_PLUGINS_JSON)
    data = _load_json(INSTALLED_PLUGINS_JSON)
    data.setdefault("version", 2)
    data.setdefault("plugins", {})
    v = _current_version() or "0.0.0"
    cache_path = PLUGINS_DIR / "cache" / MARKETPLACE_NAME / "renmark" / v
    now = _dt.datetime.now(_dt.timezone.utc).isoformat().replace("+00:00", "Z")
    data["plugins"][PLUGIN_KEY] = [
        {
            "scope": "user",
            "installPath": str(cache_path),
            "version": v,
            "installedAt": now,
            "lastUpdated": now,
        }
    ]
    INSTALLED_PLUGINS_JSON.write_text(json.dumps(data, indent=2))
    # Also ensure the cache symlink exists
    _fix_cache_symlink()
    return f"registered {PLUGIN_KEY} v{v} at {cache_path}"


def _fix_cache_symlink() -> str:
    v = _current_version() or "0.0.0"
    cache_path = PLUGINS_DIR / "cache" / MARKETPLACE_NAME / "renmark" / v
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    # Clean up other versions
    for sibling in cache_path.parent.iterdir():
        if sibling != cache_path and (sibling.is_symlink() or sibling.is_dir()) and sibling.is_symlink():
            sibling.unlink()
            # Don't delete real dirs — could be user data
    if cache_path.exists() or cache_path.is_symlink():
        cache_path.unlink()
    cache_path.symlink_to(PLUGIN_SOURCE)
    return f"cache symlink {cache_path} → {PLUGIN_SOURCE}"


def _fix_install_global_routing_rule() -> str:
    """ADVISORY: install the opt-in global routing rule. Never affects exit status."""
    result = global_routing.install_global_rule()
    action = result.get("action")
    path = result.get("path")
    backup = result.get("backup")
    if action == "already-present":
        return f"global auto-routing rule already present ({path})"
    msg = f"global auto-routing rule {action} ({path})"
    if backup:
        msg += f"; prior file backed up to {backup}"
    return msg


def apply_fixes(report: DoctorReport) -> list[str]:
    """Run fix_fn for every check with auto_fixable=True. Returns list of applied descriptions."""
    applied: list[str] = []
    for c in report.checks:
        if c.status == "fail" and c.auto_fixable and c.fix_fn:
            try:
                desc = c.fix_fn()
                applied.append(f"[{c.name}] {desc}")
            except Exception as exc:
                applied.append(f"[{c.name}] FIX FAILED: {exc}")
    return applied


# ── Output rendering ─────────────────────────────────────────────────────────


_GLYPH = {"pass": "✓", "fail": "✗", "warn": "!", "info": "i"}


def render_human(report: DoctorReport) -> str:
    out: list[str] = []
    out.append("renmark doctor — diagnosis")
    out.append("")
    for c in report.checks:
        glyph = _GLYPH.get(c.status, "?")
        out.append(f"[{glyph}] {c.name}: {c.detail}")
        if c.status == "fail" and c.fix_cmd:
            out.append(f"     fix: {c.fix_cmd}")
    out.append("")

    n_fail = len(report.failed())
    n_warn = len(report.warned())
    if n_fail == 0 and n_warn == 0:
        out.append("✅ All checks pass. /renmark:* slash commands should be available.")
    else:
        bits = []
        if n_fail:
            bits.append(f"{n_fail} failure{'s' if n_fail != 1 else ''}")
        if n_warn:
            bits.append(f"{n_warn} warning{'s' if n_warn != 1 else ''}")
        out.append(f"{', '.join(bits)} detected.")
        auto = sum(1 for c in report.failed() if c.auto_fixable)
        if auto:
            out.append(f"{auto} can be auto-fixed: `python -m renmark.doctor --fix`")
    return "\n".join(out)


def render_json(report: DoctorReport) -> str:
    return json.dumps(
        {
            "checks": [
                {"name": c.name, "status": c.status, "detail": c.detail, "fix_cmd": c.fix_cmd} for c in report.checks
            ],
            "ok": report.ok(),
        },
        indent=2,
    )


# ── CLI ──────────────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    fix = "--fix" in argv
    as_json = "--json" in argv
    if "-h" in argv or "--help" in argv or "help" in argv:
        sys.stdout.write(__doc__ or "")
        return 0

    report = run_checks()
    if fix:
        applied = apply_fixes(report)
        # ADVISORY: install the opt-in global routing rule on --fix. This is
        # separate from apply_fixes (which only acts on "fail" checks) so it
        # never touches the pass/fail tally, yet --fix still opts the user in.
        try:
            applied.append(f"[Global auto-routing rule] {_fix_install_global_routing_rule()}")
        except Exception as exc:
            applied.append(f"[Global auto-routing rule] FIX FAILED: {exc}")
        if applied and not as_json:
            sys.stdout.write("Applying fixes:\n")
            for line in applied:
                sys.stdout.write(f"  • {line}\n")
            sys.stdout.write("\nRe-checking…\n\n")
        # Re-run after fixes
        report = run_checks()

    if as_json:
        sys.stdout.write(render_json(report) + "\n")
    else:
        sys.stdout.write(render_human(report) + "\n")

    if not report.ok():
        if fix:
            sys.stdout.write("\nSome checks still fail after auto-fix. Manual intervention required.\n")
            sys.stdout.write("After fixing, run `/reload-plugins` in Claude Code.\n")
        else:
            sys.stdout.write("\nAfter fixing, run `/reload-plugins` in Claude Code.\n")
        return 1

    if fix:
        sys.stdout.write("\nRun `/reload-plugins` in Claude Code to pick up the changes.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
