from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
QA_FLOWS_PATH = REPO_ROOT / ".renmark" / "memory" / "qa-flows.md"
VERIFY_SKILL_PATH = REPO_ROOT / "plugin" / "skills" / "verify" / "SKILL.md"
MEMORY_INDEX_PATH = REPO_ROOT / ".renmark" / "memory" / "INDEX.md"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_qa_flows_store_exists_and_has_template() -> None:
    contents = read_text(QA_FLOWS_PATH)

    assert QA_FLOWS_PATH.exists()
    assert "## Flow:" in contents
    for label in (
        "Preconditions",
        "Actions",
        "Expected",
        "Known risks",
        "Last passing",
    ):
        assert label in contents


def test_verify_reads_qa_flows_before_choosing() -> None:
    contents = read_text(VERIFY_SKILL_PATH)

    assert "qa-flows.md" in contents
    assert "Before deriving the happy-path flow" in contents
    assert "before" in contents.lower()
    assert "choosing a flow" in contents.lower() or "selected flow" in contents.lower()


def test_verify_handles_missing_qa_flows() -> None:
    contents = read_text(VERIFY_SKILL_PATH)

    assert "missing or empty" in contents
    assert "Existing QA must not break in the absence of QA-flow memory" in contents


def test_verify_bootstrap_flag_documented() -> None:
    contents = read_text(VERIFY_SKILL_PATH)

    assert "--qa --bootstrap" in contents


def test_verify_promotes_passing_flow() -> None:
    contents = read_text(VERIFY_SKILL_PATH)

    assert "promote" in contents.lower()
    assert "On **pass**" in contents


def test_index_registers_qa_flows() -> None:
    contents = read_text(MEMORY_INDEX_PATH)

    assert "qa-flows.md" in contents
