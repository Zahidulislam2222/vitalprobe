# VitalProbe

[![CI](https://github.com/Zahidulislam2222/vitalprobe/actions/workflows/ci.yml/badge.svg)](https://github.com/Zahidulislam2222/vitalprobe/actions/workflows/ci.yml)

**Safety and compliance evidence testing for healthcare & wellness AI assistants.**

VitalProbe runs your chatbot, RAG app, or AI agent through synthetic healthcare safety scenarios (emergencies, medication questions, crisis language, prompt injection) and produces an evidence report you can show a stakeholder: what was tested, what failed, and proof for every verdict. Synthetic patients only — VitalProbe never needs real patient data.

> Status: pre-0.1 source release. Runner, HTML/JSON reporting, local history, offline
> entitlements, local-model demo audits, and baseline comparison are implemented. PyPI publishing
> is intentionally deferred.

## Quickstart

Until the deferred PyPI release, install from source:

```bash
git clone https://github.com/Zahidulislam2222/vitalprobe.git
cd vitalprobe
uv sync --locked
uv run vitalprobe validate --suite packs/emergency-core
```

See the [complete quickstart](docs/quickstart.md), [test authoring guide](docs/writing-tests.md),
and [CI regression workflow](docs/ci.md).

### One-command Docker demo

With Docker installed, a single command starts the local dashboard plus a scripted demo
health bot and runs everything inside containers — nothing is exposed beyond your own
machine (the dashboard publishes on `127.0.0.1` only):

```bash
docker compose up --build
```

Then open http://127.0.0.1:8800, go to **Trigger run**, and submit
`packs/emergency-core` against `http://demo-bot:8000/chat` to watch a full audit of the
intentionally naive demo bot land on the dashboard. Run history persists in a named
Docker volume across restarts. No accounts, no telemetry, no external assets — the
demo works fully offline after the image build.

## Evidence report

![VitalProbe HTML evidence report](docs/assets/report-preview.png)

The report is self-contained, print-friendly, and records synthetic input, observed output,
verdicts, deterministic evidence, and limitations.

## Demo target

The bundled [demo health bot](demo/README.md) supports deterministic scripted checks and an
intentionally naive local Ollama mode for zero-cost real audits.

## Tiers

- **Automated Report — available (this tool).** Run VitalProbe yourself and get the full HTML evidence report: every scenario, every check, every verdict, with evidence.
- **Clinician-Reviewed Dossier — UPCOMING.** Everything in Automated, plus review of flagged failures by a named licensed clinician and a signed review attestation.

## What VitalProbe is not

Reports describe observed test results and their limitations. VitalProbe does not certify chatbots, does not grant regulatory approval, and is not legal advice.

## License

Apache-2.0
