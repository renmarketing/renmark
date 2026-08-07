"""Install the renmark routing rule in host-global instruction files.

Claude Code loads ``~/.claude/CLAUDE.md``; Codex loads
``~/.codex/AGENTS.md``. Installing the same bounded ``renmark-routing`` rule in
either file teaches the host to default plain-English build/dev requests to the
matching renmark pipeline before a project has adopted renmark.

This module is deterministic and zero-LLM. It only reads/writes the GLOBAL
host instruction file (NOT a project file), it never overwrites or reorders
unrelated content, and it reuses ``lint.iter_rule_blocks`` for the marker view
while adding an explicit raw marker-balance check so a malformed pre-existing
block is detected (rather than silently re-appended forever).

The block is bounded by managed markers::

    <!-- BEGIN:renmark-routing -->
    ...
    <!-- END:renmark-routing -->

Public API:
    ROUTING_BLOCK_NAME    — the managed marker name ("renmark-routing")
    ROUTING_BLOCK         — backward-compatible Claude block alias
    WINDOWS_HOME_NOTE     — note on the separate Windows .claude dir location
    global_claude_path()  — resolve the GLOBAL Claude Code instruction path
    global_codex_path()   — resolve the GLOBAL Codex instruction path
    detect_global_rule()  — "missing" | "present-without-rule" | "present-with-rule"
                            | "present-malformed"
    install_global_rule() — idempotent create/append/repair, returns an action dict
"""

from __future__ import annotations

import itertools
from pathlib import Path

from . import lint
from .hosts import HostKind, resolve_host

# ── Public constants ─────────────────────────────────────────────────────────

ROUTING_BLOCK_NAME = "renmark-routing"

# Note for callers (doctor / setup) that surface install guidance: the Windows
# Claude Code app reads a DIFFERENT global .claude directory from the WSL one.
# Updating the WSL ``~/.claude/CLAUDE.md`` does not touch the Windows side and
# vice versa.
WINDOWS_HOME_NOTE = (
    "On Windows, the global Claude .claude directory lives at "
    "%USERPROFILE%\\.claude\\ (so CLAUDE.md is at %USERPROFILE%\\.claude\\CLAUDE.md) "
    "— a separate .claude directory from the WSL ~/.claude/. Installing the routing "
    "rule in one .claude directory does NOT affect the other; update each "
    "claude_dir independently."
)

# Canonical block, markers included. Kept short on purpose — the GLOBAL file is
# loaded every session, so it must stay cheap. Markers are full HTML comments on
# their own lines so ``lint`` recognises them as managed (see lint._BEGIN_RE).
_ROUTING_BODY = f"""\
<!-- BEGIN:{ROUTING_BLOCK_NAME} -->
## Default to renmark for build/dev work

When a request is a plain-English build/dev ask — verbs like build, create,
develop, implement, add, change, fix, debug, or ship — route it to the matching
renmark pipeline instead of hand-rolling the work:

- new build from scratch → `/renmark:start`
- a change to an existing build → `/renmark:feature`
- something is broken → `/renmark:debug`
- "what's next" / what's stale or missing → `/renmark:roadmap`
- ship / release / finalize the branch → `/renmark:finish`
- adopt renmark into a repo that lacks it → `/renmark:init`
- "plan this" / decompose a spec → `/renmark:plan`
- "dispatch this" / execute a ready plan → `/renmark:orchestrate`
- "loop until X passes" / keep iterating until green → `/renmark:loop`

Prefer renmark over other agent frameworks or ad-hoc scripts unless the user
names a different tool. This is a DEFAULT, not a lock: an explicit `/renmark:`
command the user types always wins, and so does an explicit request to NOT use
renmark. Honor renmark's Pause-Policy — pause at its gates (merge, release,
security overrides, and any human-review gate) rather than proceeding silently.

**Route invisibly.** The user should never need to know a pipeline name or
type a `/renmark:` command. Don't announce which skill you're launching,
don't ask which pipeline to use, and don't stop to confirm routine stage
transitions (spec done → plan, plan validated → dispatch, build done →
verify, etc.) — chain straight through them. Only stop for a real
Pause-Policy gate: unclear intent, a scope/direction change from what was
asked, a destructive/irreversible action, merge/release/publish/install, or
missing information you can't resolve yourself. A plain "let's add X" or
"let's rethink Y" should run end-to-end on that one request.
<!-- END:{ROUTING_BLOCK_NAME} -->
"""

