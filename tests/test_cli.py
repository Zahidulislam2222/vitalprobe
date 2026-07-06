"""CLI behavior and exit-code tests."""

import re
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from vitalprobe import __version__, cli
from vitalprobe.experience.store import Regression
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

runner = CliRunner()
DATA_DIR = Path(__file__).parent / "data"
SUITE_DIR = DATA_DIR / "suite"
BROKEN_SUITE_DIR = DATA_DIR / "broken-suite"


def test_version() -> None:
    result = runner.invoke(cli.app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_validate_exit_codes() -> None:
    valid = runner.invoke(cli.app, ["validate", "--suite", str(SUITE_DIR)])
    broken = runner.invoke(cli.app, ["validate", "--suite", str(BROKEN_SUITE_DIR)])
    assert valid.exit_code == 0
    assert broken.exit_code == 2


class FakeAdapter:
    name = "rest"
    endpoint_redacted = "https://example.test/chat"

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        pass

    async def aclose(self) -> None:
        pass


def _run_result(verdict: RunVerdict) -> RunResult:
    counts = {
        RunVerdict.PASSED: RunCounts(pass_=1),
        RunVerdict.PASSED_WITH_WARNINGS: RunCounts(warn=1),
        RunVerdict.FAILED: RunCounts(fail=1),
    }[verdict]
    return RunResult(
        vitalprobe_version=__version__,
        run_id="00000000-0000-0000-0000-000000000000",
        started_at="2026-07-05T00:00:00+00:00",
        finished_at="2026-07-05T00:00:01+00:00",
        target=TargetInfo(endpoint_redacted=FakeAdapter.endpoint_redacted, adapter="rest"),
        suite=SuiteInfo(name="exit-code-suite", path="tests/data/suite", case_count=0),
        verdict=verdict,
        counts=counts,
        results=[],
    )


@pytest.mark.parametrize(
    ("verdict", "extra_args", "expected"),
    [
        (RunVerdict.PASSED, [], 0),
        (RunVerdict.PASSED_WITH_WARNINGS, [], 0),
        (RunVerdict.PASSED_WITH_WARNINGS, ["--strict-warn"], 1),
        (RunVerdict.FAILED, [], 1),
    ],
)
def test_run_exit_codes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    verdict: RunVerdict,
    extra_args: list[str],
    expected: int,
) -> None:
    async def fake_run(*_args: Any, **_kwargs: Any) -> RunResult:
        return _run_result(verdict)

    monkeypatch.setattr(cli, "RestAdapter", FakeAdapter)
    monkeypatch.setattr(cli, "run_suite_async", fake_run)
    result = runner.invoke(
        cli.app,
        [
            "run",
            "--suite",
            str(SUITE_DIR),
            "--output",
            str(tmp_path),
            *extra_args,
        ],
    )
    assert result.exit_code == expected
    assert (tmp_path / "run.json").is_file()
    assert (tmp_path / "report.html").is_file()


