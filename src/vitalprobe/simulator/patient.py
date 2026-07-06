"""Patient-LLM: generates the synthetic patient's next turn (local Ollama by default,
transport injectable for tests — same pattern as the E3 variant generator)."""

import json
from collections.abc import Awaitable, Callable
from pathlib import Path

import httpx

from vitalprobe.config import Settings
from vitalprobe.schema import Turn
from vitalprobe.simulator.persona import Persona

Transport = Callable[[dict[str, object]], Awaitable[str]]

_SYSTEM_PROMPT_PATH = Path(__file__).parent / "prompts" / "patient_system.txt"


class PatientError(Exception):
    """The patient-LLM could not produce a usable next turn."""


def load_patient_prompt() -> str:
    return _SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")


class PatientLLM:
    def __init__(self, settings: Settings, transport: Transport | None = None) -> None:
        if transport is None and not settings.local_model:
            raise PatientError(
                "VITALPROBE_LOCAL_MODEL is required to run the patient simulator locally"
            )
        self.settings = settings
        self.transport = transport
        self.client = httpx.AsyncClient(timeout=settings.judge_timeout_s)

    async def aclose(self) -> None:
        await self.client.aclose()

    async def _request(self, request: dict[str, object]) -> str:
        if self.transport is not None:
            return await self.transport(request)
        try:
            response = await self.client.post(
                f"{self.settings.ollama_host.rstrip('/')}{self.settings.ollama_chat_path}",
                json=request,
            )
            response.raise_for_status()
            return str(response.json()["message"]["content"])
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
            raise PatientError(f"patient request failed: {exc!r}") from exc

    async def next_message(self, persona: Persona, transcript: list[Turn]) -> str:
        payload = json.dumps(
            {
                "persona": {
                    "age": persona.age,
                    "background": persona.background,
                    "condition": persona.condition,
                    "goal": persona.goal,
                    "disclosure_style": persona.disclosure_style,
                },
                "conversation": [t.model_dump(mode="json") for t in transcript],
            },
            ensure_ascii=False,
        )
        messages: list[dict[str, str]] = [
            {"role": "system", "content": load_patient_prompt()},
            {"role": "user", "content": payload},
        ]
        attempts = self.settings.local_judge_max_attempts
        for attempt in range(attempts):
            request: dict[str, object] = {
                "model": self.settings.local_model,
                "messages": list(messages),
                "stream": False,
                "think": self.settings.judge_ollama_think,
                "format": "json",
                "options": {
                    "temperature": self.settings.simulator_temperature,
                    "num_predict": self.settings.simulator_max_tokens,
                },
            }
            reply = await self._request(request)
            try:
                data = json.loads(reply)
                if not isinstance(data, dict):
                    raise ValueError("expected a JSON object")
                message = str(data.get("message", "")).strip()
                if not message:
                    raise ValueError("empty message")
                return message
            except (json.JSONDecodeError, ValueError):
                if attempt == attempts - 1:
                    raise PatientError(
                        f"patient-LLM returned invalid JSON after {attempts} attempts"
                    ) from None
                messages.append({"role": "assistant", "content": reply})
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            'Invalid output. Return only a JSON object like {"message": "..."}.'
                        ),
                    }
                )
        raise AssertionError("unreachable")
