"""SQLite Experience Store: run memory, history, and automatic regressions."""

import json
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from sqlalchemy.engine import Engine
from sqlmodel import Field, Session, SQLModel, col, create_engine, select

from vitalprobe.config import get_settings
from vitalprobe.report.json_report import redact_secrets
from vitalprobe.schema import RunResult, Verdict


class TargetRecord(SQLModel, table=True):
    __tablename__ = "targets"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    endpoint_hash: str = Field(index=True)


class RunRecord(SQLModel, table=True):
    __tablename__ = "runs"

    id: int | None = Field(default=None, primary_key=True)
    run_id: str = Field(index=True, unique=True)
    target_id: int = Field(foreign_key="targets.id", index=True)
    started_at: str
    finished_at: str
    verdict: str
    pass_count: int
    warn_count: int
    fail_count: int
    error_count: int
    target_endpoint_redacted: str
    target_adapter: str
    suite_name: str
    suite_path: str
    suite_case_count: int
    suite_pack_version: str | None = None
    payload_json: str


class ResultRecord(SQLModel, table=True):
    __tablename__ = "results"

    id: int | None = Field(default=None, primary_key=True)
    run_id: int = Field(foreign_key="runs.id", index=True)
    case_id: str = Field(index=True)
    title: str
    category: str
    severity: str
    verdict: str
    latency_ms: int | None = None
    input_turns_json: str
    response_text: str
    judge_json: str | None = None
    error: str | None = None


class CheckRecord(SQLModel, table=True):
    __tablename__ = "checks"

    id: int | None = Field(default=None, primary_key=True)
    result_id: int = Field(foreign_key="results.id", index=True)
    check_type: str
    passed: bool
    evidence: str


@dataclass(frozen=True, slots=True)
class Regression:
    case_id: str
    previous: Verdict
    current: Verdict


@dataclass(frozen=True, slots=True)
class HistoryEntry:
    run_id: str
    started_at: str
    verdict: str
    pass_count: int
    warn_count: int
    fail_count: int
    error_count: int
    regression_count: int


def compare_regressions(previous: RunResult, current: RunResult) -> list[Regression]:
    """Return PASS→WARN/FAIL transitions shared by two runs."""
    before = {result.id: result.verdict for result in previous.results}
    found = [
        Regression(result.id, before[result.id], result.verdict)
        for result in current.results
        if before.get(result.id) is Verdict.PASS
        and result.verdict in (Verdict.WARN, Verdict.FAIL)
    ]
    return sorted(found, key=lambda item: item.case_id)


class ExperienceStore:
    """Persistent index over canonical RunResult payloads."""

    def __init__(self, db_path: Path | None = None, *, engine: Engine | None = None) -> None:
        if engine is None:
            path = db_path or get_settings().db_path
            path.parent.mkdir(parents=True, exist_ok=True)
            engine = create_engine(f"sqlite:///{path}")
        self.engine = engine
        SQLModel.metadata.create_all(self.engine)

    @staticmethod
    def target_name(run: RunResult) -> str:
        return run.target.endpoint_redacted

    def record_run(
        self, run: RunResult, secrets: list[str] | None = None
    ) -> list[Regression]:
        """Record a run and return regressions against the preceding target run."""
        known_secrets = secrets if secrets is not None else [get_settings().target_token]
        run = RunResult.model_validate_json(
            redact_secrets(run.model_dump_json(by_alias=True), known_secrets)
        )
        target_name = self.target_name(run)
        previous = self.last_run(target_name)
        with Session(self.engine) as session:
            target = session.exec(
                select(TargetRecord).where(TargetRecord.name == target_name)
            ).first()
            if target is None:
                target = TargetRecord(
                    name=target_name,
                    endpoint_hash=sha256(target_name.encode("utf-8")).hexdigest(),
                )
                session.add(target)
                session.flush()
            if target.id is None:
                raise RuntimeError("target row did not receive an id")

            row = RunRecord(
                run_id=run.run_id,
                target_id=target.id,
                started_at=run.started_at,
                finished_at=run.finished_at,
                verdict=run.verdict,
                pass_count=run.counts.pass_,
                warn_count=run.counts.warn,
                fail_count=run.counts.fail,
                error_count=run.counts.error,
                target_endpoint_redacted=run.target.endpoint_redacted,
                target_adapter=run.target.adapter,
                suite_name=run.suite.name,
                suite_path=run.suite.path,
                suite_case_count=run.suite.case_count,
                suite_pack_version=run.suite.pack_version,
                payload_json=run.model_dump_json(by_alias=True),
            )
            session.add(row)
            session.flush()
            if row.id is None:
                raise RuntimeError("run row did not receive an id")

            for result in run.results:
                result_row = ResultRecord(
                    run_id=row.id,
                    case_id=result.id,
                    title=result.title,
                    category=result.category,
                    severity=result.severity,
                    verdict=result.verdict,
                    latency_ms=result.latency_ms,
                    input_turns_json=json.dumps(
                        [turn.model_dump() for turn in result.input_turns]
                    ),
                    response_text=result.response_text,
                    judge_json=result.judge.model_dump_json() if result.judge else None,
                    error=result.error,
                )
                session.add(result_row)
                session.flush()
                if result_row.id is None:
                    raise RuntimeError("result row did not receive an id")
                session.add_all(
                    [
                        CheckRecord(
                            result_id=result_row.id,
                            check_type=check.type,
                            passed=check.passed,
                            evidence=check.evidence,
                        )
                        for check in result.checks
                    ]
                )
            session.commit()
        return compare_regressions(previous, run) if previous else []

    def _run_rows(self, target: str) -> list[RunRecord]:
        with Session(self.engine) as session:
            target_row = session.exec(
                select(TargetRecord).where(TargetRecord.name == target)
            ).first()
            if target_row is None or target_row.id is None:
                return []
            return list(
                session.exec(
                    select(RunRecord)
                    .where(RunRecord.target_id == target_row.id)
                    .order_by(col(RunRecord.id))
                ).all()
            )

    def history(self, target: str) -> list[HistoryEntry]:
        rows = self._run_rows(target)
        entries: list[HistoryEntry] = []
        previous: RunResult | None = None
        for row in rows:
            current = RunResult.model_validate_json(row.payload_json)
            count = len(compare_regressions(previous, current)) if previous else 0
            entries.append(
                HistoryEntry(
                    run_id=row.run_id,
                    started_at=row.started_at,
                    verdict=row.verdict,
                    pass_count=row.pass_count,
                    warn_count=row.warn_count,
                    fail_count=row.fail_count,
                    error_count=row.error_count,
                    regression_count=count,
                )
            )
            previous = current
        return list(reversed(entries))

    def last_run(self, target: str) -> RunResult | None:
        rows = self._run_rows(target)
        return RunResult.model_validate_json(rows[-1].payload_json) if rows else None

    def regressions(self, target: str) -> list[Regression]:
        rows = self._run_rows(target)
        if len(rows) < 2:
            return []
        previous = RunResult.model_validate_json(rows[-2].payload_json)
        current = RunResult.model_validate_json(rows[-1].payload_json)
        return compare_regressions(previous, current)


def record_run(run: RunResult, secrets: list[str] | None = None) -> list[Regression]:
    return ExperienceStore().record_run(run, secrets)


def history(target: str) -> list[HistoryEntry]:
    return ExperienceStore().history(target)


def last_run(target: str) -> RunResult | None:
    return ExperienceStore().last_run(target)


def regressions(target: str) -> list[Regression]:
    return ExperienceStore().regressions(target)
