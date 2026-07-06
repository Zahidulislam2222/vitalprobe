"""Zero-cost Ollama JSON judge with at most two invalid-JSON reprompts."""

import json
from collections.abc import Awaitable, Callable

import httpx

from vitalprobe.judges._structured import parse_result
from vitalprobe.judges.base import JudgeError, Rubric
from vitalprobe.schema import JudgeResult, TestCase

Transport = Callable[[dict[str, object]], Awaitable[str]]


class OllamaJudge:
    def __init__(
        self,
        model: str,
        transport: Transport | None = None,
        *,
        host: str,
        chat_path: str,
        timeout_s: float,
        max_attempts: int,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.model = model
        self.transport = transport
        self.host = host.rstrip("/")
        self.chat_path = chat_path
        self.max_attempts = max_attempts
        self.client = client or httpx.AsyncClient(timeout=timeout_s)

    async def aclose(self) -> None:
        await self.client.aclose()

    async def _request(self, request: dict[str, object]) -> str:
        if self.transport is not None:
            return await self.transport(request)
        response = await self.client.post(f"{self.host}{self.chat_path}", json=request)
        try:
            response.raise_for_status()
            return str(response.json()["message"]["content"])
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
            raise JudgeError(f"invalid Ollama judge response: {exc}") from exc

    async def score(self, rubric: Rubric, case: TestCase, response_text: str) -> JudgeResult:
        request: dict[str, object] = {
            "model": self.model,
            "format": "json",
            "rubric": rubric.model_dump(mode="json"),
            "case": case.model_dump(mode="json"),
            "response": response_text,
        }
        for attempt in range(self.max_attempts):
            try:
                data = json.loads(await self._request(request))
                if not isinstance(data, dict):
                    raise ValueError("judge output is not an object")
                return parse_result(data, rubric, self.model)
            except (json.JSONDecodeError, KeyError, TypeError, ValueError):
                if attempt == self.max_attempts - 1:
                    raise ValueError(
                        "local judge returned invalid JSON after "
                        f"{self.max_attempts} attempts"
                    ) from None
                request["reprompt"] = "Return only JSON with numeric score and string rationale."
        raise AssertionError("unreachable")
