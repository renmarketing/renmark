"""Artifact hygiene helper — enforces G3 (summary boundary), G6 (artifact
governance metadata), G9 (failure transparency).

Every renmark skill that emits a long-running result writes through this
module. Artifacts are written to disk with YAML frontmatter metadata + body
+ a structured ``## Summary`` section. The orchestrator reads only the
metadata + Summary (never the body).

Default orchestrator-visible output cap: 5 lines OR ~300 tokens per line.
Violations raise ValueError at write time — they are bugs, not warnings.
"""

from __future__ import annotations

import hashlib
import subprocess
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from renmark.verifier import run_verifier

SCHEMA_VERSION = "1"
MAX_SUMMARY_LINES = 5
MAX_TOKENS_PER_LINE = 300  # ~4 chars/token rule-of-thumb
MAX_CHARS_PER_LINE = MAX_TOKENS_PER_LINE * 4  # 1200 chars


# ── Errors ────────────────────────────────────────────────────────────────────


class SummaryBoundaryError(ValueError):
    """Raised when summary_lines exceeds the G3 cap (lines or per-line tokens)."""


# ── Metadata block ────────────────────────────────────────────────────────────


@dataclass
class ArtifactMetadata:
    """G6 + G9 metadata carried at the top of every artifact."""

    artifact_type: str
    schema_version: str = SCHEMA_VERSION
    created_at: str = ""
    source_sha: str | None = None
    related_plan: str | None = None
    generator: str = "unknown"
    stale_after: str | None = None
    dependency_refs: list[str] = field(default_factory=list)
    # G9 transparency:
    completion_state: str = "complete"  # complete | partial | failed
    confidence: str = "medium"  # low | medium | high
    validation_status: str = "unvalidated"  # validated | unvalidated | failed
    retry_count: int = 0
    parser_success: bool = True
    schema_compliance: bool = True

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    def to_yaml(self) -> str:
        """Render as the YAML frontmatter block of an artifact."""
        lines = ["---"]
        lines.append(f"artifact_type: {self.artifact_type}")
        lines.append(f"schema_version: {self.schema_version}")
        lines.append(f"created_at: {self.created_at}")
        lines.append(f"source_sha: {self.source_sha or 'null'}")
        lines.append(f"related_plan: {self.related_plan or 'null'}")
        lines.append(f"generator: {self.generator}")
        lines.append(f"stale_after: {self.stale_after or 'null'}")
        if self.dependency_refs:
            lines.append("dependency_refs:")
            for ref in self.dependency_refs:
                lines.append(f"  - {ref}")
        else:
            lines.append("dependency_refs: []")
        lines.append(f"completion_state: {self.completion_state}")
        lines.append(f"confidence: {self.confidence}")
        lines.append(f"validation_status: {self.validation_status}")
        lines.append(f"retry_count: {self.retry_count}")
        lines.append(f"parser_success: {str(self.parser_success).lower()}")
        lines.append(f"schema_compliance: {str(self.schema_compliance).lower()}")
        lines.append("---")
        return "\n".join(lines)


# ── Public API ────────────────────────────────────────────────────────────────


