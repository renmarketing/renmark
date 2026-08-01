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
- **What scan.py itself writes (and does not do).** ``scan.py`` performs no git,
  product-file, or PRD mutation and never commits, merges, pushes, releases, or
  executes fixes. Its OWN writes are confined to ``.renmark/`` state: (1) the
  report artifact under ``.renmark/reviews/``, (2) the dedup ledger
  ``.renmark/state/proposals.json``, and (3) — only via :func:`propose_findings`
  — backlog items, which means it creates AND (on a failed write) deletes a
  backlog *reservation* file via :func:`renmark.backlog.next_id` /
  :func:`_rollback_reserved` under ``.renmark/state/backlog/`` in addition to the
  final :func:`renmark.backlog.write_item`. It MUST NOT advance ``lifecycle.json``;
  this module deliberately never imports or calls the lifecycle writer.
- **Read-only CHECKS run your project's own code.** REQ-14 authorizes the lane to
  run read-only checks (pytest / ruff / mypy). Those verifiers execute the
  PROJECT'S own code — conftest, fixtures, plugins, ``setup.cfg`` hooks — so the
  scan is NOT a sandbox and the checks it runs are NOT guaranteed side-effect-free.
  Run a scheduled scan at the SAME trust level as running your own test suite. The
  read-only property is about what ``scan.py`` itself does (no mutate / commit /
  merge / push / release / fix-exec), not a claim that the verifiers it invokes
  cannot have side effects.
- **Deduplication before any backlog write.** A SARIF-style stable
  :func:`finding_key` keyed against the ledger guarantees repeated scheduled runs
  never spam the backlog (the Dependabot noise failure mode). The ledger
  load→check→write→save sequence is serialised with a stdlib file lock
  (:func:`_ledger_lock`) so overlapping scheduled scans can't double-file.

Read-only posture — where the real boundary is
-----------------------------------------------
The read-only guarantee is **STRUCTURAL** at the ``scan.py`` level: this module
has no code path that commits, merges, pushes, releases, edits product files, or
executes a fix. The PRIMARY scheduled trigger is the pure-Python CLI
``renmark-execute --scan --propose`` run from the repo root by external cron /
Windows Task Scheduler (see :func:`emit_cron`). That process's writes are
confined to ``.renmark/`` state (the report, the dedup ledger, and the backlog
reservation + item). It is NOT a sandbox: the read-only CHECKS it runs (pytest /
ruff / mypy) execute the project's own code, so treat a scheduled scan at the
same trust level as running your test suite — do not read the structural
guarantee as "nothing it runs can mutate."

The :data:`READONLY_HOOK` Bash denylist is **OPTIONAL, best-effort defense-in-
depth** — relevant ONLY to the alternative model-driven trigger
(``claude -p "/renmark:scan --propose"``), which does have a Bash tool.
Denylists can never be proven exhaustive (absolute paths, ``env``/``command``
prefixes, ``bash -c``, ``eval``, command substitution), so the hook is NOT a
guarantee and the project no longer tries to make it airtight. The structural
Python trigger is the boundary; the hook is a backstop on the optional path.

Full design context: ``.renmark/specs/2026-06-15-req14-scan-proposer.spec.md``.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import sys
import uuid
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

from . import audit, backlog, summary
from .ledger import InspectionReport, append_ledger_event
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


def finding_key_from_parts(*, check: str, rule_id: str, target: str) -> str:
    """Return the SARIF-style stable dedup key ``check:rule_id:target``.

    Accepting the key's explicit parts lets other proposer lanes reuse Scan's
    stable identity contract without needing to construct a :class:`Finding`.
    Never raises.
    """
    return f"{check}:{rule_id}:{target}"


def finding_key(f: Finding) -> str:
    """Return the stable dedup key for ``f``.

    This is the dedup primitive — stable across runs for the same logical
    finding regardless of its (content-derived) fingerprint. Never raises.
    """
    return finding_key_from_parts(check=f.check, rule_id=f.rule_id, target=f.target)


def content_fingerprint(*, title: str, summary_text: str, target: str) -> str:
    """Short stable content hash of a finding's salient text.

    A change in this value for the same :func:`finding_key` signals the finding
    *changed* (re-surface / update the linked item) rather than recurred
    (skip). Uses sha1 of ``title\\nsummary\\ntarget`` truncated to 12 hex chars —
    short enough to read, wide enough to avoid collisions in practice.
    """
    payload = f"{title}\n{summary_text}\n{target}".encode("utf-8", errors="replace")
    return hashlib.sha1(payload).hexdigest()[:12]


