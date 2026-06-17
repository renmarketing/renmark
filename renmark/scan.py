"""The v1 engine for the REQ-14 read-only scheduled QA proposer lane
(``/renmark:scan``).

This module composes the existing read-only deterministic checks — the
:mod:`renmark.audit` engine plus the project's own shell verifiers — normalizes
their output into a flat list of :class:`Finding`, writes a bounded report
artifact, and (on ``--propose``) lands **deduplicated** ``source="qa"`` backlog
items for human triage.

Design contract (mirrors :mod:`renmark.audit` / :mod:`renmark.backlog`):

- **Zero-LLM, never raises into the caller.** Every check is wrapped; a check
  that cannot run is recorded in ``checks_failed_to_run``, downgrades the report
  to ``completion_state="partial"`` with lowered confidence, and the scan
  continues — it never crashes.
- **Read-only by contract.** The ONLY writes a scan performs are (1) its report
  artifact under ``.renmark/reviews/``, (2) the dedup ledger
  ``.renmark/state/proposals.json``, and (3) — only via
  :func:`propose_findings` — backlog items through
  :func:`renmark.backlog.write_item`. It MUST NOT advance ``lifecycle.json``;
  this module deliberately never imports ``renmark.lifecycle.write_lifecycle``.
- **Deduplication before any backlog write.** A SARIF-style stable
  :func:`finding_key` keyed against the ledger guarantees repeated scheduled runs
  never spam the backlog (the Dependabot noise failure mode).

Full design context: ``.renmark/specs/2026-06-15-req14-scan-proposer.spec.md``.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

from . import audit, backlog, summary
from .state import now_iso, state_dir
from .verifier import run_verifier

# ── Tunables ──────────────────────────────────────────────────────────────────

#: The project shell verifiers a scan composes (the project's dev gates). Each is
#: ``(check-name, shell-command, risk)``. A non-zero exit (or a verifier that
#: cannot run) maps to a Finding; a command that cannot run at all is recorded in
#: ``checks_failed_to_run`` and degrades the report to partial.
PROJECT_VERIFIERS: tuple[tuple[str, str, str], ...] = (
    ("pytest", "pytest -q", "high"),
    ("ruff", "ruff check", "medium"),
    ("mypy", "mypy .", "medium"),
)

#: Per-verifier timeout. pytest can be slow on a big suite; keep it generous but
#: bounded so a hung process never wedges a scheduled scan.
_VERIFIER_TIMEOUT_S: int = 300

#: Risk assigned to a normalized audit finding (audit issues are governance /
#: health drift — medium by default).
_AUDIT_RISK: str = "medium"

#: Relative path of the dedup ledger inside ``.renmark/state/``.
_LEDGER_NAME: str = "proposals.json"


# ── Finding ─────────────────────────────────────────────────────────────────


@dataclass
class Finding:
    """One normalized read-only finding. Every field is ``str`` so the dataclass
    is JSON-trivial (mirrors :class:`renmark.backlog.BacklogItem`)."""

    check: str
    rule_id: str
    target: str
    risk: str
    title: str
    summary: str
    recommended_action: str
    fingerprint: str


def finding_key(f: Finding) -> str:
    """Return the SARIF-style stable dedup key ``check:rule_id:target``.

    This is the dedup primitive — stable across runs for the same logical
    finding regardless of its (content-derived) fingerprint. Never raises.
    """
    return f"{f.check}:{f.rule_id}:{f.target}"


def _fingerprint(*, title: str, summary_text: str, target: str) -> str:
    """Short stable content hash of a finding's salient text.

    A change in this value for the same :func:`finding_key` signals the finding
    *changed* (re-surface / update the linked item) rather than recurred
    (skip). Uses sha1 of ``title\\nsummary\\ntarget`` truncated to 12 hex chars —
    short enough to read, wide enough to avoid collisions in practice.
    """
    payload = f"{title}\n{summary_text}\n{target}".encode("utf-8", errors="replace")
    return hashlib.sha1(payload).hexdigest()[:12]


def make_finding(
    *, check: str, rule_id: str, target: str, risk: str, title: str, summary_text: str, action: str
) -> Finding:
    """Construct a :class:`Finding` with its ``fingerprint`` computed from the
    salient content. Centralizes fingerprint derivation so every Finding is
    fingerprinted the same way. Never raises."""
    return Finding(
        check=check,
        rule_id=rule_id,
        target=target,
        risk=risk,
        title=title,
        summary=summary_text,
        recommended_action=action,
        fingerprint=_fingerprint(title=title, summary_text=summary_text, target=target),
    )


# ── Scan report ────────────────────────────────────────────────────────────────


@dataclass
class ScanReport:
    """Structured result of :func:`run_scan`. Carries the G9 transparency fields.

    ``completion_state`` starts ``"complete"`` and downgrades to ``"partial"`` if
    any check fails to run; ``confidence`` is lowered in lockstep.
    """

    findings: list[Finding] = field(default_factory=list)
    checks_run: list[str] = field(default_factory=list)
    checks_failed_to_run: list[str] = field(default_factory=list)
    # G9 transparency:
    completion_state: str = "complete"  # complete | partial | failed
    confidence: str = "high"  # low | medium | high
    validation_status: str = "validated"  # validated | unvalidated | failed

    @property
    def finding_count(self) -> int:
        return len(self.findings)


# ── Read-only check composition ─────────────────────────────────────────────


def _normalize_audit(report: audit.AuditReport) -> list[Finding]:
    """Normalize an :class:`renmark.audit.AuditReport` into Findings.

    ``AuditReport.passes`` maps a pass-name → a list of human-readable issue
    strings. Each issue string becomes one Finding whose ``rule_id`` is the pass
    name and whose ``target`` is a short stable slug derived from the issue text
    (so the same issue keys consistently across runs). Never raises.
    """
    findings: list[Finding] = []
    for pass_name, issues in report.passes.items():
        for issue in issues:
            # The audit issue strings are formatted "<pass>: <detail>"; strip a
            # redundant leading "<pass>: " so the target slug is the detail.
            detail = issue
            prefix = f"{pass_name}: "
            if detail.startswith(prefix):
                detail = detail[len(prefix) :]
            target = _slug(detail)
            findings.append(
                make_finding(
                    check="audit",
                    rule_id=pass_name,
                    target=target,
                    risk=_AUDIT_RISK,
                    title=f"audit/{pass_name}: {_truncate(detail, 80)}",
                    summary_text=issue,
                    action=f"Resolve the {pass_name} issue, then re-run /renmark:audit to confirm.",
                )
            )
    return findings


def _slug(text: str) -> str:
    """A short, stable, filesystem-safe, collision-resistant slug for a finding
    target.

    Deterministic; never raises. The readable prefix (first 48 chars of the
    alnum-collapsed text) is suffixed with a short content hash so two *distinct*
    audit issues whose readable prefixes happen to collide still produce distinct
    ``finding_key``s — without the suffix, a long shared prefix would silently
    merge two different findings into one ledger entry.
    """
    cleaned = "".join(c if c.isalnum() else "-" for c in text.strip().lower())
    cleaned = "-".join(part for part in cleaned.split("-") if part)
    prefix = cleaned[:48].strip("-")
    suffix = hashlib.sha1(text.strip().encode("utf-8", errors="replace")).hexdigest()[:8]
    return f"{prefix}-{suffix}" if prefix else suffix


def _truncate(text: str, n: int) -> str:
    text = text.strip()
    return text if len(text) <= n else text[: n - 1] + "…"


def _run_project_verifiers(repo: Path, report: ScanReport) -> None:
    """Run each project shell verifier, appending a Finding for any failure and
    recording un-runnable checks in ``checks_failed_to_run``. Mutates ``report``
    in place. Never raises."""
    for name, command, risk in PROJECT_VERIFIERS:
        try:
            result = run_verifier(command, cwd=repo, timeout_s=_VERIFIER_TIMEOUT_S)
        except Exception:  # pragma: no cover - run_verifier already never raises
            report.checks_failed_to_run.append(name)
            continue
        report.checks_run.append(name)
        # exit code 127 (command not found) / a timeout both mean the check could
        # not actually evaluate the tree — treat as "failed to run", not a finding.
        if result.timed_out or result.exit_code == 127:
            report.checks_failed_to_run.append(name)
            continue
        if result.exit_code != 0:
            tail = _truncate(result.tail.replace("\n", " ⏎ "), 600)
            report.findings.append(
                make_finding(
                    check="verifier",
                    rule_id=name,
                    target=name,
                    risk=risk,
                    title=f"{name} failed (exit {result.exit_code})",
                    summary_text=f"`{command}` exited {result.exit_code}. Tail: {tail}",
                    action=f"Run `{command}` locally and fix the reported failures.",
                )
            )


def run_scan(repo: Path | str) -> ScanReport:
    """Run the full read-only scan and return a structured :class:`ScanReport`.

    Composes :func:`renmark.audit.run_audit` and the project shell verifiers
    (``pytest -q`` / ``ruff check`` / ``mypy .``), normalizing every issue /
    failure into a :class:`Finding`. A check that cannot run is recorded in
    ``checks_failed_to_run`` and downgrades the report to ``partial`` with
    lowered confidence. Zero-LLM; never raises into the caller.
    """
    repo = Path(repo)
    report = ScanReport()

    # 1. Audit engine (already never raises).
    try:
        audit_report = audit.run_audit(repo)
    except Exception:  # pragma: no cover - run_audit is defensive, belt-and-braces
        report.checks_failed_to_run.append("audit")
    else:
        report.checks_run.append("audit")
        report.findings.extend(_normalize_audit(audit_report))

    # 2. Project shell verifiers.
    _run_project_verifiers(repo, report)

    # 3. Degrade the report's G9 fields if any check could not run.
    if report.checks_failed_to_run:
        report.completion_state = "partial"
        report.confidence = "low"
        report.validation_status = "unvalidated"
    elif not report.checks_run:
        # Nothing ran at all — the scan produced no evidence.
        report.completion_state = "failed"
        report.confidence = "low"
        report.validation_status = "failed"

    return report


# ── Dedup ledger ───────────────────────────────────────────────────────────────


def _ledger_path(repo: Path | str) -> Path:
    return state_dir(repo) / _LEDGER_NAME


def load_ledger(repo: Path | str) -> dict[str, dict[str, object]]:
    """Load the dedup ledger from ``.renmark/state/proposals.json``.

    Maps ``finding_key`` → ``{backlog_id, fingerprint, first_seen, last_seen,
    state}``. A missing or corrupt file (unreadable bytes, invalid JSON, or a
    non-dict payload) degrades to an empty dict so the scan rebuilds rather than
    blocking. Never raises.
    """
    path = _ledger_path(repo)
    try:
        if not path.exists():
            return {}
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    # Drop any non-dict entries so downstream readers can assume a dict value.
    return {k: v for k, v in data.items() if isinstance(k, str) and isinstance(v, dict)}


def save_ledger(repo: Path | str, ledger: dict[str, dict[str, object]]) -> None:
    """Persist the dedup ledger to ``.renmark/state/proposals.json``.

    Best-effort atomic replace (sibling ``.tmp`` then ``Path.replace``); a
    non-serialisable ledger or any IO failure degrades to a no-op — never raises
    into the caller (mirrors :func:`renmark.backlog.write_item`).
    """
    path = _ledger_path(repo)
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        payload = json.dumps(ledger, indent=2, sort_keys=True) + "\n"
    except (TypeError, ValueError):
        return
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(payload, encoding="utf-8")
        tmp.replace(path)
    except OSError:
        try:
            if tmp.exists():
                tmp.unlink()
        except OSError:
            pass
        return


# ── Report writer ──────────────────────────────────────────────────────────────


def _report_rel_path(repo: Path | str) -> str:
    """Compute the report's repo-relative path (``.renmark/reviews/<date>-scan.review.md``).

    Date comes from :func:`renmark.state.now_iso` (NOT ``datetime.now`` — keeps
    the determinism convention so tests can pin time at one seam). Never raises.
    """
    date_str = now_iso()[:10]  # YYYY-MM-DD slice of the ISO8601 timestamp
    return f".renmark/reviews/{date_str}-scan.review.md"


def _render_body(report: ScanReport) -> str:
    """Render the full findings + evidence markdown body (heavy text lives on
    disk, never in the orchestrator summary)."""
    lines = ["# renmark scan report", ""]
    lines.append(f"- checks run: {', '.join(report.checks_run) or '(none)'}")
    lines.append(f"- checks failed to run: {', '.join(report.checks_failed_to_run) or '(none)'}")
    lines.append(f"- findings: {report.finding_count}")
    lines.append("")
    if not report.findings:
        lines.append("## Findings\n\n- (clean — no findings)")
        return "\n".join(lines)
    lines.append("## Findings")
    lines.append("")
    for f in report.findings:
        lines.append(f"### {f.title}")
        lines.append(f"- key: `{finding_key(f)}`")
        lines.append(f"- fingerprint: `{f.fingerprint}`")
        lines.append(f"- risk: {f.risk}")
        lines.append(f"- summary: {f.summary}")
        lines.append(f"- recommended action: {f.recommended_action}")
        lines.append("")
    return "\n".join(lines).rstrip()


def write_report(repo: Path | str, report: ScanReport) -> str:
    """Write the scan report to ``.renmark/reviews/<date>-scan.review.md``.

    Delegates to :func:`renmark.summary.write_artifact` so G6 provenance + G9
    transparency metadata is automatic, and the orchestrator/user sees only the
    ≤5-line ``## Summary``. Returns the repo-relative artifact path — the same
    path :func:`propose_findings` records as each item's ``evidence_path`` (so
    compute it once, before proposing). Never raises into the caller beyond a
    summary-boundary bug (which is a real programmer error, not runtime data).
    """
    repo = Path(repo)
    rel_path = _report_rel_path(repo)
    out_path = repo / rel_path

    summary_lines: list[str] = [
        f"{report.finding_count} finding{'s' if report.finding_count != 1 else ''} "
        f"({report.completion_state}, confidence={report.confidence})",
        f"checks run: {', '.join(report.checks_run) or '(none)'}",
    ]
    if report.checks_failed_to_run:
        summary_lines.append(f"could not run: {', '.join(report.checks_failed_to_run)}")
    # Lead with the highest-risk finding titles, bounded by the G3 cap.
    for f in report.findings:
        if len(summary_lines) >= summary.MAX_SUMMARY_LINES:
            break
        summary_lines.append(_truncate(f.title, 110))
    if report.finding_count == 0 and len(summary_lines) < summary.MAX_SUMMARY_LINES:
        summary_lines.append("no findings — nothing to propose")

    summary.write_artifact(
        out_path,
        artifact_type="scan",
        body=_render_body(report),
        summary_lines=summary_lines[: summary.MAX_SUMMARY_LINES],
        source_sha=summary.git_head_sha(repo),
        generator="scan",
        completion_state=report.completion_state,
        confidence=report.confidence,
        validation_status=report.validation_status,
    )
    return rel_path


# ── Proposal (the single backlog seam) ──────────────────────────────────────────


def propose_findings(repo: Path | str, report: ScanReport) -> list[str]:
    """Land deduplicated ``source="qa"`` backlog items for the report's findings.

    For each finding, keyed by :func:`finding_key` against the ledger:

    - **unseen key** → write a new ``status="needs review"`` / ``source="qa"``
      :class:`renmark.backlog.BacklogItem` (with ``evidence_path`` → the report)
      and record it in the ledger.
    - **seen + same fingerprint** → skip (the dedup guarantee — repeated scans
      never spam the backlog).
    - **seen + changed fingerprint** → update / re-surface the linked item
      (rewrite it back to ``needs review`` so the human re-triages) and refresh
      the ledger's fingerprint + ``last_seen``.

    The report MUST already be written (so ``evidence_path`` resolves) — callers
    invoke :func:`write_report` first. Returns the list of newly-proposed backlog
    IDs (re-surfaced existing items are not counted as new). A ``write_item``
    failure is swallowed per-finding (the report still persists); the finding is
    not recorded so a later run retries it. Never raises into the caller.
    """
    repo = Path(repo)
    ledger = load_ledger(repo)
    evidence_path = _report_rel_path(repo)
    stamp = now_iso()
    new_ids: list[str] = []

    for f in report.findings:
        key = finding_key(f)
        entry = ledger.get(key)

        if isinstance(entry, dict) and entry.get("fingerprint") == f.fingerprint:
            # Seen, unchanged — skip. Touch last_seen so the ledger reflects the run.
            entry["last_seen"] = stamp
            continue

        if isinstance(entry, dict) and entry.get("backlog_id"):
            # Seen but changed — re-surface the linked item rather than duplicate.
            item_id = str(entry.get("backlog_id"))
            existing = backlog.read_item(repo, item_id)
            if existing is not None:
                existing.title = f.title
                existing.summary = f.summary
                existing.risk = f.risk
                existing.recommended_action = f.recommended_action
                existing.evidence_path = evidence_path
                existing.status = "needs review"  # re-surface for triage
                existing.updated_at = stamp
                backlog.write_item(repo, existing)
            entry["fingerprint"] = f.fingerprint
            entry["last_seen"] = stamp
            entry["state"] = "re-surfaced"
            continue

        # Unseen — propose a fresh backlog item.
        item_id = backlog.next_id(repo)
        item = backlog.BacklogItem(
            id=item_id,
            title=f.title,
            status="needs review",
            source="qa",
            risk=f.risk,
            summary=f.summary,
            evidence_path=evidence_path,
            recommended_action=f.recommended_action,
            created_at=stamp,
            updated_at=stamp,
        )
        written = backlog.write_item(repo, item)
        if written is None:
            # write_item failed — don't record so a later run retries this finding.
            continue
        ledger[key] = {
            "backlog_id": item_id,
            "fingerprint": f.fingerprint,
            "first_seen": stamp,
            "last_seen": stamp,
            "state": "proposed",
        }
        new_ids.append(item_id)

    save_ledger(repo, ledger)
    return new_ids


# ── Read-only enforcement (PreToolUse hook) ─────────────────────────────────────

#: PreToolUse hook command. Reads the proposed Bash command from the hook stdin
#: JSON (``tool_input.command``) and emits a block decision when it matches any
#: git-mutating / destructive verb. Matched → print a ``{"decision":"block"}``
#: JSON object AND exit non-zero (defense in depth: either signal is sufficient
#: for Claude Code to deny). Otherwise allow (exit 0, no output).
#:
#: Kept as a single self-contained python one-liner so it pastes into
#: settings.json with no external script file to install.
_READONLY_HOOK_COMMAND: str = (
    "python3 -c \""
    "import sys,json,re;"
    "d=json.load(sys.stdin);"
    "c=(d.get('tool_input') or {}).get('command','');"
    "pat=re.compile(r'\\\\bgit\\\\s+(commit|push|merge|rebase|tag)\\\\b"
    "|\\\\bgit\\\\s+reset\\\\s+--hard\\\\b"
    "|\\\\bgit\\\\s+branch\\\\s+-[dD]\\\\b"
    "|\\\\bgit\\\\s+checkout\\\\s+-b\\\\b"
    "|\\\\brm\\\\s+-rf\\\\b');"
    "m=pat.search(c);"
    "print(json.dumps({'decision':'block',"
    "'reason':'renmark:scan is read-only; mutating git/rm command denied'})) if m else None;"
    "sys.exit(2 if m else 0)"
    "\""
)

#: Claude Code PreToolUse hook config for the read-only scheduled scan. Paste the
#: ``hooks`` block into settings.json; the matcher fires only on ``Bash`` tool
#: calls and the command denies git-mutating / destructive verbs.
READONLY_HOOK: dict[str, object] = {
    "hooks": {
        "PreToolUse": [
            {
                "matcher": "Bash",
                "hooks": [
                    {
                        "type": "command",
                        "command": _READONLY_HOOK_COMMAND,
                    }
                ],
            }
        ]
    }
}


# ── Cron / trigger helper ────────────────────────────────────────────────────


def emit_cron(repo: Path | str) -> str:
    """Return (PRINT-only, no writes) the headless read-only trigger setup text.

    Three blocks: (1) the headless cron line with the restricted tool-list +
    ``--permission-mode dontAsk``; (2) the :data:`READONLY_HOOK` JSON to paste
    into ``settings.json`` (defense-in-depth Bash denylist); (3) the one-time
    auth note. Pure string — never writes, never raises.
    """
    repo = Path(repo)
    cron_line = (
        'claude -p "/renmark:scan --propose" '
        '--tools "Read,Bash,Grep,Glob" '
        '--disallowedTools "Edit,Write" '
        "--permission-mode dontAsk"
    )
    hook_json = json.dumps(READONLY_HOOK, indent=2)
    return (
        "# renmark:scan — read-only scheduled QA proposer trigger\n"
        f"# repo: {repo}\n"
        "#\n"
        "# 1. Headless cron line (WSL cron / Windows Task Scheduler):\n"
        f"{cron_line}\n"
        "#\n"
        "# 2. PreToolUse Bash-denylist hook — paste into settings.json (the\n"
        "#    `hooks` key denies git-mutating / destructive commands even though\n"
        "#    Bash is enabled for verifiers):\n"
        f"{hook_json}\n"
        "#\n"
        "# 3. One-time auth (headless runs need a token, not interactive login):\n"
        "#    claude setup-token\n"
        "#    export CLAUDE_CODE_OAUTH_TOKEN=<token printed above>\n"
    )


__all__ = [
    "READONLY_HOOK",
    "Finding",
    "ScanReport",
    "emit_cron",
    "finding_key",
    "load_ledger",
    "make_finding",
    "propose_findings",
    "run_scan",
    "save_ledger",
    "write_report",
]
