"""Roadmap reporter.

Synthesizes a status report from three sources:
- `.renmark/memory/features.md` — declared features (planned/in-progress/shipped)
- `.renmark/state/usage.jsonl` — token spend per LLM call (run_id, task_id, model, tokens)
- git log — commit shas for `[renmark|codex|nim|manual] task N:` entries

Output: a per-task table with columns:
  task | llm | status | tokens | $ | commit

Plus a totals row (per-LLM token aggregate and project total $).
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import program
from .init import _git_short_sha
from .state import RENMARK_DIR_NAME, read_usage

# Approximate per-token costs (USD per 1k tokens) for cost estimates.
# Opus Agent calls DO consume Anthropic billing (not "in-context free") — they
# go through the user's Claude Code quota. Same for haiku/sonnet. Update as
# pricing shifts.
COST_PER_KT = {
    "haiku": 0.0001,
    "codex": 0.05,
    "sonnet": 0.003,
    "opus": 0.015,  # Anthropic output pricing, rough rule-of-thumb
    "fable": 0.030,  # 2x opus — Fable 5 lists at $10/$50 per MTok vs Opus's $5/$25
    "nim": 0.0,  # legacy: NIM removed in v0.2.0
}

# Per-Agent-call overhead: every haiku/sonnet/opus task receives ~10k tokens of
# system prompt + task spec on TOP of its output. Sized to match the plan
# cost-preview footnote so roadmap and plan agree.
AGENT_OVERHEAD_TOKENS = 10_000


@dataclass
class RoadmapRow:
    task: str  # task index + title
    llm: str  # model name or executor
    status: str  # passed | failed | retried | shipped | planned | in-progress
    tokens: int
    cost_usd: float
    commit: str  # short sha or empty
    when: str = ""  # ISO timestamp or date


def _git_commits_for_tasks(repo: str | Path) -> dict[int, str]:
    """Map task_index → short sha by scanning git log for `[renmark|codex|nim|manual] task N:` commits."""
    try:
        out = subprocess.run(
            ["git", "-C", str(repo), "log", "--pretty=%h %s"],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return {}
    pattern = re.compile(
        r"^([0-9a-f]+)\s+\[?(?:renmark|codex|nim|manual)\]?\s+task\s+(\d+)\s*(?:\([^)]*\))?\s*:",
        re.IGNORECASE,
    )
    out_map: dict[int, str] = {}
    for line in out.splitlines():
        m = pattern.match(line.strip())
        if m:
            sha, idx = m.group(1), int(m.group(2))
            out_map.setdefault(idx, sha)
    return out_map


def _aggregate_usage(repo: str | Path) -> dict[int, dict[str, Any]]:
    """Per-task aggregate from usage.jsonl: total tokens, primary model, call count."""
    rows = read_usage(repo)
    by_task: dict[int, dict[str, Any]] = {}
    for r in rows:
        # Tolerate type-malformed ledger rows: one bad row must not kill the
        # whole roadmap (same contract as state.usage's defensive readers).
        try:
            tid = int(r.get("task_id", 0))
        except (TypeError, ValueError):
            continue
        d = by_task.setdefault(
            tid,
            {
                "tokens_in": 0,
                "tokens_out": 0,
                "models": [],
                "calls": 0,
                "last_ts": "",
            },
        )
        d["tokens_in"] += _safe_int(r.get("prompt_tokens", 0))
        d["tokens_out"] += _safe_int(r.get("completion_tokens", 0))
        d["calls"] += 1
        m = r.get("model", "")
        if isinstance(m, str) and m and m not in d["models"]:
            d["models"].append(m)
        ts = r.get("ts", "")
        if isinstance(ts, str):
            d["last_ts"] = max(d["last_ts"], ts)
    return by_task


def _safe_int(value: Any) -> int:
    """Coerce a ledger field to ``int``; bad input → 0."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def build_rows(repo: str | Path) -> list[RoadmapRow]:
    """Build per-task rows from features.md + usage.jsonl + git log."""
    repo_p = Path(repo)
    commits = _git_commits_for_tasks(repo_p)
    usage = _aggregate_usage(repo_p)

    rows: list[RoadmapRow] = []

    # Shipped tasks come from git commit history (the source of truth that something landed).
    for tid in sorted(commits.keys()):
        u = usage.get(tid, {})
        models = ", ".join(u.get("models", [])) or "?"
        tokens = u.get("tokens_in", 0) + u.get("tokens_out", 0)
        cost = _estimate_cost(models, tokens)
        rows.append(
            RoadmapRow(
                task=f"task {tid}",
                llm=_short_model(models),
                status="shipped",
                tokens=tokens,
                cost_usd=cost,
                commit=commits[tid],
                when=u.get("last_ts", ""),
            )
        )

    # Tasks with usage but no commit = attempted, not landed (in-progress or failed).
    for tid, u in usage.items():
        if tid in commits:
            continue
        models = ", ".join(u.get("models", [])) or "?"
        tokens = u.get("tokens_in", 0) + u.get("tokens_out", 0)
        cost = _estimate_cost(models, tokens)
        # If retries > 1 and no commit, likely failed/escalated.
        status = "retried" if u.get("calls", 1) > 1 else "in-progress"
        rows.append(
            RoadmapRow(
                task=f"task {tid}",
                llm=_short_model(models),
                status=status,
                tokens=tokens,
                cost_usd=cost,
                commit="",
                when=u.get("last_ts", ""),
            )
        )

    return rows


