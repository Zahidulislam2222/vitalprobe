"""P9a/P9b local dashboard: read-only pages over the experience store."""

import subprocess
import sys
import tempfile
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import create_engine

from vitalprobe.config import Settings
from vitalprobe.dashboard.app import create_app
from vitalprobe.dashboard.services import TriggerOutcome
from vitalprobe.entitlements.features import FeatureFlag
from vitalprobe.entitlements.license import EntitlementStatus
from vitalprobe.experience.store import CalibrationLabelRecord, ExperienceStore
from vitalprobe.law import LAW_DISCLAIMER
from vitalprobe.schema import (
    CheckResult,
    RunCounts,
    RunResult,
    RunVerdict,
    SuiteInfo,
    TargetInfo,
    Turn,
    Verdict,
)
from vitalprobe.schema import (
    TestResult as CaseResult,
)

TARGET = "https://example.test/chat"


def _run(
    run_id: str,
    verdict: Verdict,
    *,
    title: str = "Emergency escalation",
    evidence: str = "seed evidence text",
) -> RunResult:
    result = CaseResult(
        id="case-001",
        title=title,
        category="safety",
        severity="critical",
        verdict=verdict,
        latency_ms=12,
        input_turns=[Turn(role="user", content="synthetic input")],
        response_text="observed response",
        checks=[
            CheckResult(
                type="must_contain",
                passed=verdict is Verdict.PASS,
                evidence=evidence,
            )
        ],
    )
    return RunResult(
        vitalprobe_version="0.1.0.dev0",
        run_id=run_id,
        started_at=f"2026-07-17T00:00:0{run_id}+00:00",
        finished_at=f"2026-07-17T00:00:1{run_id}+00:00",
        target=TargetInfo(endpoint_redacted=TARGET, adapter="rest"),
        suite=SuiteInfo(name="seed-suite", path="tests/data/suite", case_count=1),
        verdict=RunVerdict.PASSED if verdict is Verdict.PASS else RunVerdict.FAILED,
        counts=RunCounts(pass_=int(verdict is Verdict.PASS), fail=int(verdict is Verdict.FAIL)),
        results=[result],
    )


def _store() -> ExperienceStore:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    return ExperienceStore(engine=engine)


def _client(store: ExperienceStore) -> TestClient:
    return TestClient(create_app(store))


def _seeded_store() -> ExperienceStore:
    store = _store()
    store.record_run(_run("1", Verdict.PASS), secrets=[])
    store.record_run(_run("2", Verdict.FAIL), secrets=[])
    return store


def test_runs_index_empty_state() -> None:
    response = _client(_store()).get("/")
    assert response.status_code == 200
    assert "No tracked runs yet" in response.text


def test_runs_index_lists_runs_newest_first() -> None:
    html = _client(_seeded_store()).get("/").text
    assert html.index("/runs/2") < html.index("/runs/1")
    assert "FAILED" in html
    assert "seed-suite" in html


def test_run_summaries_and_targets_store_api() -> None:
    store = _seeded_store()
    summaries = store.run_summaries()
    assert [s.run_id for s in summaries] == ["2", "1"]
    assert summaries[0].target == TARGET
    assert summaries[0].fail_count == 1
    assert store.targets() == [TARGET]


def test_run_detail_shows_checks_and_evidence() -> None:
    html = _client(_seeded_store()).get("/runs/2").text
    assert "case-001" in html
    assert "must_contain" in html
    assert "seed evidence text" in html
    assert "observed response" not in html  # responses stay in reports, not list pages


def test_run_detail_unknown_id_is_404() -> None:
    assert _client(_seeded_store()).get("/runs/nope").status_code == 404


def test_history_page_shows_regression() -> None:
    html = _client(_seeded_store()).get("/history", params={"target": TARGET}).text
    assert "1 regression" in html


def test_compare_page_reports_regression_and_improvement() -> None:
    client = _client(_seeded_store())
    regressed = client.get("/compare", params={"baseline": "1", "current": "2"}).text
    assert "Regressions (1)" in regressed
    improved = client.get("/compare", params={"baseline": "2", "current": "1"}).text
    assert "Improvements (1)" in improved


