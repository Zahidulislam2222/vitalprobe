"""Shared parsing for structured judge responses."""

from typing import Any

from vitalprobe.judges.base import Rubric
from vitalprobe.schema import JudgeResult, Verdict


def parse_result(
    data: dict[str, Any], rubric: Rubric, model: str, *, cost: float = 0.0
) -> JudgeResult:
    score = float(data["score"])
    verdict = (
        Verdict.PASS
        if score >= rubric.pass_at
        else Verdict.WARN
        if score >= rubric.warn_at
        else Verdict.FAIL
    )
    return JudgeResult(
        rubric=rubric.id,
        score=score,
        threshold=rubric.pass_at,
        verdict=verdict,
        rationale=str(data["rationale"]),
        model=model,
        input_tokens=int(data.get("input_tokens", 0)),
        output_tokens=int(data.get("output_tokens", 0)),
        est_cost_usd=cost,
    )
