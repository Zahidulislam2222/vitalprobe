# VitalProbe

**Safety and compliance evidence testing for healthcare & wellness AI assistants.**

VitalProbe runs your chatbot, RAG app, or AI agent through synthetic healthcare safety scenarios (emergencies, medication questions, crisis language, prompt injection) and produces an evidence report you can show a stakeholder: what was tested, what failed, and proof for every verdict. Synthetic patients only — VitalProbe never needs real patient data.

> Status: early development (pre-0.1). The CLI scaffold is in place; the test runner lands in milestone M1.

## Quickstart

Coming with v0.1. The planned shape:

```bash
uvx vitalprobe run --suite packs/emergency-core --output artifacts/run-1
```

## Tiers

- **Automated Report — available (this tool).** Run VitalProbe yourself and get the full HTML evidence report: every scenario, every check, every verdict, with evidence.
- **Clinician-Reviewed Dossier — UPCOMING.** Everything in Automated, plus review of flagged failures by a named licensed clinician and a signed review attestation.

## What VitalProbe is not

Reports describe observed test results and their limitations. VitalProbe does not certify chatbots, does not grant regulatory approval, and is not legal advice.

## License

Apache-2.0