def test_compare_unknown_run_shows_error_not_crash() -> None:
    response = _client(_seeded_store()).get(
        "/compare", params={"baseline": "1", "current": "nope"}
    )
    assert response.status_code == 200
    assert "unknown run id" in response.text


def test_pages_reference_no_external_assets(monkeypatch: pytest.MonkeyPatch) -> None:
    _isolate_free_tier(monkeypatch)  # deterministic: learning/law render their locked pages
    client = _client(_seeded_store())
    for path in ("/", "/runs/2", "/compare", "/trigger-run", "/learning", "/law"):
        html = client.get(path).text
        assert 'src="http' not in html
        assert 'href="http' not in html
        assert "@import" not in html


def test_untrusted_target_content_is_escaped() -> None:
    """Bot output is hostile input: titles/evidence must never render as HTML."""
    store = _store()
    payload = "<script>alert(1)</script>"
    store.record_run(_run("9", Verdict.FAIL, title=payload, evidence=payload), secrets=[])
    html = _client(store).get("/runs/9").text
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html


def test_api_schema_endpoints_disabled() -> None:
    client = _client(_store())
    assert client.get("/docs").status_code == 404
    assert client.get("/openapi.json").status_code == 404


def test_license_page_defaults_to_free_tier_with_locked_flags(
    monkeypatch: "pytest.MonkeyPatch",
) -> None:
    monkeypatch.delenv("VITALPROBE_LICENSE_FILE", raising=False)
    monkeypatch.chdir(tempfile.gettempdir())  # no project .env
    html = _client(_store()).get("/license").text
    assert "free" in html
    assert "locked — paid tier" in html
    assert "law_mapping" in html
    assert "mcp_server" in html


def test_calibration_page_zero_state_and_counts() -> None:
    store = _store()
    client = _client(store)
    assert "No labels recorded yet" in client.get("/calibration").text
    store.record_calibration_labels(
        [
            CalibrationLabelRecord(
                item_id="i1", case_id="case-001", judge="h", human_verdict="PASS"
            ),
            CalibrationLabelRecord(
                item_id="i2", case_id="case-002", judge="h", human_verdict="FAIL"
            ),
            CalibrationLabelRecord(
                item_id="i3", case_id="case-002", judge="h", human_verdict="FAIL"
            ),
        ]
    )
    html = client.get("/calibration").text
    assert ">3<" in html
    assert ">2<" in html


def test_dashboard_defaults_are_localhost_only() -> None:
    settings = Settings(_env_file=None)
    assert settings.dashboard_host == "127.0.0.1"
    assert 1 <= settings.dashboard_port <= 65535


# --- P9b part 2: paid surfaces (learning, law) + trigger-run form ---


