# Quickstart

VitalProbe is pre-release software. PyPI publishing is intentionally deferred, so this guide runs
the CLI from a source checkout.

## Prerequisites

- Python 3.12 or newer
- [uv](https://docs.astral.sh/uv/)
- A chatbot staging endpoint that accepts synthetic test traffic

Never point the starter workflow at production conversations or real patient data.

## Install from source

```bash
git clone https://github.com/Zahidulislam2222/vitalprobe.git
cd vitalprobe
uv sync --locked
uv run vitalprobe --version
```

## Try the bundled scripted target

In terminal 1:

```bash
uv run --extra demo uvicorn vitalprobe.demo.demo_health_bot:app --port 8000
```

In terminal 2:

```bash
export VITALPROBE_TARGET_URL=http://127.0.0.1:8000/chat
uv run vitalprobe validate --suite packs/emergency-core
uv run vitalprobe run \
  --suite packs/emergency-core \
  --output artifacts/first-run \
  --save-baseline baselines/demo
```

The public starter pack is deliberately still marked `draft` pending founder clinical review.
Local runs may use it for development, but it must not be represented as clinician-reviewed.

The run writes:

- `artifacts/first-run/run.json` — canonical machine-readable result
- `artifacts/first-run/report.html` — self-contained evidence dossier
- `baselines/demo/run.json` — canonical baseline copy

Exit code `0` means PASSED or PASSED_WITH_WARNINGS, `1` means observed test failure, and `2` means
a runner/configuration error. A failing demo result is expected because some scripted responses
are intentionally unsafe.

## Compare a later run

```bash
uv run vitalprobe compare \
  --baseline baselines/demo/run.json \
  --current artifacts/later-run/run.json
```

Comparison exits `1` only when a shared case regresses from PASS to WARN/FAIL. It also reports
improvements, new cases, and removed cases.

## Test your own endpoint

Copy the starter pack, adjust its `adapter.default.yaml` to match your request and response shape,
and set secrets only through environment variables:

```bash
export VITALPROBE_TARGET_URL=https://staging.example.test/chat
export VITALPROBE_TARGET_TOKEN=replace-with-a-revocable-staging-token
uv run vitalprobe run --suite path/to/your-suite --output artifacts/current
```

Do not commit `.env`, tokens, generated reports containing customer responses, or real patient
information.

## Optional local model

Install Ollama, pull a model suitable for your own machine, and configure its tag without changing
source code:

```bash
export DEMOBOT_PROVIDER=ollama
export DEMOBOT_MODEL=your-local-model-tag
export OLLAMA_HOST=http://localhost:11434
```

Then start the demo target as above. Local inference uses your machine and does not require a paid
judge API.
