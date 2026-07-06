"""Canonical run.json baseline comparison tests."""

from copy import deepcopy
from pathlib import Path

import pytest

from vitalprobe.baseline import BaselineError, compare_runs, load_run
from vitalprobe.schema import (
    RunCounts,
    RunResult,
    RunVerdict,
    SuiteInfo,
    TargetInfo,
    Turn,
    Verdict,
)
from vitalprobe.schema import TestResult as CaseResult


def _result(case_id: str, verdict: Verdict) -> CaseResult:
    return CaseResult(
        id=case_id,
        title=case_id,
        category="safety",
        severity="high",
        verdict=verdict,
        latency_ms=1,
        input_turns=[Turn(role="user", content="synthetic")],
        response_text="observed",
    )


def _run(results: list[CaseResult]) -> RunResult:
    return RunResult(
        vitalprobe_version="0.1.0.dev0",
        run_id="00000000-0000-0000-0000-000000000000",
        started_at="2026-07-06T00:00:00+00:00",
        finished_at="2026-07-06T00:00:01+00:00",
        target=TargetInfo(endpoint_redacted="https://example.test/chat", adapter="rest"),
        suite=SuiteInfo(name="seed", path="seed", case_count=len(results)),
        verdict=RunVerdict.FAILED,
        counts=RunCounts(),
        results=results,
    )


def test_compare_reports_regression_improvement_new_and_removed() -> None:
    baseline = _run(
        [
            _result("regressed", Verdict.PASS),
            _result("improved", Verdict.FAIL),
            _result("removed", Verdict.WARN),
            _result("unchanged", Verdict.PASS),
        ]
    )
    current = _run(
        [
            _result("regressed", Verdict.FAIL),
            _result("improved", Verdict.PASS),
            _result("new", Verdict.WARN),
            _result("unchanged", Verdict.PASS),
        ]
    )

    comparison = compare_runs(baseline, current)

    assert [(item.case_id, item.previous, item.current) for item in comparison.regressions] == [
        ("regressed", Verdict.PASS, Verdict.FAIL)
    ]
    assert [(item.case_id, item.previous, item.current) for item in comparison.improvements] == [
        ("improved", Verdict.FAIL, Verdict.PASS)
    ]
    assert [(item.case_id, item.verdict) for item in comparison.new_cases] == [
        ("new", Verdict.WARN)
    ]
    assert [(item.case_id, item.verdict) for item in comparison.removed_cases] == [
        ("removed", Verdict.WARN)
    ]


def test_compare_does_not_mutate_runs() -> None:
    baseline = _run([_result("case", Verdict.PASS)])
    current = _run([_result("case", Verdict.FAIL)])
    baseline_before = deepcopy(baseline.model_dump())
    current_before = deepcopy(current.model_dump())

    compare_runs(baseline, current)

    assert baseline.model_dump() == baseline_before
    assert current.model_dump() == current_before


def test_load_run_rejects_invalid_json(tmp_path: Path) -> None:
    path = tmp_path / "run.json"
    path.write_text("not-json", encoding="utf-8")
    with pytest.raises(BaselineError, match="cannot load run artifact"):
        load_run(path)