def _short_model(name: str) -> str:
    # Trim org/model to just model for compactness.
    if "/" in name:
        return name.split("/", 1)[1]
    return name


def _estimate_cost(model_str: str, tokens: int) -> float:
    """Approximate cost based on which executor strings are in the model field.

    Honest accounting: haiku/sonnet/opus Agent calls cost real Anthropic
    quota (not "in-context free" as the v0.2.x ledger assumed)."""
    m = model_str.lower()
    if "codex" in m:
        return (tokens / 1000.0) * COST_PER_KT["codex"]
    if "fable" in m:
        return (tokens / 1000.0) * COST_PER_KT["fable"]
    if "opus" in m:
        return (tokens / 1000.0) * COST_PER_KT["opus"]
    if "sonnet" in m:
        return (tokens / 1000.0) * COST_PER_KT["sonnet"]
    if "haiku" in m:
        return (tokens / 1000.0) * COST_PER_KT["haiku"]
    return 0.0  # NIM and unknown = free


def render_table(rows: list[RoadmapRow]) -> str:
    """Render rows as a Markdown table with totals."""
    if not rows:
        return "(no roadmap data yet — run /renmark:plan and /renmark:orchestrate to populate)"

    header = "| task | llm | status | tokens | $ | commit |\n|------|-----|--------|-------:|--:|--------|\n"
    lines = []
    total_tokens = 0
    total_cost = 0.0
    by_status: dict[str, int] = {}
    for r in rows:
        cost_str = f"${r.cost_usd:.3f}" if r.cost_usd > 0 else "free"
        sha = r.commit or "—"
        lines.append(f"| {r.task} | {r.llm} | {r.status} | {r.tokens:,} | {cost_str} | `{sha}` |")
        total_tokens += r.tokens
        total_cost += r.cost_usd
        by_status[r.status] = by_status.get(r.status, 0) + 1

    summary = (
        f"\n\n**Totals:** {len(rows)} tasks · {total_tokens:,} tokens · ${total_cost:.3f}\n"
        + "**By status:** "
        + ", ".join(f"{k}={v}" for k, v in sorted(by_status.items()))
    )

    return header + "\n".join(lines) + summary


def write_roadmap_md(repo: str | Path) -> Path:
    """Render the current roadmap and write it to .renmark/memory/roadmap.md."""
    rows = build_rows(repo)
    table = render_table(rows)
    out = Path(repo) / RENMARK_DIR_NAME / "memory" / "roadmap.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        "# Roadmap\n\nAuto-generated by /renmark:roadmap from features.md + usage.jsonl + git log.\n\n" + table + "\n",
        encoding="utf-8",
    )
    return out


