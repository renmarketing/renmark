"""Prompt templates for mode A (new file) and mode B (unified diff)."""
from __future__ import annotations

from pathlib import Path

from .parser import Task


_EXT_LANG = {
    ".py": "Python", ".js": "JavaScript", ".mjs": "JavaScript",
    ".ts": "TypeScript", ".tsx": "TypeScript", ".sh": "Bash",
    ".json": "JSON", ".md": "Markdown", ".yaml": "YAML", ".yml": "YAML",
    ".html": "HTML", ".css": "CSS", ".go": "Go", ".rs": "Rust",
}


def language_of(target: str) -> str:
    return _EXT_LANG.get(Path(target).suffix.lower(), "code")


def mode_a_prompt(task: Task) -> str:
    lang = language_of(task.target)
    return (
        "You are writing a single file. Output ONLY the file contents — no prose, "
        "no markdown code fences, no commentary, no explanations.\n\n"
        f"Target path: {task.target}\n\n"
        "Specification:\n"
        f"{task.spec}\n\n"
        "Constraints:\n"
        f"- Output must be valid {lang} that parses cleanly.\n"
        "- Do not include explanations, usage examples, or test code in this file.\n"
        "- Follow standard style for the language (PEP 8 for Python, etc.).\n"
        "- The first line of your response must be the first line of the file.\n"
    )


def mode_b_prompt(task: Task, current_contents: str, context: dict[str, str]) -> str:
    parts = [
        "You are producing a unified diff to apply to ONE file.\n",
        f"\nTarget path: {task.target}\n",
        "\nCurrent contents of the target file:\n",
        "<<<FILE\n",
        current_contents.rstrip() + "\n",
        "FILE>>>\n",
    ]
    for ctx_path, body in context.items():
        parts.extend([
            f"\nAdditional read-only context (do not modify):\n",
            f"<<<CONTEXT path={ctx_path}\n",
            body.rstrip() + "\n",
            "CONTEXT>>>\n",
        ])
    parts.extend([
        "\nSpecification:\n",
        task.spec + "\n",
        "\nOutput ONLY a unified diff in `diff -u` format that:\n",
        "- Applies cleanly with `patch -p0` from the repo root.\n",
        f"- Modifies exactly one file: {task.target}.\n",
        "- Uses 3 lines of context per hunk.\n",
        "- Begins with two header lines: `--- <path>` and `+++ <path>`.\n",
        "\nDo not include prose, markdown fences, or commentary.\n",
    ])
    return "".join(parts)


def retry_prompt(original: str, verifier_tail: str) -> str:
    return (
        original
        + "\n\n---\nThe previous attempt FAILED. Verifier output (last lines):\n"
        + "<<<VERIFIER\n"
        + verifier_tail.rstrip()
        + "\nVERIFIER>>>\n"
        + "\nFix the issue and produce a corrected response in the same format.\n"
    )


def format_reminder_prompt(original: str, problem: str) -> str:
    return (
        original
        + "\n\n---\nThe previous response had a STRUCTURAL problem:\n"
        + problem
        + "\nProduce a corrected response. Output ONLY the required format — "
        + "no markdown fences, no prose, no commentary.\n"
    )
