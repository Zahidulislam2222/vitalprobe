"""P2 user-documentation contract tests."""

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).parents[1]


def test_p2_docs_and_report_preview_exist() -> None:
    required = [
        ROOT / "docs/quickstart.md",
        ROOT / "docs/writing-tests.md",
        ROOT / "docs/ci.md",
        ROOT / "docs/assets/report-preview.png",
    ]
    assert [str(path.relative_to(ROOT)) for path in required if not path.is_file()] == []
    assert (ROOT / "docs/assets/report-preview.png").stat().st_size > 0


def test_ci_document_contains_valid_pinned_workflow() -> None:
    text = (ROOT / "docs/ci.md").read_text(encoding="utf-8")
    workflow = text.split("```yaml", 1)[1].split("```", 1)[0]
    assert isinstance(yaml.safe_load(workflow), dict)
    uses = re.findall(r"uses:\s*(\S+)", workflow)
    assert uses
    assert all(re.fullmatch(r"[^@]+@[0-9a-f]{40}", value) for value in uses)
    assert "continue-on-error: true" in workflow
    assert "if: always()" in workflow
    assert "vitalprobe compare" in workflow


def test_readme_is_honest_about_deferred_pypi_release() -> None:
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "PyPI publishing" in text
    assert "intentionally deferred" in text
    assert "docs/assets/report-preview.png" in text
    assert "pypi.org" not in text.casefold()
