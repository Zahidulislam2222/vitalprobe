"""OpenAI structured judge backend with an injectable, mockable transport."""

from collections.abc import Awaitable, Callable
from typing import Any

from vitalprobe.judges._structured import parse_result
from vitalprobe.judges.base import Rubric
from vitalprobe.schema import JudgeResult, TestCase

Transport = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]


class OpenAIJudge:
    def __init__(self, model: str, transport: Transport) -> None:
        self.model = model
        self.transport = transport

    async def score(self, rubric: Rubric, case: TestCase, response_text: str) -> JudgeResult:
        request = {
            "model": self.model,
            "input": {
                "case": case.model_dump(mode="json"),
                "response": response_text,
                "rubric": rubric.model_dump(mode="json"),
            },
            "temperature": 0,
            "structured_output": {"score": "number 0-5", "rationale": "string"},
        }
        return parse_result(await self.transport(request), rubric, self.model)
