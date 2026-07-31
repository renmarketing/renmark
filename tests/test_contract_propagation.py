"""End-to-end regression coverage for managed delivery-contract propagation."""

from __future__ import annotations

from pathlib import Path

import pytest

from renmark import init, memory

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "plugin" / "skills" / ".shared" / "project-delivery-contract.md"


def _guidance(repo: Path) -> dict[str, bytes]:
    return {name: (repo / name).read_bytes() for name in ("CLAUDE.md", "AGENTS.md")}


def _managed_exterior(content: bytes) -> tuple[bytes, bytes]:
    """Return the exact user-owned bytes on either side of the managed range."""
    begin = init.PROJECT_DELIVERY_BEGIN.encode("utf-8")
    end = init.PROJECT_DELIVERY_END.encode("utf-8")
    start = content.index(begin)
    finish = content.index(end, start) + len(end)
    return content[:start], content[finish:]


def _write_stale_guidance(repo: Path) -> str:
    custom = "# Team instructions\n\nKeep this user-owned instruction exactly.\n"
    stale = (
        f"{init.PROJECT_DELIVERY_BEGIN}\n"
        "<!-- Last refreshed: @ stale -->\n"
        "Old managed contract.\n"
        f"{init.PROJECT_DELIVERY_END}\n"
    )
    for name in ("CLAUDE.md", "AGENTS.md"):
        (repo / name).write_text(custom + "\n" + stale, encoding="utf-8")
    return custom


def test_first_refresh_preserves_exact_crlf_custom_guidance_outside_managed_range(tmp_path: Path) -> None:
    """The initial repair must not normalize user-owned bytes around the contract."""
    stale = (
        f"{init.PROJECT_DELIVERY_BEGIN}\r\n"
        "<!-- Last refreshed: @ stale -->\r\n"
        "Old managed contract.\r\n"
        f"{init.PROJECT_DELIVERY_END}"
    ).encode()
    before: dict[str, tuple[bytes, bytes]] = {}
    for name in ("CLAUDE.md", "AGENTS.md"):
        prefix = (
            f"# {name} custom heading\r\n\r\n"
            "  Keep this indented user-owned line exactly.  \r\n"
        ).encode()
        suffix = (
            b"\r\n\r\n<!-- custom footer: preserve spacing -->\r\n"
            b"Owner-only postscript.\r\n"
        )
        original = prefix + stale + suffix
        (tmp_path / name).write_bytes(original)
        before[name] = _managed_exterior(original)

    assert init.merge_project_delivery_contract(tmp_path) == {
        "CLAUDE.md": "refreshed",
        "AGENTS.md": "refreshed",
    }

    for name, expected_exterior in before.items():
        refreshed = (tmp_path / name).read_bytes()
        assert _managed_exterior(refreshed) == expected_exterior, name
        assert b"\r\n" in refreshed, name


def _managed_body(text: str) -> str:
    body = init._marked_block_body(text, init.PROJECT_DELIVERY_MARKER)
    assert body is not None
    lines = body.splitlines()
    while lines and not lines[0]:
        lines.pop(0)
    if lines and lines[0].startswith("<!-- Last refreshed: @ "):
        lines.pop(0)
    return "\n".join(lines)


def _semantic(text: str) -> str:
    return " ".join(text.casefold().split())


@pytest.mark.parametrize("existing", (False, True), ids=("new", "existing"))
def test_init_converges_new_and_existing_projects_without_clobbering_custom_guidance(
    tmp_path: Path, existing: bool
) -> None:
    custom = "# Our project\n\nNever remove this owner instruction.\n"
    if existing:
        for name in ("CLAUDE.md", "AGENTS.md"):
            (tmp_path / name).write_text(custom, encoding="utf-8")

    code, summary = init.run(tmp_path)

    assert code == 0, summary
    for name, text in ((name, (tmp_path / name).read_text(encoding="utf-8")) for name in ("CLAUDE.md", "AGENTS.md")):
        if existing:
            assert text.startswith(custom), name
        assert init.contract_is_fresh(text, tmp_path), name
    assert init.contracts_are_semantically_equal(
        (tmp_path / "CLAUDE.md").read_text(encoding="utf-8"),
        (tmp_path / "AGENTS.md").read_text(encoding="utf-8"),
    )


@pytest.mark.parametrize("entrypoint", ("start", "feature"))
def test_stale_start_and_feature_routes_converge_through_the_same_safe_writer(
    tmp_path: Path, entrypoint: str
) -> None:
    """Both entry instructions route staleness to init, never to a competing writer."""
    skill = ROOT / "plugin" / "skills" / entrypoint / "SKILL.md"
    wording = skill.read_text(encoding="utf-8")
    assert "renmark.init.contract_is_fresh" in wording
    assert "renmark.init.merge_project_delivery_contract(repo)" in wording
    assert "sole safe" in wording

    custom = _write_stale_guidance(tmp_path)
    assert not all(
        init.contract_is_fresh((tmp_path / name).read_text(encoding="utf-8"), tmp_path)
        for name in ("CLAUDE.md", "AGENTS.md")
    )

    result = init.merge_project_delivery_contract(tmp_path)
    assert result == {"CLAUDE.md": "refreshed", "AGENTS.md": "refreshed"}
    first = _guidance(tmp_path)
    assert all(content.decode("utf-8").startswith(custom) for content in first.values())
    assert all(init.contract_is_fresh(content.decode("utf-8"), tmp_path) for content in first.values())
    assert init.contracts_are_semantically_equal(
        first["CLAUDE.md"].decode("utf-8"), first["AGENTS.md"].decode("utf-8")
    )

    assert init.merge_project_delivery_contract(tmp_path) == {
        "CLAUDE.md": "unchanged",
        "AGENTS.md": "unchanged",
    }
    assert _guidance(tmp_path) == first


def test_root_templates_and_installed_templates_share_the_canonical_contract_and_selector_words() -> None:
    """Source, root guidance, and the installed scaffold templates stay semantically aligned."""
    template_dir = memory.template_dir()
    assert template_dir is not None
    canonical = _semantic(CONTRACT.read_text(encoding="utf-8"))
    bodies = [
        _managed_body((ROOT / name).read_text(encoding="utf-8"))
        for name in ("CLAUDE.md", "AGENTS.md")
    ] + [
        _managed_body((template_dir.parent / name).read_text(encoding="utf-8"))
        for name in ("CLAUDE.md.template", "AGENTS.md.template")
    ]

    assert all(_semantic(body) == canonical for body in bodies)
    for phrase in (
        "native picker",
        "numbered fallback",
        "recommended safe option first",
        "different decision or an automatic approval",
        "interactive claude code main session",
        "askuserquestion",
        "real `options` array",
    ):
        assert phrase in canonical


def test_stale_entry_marker_corruption_fails_safe_without_touching_either_guidance_file(tmp_path: Path) -> None:
    _write_stale_guidance(tmp_path)
    broken = tmp_path / "CLAUDE.md"
    broken.write_text(
        "# Custom instruction\n\n" + init.PROJECT_DELIVERY_BEGIN + "\nunfinished\n",
        encoding="utf-8",
    )
    before = _guidance(tmp_path)

    with pytest.raises(init.MarkerCorruptionError):
        init.merge_project_delivery_contract(tmp_path)

    assert _guidance(tmp_path) == before
