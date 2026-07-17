# VitalProbe agent rules (Claude Code, Codex, and any other AI agent)

Binding for every AI-assisted change in this repository.

## Compliance gate

If the parent folder contains `COMPLIANCE-GATE.md` (the founder's working layout),
execute it before and after every change. On a standalone clone, the invariants below
still apply in full.

## Invariants (never break, in code, docs, tests, or commit messages)

- VitalProbe processes only synthetic, fictional patients: never add ingestion of real
  patient data, hosted accounts, server-side response storage, or any default/silent
  transmission of data to a third party. Never add telemetry, analytics, crash
  reporting, or phone-home of any kind.
- Never write positive compliance, certification, or regulatory-approval claims about
  VitalProbe or any target; negated/disclaimer usage is the only allowed form. Say
  "no-PHI architecture" instead.
- `LAW_DISCLAIMER` in `src/vitalprobe/law.py` and the Methodology & limitations block
  in the dossier template are load-bearing legal text — never remove or weaken them.
- Token redaction stays in every output surface. Secrets only via `.env` (gitignored);
  no hardcoded provider URLs, model IDs, prices, or paths — the typed settings module
  owns configuration.
- Human review gates (clinical pack review, calibration labels, attorney review) are
  human-only: an AI must never mark them complete or present AI output as human
  validation.

## Verification before claiming done (run all, report each)

```
uv run ruff check .
uv run mypy
uv run pytest
```

`tests/test_compliance_guard.py` and `tests/test_config_hygiene.py` enforce the
invariants above; if one fails, fix the change — never the guard.
