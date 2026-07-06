"""Simulation loop (M8 step 1): persona → multi-turn conversation → trajectory verdicts.

Each persona becomes one TestResult whose `input_turns` is the FULL transcript, so the
existing dossier renders the multi-turn finding as a transcript view unchanged.
"""

import re
import uuid
from datetime import UTC, datetime

from vitalprobe import __version__
from vitalprobe.schema import (
    CheckResult,
    RunResult,
    SuiteInfo,
    TargetInfo,
    TestResult,
    Turn,
    Verdict,
    case_verdict,
    count_results,
    run_verdict,
)
from vitalprobe.simulator.patient import PatientError, PatientLLM
from vitalprobe.simulator.persona import Persona
from vitalprobe.simulator.trajectory import TRAJECTORY_CHECKS
from vitalprobe.targets.base import TargetAdapter
from vitalprobe.targets.rest import AdapterError


def target_escalated(reply: str, patterns: list[str]) -> bool:
    return any(re.search(p, reply, re.IGNORECASE) for p in patterns)


def run_trajectory_checks(
    persona: Persona, transcript: list[Turn]
) -> tuple[list[CheckResult], int]:
    results: list[CheckResult] = []
    specs = list(persona.checks.must) + list(persona.checks.warn)
    for spec in specs:
        check = TRAJECTORY_CHECKS.get(spec.type)
        if check is None:
            results.append(
                CheckResult(
                    type=spec.type,
                    passed=False,
                    evidence=(
                        f"unknown trajectory check '{spec.type}' "
                        f"(known: {sorted(TRAJECTORY_CHECKS)})"
                    ),
                )
            )
            continue
        results.append(check(transcript, spec.params()))
    return results, len(persona.checks.must)


async def simulate_persona(
    persona: Persona, adapter: TargetAdapter, patient: PatientLLM
) -> TestResult:
    transcript: list[Turn] = [Turn(role="user", content=persona.opening_message)]
    reveals = {entry.turn: entry.message for entry in persona.escalation_script}
    total_latency = 0
    last_reply = ""
    error: str | None = None

    for turn_number in range(1, persona.max_turns + 1):
        try:
            meta = await adapter.send(transcript)
        except AdapterError as exc:
            error = str(exc)
            break
        total_latency += meta.latency_ms
        last_reply = meta.text
        transcript.append(Turn(role="assistant", content=meta.text))
        if target_escalated(meta.text, persona.stop_on_escalation):
            break
        if turn_number == persona.max_turns:
            break
        next_turn = turn_number + 1
        if next_turn in reveals:
            message = reveals[next_turn]
        else:
            try:
                message = await patient.next_message(persona, transcript)
            except PatientError as exc:
                error = str(exc)
                break
        transcript.append(Turn(role="user", content=message))

    if error is not None:
        return TestResult(
            id=persona.id,
            title=persona.title,
            category=persona.category,
            severity=persona.severity,
            verdict=Verdict.ERROR,
            latency_ms=total_latency or None,
            input_turns=transcript,
            response_text=last_reply,
            checks=[],
            error=error,
        )

    checks, must_count = run_trajectory_checks(persona, transcript)
    return TestResult(
        id=persona.id,
        title=persona.title,
        category=persona.category,
        severity=persona.severity,
        verdict=case_verdict(checks, must_count),
        latency_ms=total_latency,
        input_turns=transcript,
        response_text=last_reply,
        checks=checks,
    )


async def simulate(
    personas: list[Persona],
    adapter: TargetAdapter,
    patient: PatientLLM,
    *,
    suite_name: str,
    suite_path: str,
) -> RunResult:
    """Run every persona SEQUENTIALLY (multi-turn + local models: keep the load light)."""
    started_at = datetime.now(UTC).isoformat()
    results = [await simulate_persona(persona, adapter, patient) for persona in personas]
    results.sort(key=lambda r: r.id)
    finished_at = datetime.now(UTC).isoformat()
    return RunResult(
        vitalprobe_version=__version__,
        run_id=str(uuid.uuid4()),
        started_at=started_at,
        finished_at=finished_at,
        target=TargetInfo(endpoint_redacted=adapter.endpoint_redacted, adapter=adapter.name),
        suite=SuiteInfo(
            name=suite_name, path=suite_path, case_count=len(personas), pack_version=None
        ),
        verdict=run_verdict(results),
        counts=count_results(results),
        results=results,
    )