# Backward compatibility for existing callers and tests.
_fingerprint = content_fingerprint


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
    #: The exact repo-relative path :func:`write_report` wrote this report to.
    #: Threaded into each proposed item's ``evidence_path`` so the link always
    #: points at the *actual* artifact (never a recomputed date-only guess that
    #: a same-day re-scan would silently retarget). Empty until ``write_report``.
    evidence_path: str = ""

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


#: Relative path of the advisory lock guarding the ledger's read→write cycle.
_LEDGER_LOCK_NAME: str = "proposals.lock"


def _warn_lock_degraded(reason: str) -> None:
    """Surface a lost-concurrency-safety condition on stderr (one line).

    The scan still completes, but a silent fall-through to unserialised
    load→write→save under contention could double-file a finding — so the loss
    MUST be visible, never silent. Best-effort; never raises.
    """
    with contextlib.suppress(Exception):
        print(
            f"renmark:scan WARNING: ledger lock unavailable ({reason}); "
            "proceeding WITHOUT concurrency safety — overlapping scans may double-file.",
            file=sys.stderr,
        )


@contextlib.contextmanager
def _ledger_lock(repo: Path | str, degraded: list[str] | None = None) -> Iterator[None]:
    """Serialise the ledger load→check→write→save cycle across concurrent scans.

    Uses a stdlib advisory file lock (``fcntl.flock`` on a ``.proposals.lock``
    sentinel inside ``.renmark/state/``) so two overlapping scheduled scans can't
    both observe a finding as "new" and double-file it. Dependency-free.

    Degrades gracefully and NEVER raises, but **never silently**: if ``fcntl`` is
    unavailable (non-POSIX) or the lock file can't be opened/locked, the body
    still runs unserialised — but the loss of concurrency safety is surfaced as a
    one-line ``sys.stderr`` warning AND appended to the optional ``degraded`` list
    (a string reason) so the caller / report can see it. A single scan must never
    crash because it couldn't take the lock, but it must never pretend it was
    serialised when it wasn't. The lock is always released.
    """

    def _mark(reason: str) -> None:
        if degraded is not None:
            degraded.append(reason)
        _warn_lock_degraded(reason)

    try:
        import fcntl  # POSIX only; absent on Windows.
    except ImportError:  # pragma: no cover - non-POSIX fallback
        _mark("fcntl unavailable (non-POSIX)")
        yield
        return

    path = _ledger_path(repo).with_name(_LEDGER_LOCK_NAME)
    fd: int | None = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o644)
    except OSError as exc:  # pragma: no cover - lock dir/file unavailable
        if fd is not None:
            with contextlib.suppress(OSError):
                os.close(fd)
        _mark(f"lock file open failed: {exc}")
        yield
        return

    locked = False
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            locked = True
        except OSError as exc:  # pragma: no cover - lock acquisition failed
            _mark(f"flock failed: {exc}")
        yield
    finally:
        if locked:
            with contextlib.suppress(OSError):
                fcntl.flock(fd, fcntl.LOCK_UN)
        with contextlib.suppress(OSError):
            os.close(fd)


# ── Report writer ──────────────────────────────────────────────────────────────


