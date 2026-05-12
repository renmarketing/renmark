"""Apply NIM output to the repo: write file (mode A) or patch (mode B), with validation."""
from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path


class ApplyError(RuntimeError):
    """Apply failed structurally (malformed output, patch rejected, syntax error)."""


# file_ext -> syntax-check command template. {path} is substituted.
_SYNTAX_CHECKERS: dict[str, list[str]] = {
    ".py": ["python", "-m", "py_compile", "{path}"],
    ".js": ["node", "--check", "{path}"],
    ".mjs": ["node", "--check", "{path}"],
    ".cjs": ["node", "--check", "{path}"],
    ".ts": ["npx", "--no-install", "tsc", "--noEmit", "--allowJs", "{path}"],
    ".tsx": ["npx", "--no-install", "tsc", "--noEmit", "--jsx", "preserve",
             "--allowJs", "{path}"],
    ".sh": ["bash", "-n", "{path}"],
    ".json": ["python", "-c",
              "import json,sys; json.load(open(sys.argv[1]))", "{path}"],
}

_FENCE_RE = re.compile(r"^```[a-zA-Z0-9_+\-]*\s*\n", re.MULTILINE)
_TRAILING_FENCE_RE = re.compile(r"\n```\s*$")


@dataclass
class ApplyResult:
    written_path: str
    bytes_written: int


def strip_markdown_fences(text: str) -> str:
    """Drop one leading and trailing ``` fence if present.

    NIM is told not to use fences but sometimes does anyway.
    """
    text = text.lstrip()
    m = _FENCE_RE.match(text + "\n")
    if m:
        text = text[m.end() - 1 :]  # keep nothing of the fence line
    text = _TRAILING_FENCE_RE.sub("", text)
    return text.strip() + "\n" if text.strip() else ""


def syntax_check(path: Path) -> tuple[bool, str]:
    """Run the language-appropriate syntax checker. Returns (ok, message).

    Unknown extensions are accepted (no check available).
    """
    ext = path.suffix.lower()
    tmpl = _SYNTAX_CHECKERS.get(ext)
    if tmpl is None:
        return True, f"no syntax checker for {ext}; skipping"
    cmd = [arg.replace("{path}", str(path)) for arg in tmpl]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        return True, f"syntax-checker unavailable ({e}); skipping"
    if proc.returncode == 0:
        return True, "ok"
    return False, (proc.stderr or proc.stdout or "syntax check failed").strip()


def apply_mode_a(
    repo_root: str | Path, target: str, body: str
) -> ApplyResult:
    """Write a new file. Strip fences, run syntax check, then write atomically."""
    cleaned = strip_markdown_fences(body)
    if not cleaned:
        raise ApplyError("mode A: NIM returned empty content")

    target_path = (Path(repo_root) / target).resolve()
    repo_root_resolved = Path(repo_root).resolve()
    if not str(target_path).startswith(str(repo_root_resolved) + "/") \
            and target_path != repo_root_resolved:
        raise ApplyError(f"target escapes repo root: {target}")
    target_path.parent.mkdir(parents=True, exist_ok=True)

    # Syntax-check in a temp file first; don't pollute the target on failure.
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=target_path.suffix, delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(cleaned)
        tmp_path = Path(tmp.name)
    try:
        ok, msg = syntax_check(tmp_path)
        if not ok:
            raise ApplyError(f"mode A: syntax check failed: {msg}")
    finally:
        try:
            tmp_path.unlink()
        except FileNotFoundError:
            pass

    target_path.write_text(cleaned, encoding="utf-8")
    return ApplyResult(written_path=str(target_path), bytes_written=len(cleaned))


def apply_mode_b(
    repo_root: str | Path, target: str, diff_text: str
) -> ApplyResult:
    """Apply a unified diff via `patch -p0`. Dry-run first; abort on failure."""
    cleaned = strip_markdown_fences(diff_text).rstrip() + "\n"
    if not cleaned.lstrip().startswith("--- ") or "@@" not in cleaned:
        raise ApplyError(
            "mode B: response is not a unified diff "
            "(must start with '--- ' and contain '@@')"
        )

    target_path = (Path(repo_root) / target).resolve()
    if not target_path.is_file():
        raise ApplyError(f"mode B target file does not exist: {target}")

    # Verify the diff only touches `target`.
    touched = _diff_touched_files(cleaned)
    if not touched:
        raise ApplyError("mode B: diff did not list any files")
    if set(touched) - {target, "./" + target}:
        raise ApplyError(
            f"mode B: diff must modify exactly one file ({target}); got {touched}"
        )

    if not shutil.which("patch"):
        raise ApplyError("`patch` command not found in PATH")

    # Dry run.
    dry = subprocess.run(
        ["patch", "-p0", "--dry-run", "--forward", "--silent"],
        input=cleaned, capture_output=True, text=True, cwd=repo_root,
    )
    if dry.returncode != 0:
        raise ApplyError(
            "mode B: patch --dry-run rejected:\n"
            f"{(dry.stderr or dry.stdout)[-800:]}"
        )
    # Apply for real.
    real = subprocess.run(
        ["patch", "-p0", "--forward", "--silent"],
        input=cleaned, capture_output=True, text=True, cwd=repo_root,
    )
    if real.returncode != 0:
        raise ApplyError(
            "mode B: patch failed after dry-run passed (race?):\n"
            f"{(real.stderr or real.stdout)[-800:]}"
        )
    return ApplyResult(written_path=str(target_path), bytes_written=len(cleaned))


def _diff_touched_files(diff_text: str) -> list[str]:
    paths: list[str] = []
    for line in diff_text.splitlines():
        if line.startswith("+++ "):
            rest = line[4:].strip()
            # Strip timestamp if present.
            rest = rest.split("\t", 1)[0].strip()
            if rest and rest != "/dev/null":
                paths.append(rest)
    return paths
