# Testing and acceptance

Use fictional data, local targets and `VITALPROBE_JUDGE=none` for the zero-provider-spend
workflow. Automated tests use mocked judge/payment responses; passing them is distinct
from real provider acceptance and qualified human review.

## Python gates

```bash
uv sync --locked --all-extras
uv run ruff check .
uv run mypy
uv run pytest
uvx --from bandit==1.9.4 bandit -q -ll -r src
uv build
uvx --from twine twine check dist/*
```

Strict mypy covers configured source, tests and examples. The suite covers deterministic
checks, adapters, judges, redaction, reports, comparison, history, simulator, calibration,
local generation, entitlements, MCP, dashboard, isolated payment behavior, compliance
and configuration hygiene. See the [CI workflow](.github/workflows/ci.yml) for locked
dependency audits, Semgrep, Gitleaks and isolated wheel installation.

## Frontend gates

In `web/` with Node 24:

```bash
npm ci --ignore-scripts --no-fund
npm run typecheck
npm run lint
npm test
npm audit --audit-level=low
npm run build
```

Vitest covers evidence/configuration boundaries and route/content invariants.
Browser verification additionally exercises every direct route, keyboard
navigation, mobile layouts, evidence filtering, clipboard feedback, autoplay fallback,
and initial/changing reduced-motion preferences. Automated accessibility scans do not
replace keyboard and visual inspection or establish full standards conformance.

## Exercise the real flow

Follow [quickstart](docs/quickstart.md), not just unit tests. Confirm target health,
validate the starter, run all 25 scenarios, inspect canonical JSON/HTML, compare a later
run, and inspect tracked history. The scripted target deliberately produces failures;
verify `counts.error == 0` to distinguish observed behavior from transport failures.
Test the negative CI artifact gate as well as a passing artifact.

For local dashboard acceptance, verify loopback binding and safe argument construction;
exercise report/history views and an actual triggered run. Without a valid license,
`vitalprobe license check mcp_server` must refuse paid access. Model-dependent or
licensed flows require their configured local model/content and their own evidence.

## Payment and review gates

[Stripe sandbox acceptance](docs/stripe-sandbox-e2e.md) is a separate local test-mode
matrix. Mock tests do not establish real checkout, webhook, refund or dispute results.
Do not use live keys or payment methods. Public billing remains unavailable.

Clinical review, counsel review and 50 qualified human calibration labels remain open.
`validate --release` must reject draft clinical cases. AI-generated labels and a green
build cannot close a human gate.

## Recorded baseline

On 2026-10-12 the runtime release passed 182 Python tests, strict typing across 86
files, 39 frontend tests, lint, package validation and security checks. Its exact source
commit and CI evidence are linked in [release status](docs/release-status.md). Re-run
checks for a new commit; do not treat these counts as perpetual evidence.

Manual operator tooling belongs in an ignored local test folder; the genuine tracked
`tests/` suite is CI tooling and remains committed. Retain manual scripts for reruns.
