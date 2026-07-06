"""Async run orchestration: configured concurrency, per case adapter → checks → verdict."""

import asyncio
import uuid
from datetime import UTC, datetime

from vitalprobe import __version__
from vitalprobe.evaluators import CHECKS
from vitalprobe.judges.base import JudgeBackend, JudgeError, load_rubric
from vitalprobe.packs.loader import LoadedSuite
from vitalprobe.schema import (
    CheckResult,
    ResponseMeta,
    RunResult,
    SuiteInfo,
    TargetInfo,
    TestCase,
    TestResult,
    Verdict,
    case_verdict,
    count_results,
    run_verdict,
)
from vitalprobe.targets.rest import AdapterError, RestAdapter


def _run_checks(case: TestCase, meta: ResponseMeta) -> tuple[list[CheckResult], int]:
    results: list[CheckResult] = []
    specs = list(case.expect.must) + list(case.expect.warn)
    for spec in specs:
        evaluator = CHECKS.get(spec.type)
        if evaluator is None:
            results.append(
                CheckResult(
                    type=spec.type,
                    passed=False,
                    evidence=f"unknown check type '{spec.type}' (known: {sorted(CHECKS)})",
                )
            )
            continue
        results.append(evaluator(meta.text, meta, spec.params()))
    return results, len(case.expect.must)


async def _run_case(
    case: TestCase,
    adapter: RestAdapter,
    sem: asyncio.Semaphore,
    judge: JudgeBackend | None,
) -> TestResult:
    async with sem:
        try:
            meta = await adapter.send(case.input.turns)
        except AdapterError as exc:
            return TestResult(
                id=case.id,
                title=case.title,
                category=case.category,
                severity=case.severity,
                verdict=Verdict.ERROR,
                latency_ms=None,
                input_turns=case.input.turns,
                response_text="",
                checks=[],
                error=str(exc),
            )
    checks, must_count = _run_checks(case, meta)
    deterministic_verdict = case_verdict(checks, must_count)
    judge_result = None
    if case.expect.judge is not None and judge is not None:
        try:
            judge_result = await judge.score(
                load_rubric(case.expect.judge.rubric), case, meta.text
            )
        except (JudgeError, ValueError) as exc:
            return TestResult(
                id=case.id,
                title=case.title,
                category=case.category,
                severity=case.severity,
                verdict=Verdict.ERROR,
                latency_ms=meta.latency_ms,
                input_turns=case.input.turns,
                response_text=meta.text,
                checks=checks,
                error=f"judge error: {exc}",
            )
    verdict = deterministic_verdict
    if judge_result is not None:
        if judge_result.verdict is Verdict.FAIL:
            verdict = Verdict.FAIL
        elif judge_result.verdict is Verdict.WARN and verdict is Verdict.PASS:
            verdict = Verdict.WARN
    return TestResult(
        id=case.id,
        title=case.title,
        category=case.category,
        severity=case.severity,
        verdict=verdict,
        latency_ms=meta.latency_ms,
        input_turns=case.input.turns,
        response_text=meta.text,
        checks=checks,
        judge=judge_result,
    )


async def run_suite(
    suite: LoadedSuite,
    adapter: RestAdapter,
    judge: JudgeBackend | None = None,
    *,
    max_concurrency: int,
) -> RunResult:
    started_at = datetime.now(UTC).isoformat()
    sem = asyncio.Semaphore(max_concurrency)
    results = list(
        await asyncio.gather(*(_run_case(case, adapter, sem, judge) for case in suite.cases))
    )
    results.sort(key=lambda r: r.id)
    finished_at = datetime.now(UTC).isoformat()

    return RunResult(
        vitalprobe_version=__version__,
        run_id=str(uuid.uuid4()),
        started_at=started_at,
        finished_at=finished_at,
        target=TargetInfo(endpoint_redacted=adapter.endpoint_redacted, adapter=adapter.name),
        suite=SuiteInfo(
            name=suite.name,
            path=str(suite.path),
            case_count=len(suite.cases),
            pack_version=suite.pack_version,
        ),
        verdict=run_verdict(results),
        counts=count_results(results),
        results=results,
    )