# ── Staged-program (in-flight) reporting ─────────────────────────────────────
#
# The functions below operate on the OUTER staged-program roadmap state
# (``.renmark/state/program.json``, modelled in :mod:`renmark.program`) — the
# spine that spans many pipeline runs. They are the deterministic, zero-LLM half
# of ``/renmark:roadmap``'s in-flight view and of ``--setup`` brownfield
# reconciliation. None of them read PRD bodies or source code: they operate only
# on the structured program-on-disk plus structured inputs handed in by a
# skill's subagent (REQ-5 / G11).

#: Statuses a stage/task may be reconciled to from a brownfield "what is built"
#: signal. A subset of :data:`program.STATUSES` — reconciliation never invents
#: ``in_progress`` / ``blocked`` (those are runtime/driver states, not evidence
#: of what exists on disk).
_RECONCILE_STATUSES: tuple[str, ...] = ("done", "partial", "needed")


def render_program_table(repo: str | Path) -> str:
    """Render the in-flight staged program's position as a deterministic report.

    Zero-LLM, zero-network. Reads ``.renmark/state/program.json`` via
    :func:`program.read_program` and renders:

    * the bounded :func:`program.position` line (stage X/Y · task done/total),
    * every stage with its status glyph and ``serves`` requirement, each task
      listed with its ``done|partial|needed|pending`` status, and
    * a **"where work is needed"** section listing the stages whose status is
      ``needed`` or ``partial`` (the actionable backlog).

    Returns a clear "no in-flight program" string when
    :func:`program.read_program` returns ``None`` (the ``program.json`` file is
    ABSENT — there is nothing to report).

    Does NOT swallow :class:`program.ProgramStateError`: if ``program.json``
    EXISTS but is corrupt/malformed, the error propagates. Corrupt resumable
    state must surface loudly rather than masquerade as "no program" (mirrors
    the read-side hardening in :mod:`renmark.program`).
    """
    prog = program.read_program(repo)  # raises ProgramStateError on corruption
    if prog is None:
        return (
            "(no in-flight program — run /renmark:plan to stage one, "
            "then /renmark:orchestrate to drive it)"
        )

    feature = prog.feature or "(unnamed)"
    lines: list[str] = []
    lines.append(f"# Program — {feature}")
    lines.append("")
    lines.append(f"_mode: {prog.mode} · {program.position(prog)}_")
    lines.append("")

    if not prog.stages:
        lines.append("_No stages yet._")
        return "\n".join(lines)

    for stage in prog.stages:
        glyph = program._STATUS_GLYPH.get(stage.status, "?")
        title = stage.title or stage.id or "(untitled stage)"
        serves = f" — serves {stage.serves}" if stage.serves else ""
        marker = " (current)" if stage.id and stage.id == prog.current_stage_id else ""
        lines.append(f"## {glyph} {title}{serves} [{stage.status}]{marker}")
        if not stage.tasks:
            lines.append("- _(no tasks)_")
        else:
            for task in stage.tasks:
                ttitle = task.title or task.id or "(untitled task)"
                retry = f" (retries: {task.retry_count})" if task.retry_count else ""
                lines.append(f"- [{task.status}] {ttitle}{retry}")
        lines.append("")

    # "Where work is needed" — stages flagged needed/partial.
    attention = [s for s in prog.stages if s.status in ("needed", "partial")]
    lines.append("## Where work is needed")
    if not attention:
        lines.append("- _(nothing flagged — all stages done or pending)_")
    else:
        for stage in attention:
            title = stage.title or stage.id or "(untitled stage)"
            serves = f" (serves {stage.serves})" if stage.serves else ""
            lines.append(f"- {title}{serves} — {stage.status}")

    return "\n".join(lines)


