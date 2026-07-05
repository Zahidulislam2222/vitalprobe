# Founder acceptance testing

This is the zero-spend acceptance gate. Do not configure cloud keys or run live judges here.

## 1. Install and verify

```bash
uv sync --all-extras --locked
uv run ruff check .
uv run mypy src
uv run pytest -q
uv run vitalprobe --version
```

Expected: all quality gates pass.

## 2. Start the scripted demo target

Terminal A:

```bash
uv run --extra demo uvicorn vitalprobe.demo.demo_health_bot:app --port 8000
```

Open `http://127.0.0.1:8000/health`. Expected: `{"status":"ok","mode":"scripted"}`.

## 3. Run the deterministic suite

Copy `tests/data/suite/adapter.default.yaml`, set its `url` to
`http://127.0.0.1:8000/chat`, and remove `url_env`. Then run:

```bash
uv run vitalprobe validate --suite tests/data/suite
uv run vitalprobe run --suite tests/data/suite --output artifacts/founder-run
```

Inspect `run.json` and `report.html`. Confirm PASS/WARN/FAIL evidence, redacted values, tier
language, and clean print preview.

## 4. Verify memory

Run the same command twice with `--track`, then:

```bash
uv run vitalprobe history --target http://127.0.0.1:8000/chat
```

Expected: two remembered runs and regression counts.

## 5. Verify entitlements

```bash
uv run vitalprobe license show
uv run vitalprobe license check mcp_server
```

Expected without a license: free tier remains usable; the paid feature check exits 2 with a
clear upgrade message. Do not share or move the founder signing key.

## 6. Verify mocked judge engine

```bash
uv run pytest tests/test_judges.py -q
```

Expected: mocked OpenAI and Anthropic judges identify the seeded subtle failure; mocked Ollama
recovers from two invalid JSON responses and fails cleanly after three. These tests make no
network calls and spend nothing.

## Acceptance record

Record date, machine, commands, results, report review notes, and either ACCEPTED or REJECTED
in `BUILD-LOG.md`. Live cloud judge calls, model downloads, publication, and live audits remain
blocked until the founder marks this gate ACCEPTED.