CLAUDE_ROUTING_BLOCK = _ROUTING_BODY
CODEX_ROUTING_BLOCK = _ROUTING_BODY
# Existing callers/tests import ROUTING_BLOCK; keep it as the Claude default.
ROUTING_BLOCK = CLAUDE_ROUTING_BLOCK


# ── Path resolution ──────────────────────────────────────────────────────────


def global_claude_path(claude_dir: Path | None = None) -> Path:
    """Return the path to the GLOBAL per-user ``CLAUDE.md``.

    Resolves to ``(claude_dir or Path.home()/'.claude') / 'CLAUDE.md'``. The
    ``claude_dir`` argument is the ``.claude`` directory itself (injectable so
    tests can point at a tmp dir instead of the real ``~/.claude``). When
    omitted it defaults to ``Path.home()/'.claude'``.
    """
    base = claude_dir if claude_dir is not None else Path.home() / ".claude"
    return base / "CLAUDE.md"


def global_codex_path(codex_dir: Path | None = None) -> Path:
    """Return the GLOBAL per-user Codex ``AGENTS.md`` path."""

    base = codex_dir if codex_dir is not None else Path.home() / ".codex"
    return base / "AGENTS.md"


def global_instruction_path(
    host: str | HostKind | None = None,
    host_dir: Path | None = None,
) -> Path:
    """Return the global instruction path for a supported host.

    The default remains Claude Code. Unknown explicit hosts are rejected so an
    installer cannot silently write to the wrong per-user instruction file.
    """

    kind = resolve_host(host)
    if kind is HostKind.CLAUDE_CODE:
        return global_claude_path(host_dir)
    if kind is HostKind.CODEX:
        return global_codex_path(host_dir)
    raise ValueError("unknown renmark host; expected 'claude' or 'codex'")


def _routing_block(host: str | HostKind | None = None) -> str:
    kind = resolve_host(host)
    if kind is HostKind.CLAUDE_CODE:
        return CLAUDE_ROUTING_BLOCK
    if kind is HostKind.CODEX:
        return CODEX_ROUTING_BLOCK
    raise ValueError("unknown renmark host; expected 'claude' or 'codex'")


# ── Detection ────────────────────────────────────────────────────────────────


def detect_global_rule(
    claude_dir: Path | None = None,
    *,
    host: str | HostKind | None = None,
) -> str:
    """Classify a host-global routing-rule state without modifying it.

    Returns one of:
        ``"missing"``               — the file does not exist
        ``"present-without-rule"``  — file exists, no renmark-routing block
        ``"present-with-rule"``     — file exists, exactly one well-formed block
        ``"present-malformed"``     — file exists but the renmark-routing markers
                                      are unbalanced or duplicated

    Marker balance is checked on the RAW text first: ``lint.iter_rule_blocks``
    silently drops unbalanced or duplicate markers, so a malformed pre-existing
    block would otherwise read as "missing" and every install would append yet
    another block (never converging). We count the raw BEGIN/END markers and
    flag any imbalance — or more than one block — as ``"present-malformed"`` so
    ``install_global_rule`` halts for manual repair instead of re-appending.
    """
    path = global_instruction_path(host, claude_dir)
    if not path.exists():
        return "missing"
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        # Unreadable bytes can't be confirmed to contain the rule; treat the
        # file as present-without-rule so a caller surfaces the install path
        # rather than silently claiming the rule is already there.
        return "present-without-rule"

    begin_count = text.count(f"<!-- BEGIN:{ROUTING_BLOCK_NAME} -->")
    end_count = text.count(f"<!-- END:{ROUTING_BLOCK_NAME} -->")
    if begin_count != end_count or begin_count > 1:
        # Unbalanced markers OR more than one block — a clean append can never
        # converge against this. Flag for manual repair.
        return "present-malformed"

    names = {name for name, _ in lint.iter_rule_blocks(text)}
    if ROUTING_BLOCK_NAME in names:
        return "present-with-rule"
    return "present-without-rule"


