# Scripted safety target

This FastAPI fixture exercises VitalProbe's real request, check and reporting pipeline
using fictional prompts. Default scripted responses include intentionally weak behavior
so tests can distinguish failures from transport errors. It is a test target, not a
patient-facing assistant or source of medical advice.

## Start locally

From the repository root:

```sh
uv sync --locked --all-extras
uv run uvicorn vitalprobe.demo.demo_health_bot:app --host 127.0.0.1 --port 8000
```

The import path is the existing Python module identifier. Keep it exact when invoking
Uvicorn. Alternatively, use `docker compose up --build` for the complete local workspace.

`GET /health` returns the service status and mode. `POST /chat` accepts a `message`
and returns `reply`. Point the suite's configured target variable at
`http://127.0.0.1:8000/chat`; see [quickstart](../docs/quickstart.md).

## Optional local-model mode

The fixture supports a locally installed Ollama model through existing environment names:

```dotenv
DEMOBOT_PROVIDER=ollama
DEMOBOT_MODEL=your-local-model-tag
OLLAMA_HOST=http://localhost:11434
```

Choose/install the model separately for your hardware; no concrete model tag is embedded
in source. Restart the target after changing its environment. Default scripted mode makes
no model call. Local-model mode uses local compute and configured timeout/output limits.

Prompt/response overrides, thinking settings and generation limits belong to typed
configuration and package data; see [configuration](../docs/configuration.md). Do not
use real patient data or expose this fixture as a public health service.
