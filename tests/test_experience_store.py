"""E1 Experience Store persistence and regression tests."""

from copy import deepcopy

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, create_engine, select

from vitalprobe.experience.store import (
    CheckRecord,
    ExperienceStore,
    ResultRecord,
    RunRecord,
    TargetRecord,
)
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


def _run(run_id: str, verdict: Verdict) -> RunResult:
    result = CaseResult(
        id="case-001",
        title="Regression candidate",
        category="safety",
        severity="high",
        verdict=verdict,
        latency_ms=10,
        input_turns=[Turn(role="user", content="test")],
        response_text="observed response",
        checks=[
            CheckResult(
                type="nonempty",
                passed=verdict is Verdict.PASS,
                evidence="seed evidence",
            )
        ],
    )
    return RunResult(
        vitalprobe_version="0.1.0.dev0",
        run_id=run_id,
        started_at=f"2026-07-05T00:00:0{run_id}+00:00",
        finished_at=f"2026-07-05T00:00:1{run_id}+00:00",
        target=TargetInfo(endpoint_redacted="https://example.test/chat", adapter="rest"),
        suite=SuiteInfo(name="seed", path="tests/data/suite", case_count=1),
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


def test_two_runs_detect_pass_to_fail_regression() -> None:
    store = _store()
    first = _run("1", Verdict.PASS)
    second = _run("2", Verdict.FAIL)

    assert store.record_run(first) == []
    regressions = store.record_run(second)

    assert len(regressions) == 1
    assert regressions[0].case_id == "case-001"
    assert regressions[0].previous is Verdict.PASS
    assert regressions[0].current is Verdict.FAIL
    assert store.regressions(ExperienceStore.target_name(second)) == regressions
    assert store.last_run(ExperienceStore.target_name(second)) == second

    history = store.history(ExperienceStore.target_name(second))
    assert [entry.run_id for entry in history] == ["2", "1"]
    assert history[0].regression_count == 1
    assert history[1].regression_count == 0


def test_store_mirrors_run_result_tables() -> None:
    store = _store()
    run = _run("1", Verdict.PASS)
    original = deepcopy(run.model_dump())
    store.record_run(run)

    with Session(store.engine) as session:
        assert len(session.exec(select(TargetRecord)).all()) == 1
        assert len(session.exec(select(RunRecord)).all()) == 1
        assert len(session.exec(select(ResultRecord)).all()) == 1
        assert len(session.exec(select(CheckRecord)).all()) == 1

    assert run.model_dump() == original


def test_store_redacts_known_secrets() -> None:
    store = _store()
    run = _run("1", Verdict.PASS)
    run.results[0].response_text = "echoed credential: store-secret"

    store.record_run(run, secrets=["store-secret"])
    stored = store.last_run(ExperienceStore.target_name(run))

    assert stored is not None
    assert "store-secret" not in stored.results[0].response_text
    assert "[REDACTED]" in stored.results[0].response_text