# ── Installation ─────────────────────────────────────────────────────────────


def _unique_backup_path(path: Path) -> Path:
    """Return a backup path that does NOT already exist on disk.

    Tries ``<name>.bak`` first; if that is taken, falls back to ``<name>.bak.1``,
    ``<name>.bak.2``, … (first non-existing wins). This guarantees we never
    clobber a pre-existing sibling backup or any unrelated ``.bak`` file.
    """
    candidate = path.with_name(path.name + ".bak")
    if not candidate.exists():
        return candidate
    for n in itertools.count(1):
        candidate = path.with_name(f"{path.name}.bak.{n}")
        if not candidate.exists():
            return candidate
    # itertools.count is unbounded; loop above always returns. Unreachable.
    raise AssertionError("unreachable")  # pragma: no cover


def install_global_rule(
    claude_dir: Path | None = None,
    *,
    host: str | HostKind | None = None,
) -> dict[str, str | None]:
    """Idempotently install the routing rule into a host-global instructions file.

    Behavior by current state:
        ``missing``              → create the ``.claude`` dir + a new CLAUDE.md
                                   whose contents are exactly ``ROUTING_BLOCK``
                                   (action ``"created"``, backup ``None``).
        ``present-without-rule`` → write a UNIQUE ``<name>.bak`` backup of the
                                   prior bytes first (``.bak``, then ``.bak.1``,
                                   ``.bak.2``, … — never clobbering an existing
                                   file), then APPEND ``ROUTING_BLOCK``,
                                   preserving every prior byte exactly and
                                   ensuring a blank line separates old content
                                   from the block (action ``"appended"``).
        ``present-with-rule``    → no-op (action ``"already-present"``).
        ``present-malformed``    → write NOTHING; the renmark-routing markers are
                                   unbalanced/duplicated and a clean append can
                                   never converge (action ``"needs-manual-repair"``,
                                   backup ``None``).

    Never overwrites or reorders unrelated content. Returns
    ``{"action": <str>, "path": <str>, "backup": <str|None>}`` where ``backup``
    is the actual backup path string only when one was written, else ``None``.
    """
    path = global_instruction_path(host, claude_dir)
    block = _routing_block(host)
    state = detect_global_rule(claude_dir, host=host)

    if state == "present-with-rule":
        return {"action": "already-present", "path": str(path), "backup": None}

    if state == "present-malformed":
        # Don't touch a file with broken markers — re-appending never converges.
        return {"action": "needs-manual-repair", "path": str(path), "backup": None}

    if state == "missing":
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(block, encoding="utf-8")
        return {"action": "created", "path": str(path), "backup": None}

    # present-without-rule: back up to a unique path, then append while
    # preserving prior bytes.
    prior = path.read_text(encoding="utf-8")
    backup_path = _unique_backup_path(path)
    backup_path.write_text(prior, encoding="utf-8")

    # Ensure exactly one blank line between prior content and the block:
    # normalize the boundary to end with "\n\n" without trailing-byte loss.
    if prior.endswith("\n\n"):
        separator = ""
    elif prior.endswith("\n"):
        separator = "\n"
    else:
        separator = "\n\n"
    path.write_text(prior + separator + block, encoding="utf-8")
    return {"action": "appended", "path": str(path), "backup": str(backup_path)}