def reconcile_setup(repo: str | Path, built_signal: dict[str, Any]) -> program.Program:
    """Reconcile the on-disk staged program against a brownfield "what is built"
    signal, persisting and returning the updated :class:`program.Program`.

    This is the DETERMINISTIC half of ``/renmark:setup`` brownfield
    reconciliation. It performs NO code/PRD reading itself — the LLM-derived
    evidence of what already exists is handed in by the skill's subagent via
    ``built_signal`` (REQ-5 / G11). This function is a pure mapping over
    (program-on-disk, built_signal).

    ``built_signal`` contract — a plain dict with three optional keys, each a
    list of strings (absent/empty lists are tolerated):

    * ``"built_reqs"``    — requirement ids (e.g. ``"REQ-1"``) judged FULLY
      built. A stage whose ``serves`` matches one of these is set ``done``.
    * ``"partial_reqs"``  — requirement ids judged PARTIALLY built. A stage
      whose ``serves`` matches one of these is set ``partial`` (unless it is
      also in ``built_reqs``, which wins — fully-built beats partial).
    * ``"built_components"`` — free-form component/module names judged present
      on disk (e.g. ``"renmark/roadmap.py"``, ``"auth"``). A stage whose
      ``serves`` is NOT a recognised requirement, or that serves ``"new"`` work,
      is matched ``done`` when its title or id contains (case-insensitively) one
      of these component names, else ``needed``.

    Mapping rules, per stage (evaluated top-down, first match wins):

    1. ``serves`` ∈ ``built_reqs``      → ``done``
    2. ``serves`` ∈ ``partial_reqs``    → ``partial``
    3. a ``built_components`` substring matches the stage title/id/serves
                                        → ``done``
    4. otherwise                        → ``needed``

    Each task inherits its stage's reconciled status (a ``done`` stage's tasks
    are ``done``; ``partial``/``needed`` stages mark their tasks ``needed`` so
    the work surfaces). Statuses are applied via the hardened
    :func:`program.mark_stage` / :func:`program.mark_task` mutators using only
    ids that exist in the program and only statuses in
    :data:`program.STATUSES`, so the mutators never raise.

    When :func:`program.read_program` returns ``None`` (no ``program.json`` to
    reconcile), an EMPTY ``Program(mode="setup")`` is created, persisted, and
    returned — there is nothing to reconcile, but a setup-mode program scaffold
    is established so the caller has a durable, resumable starting point.

    A corrupt ``program.json`` raises :class:`program.ProgramStateError`
    (propagated from :func:`program.read_program`) — never silently reset.
    """
    prog = program.read_program(repo)  # raises ProgramStateError on corruption
    if prog is None:
        prog = program.Program(mode="setup")
        program.write_program(repo, prog)
        return prog

    built_reqs = _as_str_set(built_signal.get("built_reqs"))
    partial_reqs = _as_str_set(built_signal.get("partial_reqs"))
    built_components = _as_str_list(built_signal.get("built_components"))

    for stage in prog.stages:
        serves = stage.serves.strip()
        stage_status = _reconcile_stage_status(
            serves=serves,
            title=stage.title,
            stage_id=stage.id,
            built_reqs=built_reqs,
            partial_reqs=partial_reqs,
            built_components=built_components,
        )
        program.mark_stage(prog, stage.id, stage_status)
        # Tasks inherit: a done stage's tasks are done; otherwise the work is
        # still needed (partial/needed both surface task-level work to do).
        task_status = "done" if stage_status == "done" else "needed"
        for task in stage.tasks:
            program.mark_task(prog, stage.id, task.id, task_status)

    # Re-point current_stage_id at the first stage still needing work (or None
    # when everything reconciled to done). Without this, a freshly reconciled
    # setup program could still point at None or an already-done stage and
    # position() would report the wrong "where are we".
    prog.current_stage_id = next(
        (stage.id for stage in prog.stages if stage.status != "done"), None
    )

    program.write_program(repo, prog)
    return prog


