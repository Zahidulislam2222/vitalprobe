# Scripted demo health bot

This intentionally limited FastAPI target exists for deterministic founder acceptance tests.
It uses canned responses only: no model, API key, network service, patient data, or spend.

Run it with:

```bash
uv run --extra demo uvicorn vitalprobe.demo.demo_health_bot:app --port 8000
```

Then point a VitalProbe adapter at `http://127.0.0.1:8000/chat`. Some responses are deliberately
unsafe so the evidence pipeline can demonstrate genuine PASS and FAIL outcomes.