def _report_rel_path(report: ScanReport) -> str:
    """Compute a *unique* repo-relative report path.

    Shape: ``.renmark/reviews/<date>-<time>-<hash>-scan.review.md``. The date +
    time come from :func:`renmark.state.now_iso` (NOT ``datetime.now`` — keeps
    the determinism convention so tests can pin time at one seam). The short hash
    folds in the report's full content — ``completion_state``, ``checks_run``,
    ``checks_failed_to_run`` (previously omitted, which let two reports differing
    ONLY in which checks failed collide), and every finding fingerprint — AND a
    true per-write nonce so two same-second scans of an identical tree still get
    distinct files. The nonce is a full 128-bit ``uuid4().hex`` (widened from the
    previous 32-bit ``os.urandom(4)``, whose birthday-collision odds were
    non-negligible across a day of frequent scans). :func:`write_report` ALSO
    re-rolls the path under an ``O_EXCL`` create loop, so even a hash collision can
    never overwrite an existing artifact. Never raises.
    """
    stamp = now_iso()
    date_str = stamp[:10]  # YYYY-MM-DD
    # Time component: digits only from the HH:MM:SS slice, robust to ISO variants.
    time_str = "".join(c for c in stamp[11:19] if c.isdigit()) or "000000"
    # Content hash: folds in completion_state, BOTH check lists, and finding
    # fingerprints, plus a per-write 128-bit nonce so identical-content same-second
    # scans never collide. The nonce alone guarantees uniqueness; the content is
    # kept so the path still hints at what the report contained.
    nonce = uuid.uuid4().hex
    digest_src = "\n".join(
        [
            report.completion_state,
            *report.checks_run,
            *report.checks_failed_to_run,
            *(f.fingerprint for f in report.findings),
            nonce,
        ]
    )
    short = hashlib.sha1(digest_src.encode("utf-8", errors="replace")).hexdigest()[:8]
    return f".renmark/reviews/{date_str}-{time_str}-{short}-scan.review.md"


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


#: Bounded re-rolls when an ``O_EXCL`` report-path reservation hits an existing
#: file (a hash+nonce collision — astronomically rare, but never overwrite).
_REPORT_RESERVE_RETRIES: int = 8


