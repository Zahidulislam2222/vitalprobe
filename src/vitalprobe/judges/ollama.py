"""Zero-cost Ollama JSON judge with at most two invalid-JSON reprompts."""

import json
from collections.abc import Awaitable, Callable
from pathlib import Path

import httpx

from vitalprobe.judges._structured import parse_result
from vitalprobe.judges.base import JudgeError, Rubric
from vitalprobe.schema import JudgeResult, TestCase

Transport = Callable[[dict[str, object]], Awaitable[str]]

_SYSTEM_PROMPT_PATH = Path(__file__).parent / "prompts" / "local_judge_system.txt"


def load_local_judge_prompt() -> str:
    return _SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")


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
        think: bool = False,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.model = model
        self.transport = transport
        self.host = host.rstrip("/")
        self.chat_path = chat_path
        self.max_attempts = max_attempts
        self.think = think
        self.client = client or httpx.AsyncClient(timeout=timeout_s)

    async def aclose(self) -> None:
        await self.client.aclose()

    async def _request(self, request: dict[str, object]) -> str:
        if self.transport is not None:
            return await self.transport(request)
        try:
            response = await self.client.post(f"{self.host}{self.chat_path}", json=request)
            response.raise_for_status()
            return str(response.json()["message"]["content"])
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
            raise JudgeError(f"Ollama judge request failed: {exc!r}") from exc

    async def score(self, rubric: Rubric, case: TestCase, response_text: str) -> JudgeResult:
        payload = json.dumps(
            {
                "rubric": rubric.model_dump(mode="json"),
                "case": case.model_dump(mode="json"),
                "response": response_text,
            }
        )
        messages: list[dict[str, str]] = [
            {"role": "system", "content": load_local_judge_prompt()},
            {"role": "user", "content": payload},
        ]
        for attempt in range(self.max_attempts):
            request: dict[str, object] = {
                "model": self.model,
                "messages": list(messages),
                "stream": False,
                "think": self.think,
                "format": "json",
                # temperature 0 is the fixed deterministic-judging contract shared by all judges
                "options": {"temperature": 0},
            }
            reply = await self._request(request)
            try:
                data = json.loads(reply)
                if not isinstance(data, dict):
                    raise ValueError("judge output is not an object")
                return parse_result(data, rubric, self.model)
            except (json.JSONDecodeError, KeyError, TypeError, ValueError):
                if attempt == self.max_attempts - 1:
                    raise ValueError(
                        "local judge returned invalid JSON after "
                        f"{self.max_attempts} attempts"
                    ) from None
                messages.append({"role": "assistant", "content": reply})
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "Invalid output. Return only one JSON object with a numeric "
                            '"score" and a string "rationale".'
                        ),
                    }
                )
        raise AssertionError("unreachable")
