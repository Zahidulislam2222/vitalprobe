"""OpenAI structured judge backend with an injectable, mockable transport."""

import json
from collections.abc import Awaitable, Callable
from typing import Any

import httpx

from vitalprobe.judges._structured import parse_result
from vitalprobe.judges.base import JudgeError, Rubric
from vitalprobe.schema import JudgeResult, TestCase

Transport = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]


class OpenAIJudge:
    def __init__(
        self,
        model: str,
        transport: Transport | None = None,
        *,
        base_url: str,
        responses_path: str,
        timeout_s: float,
        api_key: str = "",
        client: httpx.AsyncClient | None = None,
        input_price: float = 0,
        output_price: float = 0,
    ) -> None:
        self.model = model
        self.transport = transport
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.responses_path = responses_path
        self.client = client or httpx.AsyncClient(timeout=timeout_s)
        self.input_price = input_price
        self.output_price = output_price

    async def aclose(self) -> None:
        await self.client.aclose()

    async def _request(self, request: dict[str, Any]) -> dict[str, Any]:
        if self.transport is not None:
            return await self.transport(request)
        if not self.api_key:
            raise JudgeError("OPENAI_API_KEY is required for the OpenAI judge")
        try:
            response = await self.client.post(
                f"{self.base_url}{self.responses_path}",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=request,
            )
            response.raise_for_status()
            payload = response.json()
            text = payload["output"][0]["content"][0]["text"]
            result = json.loads(text)
            if not isinstance(result, dict):
                raise ValueError("structured output is not an object")
            usage = payload.get("usage", {})
            result["input_tokens"] = usage.get("input_tokens", 0)
            result["output_tokens"] = usage.get("output_tokens", 0)
            return dict(result)
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
            raise JudgeError(f"invalid OpenAI judge response: {exc}") from exc

    async def score(self, rubric: Rubric, case: TestCase, response_text: str) -> JudgeResult:
        request: dict[str, Any] = {
            "model": self.model,
            "input": json.dumps(
                {
                    "case": case.model_dump(mode="json"),
                    "response": response_text,
                    "rubric": rubric.model_dump(mode="json"),
                }
            ),
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "judgment",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "properties": {
                            "score": {"type": "number", "minimum": 0, "maximum": 5},
                            "rationale": {"type": "string"},
                        },
                        "required": ["score", "rationale"],
                        "additionalProperties": False,
                    },
                }
            },
        }
        data = await self._request(request)
        cost = (
            data.get("input_tokens", 0) * self.input_price
            + data.get("output_tokens", 0) * self.output_price
        ) / 1_000_000
        return parse_result(data, rubric, self.model, cost=cost)