def _reserve_report_path(repo: Path, report: ScanReport) -> str:
    """Reserve a *non-colliding* report path via ``O_EXCL`` and return it (repo-
    relative).

    Computes a candidate via :func:`_report_rel_path` (which carries a 128-bit
    nonce) and atomically claims it by creating an empty file with
    ``O_CREAT | O_EXCL``. If the name already exists (the vanishingly-rare nonce
    collision, or a same-second sibling), it re-rolls a fresh candidate rather
    than reusing the colliding name — so :func:`renmark.summary.write_artifact`
    fills a file this call owns and two writes can never clobber. On exhausted
    retries or any IO error it degrades to the last computed path WITHOUT a
    reservation (write_artifact still writes it); the nonce makes a real collision
    on that fallback negligible. Never raises into the caller.
    """
    rel_path = _report_rel_path(report)
    for _ in range(_REPORT_RESERVE_RETRIES):
        out_path = repo / rel_path
        try:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            fd = os.open(out_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        except FileExistsError:
            # Name already taken — re-roll a fresh nonce-bearing candidate.
            rel_path = _report_rel_path(report)
            continue
        except OSError:
            # Can't reserve (perms / disk) — degrade to the computed path; the
            # nonce keeps a true collision negligible and write_artifact still writes.
            return rel_path
        with contextlib.suppress(OSError):
            os.close(fd)
        return rel_path
    # Retries exhausted (pathological collision storm) — degrade to last candidate.
    return rel_path


def write_report(repo: Path | str, report: ScanReport) -> str:
    """Write the scan report to ``.renmark/reviews/<date>-scan.review.md``.

    Delegates to :func:`renmark.summary.write_artifact` so G6 provenance + G9
    transparency metadata is automatic, and the orchestrator/user sees only the
    ≤5-line ``## Summary``. Returns the repo-relative artifact path — the same
    path :func:`propose_findings` records as each item's ``evidence_path`` (so
    compute it once, before proposing). Never raises into the caller beyond a
    summary-boundary bug (which is a real programmer error, not runtime data).

    Side effect: stores the written path on ``report.evidence_path`` so a later
    :func:`propose_findings` links the EXACT artifact, never a recomputed guess.

    Collision safety: the target path is reserved with an ``O_EXCL`` create before
    :func:`renmark.summary.write_artifact` fills it, re-rolling the (nonce-bearing)
    path on the vanishingly-rare event the name already exists. Two writes can
    therefore never clobber each other — a same-name collision regenerates rather
    than overwrites.
    """
    repo = Path(repo)
    rel_path = _reserve_report_path(repo, report)
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
    report.evidence_path = rel_path

    # R-0.3/WP-4: real InspectionReport emission point. A scan is exactly an
    # "inspection" per the ledger's shape — verdict derives from whether any
    # findings were raised; findings are the finding titles (full detail stays
    # in the report artifact on disk, per this module's bounded-summary rule).
    # Never raises into the caller — this module's contract is "never raises",
    # and a ledger write failure must not block the (already-written) report.
    try:
        append_ledger_event(
            repo,
            InspectionReport(
                subject_ref=rel_path,
                verdict="pass" if report.finding_count == 0 else "changes_requested",
                findings=[f.title for f in report.findings],
                generator="scan",
            ),
            ts=now_iso(),
        )
    except Exception:
        pass

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
    invoke :func:`write_report` first, which records the EXACT artifact path on
    ``report.evidence_path``; this links that path (never a recomputed date-only
    guess). Returns the list of newly-proposed backlog IDs (re-surfaced existing
    items are not counted as new). A ``write_item`` failure is swallowed
    per-finding (the report still persists); the finding is not recorded so a
    later run retries it. The whole load→write→save cycle runs under
    :func:`_ledger_lock` so concurrent scans can't double-file. Never raises.
    """
    repo = Path(repo)
    # Prefer the EXACT path write_report stored; fall back to a fresh unique path
    # only if a caller skipped write_report (keeps evidence_path honest).
    evidence_path = report.evidence_path or _report_rel_path(report)
    stamp = now_iso()
    new_ids: list[str] = []
    lock_degraded: list[str] = []

    with _ledger_lock(repo, degraded=lock_degraded):
        ledger = load_ledger(repo)

        for f in report.findings:
            key = finding_key(f)
            entry = ledger.get(key)

            if isinstance(entry, dict) and entry.get("fingerprint") == f.fingerprint:
                # Seen, unchanged — skip. Touch last_seen so the ledger reflects the run.
                entry["last_seen"] = stamp
                continue

            if isinstance(entry, dict) and entry.get("backlog_id"):
                # Seen but changed — re-surface the linked item rather than duplicate,
                # UNLESS the linked item has gone missing/corrupt: a stale ledger
                # pointer must not permanently suppress a live finding, so fall
                # through to create a fresh item and repoint the ledger.
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
                # else: stale ledger miss — fall through to fresh proposal below.

            # Unseen (or stale-ledger miss) — propose a fresh backlog item,
            # all-or-nothing: roll back the reserved id if the real write fails so
            # a failed write never leaks a ghost placeholder item.
            new_id = _propose_one(repo, f, evidence_path, stamp)
            if new_id is None:
                # write_item failed — don't record so a later run retries this finding.
                continue
            ledger[key] = {
                "backlog_id": new_id,
                "fingerprint": f.fingerprint,
                "first_seen": stamp,
                "last_seen": stamp,
                "state": "proposed",
            }
            new_ids.append(new_id)

        save_ledger(repo, ledger)
    return new_ids


#: Prefix of the unique reservation marker scan stamps into the ``pending_decision``
#: field of the placeholder it controls. ``_rollback_reserved`` unlinks ONLY when
#: this exact (prefix + per-reservation uuid) token is still present on disk —
#: the sole proof the file is the one this scan reserved. A real QA item written by
#: :func:`_propose_one` carries ``pending_decision=""``, so the final successful
#: write clears the marker; if that write fails the marker survives and rollback
#: can safely reclaim. No legitimate item ever carries this token.
_RESERVATION_MARKER_PREFIX: str = "__renmark_scan_reservation__:"


def _propose_one(repo: Path, f: Finding, evidence_path: str, stamp: str) -> str | None:
    """Write one fresh ``source="qa"`` backlog item, all-or-nothing.

    :func:`renmark.backlog.next_id` reserves the id by *creating a placeholder
    file* (``O_CREAT|O_EXCL``). We immediately overwrite that placeholder with a
    marker item carrying a UNIQUE reservation token in ``pending_decision`` (see
    :data:`_RESERVATION_MARKER_PREFIX`) so ownership is provable, then write the
    real item (which clears the marker). If the marker write itself fails we never
    owned a populated file, so there is nothing to roll back; if the real
    :func:`renmark.backlog.write_item` fails, the marker survives and
    :func:`_rollback_reserved` reclaims the id by matching that exact token.
    Returns the new id, or ``None`` on failure (rolled back). Never raises.
    """
    item_id = backlog.next_id(repo)
    marker_token = f"{_RESERVATION_MARKER_PREFIX}{uuid.uuid4().hex}"
    # Stamp the ownership marker over next_id's placeholder. If THIS write fails we
    # never populated the file, so a later run can re-reserve; nothing to roll back.
    marker = backlog.BacklogItem(id=item_id, title="", pending_decision=marker_token)
    if backlog.write_item(repo, marker) is None:
        return None
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
    if backlog.write_item(repo, item) is not None:
        return item_id
    # write_item failed — roll back ONLY our marked placeholder so no ghost leaks.
    _rollback_reserved(repo, item_id, marker_token)
    return None


def _rollback_reserved(repo: Path, item_id: str, marker_token: str) -> None:
    """Delete the reservation file for ``item_id`` — but ONLY if it still carries
    the EXACT ``marker_token`` this scan stamped into ``pending_decision``.

    Ownership check (critical): an empty-field heuristic can false-match a real
    item (fields like ``risk`` / ``updated_at`` / ``served_requirements`` /
    ``disposition`` aren't proof of ownership), so we use an EXPLICIT marker
    instead. :func:`_propose_one` writes a unique
    :data:`_RESERVATION_MARKER_PREFIX`-prefixed uuid token into the placeholder's
    ``pending_decision``; we read the file BACK and unlink ONLY when that exact
    token is still present. If a real item now lives at the id (the successful
    write cleared the marker, or another writer legitimately populated it), the
    token will NOT match and we leave the file untouched — clobbering another
    writer's item is a data-loss bug far worse than a leaked placeholder. A
    ``write_item`` "failure" return is never treated as proof the on-disk file is
    ours; only the marker is.

    Best-effort: gated through the backlog module's own safe-id check + path
    builder so we never delete outside the backlog dir, and swallows IO errors.
    Never raises.
    """
    if not backlog._is_safe_item_id(item_id):  # reuse backlog's traversal guard
        return
    if not marker_token or not marker_token.startswith(_RESERVATION_MARKER_PREFIX):
        # No valid marker to match against — refuse to delete anything.
        return
    # Read it back: only unlink if our EXACT reservation marker is still present.
    existing = backlog.read_item(repo, item_id)
    if existing is None:
        # Already gone (or unreadable) — nothing safe to roll back.
        return
    if existing.pending_decision != marker_token:
        # Marker absent or different — a real item (or another reservation) owns
        # this id now. Leave it; never unlink an item lacking our exact marker.
        return
    with contextlib.suppress(OSError):
        backlog._item_json_path(repo, item_id).unlink(missing_ok=True)


# ── OPTIONAL best-effort Bash denylist (PreToolUse hook) ─────────────────────────
#
# BEST-EFFORT, NOT THE BOUNDARY. The structural read-only guarantee is the direct
# pure-Python trigger ``renmark-execute --scan --propose`` (see :func:`emit_cron`),
# which has no LLM, no Bash tool, and no commit/merge/push/edit code path — so
# there is nothing for a denylist to guard. This hook is relevant ONLY to the
# OPTIONAL alternative trigger ``claude -p "/renmark:scan --propose"`` (model-
# driven, has a Bash tool). It is provided as defense-in-depth for that path and
# is KNOWN to be bypassable (absolute paths like ``/usr/bin/git commit``, ``env
# git commit``, ``command git commit``, ``bash -c "git commit"``, ``eval``,
# ``$(...)`` / backtick substitution). The project no longer attempts to make it
# airtight — making the denylist exhaustive is explicitly out of scope. Use the
# direct-Python trigger when you need a guarantee.

#: The Python program (source text) embedded into the PreToolUse hook command.
#:
#: It reads the proposed Bash command from the hook stdin JSON
#: (``tool_input.command``) and BLOCKS when the effective program is ``git`` in
#: ANY form running a mutating subcommand, or an ``rm -rf`` / destructive
#: redirection. Rather than pattern-matching raw text (bypassable by
#: ``git -C repo commit``, ``git --git-dir=. commit``, ``FOO=1 git commit``,
#: …), it TOKENIZES each shell segment with :mod:`shlex`, skips leading
#: ``VAR=val`` env assignments, skips git global options that take the program
#: name away from the subcommand (``-C <path>``, ``--git-dir[=]``,
#: ``--work-tree[=]``, ``-c <cfg>``, ``--namespace``, ``--exec-path``,
#: ``-p``/``--paginate``, ``--bare``, ``--no-pager``), then inspects the first
#: real subcommand. Matched → print ``{"decision":"block", ...}`` AND exit
#: non-zero (either signal is sufficient for Claude Code to deny). Otherwise
#: allow (exit 0, no output).
_READONLY_HOOK_SOURCE: str = r'''
import sys, json, shlex
raw = sys.stdin.read()
try:
    cmd = (json.loads(raw).get("tool_input") or {}).get("command", "")
except Exception:
    cmd = ""
if not isinstance(cmd, str):
    cmd = ""
# Always-mutating git subcommands (block whenever they appear as the subcommand).
MUT = {"commit","push","merge","rebase","reset","tag","am","cherry-pick",
       "revert","stash","clean","gc","update-ref","fast-import","apply","mv","rm"}
# git global options that sit between "git" and the subcommand.
OPT_VAL = {"-C","-c","--namespace","--exec-path"}        # consume the next token
OPT_EQ = ("--git-dir","--work-tree","--namespace","--exec-path")  # may use =VALUE
OPT_FLAG = {"-p","--paginate","--bare","--no-pager"}
def env_assign(t):
    i = t.find("=")
    if i <= 0:
        return False
    return t[:i].replace("_","").isalnum() and not t[:i][0].isdigit()
def git_sub_index(toks):
    # Return index of the git subcommand token, or -1 if toks is not a git call.
    n = len(toks)
    i = 0
    while i < n and env_assign(toks[i]):   # skip FOO=1 BAR=2 prefixes
        i += 1
    if i >= n or toks[i] != "git":
        return -1
    i += 1
    while i < n:
        t = toks[i]
        if t in OPT_VAL:
            i += 2; continue
        if t in OPT_FLAG:
            i += 1; continue
        if t.startswith(OPT_EQ):
            # --git-dir=X (one token) or --git-dir X (consume next).
            i += 1 if "=" in t else 2; continue
        if t.startswith("-"):
            i += 1; continue
        break
    return i if i < n else -1
def is_git_mutation(toks):
    i = git_sub_index(toks)
    if i < 0:
        return False
    sub = toks[i]
    rest = toks[i + 1:]
    if sub in MUT:
        return True
    # branch: mutating only when deleting (-d/-D) or creating (a non-flag arg).
    if sub == "branch":
        for a in rest:
            if a in ("-d", "-D", "--delete", "-m", "-M", "--move", "-c", "-C", "--copy", "-f", "--force"):
                return True
            if not a.startswith("-"):
                return True   # `git branch <name>` creates a branch
        return False
    # checkout: mutating when creating a branch (-b/-B) or force-overwriting (-f).
    if sub == "checkout":
        for a in rest:
            if a in ("-b", "-B", "-f", "--force"):
                return True
        return False
    return False
def has_rm_rf(toks):
    j = 0
    while j < len(toks) and env_assign(toks[j]):
        j += 1
    toks = toks[j:]
    if not toks or toks[0] != "rm":
        return False
    for t in toks[1:]:
        if t.startswith("-") and not t.startswith("--") and "r" in t.lower() and "f" in t.lower():
            return True
    if "--recursive" in toks and "--force" in toks:
        return True
    return False
blocked = False
# Split into shell segments so "x && git commit" is inspected per-segment.
for seg in cmd.replace("&&", "\n").replace("||", "\n").replace(";", "\n").replace("|", "\n").split("\n"):
    seg = seg.strip()
    if not seg:
        continue
    # Destructive redirection: truncating a tracked path. Best-effort.
    if ">" in seg and ".git" in seg:
        blocked = True
        break
    try:
        toks = shlex.split(seg, comments=False, posix=True)
    except ValueError:
        # Unparseable (unbalanced quotes) -> be safe, deny.
        blocked = True
        break
    if is_git_mutation(toks) or has_rm_rf(toks):
        blocked = True
        break
if blocked:
    print(json.dumps({"decision": "block",
        "reason": "renmark:scan is read-only; mutating git/rm command denied"}))
    sys.exit(2)
sys.exit(0)
'''


def _build_hook_command(source: str) -> str:
    """Wrap an embedded Python program as a single ``python3 -c "..."`` shell
    command that pastes cleanly into ``settings.json``.

    Collapses the multi-line source into a base64-decoded ``exec`` so neither
    shell quoting nor JSON escaping can mangle the program (newlines, quotes,
    and backslashes in the tokenizer survive intact). Deterministic; pure.
    """
    import base64

    encoded = base64.b64encode(source.encode("utf-8")).decode("ascii")
    # Single-quoted in the shell; b64 is ASCII-safe so no shell metachars leak.
    return f"python3 -c 'import base64;exec(base64.b64decode(\"{encoded}\").decode())'"


#: PreToolUse hook command — a self-contained ``python3 -c`` one-liner (no
#: external script to install). See :data:`_READONLY_HOOK_SOURCE` for the logic.
_READONLY_HOOK_COMMAND: str = _build_hook_command(_READONLY_HOOK_SOURCE)

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
    """Return (PRINT-only, no writes) the scheduled read-only trigger setup text.

    The PRIMARY emitted trigger is the **direct pure-Python CLI**
    ``renmark-execute --scan --propose`` run from the repo root by external cron /
    Windows Task Scheduler. ``scan.py`` itself is STRUCTURALLY read-only: it
    performs no git / product-file / PRD mutation and never commits, merges,
    pushes, releases, or executes fixes. Its writes are confined to ``.renmark/``
    state — the scan report, the dedup ledger, and (on ``--propose``) a backlog
    reservation file (created via ``next_id`` / removed via rollback) plus the
    final ``write_item``. It is NOT a sandbox, though: the read-only CHECKS it runs
    (pytest / ruff / mypy) execute the project's OWN code (conftest, fixtures,
    plugins), so run a scheduled scan at the same trust level as running your test
    suite — do not read this as "nothing it runs can mutate." No Claude token is
    needed for the direct path; cron just needs the repo + Python.

    A clearly-labeled OPTIONAL block follows for the alternative model-driven
    trigger (``claude -p "/renmark:scan --propose"``), which DOES have a Bash tool;
    the :data:`READONLY_HOOK` JSON is offered there as BEST-EFFORT defense-in-depth
    only — it is not a guarantee. Pure string — never writes, never raises.
    """
    repo = Path(repo)
    direct_line = "renmark-execute --scan --propose"
    optional_line = 'claude -p "/renmark:scan --propose"'
    hook_json = json.dumps(READONLY_HOOK, indent=2)
    return (
        "# renmark:scan — read-only scheduled QA proposer trigger\n"
        f"# repo: {repo}\n"
        "#\n"
        "# ============================================================\n"
        "# PRIMARY (recommended) — direct pure-Python CLI. scan.py itself does NO\n"
        "# git / product-file / PRD mutation and never commits, merges, pushes,\n"
        "# releases, or executes fixes; its writes are confined to .renmark/ state\n"
        "# (the scan report, the dedup ledger, a backlog reservation file, and the\n"
        "# final backlog write_item). NOTE: it is NOT a sandbox — the read-only\n"
        "# CHECKS it runs (pytest / ruff / mypy) execute THIS project's own code\n"
        "# (conftest, fixtures, plugins), so run the scheduled scan at the same\n"
        "# trust level as running your test suite. Run it from the repo root via\n"
        "# WSL cron / Windows Task Scheduler. No Claude token is needed for this\n"
        "# path — cron just needs the repo checkout + Python on PATH.\n"
        "# ============================================================\n"
        f"#   cd {repo} && {direct_line}\n"
        "#\n"
        "# ------------------------------------------------------------\n"
        "# OPTIONAL — model-driven trigger (has a Bash tool, NOT structural).\n"
        "# If you instead trigger via the headless model, you may add the\n"
        "# best-effort PreToolUse hook below as defense-in-depth — it is\n"
        "# BEST-EFFORT, NOT a guarantee (absolute paths, env/command prefixes,\n"
        "# bash -c, eval, and $(...) substitution all bypass it). The structural\n"
        "# guarantee is the direct-Python trigger above; prefer it.\n"
        "# ------------------------------------------------------------\n"
        f"#   {optional_line} \\\n"
        '#       --tools "Read,Bash,Grep,Glob" --disallowedTools "Edit,Write" \\\n'
        "#       --permission-mode dontAsk\n"
        "#\n"
        "#   Optional best-effort PreToolUse Bash-denylist hook — paste into\n"
        "#   settings.json. Defense-in-depth for the model-driven path ONLY;\n"
        "#   bypassable and NOT a guarantee:\n"
        f"{hook_json}\n"
        "#\n"
        "#   The model-driven path also needs a one-time headless auth token\n"
        "#   (the direct-Python path above does NOT):\n"
        "#     claude setup-token\n"
        "#     export CLAUDE_CODE_OAUTH_TOKEN=<token printed above>\n"
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
