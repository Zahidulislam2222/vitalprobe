"""E3 learning loop L2: draft adversarial variants from failures the engine actually found.

Drafts are written to a drafts directory, NEVER into a pack; only human review flips a case
to `status: reviewed` (BUILD-PLAN §0 rule 10).
"""

import json
from collections.abc import Awaitable, Callable
from pathlib import Path

import httpx
import yaml

from vitalprobe.config import Settings
from vitalprobe.packs.loader import LoadedSuite
from vitalprobe.schema import RunResult, TestCase, Turn, Verdict

Transport = Callable[[dict[str, object]], Awaitable[str]]

_SYSTEM_PROMPT_PATH = Path(__file__).parent / "prompts" / "variant_generator_system.txt"


class GenerationError(Exception):
    """Variant generation failed for a case."""


def load_generator_prompt() -> str:
    return _SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")


class VariantGenerator:
    """Local-model variant writer (Ollama by default; transport injectable for tests)."""

    def __init__(self, settings: Settings, transport: Transport | None = None) -> None:
        if transport is None and not settings.local_model:
            raise GenerationError(
                "VITALPROBE_LOCAL_MODEL is required to generate draft variants locally"
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
            raise GenerationError(f"generator request failed: {exc!r}") from exc

    async def variant_messages(
        self, case: TestCase, response_text: str, n: int
    ) -> list[str]:
        payload = json.dumps(
            {"case": case.model_dump(mode="json"), "response": response_text, "n": n}
        )
        messages: list[dict[str, str]] = [
            {"role": "system", "content": load_generator_prompt()},
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
                    "temperature": self.settings.generator_temperature,
                    "num_predict": self.settings.generator_max_tokens,
                },
            }
            reply = await self._request(request)
            try:
                data = json.loads(reply)
                variants = [str(item).strip() for item in _as_list(data) if str(item).strip()]
                if not variants:
                    raise ValueError("no usable variants")
                return variants[:n]
            except (json.JSONDecodeError, ValueError, TypeError):
                if attempt == attempts - 1:
                    raise GenerationError(
                        f"generator returned invalid JSON after {attempts} attempts"
                    ) from None
                messages.append({"role": "assistant", "content": reply})
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "Invalid output. Return only a JSON object like "
                            '{"variants": ["...", "..."]}.'
                        ),
                    }
                )
        raise AssertionError("unreachable")


def _as_list(data: object) -> list[object]:
    """Ollama JSON mode forces a top-level object, so the contract is {"variants": [...]};
    tolerate a bare array or an object of string values from less obedient models."""
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for value in data.values():
            if isinstance(value, list):
                return value
        if data and all(isinstance(value, str) for value in data.values()):
            return list(data.values())
    raise ValueError("generator output holds no variant list")


def build_variant_case(source: TestCase, message: str, index: int, run_id: str) -> TestCase:
    """A draft variant is the SOURCE case with a harder user message: same category,
    same severity, same expectations — schema validity is enforced by the model itself."""
    turns = [Turn(role=t.role, content=t.content) for t in source.input.turns]
    for position in range(len(turns) - 1, -1, -1):
        if turns[position].role == "user":
            turns[position] = Turn(role="user", content=message)
            break
    data = source.model_dump(mode="json")
    data["id"] = f"{source.id}-var-{index}"
    data["title"] = f"{source.title} (adversarial variant {index})"
    data["status"] = "draft"
    data["input"] = {"turns": [t.model_dump(mode="json") for t in turns]}
    data["notes"] = f"auto-generated from run {run_id}, case {source.id}"
    return TestCase.model_validate(data)


async def generate_drafts(
    run: RunResult,
    suite: LoadedSuite,
    generator: VariantGenerator,
    variants_per_failure: int,
    output_dir: Path,
) -> tuple[list[Path], list[str]]:
    """Draft variants for every FAILed case in the run. Returns (files written, errors)."""
    cases = {case.id: case for case in suite.cases}
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    errors: list[str] = []
    for result in run.results:
        if result.verdict is not Verdict.FAIL:
            continue
        source = cases.get(result.id)
        if source is None:
            errors.append(f"{result.id}: case not found in suite '{suite.name}'")
            continue
        try:
            texts = await generator.variant_messages(
                source, result.response_text, variants_per_failure
            )
        except GenerationError as exc:
            errors.append(f"{result.id}: {exc}")
            continue
        variants = [
            build_variant_case(source, message, index + 1, run.run_id)
            for index, message in enumerate(texts)
        ]
        path = output_dir / f"{source.id}-variants.yaml"
        path.write_text(
            yaml.safe_dump(
                [variant.model_dump(mode="json") for variant in variants],
                sort_keys=False,
                allow_unicode=True,
            ),
            encoding="utf-8",
        )
        written.append(path)
    return written, errors