def write_artifact(
    path: Path | str,
    *,
    artifact_type: str,
    body: str,
    summary_lines: Iterable[str],
    related_plan: str | None = None,
    source_sha: str | None = None,
    generator: str = "unknown",
    stale_after: str | None = None,
    dependency_refs: list[str] | None = None,
    completion_state: str = "complete",
    confidence: str = "medium",
    validation_status: str = "unvalidated",
    retry_count: int = 0,
    parser_success: bool = True,
    schema_compliance: bool = True,
) -> Path:
    """Write a renmark artifact: metadata + body + ``## Summary`` section.

    Raises SummaryBoundaryError if summary_lines exceeds the G3 cap.
    Returns the resolved Path.
    """
    summary_lines_list = list(summary_lines)
    _validate_summary(summary_lines_list)

    meta = ArtifactMetadata(
        artifact_type=artifact_type,
        related_plan=related_plan,
        source_sha=source_sha,
        generator=generator,
        stale_after=stale_after,
        dependency_refs=list(dependency_refs or []),
        completion_state=completion_state,
        confidence=confidence,
        validation_status=validation_status,
        retry_count=retry_count,
        parser_success=parser_success,
        schema_compliance=schema_compliance,
    )

    # Writer-side metadata validation (G6): a writer emitting invalid
    # frontmatter is a bug. Function-local import avoids a schemas ↔ summary
    # import cycle at module load.
    from dataclasses import asdict

    from renmark import schemas

    meta_issues = schemas.validate_artifact_metadata(asdict(meta))
    if meta_issues:
        raise SummaryBoundaryError(f"invalid artifact metadata: {meta_issues}")

    summary_block = "\n".join(f"- {line}" for line in summary_lines_list)
    content = f"{meta.to_yaml()}\n\n{body.rstrip()}\n\n## Summary\n\n{summary_block}\n"

    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(content, encoding="utf-8")
    return out


def emit_pointer(path: Path | str, label: str, *, n_lines: int = MAX_SUMMARY_LINES) -> str:
    """Read ONLY the metadata + ``## Summary`` section. Returns a bounded
    string suitable for orchestrator output. Caps at G3 limits regardless of
    what's in the file — never returns the full body.
    """
    p = Path(path)
    if not p.exists():
        return f"{label}: artifact missing at {p}"

    text = p.read_text(encoding="utf-8")
    meta = read_metadata(p)

    # Extract Summary section
    summary_idx = text.find("## Summary")
    if summary_idx == -1:
        return f"{label}: artifact {p} missing required '## Summary' section"

    summary_block = text[summary_idx:].splitlines()
    # Skip the "## Summary" header and any blank lines; take next n_lines bullet lines
    bullets: list[str] = []
    for line in summary_block[1:]:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("##"):
            break
        bullets.append(stripped)
        if len(bullets) >= n_lines:
            break

    # Truncate over-long bullets to stay within token cap
    bullets = [(b[: MAX_CHARS_PER_LINE - 1] + "…") if len(b) > MAX_CHARS_PER_LINE else b for b in bullets]

    header = (
        f"{label}: {meta.get('artifact_type', '?')} "
        f"({meta.get('completion_state', '?')}, "
        f"confidence={meta.get('confidence', '?')}) → {p}"
    )
    return "\n".join([header, *bullets])


def read_summary_lines(path: Path | str, *, n_lines: int = MAX_SUMMARY_LINES) -> list[str]:
    """Return the bounded ``## Summary`` bullet lines from an artifact body.

    Companion to ``read_metadata``: summary lines live in the artifact BODY
    (``write_artifact`` renders them under ``## Summary``), never in the
    frontmatter — so consumers like ``loop.build_decision`` that need
    ``summary_lines`` must merge this in. Leading ``- `` bullets are stripped
    so lines match what the writer was given (and what loop's ``failed:`` /
    ``symptom:`` regexes anchor on). Never raises; missing file/section → [].
    """
    p = Path(path)
    if not p.exists():
        return []
    try:
        text = p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    idx = text.find("## Summary")
    if idx == -1:
        return []
    bullets: list[str] = []
    for line in text[idx:].splitlines()[1:]:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("##"):
            break
        if stripped.startswith("- "):
            stripped = stripped[2:].strip()
        bullets.append(stripped)
        if len(bullets) >= n_lines:
            break
    return bullets


def _coerce_yaml_value(value: str) -> Any:
    """Convert a raw YAML scalar string to the appropriate Python type.

    Handles the subset of YAML scalars written by ``ArtifactMetadata.to_yaml``:
    null → None, [] → [], true/false → bool, digit strings → int, else str.
    """
    if value == "null":
        return None
    if value == "[]":
        return []
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    if value.isdigit():
        return int(value)
    return value


