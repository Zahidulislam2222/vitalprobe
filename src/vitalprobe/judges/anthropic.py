"""Anthropic tool-structured judge backend with an injectable mock transport."""

from collections.abc import Awaitable, Callable
from typing import Any

import httpx

from vitalprobe.judges._structured import parse_result
from vitalprobe.judges.base import JudgeError, Rubric
from vitalprobe.schema import JudgeResult, TestCase

Transport = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]


class AnthropicJudge:
    def __init__(
        self,
        model: str,
        transport: Transport | None = None,
        *,
        base_url: str,
        messages_path: str,
        api_version: str,
        timeout_s: float,
        max_tokens: int,
        api_key: str = "",
        client: httpx.AsyncClient | None = None,
        input_price: float = 0,
        output_price: float = 0,
    ) -> None:
        self.model = model
        self.transport = transport
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.messages_path = messages_path
        self.api_version = api_version
        self.max_tokens = max_tokens
        self.client = client or httpx.AsyncClient(timeout=timeout_s)
        self.input_price = input_price
        self.output_price = output_price

    async def aclose(self) -> None:
        await self.client.aclose()

    async def _request(self, request: dict[str, Any]) -> dict[str, Any]:
        if self.transport is not None:
            return await self.transport(request)
        if not self.api_key:
            raise JudgeError("ANTHROPIC_API_KEY is required for the Anthropic judge")
        try:
            response = await self.client.post(
                f"{self.base_url}{self.messages_path}",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": self.api_version,
                },
                json=request,
            )
            response.raise_for_status()
            payload = response.json()
            tool = next(item for item in payload["content"] if item["type"] == "tool_use")
            result = dict(tool["input"])
            usage = payload.get("usage", {})
            result["input_tokens"] = usage.get("input_tokens", 0)
            result["output_tokens"] = usage.get("output_tokens", 0)
            return result
        except (httpx.HTTPError, KeyError, StopIteration, TypeError, ValueError) as exc:
            raise JudgeError(f"invalid Anthropic judge response: {exc}") from exc

    async def score(self, rubric: Rubric, case: TestCase, response_text: str) -> JudgeResult:
        request: dict[str, Any] = {
            "model": self.model,
            "temperature": 0,
            "max_tokens": self.max_tokens,
            "messages": [
                {
                    "role": "user",
                    "content": str(
                        {
                            "case": case.model_dump(mode="json"),
                            "response": response_text,
                            "rubric": rubric.model_dump(mode="json"),
                        }
                    ),
                }
            ],
            "tools": [
                {
                    "name": "submit_judgment",
                    "description": "Submit the rubric score.",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "score": {"type": "number", "minimum": 0, "maximum": 5},
                            "rationale": {"type": "string"},
                        },
                        "required": ["score", "rationale"],
                    },
                }
            ],
            "tool_choice": {"type": "tool", "name": "submit_judgment"},
        }
        data = await self._request(request)
        cost = (
            data.get("input_tokens", 0) * self.input_price
            + data.get("output_tokens", 0) * self.output_price
        ) / 1_000_000
        return parse_result(data, rubric, self.model, cost=cost)
