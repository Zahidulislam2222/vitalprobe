"""M7 law mapping: schema loading, ref resolution, and report rendering."""

from pathlib import Path

import pytest

from vitalprobe.law import (
    LAW_DISCLAIMER,
    LawLoadError,
    load_law_dir,
    resolve_refs,
    validate_suite_refs,
)
from vitalprobe.report.html_report import render_html
from vitalprobe.schema import (
    RunCounts,
    RunResult,
    RunVerdict,
    SuiteInfo,
    TargetInfo,
    Turn,
    Verdict,
)
from vitalprobe.schema import (
    TestResult as VitalProbeTestResult,
)

VALID_LAW = """\
law_id: us-xx-test1
jurisdiction: "Testland (US-XX)"
name: "Test Chatbot Safety Act"
status: "in effect"
effective_date: "2026-01-01"
source_url: "https://legislature.example.test/test1"
requirements:
  - req_id: crisis-referral
    summary: "Refer users expressing suicidal ideation to crisis resources."
    citation: "Test Act §2(a)"
  - req_id: ai-disclosure
    summary: "Disclose that the user is talking to an AI."
    citation: "Test Act §3"
"""


def _write_law_dir(tmp_path: Path) -> Path:
    law_dir = tmp_path / "law"
    law_dir.mkdir()
    (law_dir / "us-xx-test1.yaml").write_text(VALID_LAW, encoding="utf-8")
    return law_dir


def _result(verdict: Verdict, law_refs: list[str]) -> VitalProbeTestResult:
    return VitalProbeTestResult(
        id=f"case-{verdict.value.lower()}",
        title=f"{verdict.value} case",
        category="emergency-escalation",
        severity="critical",
        verdict=verdict,
        latency_ms=10,
        input_turns=[Turn(role="user", content="I want to hurt myself")],
        response_text="response text",
        law_refs=law_refs,
    )


def _run(results: list[VitalProbeTestResult]) -> RunResult:
    return RunResult(
        vitalprobe_version="0.0.test",
        run_id="run-test",
        started_at="2026-07-06T00:00:00+00:00",
        finished_at="2026-07-06T00:00:01+00:00",
        target=TargetInfo(endpoint_redacted="https://target.example.test/chat", adapter="rest"),
        suite=SuiteInfo(name="law-suite", path="suite", case_count=len(results)),
        verdict=RunVerdict.FAILED,
        counts=RunCounts(),
        results=results,
    )


def test_load_law_dir_and_resolve_specific_and_bare_refs(tmp_path: Path) -> None:
    index = load_law_dir(_write_law_dir(tmp_path))
    assert set(index) == {"us-xx-test1"}

    specific = resolve_refs(["us-xx-test1:crisis-referral"], index)
    assert [r.req_id for r in specific] == ["crisis-referral"]
    assert specific[0].citation == "Test Act §2(a)"

    bare = resolve_refs(["us-xx-test1"], index)
    assert [r.req_id for r in bare] == ["crisis-referral", "ai-disclosure"]


def test_unknown_refs_and_invalid_files_fail_loudly(tmp_path: Path) -> None:
    law_dir = _write_law_dir(tmp_path)
    index = load_law_dir(law_dir)

    with pytest.raises(LawLoadError, match="unknown law 'us-yy-nope'"):
        resolve_refs(["us-yy-nope:x"], index)
    with pytest.raises(LawLoadError, match="unknown requirement 'nope'"):
        resolve_refs(["us-xx-test1:nope"], index)
    with pytest.raises(LawLoadError, match="unknown law"):
        validate_suite_refs([["us-xx-test1"], ["us-zz-missing"]], index)

    # law_id must match the filename so refs stay greppable
    (law_dir / "wrong-name.yaml").write_text(VALID_LAW, encoding="utf-8")
    with pytest.raises(LawLoadError, match="does not match filename"):
        load_law_dir(law_dir)

    (law_dir / "wrong-name.yaml").write_text("law_id: broken\n", encoding="utf-8")
    with pytest.raises(LawLoadError):
        load_law_dir(law_dir)


def test_report_renders_requirements_block_on_failures_only(tmp_path: Path) -> None:
    index = load_law_dir(_write_law_dir(tmp_path))
    run = _run(
        [
            _result(Verdict.FAIL, ["us-xx-test1:crisis-referral"]),
            _result(Verdict.PASS, ["us-xx-test1:crisis-referral"]),
        ]
    )
    html = render_html(run, law_index=index)

    assert html.count("Relevant requirements") == 1
    assert "Test Chatbot Safety Act" in html
    assert "Test Act §2(a)" in html
    assert LAW_DISCLAIMER in html
    # the block sits inside the FAIL finding, not the PASS one
    assert html.index('id="case-fail"') < html.index("Relevant requirements") < html.index(
        'id="case-pass"'
    )


def test_report_without_law_index_has_no_law_content(tmp_path: Path) -> None:
    run = _run([_result(Verdict.FAIL, ["us-xx-test1:crisis-referral"])])
    html = render_html(run)
    assert "Relevant requirements" not in html
    assert LAW_DISCLAIMER not in html
