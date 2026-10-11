# Product guide

VitalProbe helps engineers inspect how healthcare and wellness AI assistants respond
to fictional safety scenarios. A run combines target responses, deterministic checks,
optional semantic judgments, and an HTML/JSON evidence dossier. It supports regression
decisions and structured review; a test verdict applies to the observed case and setup.

## Current capabilities

| Surface | Implemented behavior |
|---|---|
| Public website | Product, Evidence, Pricing, Documentation and Trust pages; bundled fictional evidence; local setup instructions |
| Python CLI | Validate suites, run audits, compare baselines, inspect history and licenses |
| Target adapters | Configured REST requests and MCP tool targets |
| Checks | Deterministic text/schema/status/latency checks and optional configured semantic judges |
| Reports | Canonical JSON and self-contained HTML with redaction and methodology limitations |
| Local dashboard | Browse runs/history/comparisons and trigger the existing CLI on loopback |
| Synthetic conversations | Persona-driven multi-turn scenarios with trajectory checks |
| Calibration | Collect judge outcomes and compare against separately supplied human labels |
| Learning | License-gated generation of draft variants from failures |
| Offline entitlements | Signed licenses and shared feature checks in CLI/dashboard/MCP surfaces |
| Payment validation | Disabled-by-default, localhost-only Stripe test lane with synthetic identities |

## Who uses it

Engineering teams use repeatable suites before a model, prompt, retrieval or integration
change. Reviewers inspect the underlying response and check evidence rather than a
headline score alone. A failed deliberately weak fixture is useful evidence that a
check runs; it does not establish clinical effectiveness.

## Workflow

1. Author fictional inputs and explicit expected behavior.
2. Configure an authorized staging target and its request/response adapter.
3. Validate the suite, then run with deterministic checks first.
4. Inspect FAIL, WARN and ERROR records and the limitations section.
5. Save a suitable baseline and compare later runs using shared case IDs.
6. Have qualified reviewers assess content, disagreements and release decisions.

The website contains bundled evidence. New audits run on the user's machine or inside
their controlled environment. It has no hosted audit API, customer account system or
payment collection. The dashboard is a local interface, not a public multi-tenant service.

## Data and review boundaries

Inputs must describe fictional people and contain no real patient or personal data.
Target responses still require inspection: a target can introduce sensitive or unrelated
content even when the prompt is fictional. Secret redaction is not a general-purpose
PHI removal guarantee. Review reports before sharing them.

Draft cases stay draft until qualified review. Fifty qualified human calibration labels,
clinical review and counsel review remain open release gates. AI-generated labels and
automated tests do not substitute for them. Reports are not legal advice or clinical
assessments, and are not a regulatory approval.

See [backend interfaces](backend.md), [tiers](tiers.md), [legal responsibilities](legal.md),
and the [roadmap](roadmap.md) for implementation and expansion details.
