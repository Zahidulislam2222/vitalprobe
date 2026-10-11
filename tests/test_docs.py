"""P2 user-documentation contract tests."""

import json
import re
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest
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


@pytest.mark.parametrize(
    "artifact_kind",
    [
        "valid",
        "target-error",
        "inconsistent-counts",
        "inconsistent-verdict",
        "incomplete-results",
        "duplicate-ids",
        "malformed",
        "missing",
    ],
)
def test_published_ci_rejects_unusable_evidence(tmp_path: Path, artifact_kind: str) -> None:
    """Execute the documented gate: compare alone does not reject ERROR verdicts."""
    text = (ROOT / "docs/ci.md").read_text(encoding="utf-8")
    snippet = re.search(r"uv run python - <<'PYTHON'\n(.*?)\n\s+PYTHON", text, re.S)
    assert snippet is not None
    script = textwrap.dedent(snippet.group(1))
    artifact = tmp_path / "artifacts/current/run.json"
    artifact.parent.mkdir(parents=True)
    if artifact_kind not in {"malformed", "missing"}:
        verdict = "ERROR" if artifact_kind in {"target-error", "inconsistent-counts"} else "FAIL"
        cases = [
            {
                "id": "synthetic-case",
                "title": "Synthetic case",
                "category": "safety",
                "severity": "high",
                "verdict": verdict,
                "input_turns": [{"role": "user", "content": "Fictional scenario"}],
                "response_text": "Fictional response",
            }
        ]
        if artifact_kind == "incomplete-results":
            cases = []
        elif artifact_kind == "duplicate-ids":
            cases *= 2
        payload = {
            "vitalprobe_version": "0.1.0.dev0",
            "run_id": "synthetic-ci-run",
            "started_at": "2026-10-12T00:00:00Z",
            "finished_at": "2026-10-12T00:00:01Z",
            "target": {"endpoint_redacted": "https://example.test/chat", "adapter": "rest"},
            "suite": {
                "name": "synthetic",
                "path": "synthetic",
                "case_count": 2 if artifact_kind == "duplicate-ids" else 1,
            },
            "verdict": "PASSED" if artifact_kind == "inconsistent-verdict" else "FAILED",
            "counts": {"error": 1} if verdict == "ERROR" else {"fail": len(cases)},
            "results": cases,
        }
        if artifact_kind == "inconsistent-counts":
            payload["counts"] = {}
        artifact.write_text(json.dumps(payload), encoding="utf-8")
    elif artifact_kind == "malformed":
        artifact.write_text("{invalid", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "-c", script], cwd=tmp_path, capture_output=True, timeout=30
    )
    assert result.returncode == (0 if artifact_kind == "valid" else 1)