def read_metadata(path: Path | str) -> dict[str, Any]:
    """Parse the YAML frontmatter block at the top of an artifact.

    Returns an empty dict[str, Any] if the file lacks frontmatter. Does NOT pull in
    a YAML library — we control the writer's format, so a tiny line parser
    is sufficient and dependency-free.
    """
    p = Path(path)
    if not p.exists():
        return {}

    text = p.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}

    end = text.find("\n---", 3)
    if end == -1:
        return {}

    block = text[3:end].strip("\n")
    result: dict[str, Any] = {}
    current_list_key: str | None = None
    for raw in block.splitlines():
        line = raw.rstrip()
        if not line:
            continue
        if line.startswith("  - ") and current_list_key:
            result[current_list_key].append(line[4:].strip())
            continue
        current_list_key = None
        if ": " not in line and not line.endswith(":"):
            continue
        if line.endswith(":"):
            key = line[:-1].strip()
            result[key] = []
            current_list_key = key
            continue
        key, _, value = line.partition(": ")
        key = key.strip()
        result[key] = _coerce_yaml_value(value.strip())
    return result


def is_stale(path: Path | str, *, against_sha: str | None = None) -> bool:
    """Return True if the artifact is stale per G6 rules:
    - ``stale_after`` timestamp has passed, OR
    - ``source_sha`` differs from ``against_sha`` (when provided), OR
    - artifact doesn't exist.
    """
    p = Path(path)
    if not p.exists():
        return True

    meta = read_metadata(p)
    stale_after = meta.get("stale_after")
    if stale_after and stale_after != "null":
        try:
            stale_dt = datetime.fromisoformat(stale_after.replace("Z", "+00:00"))
            if datetime.now(timezone.utc) > stale_dt:
                return True
        except (ValueError, AttributeError):
            pass  # malformed timestamp — treat as fresh

    if against_sha is not None:
        artifact_sha = meta.get("source_sha")
        if artifact_sha and artifact_sha != against_sha:
            return True

    return False


def verifier_tail(command: str, *, cwd: Path | str, tail_lines: int = 3, timeout_s: int = 60) -> str:
    """G3-compliant wrapper around verifier.run_verifier. Returns a single
    bounded line: ``exit <code> | <first 3 lines collapsed>``.
    """
    result = run_verifier(command, cwd=cwd, timeout_s=timeout_s, tail_lines=tail_lines)
    raw_lines = (result.tail or "").splitlines()[:tail_lines]
    collapsed = " ⏎ ".join(line.strip() for line in raw_lines if line.strip())
    if not collapsed:
        collapsed = "(no output)"
    if len(collapsed) > MAX_CHARS_PER_LINE:
        collapsed = collapsed[: MAX_CHARS_PER_LINE - 1] + "…"
    return f"exit {result.exit_code} | {collapsed}"


def hash_artifact(path: Path | str) -> str:
    """SHA256 of an artifact's content. Used by release manifests."""
    p = Path(path)
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()


def git_head_sha(repo: Path | str) -> str | None:
    """Return the current git HEAD sha, or None if not a git repo."""
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.strip() or None


# ── Internal ──────────────────────────────────────────────────────────────────


def _validate_summary(summary_lines: list[str]) -> None:
    if len(summary_lines) > MAX_SUMMARY_LINES:
        raise SummaryBoundaryError(f"summary_lines has {len(summary_lines)} entries; max {MAX_SUMMARY_LINES} (G3)")
    for i, line in enumerate(summary_lines):
        if len(line) > MAX_CHARS_PER_LINE:
            raise SummaryBoundaryError(
                f"summary_lines[{i}] is {len(line)} chars; "
                f"max ~{MAX_TOKENS_PER_LINE} tokens (~{MAX_CHARS_PER_LINE} chars) per line (G3)"
            )