def test_json_format_skips_html(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    async def fake_run(*_args: Any, **_kwargs: Any) -> RunResult:
        return _run_result(RunVerdict.PASSED)

    monkeypatch.setattr(cli, "RestAdapter", FakeAdapter)
    monkeypatch.setattr(cli, "run_suite_async", fake_run)
    result = runner.invoke(
        cli.app,
        [
            "run",
            "--suite",
            str(SUITE_DIR),
            "--output",
            str(tmp_path),
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    assert (tmp_path / "run.json").is_file()
    assert not (tmp_path / "report.html").exists()


def test_run_save_baseline_writes_canonical_copy(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    async def fake_run(*_args: Any, **_kwargs: Any) -> RunResult:
        return _run_result(RunVerdict.PASSED)

    monkeypatch.setattr(cli, "RestAdapter", FakeAdapter)
    monkeypatch.setattr(cli, "run_suite_async", fake_run)
    output = tmp_path / "output"
    baseline = tmp_path / "baseline"
    result = runner.invoke(
        cli.app,
        [
            "run",
            "--suite",
            str(SUITE_DIR),
            "--output",
            str(output),
            "--save-baseline",
            str(baseline),
        ],
    )
    assert result.exit_code == 0
    assert (baseline / "run.json").read_bytes() == (output / "run.json").read_bytes()
    assert "baseline written" in result.output


def test_run_passes_configured_concurrency_to_engine(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, Any] = {}

    async def fake_run(*_args: Any, **kwargs: Any) -> RunResult:
        captured.update(kwargs)
        return _run_result(RunVerdict.PASSED)

    monkeypatch.setenv("VITALPROBE_RUNNER_CONCURRENCY", "1")
    monkeypatch.setattr(cli, "RestAdapter", FakeAdapter)
    monkeypatch.setattr(cli, "run_suite_async", fake_run)
    result = runner.invoke(
        cli.app,
        [
            "run",
            "--suite",
            str(SUITE_DIR),
            "--output",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0
    assert captured["max_concurrency"] == 1


def test_compare_exits_one_on_seeded_regression(tmp_path: Path) -> None:
    baseline = _run_result(RunVerdict.PASSED)
    baseline.results = [
        CaseResult(
            id="case-001",
            title="seed",
            category="safety",
            severity="high",
            verdict=Verdict.PASS,
            latency_ms=1,
            input_turns=[Turn(role="user", content="synthetic")],
            response_text="before",
        )
    ]
    current = baseline.model_copy(deep=True)
    current.results[0].verdict = Verdict.FAIL
    current.verdict = RunVerdict.FAILED
    current.counts = RunCounts(fail=1)
    baseline_path = tmp_path / "baseline.json"
    current_path = tmp_path / "current.json"
    baseline_path.write_text(baseline.model_dump_json(by_alias=True), encoding="utf-8")
    current_path.write_text(current.model_dump_json(by_alias=True), encoding="utf-8")

    result = runner.invoke(
        cli.app,
        [
            "compare",
            "--baseline",
            str(baseline_path),
            "--current",
            str(current_path),
        ],
    )

    assert result.exit_code == 1
    assert "REGRESSION" in result.output
    assert "case-001" in result.output


def test_regression_output_is_legacy_windows_console_safe() -> None:
    with cli.console.capture() as capture:
        cli._print_regressions([Regression("case-001", Verdict.PASS, Verdict.FAIL)])
    output = capture.get()
    assert "PASS -> FAIL" in output
    output.encode("cp1252")


def test_track_and_history_commands(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    async def fake_run(*_args: Any, **_kwargs: Any) -> RunResult:
        return _run_result(RunVerdict.PASSED)

    db_path = tmp_path / "vitalprobe.db"
    monkeypatch.setenv("VITALPROBE_DB_PATH", str(db_path))
    monkeypatch.setattr(cli, "RestAdapter", FakeAdapter)
    monkeypatch.setattr(cli, "run_suite_async", fake_run)
    tracked = runner.invoke(
        cli.app,
        [
            "run",
            "--suite",
            str(SUITE_DIR),
            "--output",
            str(tmp_path / "output"),
            "--track",
        ],
    )
    assert tracked.exit_code == 0
    assert db_path.is_file()
    assert "No regressions" in tracked.output

    result = runner.invoke(
        cli.app,
        ["history", "--target", FakeAdapter.endpoint_redacted],
    )
    assert result.exit_code == 0
    assert "VitalProbe history" in result.output
    assert "PASSED" in result.output


def test_license_show_degrades_cleanly_to_free(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("VITALPROBE_LICENSE_FILE", raising=False)
    monkeypatch.chdir(tmp_path)  # ignore any developer .env carrying a real dev license
    result = runner.invoke(cli.app, ["license", "show"])
    assert result.exit_code == 0
    # strip ANSI style codes: Rich may colorize when the invoking shell forces color
    output = re.sub(r"\x1b\[[0-9;]*m", "", result.output)
    assert "tier: free" in output
    assert "Free engine and reporting features remain available." in result.output


def test_license_verify_rejects_tampered_file(tmp_path: Path) -> None:
    path = tmp_path / "tampered.json"
    path.write_text('{"licensee": "not-signed"}', encoding="utf-8")
    result = runner.invoke(cli.app, ["license", "verify", str(path)])
    assert result.exit_code == 2
    assert "using the free tier" in result.output


def test_gated_feature_command_shows_upgrade_message(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("VITALPROBE_LICENSE_FILE", raising=False)
    monkeypatch.chdir(tmp_path)  # ignore any developer .env carrying a real dev license
    result = runner.invoke(cli.app, ["license", "check", "mcp_server"])
    assert result.exit_code == 2
    assert "requires a paid VitalProbe license" in result.output
    assert "Current tier: free" in result.output


def test_cloud_judge_cost_preflight_requires_confirmation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("VITALPROBE_JUDGE", "openai")
    monkeypatch.setenv("VITALPROBE_JUDGE_MODEL", "configured-model")
    monkeypatch.setenv("VITALPROBE_JUDGE_INPUT_PRICE_PER_MILLION", "1")
    monkeypatch.setenv("VITALPROBE_JUDGE_OUTPUT_PRICE_PER_MILLION", "2")
    result = runner.invoke(
        cli.app,
        [
            "run",
            "--suite",
            str(SUITE_DIR),
            "--output",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 2
    assert "estimated $" in result.output
    assert "requires --yes-spend" in result.output


def test_run_law_dir_requires_license(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """--law-dir is behind the LAW_MAPPING paid flag; free tier exits 2 before any run."""
    monkeypatch.chdir(tmp_path)  # ignore the project .env (dev license)
    result = runner.invoke(
        cli.app,
        ["run", "--suite", str(SUITE_DIR), "--output", str(tmp_path), "--law-dir", str(tmp_path)],
    )
    assert result.exit_code == 2
    assert "law mapping" in result.output
    assert not (tmp_path / "run.json").exists()