def _isolate_free_tier(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("VITALPROBE_LICENSE_FILE", raising=False)
    monkeypatch.chdir(tempfile.gettempdir())  # no project .env


def _licensed(monkeypatch: pytest.MonkeyPatch) -> None:
    """Unlock learning + law_mapping exactly where `entitlements.require` looks."""
    status = EntitlementStatus(
        tier="business",
        features=frozenset({FeatureFlag.LEARNING, FeatureFlag.LAW_MAPPING}),
        valid=True,
        message="test license",
    )
    monkeypatch.setattr(
        "vitalprobe.entitlements.license.verify_license",
        lambda path=None, **kwargs: status,
    )


def _draft_case(case_id: str = "case-001-var-1") -> dict[str, object]:
    return {
        "id": case_id,
        "title": "Emergency escalation (adversarial variant 1)",
        "category": "safety",
        "severity": "critical",
        "status": "draft",
        "input": {"turns": [{"role": "user", "content": "synthetic variant"}]},
        "expect": {"category": "safety", "must": [{"type": "nonempty"}]},
        "notes": "auto-generated from run 1, case case-001",
    }


LAW_YAML = """\
law_id: test-law
jurisdiction: Testland
name: Test Health Communications Act
status: draft
effective_date: "2025-01-01"
source_url: https://example.test/law
requirements:
  - req_id: crisis-routing
    summary: Crisis messages must be routed to emergency guidance.
    citation: "Section 1(a)"
"""


def test_learning_free_tier_shows_locked_state(monkeypatch: pytest.MonkeyPatch) -> None:
    _isolate_free_tier(monkeypatch)
    response = _client(_store()).get("/learning")
    assert response.status_code == 200
    assert "requires a paid VitalProbe license" in response.text
    assert "&#39;learning&#39;" in response.text  # the flag named in the escaped CLI wording


def test_law_free_tier_shows_locked_state(monkeypatch: pytest.MonkeyPatch) -> None:
    _isolate_free_tier(monkeypatch)
    response = _client(_store()).get("/law")
    assert response.status_code == 200
    assert "requires a paid VitalProbe license" in response.text
    assert "&#39;law mapping&#39;" in response.text


def test_learning_licensed_lists_drafts_and_flags_bad_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _licensed(monkeypatch)
    drafts = tmp_path / "drafts"
    drafts.mkdir()
    (drafts / "case-001-variants.yaml").write_text(
        yaml.safe_dump([_draft_case()]), encoding="utf-8"
    )
    (drafts / "broken.yaml").write_text("just a string", encoding="utf-8")
    settings = Settings(_env_file=None, drafts_dir=drafts)
    html = TestClient(create_app(_store(), settings=settings)).get("/learning").text
    assert "case-001-var-1" in html
    assert "adversarial variant 1" in html
    assert "auto-generated from run 1" in html
    assert "broken.yaml" in html
    assert "unreadable draft file" in html


def test_learning_licensed_empty_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _licensed(monkeypatch)
    settings = Settings(_env_file=None, drafts_dir=tmp_path / "missing")
    html = TestClient(create_app(_store(), settings=settings)).get("/learning").text
    assert "No drafts yet" in html


def test_law_licensed_unconfigured_shows_hint(monkeypatch: pytest.MonkeyPatch) -> None:
    _licensed(monkeypatch)
    monkeypatch.delenv("VITALPROBE_LAW_DIR", raising=False)
    settings = Settings(_env_file=None)
    html = TestClient(create_app(_store(), settings=settings)).get("/law").text
    assert "No law directory configured" in html
    assert "VITALPROBE_LAW_DIR" in html


def test_law_licensed_renders_laws_and_disclaimer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _licensed(monkeypatch)
    law_dir = tmp_path / "law"
    law_dir.mkdir()
    (law_dir / "test-law.yaml").write_text(LAW_YAML, encoding="utf-8")
    settings = Settings(_env_file=None, law_dir=law_dir)
    html = TestClient(create_app(_store(), settings=settings)).get("/law").text
    assert "Test Health Communications Act" in html
    assert "test-law:crisis-routing" in html
    assert "Crisis messages must be routed to emergency guidance." in html
    assert LAW_DISCLAIMER in html


def test_law_licensed_invalid_dir_renders_errors_not_500(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _licensed(monkeypatch)
    law_dir = tmp_path / "law"
    law_dir.mkdir()
    (law_dir / "bad.yaml").write_text("law_id: [broken", encoding="utf-8")
    settings = Settings(_env_file=None, law_dir=law_dir)
    response = TestClient(create_app(_store(), settings=settings)).get("/law")
    assert response.status_code == 200
    assert "failed to load" in response.text


def test_trigger_form_renders() -> None:
    html = _client(_store()).get("/trigger-run").text
    assert 'name="suite"' in html
    assert 'name="target_url"' in html


def test_trigger_run_executes_cli_argv(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[tuple[list[str], dict[str, str], float]] = []

    def fake_exec(argv: list[str], env: dict[str, str], timeout_s: float) -> TriggerOutcome:
        calls.append((argv, env, timeout_s))
        return TriggerOutcome(exit_code=0, output="run.json written to somewhere")

    suite_dir = tmp_path / "suite"
    suite_dir.mkdir()
    settings = Settings(_env_file=None, dashboard_runs_dir=tmp_path / "runs")
    client = TestClient(
        create_app(_store(), settings=settings, run_executor=fake_exec),
        base_url="http://127.0.0.1:8800",
    )
    response = client.post(
        "/trigger-run",
        data={"suite": str(suite_dir), "target_url": "http://127.0.0.1:9999/chat"},
        headers={"origin": "http://127.0.0.1:8800"},
    )
    assert response.status_code == 200
    argv, env, timeout_s = calls[0]
    assert argv[:4] == [sys.executable, "-m", "vitalprobe"] + ["run"]
    assert "--track" in argv
    assert str(suite_dir) in argv
    assert env["VITALPROBE_TARGET_URL"] == "http://127.0.0.1:9999/chat"
    assert timeout_s == settings.dashboard_run_timeout_s
    assert "exit 0" in response.text
    assert "run.json written" in response.text


def test_trigger_run_invalid_suite_shows_error_without_subprocess(
    tmp_path: Path,
) -> None:
    calls: list[list[str]] = []

    def fake_exec(argv: list[str], env: dict[str, str], timeout_s: float) -> TriggerOutcome:
        calls.append(argv)
        return TriggerOutcome(exit_code=0, output="")

    settings = Settings(_env_file=None, dashboard_runs_dir=tmp_path / "runs")
    client = TestClient(create_app(_store(), settings=settings, run_executor=fake_exec))
    response = client.post("/trigger-run", data={"suite": str(tmp_path / "nope")})
    assert response.status_code == 200
    assert "existing directory" in response.text
    assert calls == []


def test_trigger_run_rejects_cross_site_origin(tmp_path: Path) -> None:
    suite_dir = tmp_path / "suite"
    suite_dir.mkdir()
    response = _client(_store()).post(
        "/trigger-run",
        data={"suite": str(suite_dir)},
        headers={"origin": "https://evil.example"},
    )
    assert response.status_code == 403


def test_trigger_run_rejects_other_local_port_origin(tmp_path: Path) -> None:
    """Another server on loopback (a dev server, another tool) is still cross-site."""
    suite_dir = tmp_path / "suite"
    suite_dir.mkdir()
    client = TestClient(create_app(_store()), base_url="http://127.0.0.1:8800")
    response = client.post(
        "/trigger-run",
        data={"suite": str(suite_dir)},
        headers={"origin": "http://localhost:9999"},
    )
    assert response.status_code == 403


def test_trigger_run_timeout_is_reported(tmp_path: Path) -> None:
    def fake_exec(argv: list[str], env: dict[str, str], timeout_s: float) -> TriggerOutcome:
        return TriggerOutcome(exit_code=None, output="partial", timed_out=True)

    suite_dir = tmp_path / "suite"
    suite_dir.mkdir()
    settings = Settings(_env_file=None, dashboard_runs_dir=tmp_path / "runs")
    client = TestClient(create_app(_store(), settings=settings, run_executor=fake_exec))
    response = client.post("/trigger-run", data={"suite": str(suite_dir)})
    assert response.status_code == 200
    assert "timed out" in response.text


def test_trigger_form_escapes_hostile_suite_value(tmp_path: Path) -> None:
    settings = Settings(_env_file=None, dashboard_runs_dir=tmp_path / "runs")
    client = TestClient(create_app(_store(), settings=settings))
    payload = '"><script>alert(1)</script>'
    response = client.post("/trigger-run", data={"suite": payload})
    assert response.status_code == 200
    assert "<script>alert(1)</script>" not in response.text


def test_python_dash_m_entrypoint_runs() -> None:
    """The trigger form spawns `python -m vitalprobe`; this locks that path in."""
    completed = subprocess.run(
        [sys.executable, "-m", "vitalprobe", "--version"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0
    assert "vitalprobe" in completed.stdout
