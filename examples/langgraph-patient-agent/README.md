# LangGraph synthetic patient workflow

This optional integration expresses VitalProbe's existing multi-turn fictional-patient
loop as a local LangGraph `StateGraph`:

`persona_state → target_bot_call → trajectory_check → stop_condition`

An unfinished conversation loops through `next_turn_generation → target_bot_call`.
Execution ends at the persona's turn limit, qualifying escalation or a target/patient
error. It returns the same `TestResult` used by core reporting.

## Install and configure

From the repository root:

```sh
uv sync --locked --all-extras
```

Start your configured local model service and an authorized synthetic target. Select
model tags through the ignored environment and configure a REST adapter as described in
[backend interfaces](../../docs/backend.md). This integration uses no hosted tracing,
LangSmith or LangGraph Platform, and does not configure a paid model.

## Run

```sh
uv run python examples/langgraph-patient-agent/patient_agent.py \
  --persona personas/ambiguous-crisis.yaml \
  --adapter-config path/to/adapter.yaml
```

Replace the adapter path with your validated configuration. Its target may come from
`VITALPROBE_TARGET_URL`. The persona is fictional and its content remains draft pending
qualified review. Never use production conversations or real patient records.

## Design and verification

The core Python loop remains the default: it is smaller and has fewer dependencies.
Named graph transitions provide explicit orchestration for later branches or review
steps while reusing the same persona, patient model, target and trajectory contracts.
A parity regression checks this integration against the core behavior.

See [architecture](../../docs/architecture.md), [testing](../../TESTING.md),
[configuration](../../docs/configuration.md) and [roadmap](../../docs/roadmap.md).
