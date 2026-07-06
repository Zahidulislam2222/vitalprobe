# LangGraph patient-agent example

This example rebuilds VitalProbe's M8 synthetic-patient conversation loop as a local
LangGraph `StateGraph`. Its nodes are:

`persona_state → target_bot_call → trajectory_check → stop_condition`

If the stop condition is false, the graph loops through
`next_turn_generation → target_bot_call`. It stops at the persona's turn limit, when the
target escalates, or on a target/patient error.

The graph reuses VitalProbe's persona schema, configured patient LLM, target adapters,
trajectory checks, and canonical `TestResult`. It does not use LangGraph Platform,
LangSmith, hosted tracing, or a paid model.

## Install

From the repository root:

```powershell
uv sync --extra examples --extra demo
```

Ollama must be running with the models configured in your local `.env`. No model ID is
hardcoded in this example.

## Run against the demo bot

Start the local demo target in one terminal using the existing quickstart instructions.
Then run:

```powershell
uv run --extra examples python examples/langgraph-patient-agent/patient_agent.py `
  --persona personas/ambiguous-crisis.yaml `
  --adapter-config path/to/adapter.yaml
```

The adapter YAML uses the same REST adapter contract as `vitalprobe run`; its URL may
come from `VITALPROBE_TARGET_URL`.

The function returns the same `TestResult` contract as the plain M8 simulator, so existing
JSON/HTML reporting code can consume it unchanged.

## LangGraph versus the plain-Python loop

The plain M8 loop is smaller and is the production default: its control flow is obvious,
has fewer dependencies, and is easier to debug for this compact workflow. The LangGraph
version makes every transition explicit as a named node and conditional edge, which becomes
useful when a patient workflow gains branches, persistence, interrupts, or review steps.
For the current simulator, LangGraph adds orchestration visibility rather than new product
behavior; the parity test prevents the example from drifting from the core.
