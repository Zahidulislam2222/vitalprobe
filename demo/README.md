# Demo health bot

This deliberately naive FastAPI target exists for deterministic founder acceptance tests and
real local-model audits. It processes synthetic prompts only.

Scripted mode is the default and uses canned responses: no model, API key, external network
service, patient data, or spend.

Run it with:

```bash
uv run --extra demo uvicorn vitalprobe.demo.demo_health_bot:app --port 8000
```

Then point a VitalProbe adapter at `http://127.0.0.1:8000/chat`. Some responses are deliberately
unsafe so the evidence pipeline can demonstrate genuine PASS and FAIL outcomes.

For a real `$0` local-model audit, start Ollama and configure:

```bash
DEMOBOT_PROVIDER=ollama
DEMOBOT_MODEL=gemma3:1b
OLLAMA_HOST=http://localhost:11434
```

The Ollama API is local. The demo explicitly disables model thinking, caps output length, and
uses the intentionally naive prompt shipped as package data. All values can be overridden through
typed settings documented in `.env.example`.
