"""LangGraph orchestration of VitalProbe's existing M8 patient simulator.

This example deliberately keeps evaluation and target behavior in the core package.
LangGraph owns only the state transitions between those existing components.
"""

import argparse
import asyncio
import json
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Literal, TypedDict, cast

from langgraph.graph import END, START, StateGraph

from vitalprobe.config import Settings
from vitalprobe.schema import CheckResult, TestResult, Turn, Verdict, case_verdict
from vitalprobe.simulator.loop import run_trajectory_checks, target_escalated
from vitalprobe.simulator.patient import PatientError, PatientLLM
from vitalprobe.simulator.persona import Persona, load_persona
from vitalprobe.targets.base import TargetAdapter
from vitalprobe.targets.rest import AdapterError, RestAdapter, load_adapter_config


class PatientGraphState(TypedDict):
    persona: Persona
    adapter: TargetAdapter
    patient: PatientLLM
    transcript: list[Turn]
    checks: list[CheckResult]
    must_count: int
    latency_ms: int
    last_reply: str
    error: str | None
    done: bool


async def persona_state(state: PatientGraphState) -> dict[str, object]:
    """Initialize the same canonical transcript used by the plain M8 loop."""
    return {
        "transcript": [Turn(role="user", content=state["persona"].opening_message)],
        "checks": [],
        "must_count": 0,
        "latency_ms": 0,
        "last_reply": "",
        "error": None,
        "done": False,
    }


async def next_turn_generation(state: PatientGraphState) -> dict[str, object]:
    persona = state["persona"]
    transcript = list(state["transcript"])
    next_turn = sum(turn.role == "user" for turn in transcript) + 1
    reveals = {entry.turn: entry.message for entry in persona.escalation_script}
    try:
        message = reveals.get(next_turn)
        if message is None:
            message = await state["patient"].next_message(persona, transcript)
    except PatientError as exc:
        return {"error": str(exc), "done": True}
    transcript.append(Turn(role="user", content=message))
    return {"transcript": transcript}


async def target_bot_call(state: PatientGraphState) -> dict[str, object]:
    transcript = list(state["transcript"])
    try:
        response = await state["adapter"].send(transcript)
    except AdapterError as exc:
        return {"error": str(exc), "done": True}
    transcript.append(Turn(role="assistant", content=response.text))
    return {
        "transcript": transcript,
        "last_reply": response.text,
        "latency_ms": state["latency_ms"] + response.latency_ms,
    }


async def trajectory_check(state: PatientGraphState) -> dict[str, object]:
    if state["error"] is not None:
        return {}
    checks, must_count = run_trajectory_checks(state["persona"], state["transcript"])
    return {"checks": checks, "must_count": must_count}


async def stop_condition(state: PatientGraphState) -> dict[str, object]:
    persona = state["persona"]
    assistant_turns = sum(turn.role == "assistant" for turn in state["transcript"])
    escalated = bool(
        state["last_reply"]
        and target_escalated(state["last_reply"], persona.stop_on_escalation)
    )
    return {
        "done": bool(
            state["error"] is not None
            or escalated
            or assistant_turns >= persona.max_turns
        )
    }


def route_after_stop(state: PatientGraphState) -> Literal["next_turn_generation", "end"]:
    return "end" if state["done"] else "next_turn_generation"


def route_after_generation(state: PatientGraphState) -> Literal["target_bot_call", "end"]:
    return "end" if state["error"] is not None else "target_bot_call"


def build_patient_graph() -> Callable[
    [PatientGraphState], Awaitable[PatientGraphState]
]:
    """Compile the local-only patient graph and return its async invoke method."""
    builder = StateGraph(PatientGraphState)
    builder.add_node("persona_state", persona_state)
    builder.add_node("next_turn_generation", next_turn_generation)
    builder.add_node("target_bot_call", target_bot_call)
    builder.add_node("trajectory_check", trajectory_check)
    builder.add_node("stop_condition", stop_condition)
    builder.add_edge(START, "persona_state")
    builder.add_edge("persona_state", "target_bot_call")
    builder.add_edge("target_bot_call", "trajectory_check")
    builder.add_edge("trajectory_check", "stop_condition")
    builder.add_conditional_edges(
        "stop_condition",
        route_after_stop,
        {"next_turn_generation": "next_turn_generation", "end": END},
    )
    builder.add_conditional_edges(
        "next_turn_generation",
        route_after_generation,
        {"target_bot_call": "target_bot_call", "end": END},
    )
    graph = builder.compile()

    async def invoke(state: PatientGraphState) -> PatientGraphState:
        result = await graph.ainvoke(state)
        return cast(PatientGraphState, result)

    return invoke


async def simulate_persona_langgraph(
    persona: Persona, adapter: TargetAdapter, patient: PatientLLM
) -> TestResult:
    """Run one persona and return the same TestResult contract as the M8 loop."""
    initial: PatientGraphState = {
        "persona": persona,
        "adapter": adapter,
        "patient": patient,
        "transcript": [],
        "checks": [],
        "must_count": 0,
        "latency_ms": 0,
        "last_reply": "",
        "error": None,
        "done": False,
    }
    state = await build_patient_graph()(initial)
    if state["error"] is not None:
        verdict = Verdict.ERROR
    else:
        verdict = case_verdict(state["checks"], state["must_count"])
    return TestResult(
        id=persona.id,
        title=persona.title,
        category=persona.category,
        severity=persona.severity,
        verdict=verdict,
        latency_ms=state["latency_ms"] or None,
        input_turns=state["transcript"],
        response_text=state["last_reply"],
        checks=state["checks"],
        error=state["error"],
    )


async def _run_local(persona_path: Path, adapter_path: Path) -> TestResult:
    adapter = RestAdapter(load_adapter_config(adapter_path))
    patient = PatientLLM(Settings())
    try:
        return await simulate_persona_langgraph(load_persona(persona_path), adapter, patient)
    finally:
        await adapter.aclose()
        await patient.aclose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the LangGraph patient-agent example.")
    parser.add_argument("--persona", type=Path, required=True)
    parser.add_argument("--adapter-config", type=Path, required=True)
    args = parser.parse_args()
    result = asyncio.run(_run_local(args.persona, args.adapter_config))
    print(json.dumps(result.model_dump(mode="json"), indent=2))


if __name__ == "__main__":
    main()
