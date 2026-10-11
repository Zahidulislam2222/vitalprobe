# Quickstart

Produce a local evidence report without a cloud judge or payment provider. Python
3.12+ and [uv](https://docs.astral.sh/uv/) are required. PyPI publication is deferred;
install from the source repository.

## Install

```bash
git clone https://github.com/Zahidulislam2222/vitalprobe.git
cd vitalprobe
uv sync --locked --all-extras
uv run vitalprobe --version
```

## Start the scripted safety target

In terminal A:

```bash
export DEMOBOT_PROVIDER=scripted
uv run uvicorn vitalprobe.demo.demo_health_bot:app --host 127.0.0.1 --port 8000
```

`GET http://127.0.0.1:8000/health` returns `{"status":"ok","mode":"scripted"}`.
The module name is a retained executable identifier. This deliberately weak target
lets you verify that the engine records unsafe fictional responses.

## Validate and run

In terminal B:

```bash
export VITALPROBE_TARGET_URL=http://127.0.0.1:8000/chat
export VITALPROBE_JUDGE=none
uv run vitalprobe validate --suite packs/emergency-core
uv run vitalprobe run   --suite packs/emergency-core   --output artifacts/first-run   --track   --save-baseline baselines/scripted
```

On PowerShell, replace `export NAME=value` with `$env:NAME = "value"`.
The public starter contains 25 fictional draft scenarios. Its scripted target has
produced 3 PASS / 22 FAIL / 0 ERROR; these counts evaluate that target only. Exit 1 is
expected because unsafe behavior is seeded. A failed audit still writes evidence:

- `artifacts/first-run/run.json`: canonical structured result.
- `artifacts/first-run/report.html`: self-contained readable report.
- `baselines/scripted/run.json`: baseline copy.

Open the report locally and inspect the actual response and failed checks. Draft
clinical content is usable for development but has not received qualified clinical
review. `validate --release` rejects draft content; do not change its status yourself.

## Compare and inspect history

```bash
uv run vitalprobe run --suite packs/emergency-core --output artifacts/later-run --track
uv run vitalprobe compare   --baseline baselines/scripted/run.json   --current artifacts/later-run/run.json
uv run vitalprobe history --target http://127.0.0.1:8000/chat
```

Comparison gates PASS-to-WARN/FAIL changes in shared cases. It reports new and removed
cases separately. ERROR needs an additional explicit gate; use the complete workflow
in [CI](ci.md). Exit 0 does not establish clinical safety or overall readiness.

## Use your own fictional staging suite

Copy the public suite into a new directory, maintain draft status, and edit its adapter
YAML to match the staging API. Configure its endpoint and required authentication
through environment variables. See [backend interfaces](backend.md), [configuration](configuration.md)
and [test authoring](writing-tests.md). Verify you control the target before sending traffic.

Do not use real patients, production conversations or real personal data. Do not
publish generated response artifacts without reviewing their contents.

## Local dashboard and containers

```bash
uv run vitalprobe dashboard
```

The dashboard defaults to `http://127.0.0.1:8800`; keep it on loopback. It is an
operator interface without a public account/authentication layer. Use `--help` for
available options and [backend interfaces](backend.md) for its routes.

Alternatively, `docker compose up --build` starts the loopback dashboard and scripted
target. Compose configures the internal target address. Stop with `docker compose down`;
its named artifact volume survives. Inspect the actual mounted data before removing
any volume. This is local development, not a production hosting recipe.

## Optional local inference

For a locally installed Ollama model, set `DEMOBOT_PROVIDER=ollama`,
`DEMOBOT_MODEL` to its installed tag, and `OLLAMA_HOST` to your local endpoint, then
restart the target. Simulator and draft generation instead use `VITALPROBE_LOCAL_MODEL`.
Hardware and local model availability remain your responsibility. Cloud judging is a
separate opt-in path requiring configured prices and explicit spending approval.
