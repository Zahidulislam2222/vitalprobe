"""P9a local dashboard: read-only pages over the experience store."""

from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import create_engine

from vitalprobe.config import Settings
from vitalprobe.dashboard.app import create_app
from vitalprobe.experience.store import ExperienceStore
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


def _run(run_id: str, verdict: Verdict) -> RunResult:
    result = CaseResult(
        id="case-001",
        title="Emergency escalation",
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
                evidence="seed evidence text",
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


def test_pages_reference_no_external_assets() -> None:
    client = _client(_seeded_store())
    for path in ("/", "/runs/2", "/compare"):
        html = client.get(path).text
        assert 'src="http' not in html
        assert 'href="http' not in html
        assert "@import" not in html


def test_api_schema_endpoints_disabled() -> None:
    client = _client(_store())
    assert client.get("/docs").status_code == 404
    assert client.get("/openapi.json").status_code == 404


def test_dashboard_defaults_are_localhost_only() -> None:
    settings = Settings(_env_file=None)
    assert settings.dashboard_host == "127.0.0.1"
    assert 1 <= settings.dashboard_port <= 65535
