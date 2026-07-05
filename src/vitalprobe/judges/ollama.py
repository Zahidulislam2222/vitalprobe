"""Zero-cost Ollama JSON judge with at most two invalid-JSON reprompts."""

import json
from collections.abc import Awaitable, Callable

from vitalprobe.judges._structured import parse_result
from vitalprobe.judges.base import Rubric
from vitalprobe.schema import JudgeResult, TestCase

Transport = Callable[[dict[str, object]], Awaitable[str]]


class OllamaJudge:
    def __init__(self, model: str, transport: Transport) -> None:
        self.model = model
        self.transport = transport

    async def score(self, rubric: Rubric, case: TestCase, response_text: str) -> JudgeResult:
        request: dict[str, object] = {
            "model": self.model,
            "format": "json",
            "rubric": rubric.model_dump(mode="json"),
            "case": case.model_dump(mode="json"),
            "response": response_text,
        }
        for attempt in range(3):
            try:
                data = json.loads(await self.transport(request))
                if not isinstance(data, dict):
                    raise ValueError("judge output is not an object")
                return parse_result(data, rubric, self.model)
            except (json.JSONDecodeError, KeyError, TypeError, ValueError):
                if attempt == 2:
                    raise ValueError("local judge returned invalid JSON after 3 attempts") from None
                request["reprompt"] = "Return only JSON with numeric score and string rationale."
        raise AssertionError("unreachable")
