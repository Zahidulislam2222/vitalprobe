"""Parity test for the M9 LangGraph patient-agent example."""

import importlib.util
import json
from pathlib import Path
from types import ModuleType

from vitalprobe.config import Settings
from vitalprobe.schema import ResponseMeta, Turn
from vitalprobe.simulator.loop import simulate_persona
from vitalprobe.simulator.patient import PatientLLM
from vitalprobe.simulator.persona import load_persona

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "langgraph-patient-agent" / "patient_agent.py"
PERSONA = ROOT / "personas" / "ambiguous-crisis.yaml"


def _load_example() -> ModuleType:
    spec = importlib.util.spec_from_file_location("langgraph_patient_agent", EXAMPLE)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load LangGraph example")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_example_has_no_hosted_langgraph_or_langsmith_integration() -> None:
    source = EXAMPLE.read_text(encoding="utf-8").casefold()
    forbidden = ["langgraph_sdk", "langsmith", "langchain_tracing", "api.smith"]
    assert [marker for marker in forbidden if marker in source] == []


class SeededAdapter:
    name = "seeded"
    endpoint_redacted = "https://target.example.test/chat"

    def __init__(self) -> None:
        self.replies = [
            "Try keeping a consistent bedtime.",
            "How have you been feeling emotionally?",
            "Please call 988 now or contact emergency services if you are in danger.",
        ]

    async def send(self, _turns: list[Turn]) -> ResponseMeta:
        return ResponseMeta(text=self.replies.pop(0), status_code=200, latency_ms=5)

    async def aclose(self) -> None:
        pass


def _patient() -> PatientLLM:
    async def transport(_request: dict[str, object]) -> str:
        return json.dumps({"message": "Mostly tired. I do not want to discuss feelings."})

    return PatientLLM(Settings(), transport=transport)


async def test_langgraph_matches_plain_simulator() -> None:
    module = _load_example()
    graph_simulate = module.simulate_persona_langgraph
    persona = load_persona(PERSONA)

    plain = await simulate_persona(persona, SeededAdapter(), _patient())
    graph = await graph_simulate(persona, SeededAdapter(), _patient())

    assert graph.model_dump(exclude={"latency_ms"}) == plain.model_dump(exclude={"latency_ms"})
    assert graph.latency_ms == plain.latency_ms == 15


async def test_langgraph_stops_after_patient_error() -> None:
    module = _load_example()
    persona = load_persona(PERSONA)

    async def invalid_transport(_request: dict[str, object]) -> str:
        return "not-json"

    settings = Settings(local_judge_max_attempts=1)
    patient = PatientLLM(settings, transport=invalid_transport)
    adapter = SeededAdapter()
    result = await module.simulate_persona_langgraph(persona, adapter, patient)

    assert result.error == "patient-LLM returned invalid JSON after 1 attempts"
    assert len(adapter.replies) == 2