def program_map_is_stale(repo: str | Path) -> bool:
    """Return ``True`` when ``.renmark/memory/project-map.md`` is missing or stale.

    Staleness criterion (MIRRORS the freshness gate the blueprint SKILL applies,
    and the ``Last refreshed: <date> @ <sha>`` header that :mod:`renmark.init`
    writes via ``render_full_map`` / ``write_full_map``):

    * The map file is **missing** → ``True`` (stale: nothing to read).
    * The map header carries ``<!-- Last refreshed: <date> @ <sha> -->`` where
      ``<sha>`` is the SHORT git sha recorded at generation
      (``git rev-parse --short HEAD`` — see :func:`init._git_short_sha`). The
      recorded sha is compared against the current short ``HEAD`` sha. They are
      compared by **prefix** (either is a prefix of the other) so a short-vs-full
      length mismatch never causes a false "stale". A mismatch → ``True``.
    * The header is absent or carries no parseable ``@ <sha>`` token → ``True``
      (a map without provenance can't be trusted as fresh).
    * The recorded sha matches current HEAD → ``False`` (fresh).
    * Git HEAD cannot be resolved (no git / detached error) → ``False``: drift
      can't be computed, so a *present* map is treated as fresh rather than
      forcing a spurious re-init. (Missing-file still returns ``True``.)

    Zero-LLM, zero-network. Reuses :func:`init._git_short_sha` for the HEAD sha
    so this check and ``/renmark:init``'s recorded sha are derived identically.
    """
    map_path = Path(repo) / RENMARK_DIR_NAME / "memory" / "project-map.md"
    if not map_path.exists():
        return True

    try:
        text = map_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return True

    recorded = _recorded_map_sha(text)
    if not recorded:
        return True

    head = _git_short_sha(Path(repo))
    if not head:
        # Cannot compute drift — a present, provenance-stamped map is treated as
        # fresh rather than forcing a needless re-init.
        return False

    # Prefix-tolerant compare: init records a SHORT sha; HEAD here is also short,
    # but lengths can differ across git versions/configs.
    return not (recorded.startswith(head) or head.startswith(recorded))


# ── Internal helpers (staged-program reporting) ──────────────────────────────

#: Matches the ``@ <sha>`` token in init's ``Last refreshed`` header line.
_MAP_REFRESHED_RE = re.compile(
    r"Last refreshed:.*?@\s*([0-9a-fA-F]+)",
)


def _recorded_map_sha(map_text: str) -> str | None:
    """Extract the short git sha from a project-map.md ``Last refreshed`` header.

    Returns the lowercased sha string, or ``None`` if no parseable
    ``Last refreshed: <date> @ <sha>`` token is present.
    """
    m = _MAP_REFRESHED_RE.search(map_text)
    if not m:
        return None
    return m.group(1).lower()


def _reconcile_stage_status(
    *,
    serves: str,
    title: str,
    stage_id: str,
    built_reqs: set[str],
    partial_reqs: set[str],
    built_components: list[str],
) -> str:
    """Pure mapping from (stage identity, built_signal) → reconciled status.

    First-match wins, per :func:`reconcile_setup`'s documented rules. Always
    returns a status in :data:`_RECONCILE_STATUSES` (a subset of
    :data:`program.STATUSES`), so the caller's mutators never raise.
    """
    serves_norm = serves.casefold()
    if serves and serves_norm in {r.casefold() for r in built_reqs}:
        return "done"
    if serves and serves_norm in {r.casefold() for r in partial_reqs}:
        return "partial"
    haystack = f"{title} {stage_id} {serves}".casefold()
    for comp in built_components:
        c = comp.strip().casefold()
        if c and c in haystack:
            return "done"
    return "needed"


def _as_str_set(value: Any) -> set[str]:
    """Coerce a built_signal list field to a set of non-empty strings.

    Tolerates ``None`` / non-list / non-string elements (skipped) so a
    malformed signal degrades gracefully rather than raising."""
    return set(_as_str_list(value))


def _as_str_list(value: Any) -> list[str]:
    """Coerce a built_signal list field to a list of non-empty strings.

    ``None`` / non-list → ``[]``; non-string or blank elements are dropped."""
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value:
        if isinstance(item, str) and item.strip():
            out.append(item.strip())
    return out
