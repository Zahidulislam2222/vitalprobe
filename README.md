# VitalProbe

[![CI](https://github.com/Zahidulislam2222/vitalprobe/actions/workflows/ci.yml/badge.svg)](https://github.com/Zahidulislam2222/vitalprobe/actions/workflows/ci.yml)

**Healthcare AI safety testing with fictional scenarios and inspectable evidence.**

VitalProbe tests a chatbot, RAG application or AI agent against synthetic safety cases,
records the observed responses and produces a structured HTML/JSON evidence report.
Engineers can compare revisions, inspect failures and support qualified review using
repeatable evidence. All patient scenarios are fictional.

[Website](https://vitalprobe.zahidul-islam.com) · [Documentation](docs/README.md) ·
[Quickstart](docs/quickstart.md) · [Roadmap](docs/roadmap.md) · [Security](SECURITY.md)

## Product and architecture

The public repository contains the React/TypeScript frontend and Python backend. The
website provides Product, Evidence, Pricing, Documentation and Trust pages. New audits
run locally or in an operator-controlled environment; there is no hosted audit API or
customer account system.

| Component | What it provides |
|---|---|
| Python engine | Validated suites, REST/MCP targets, bounded execution and deterministic checks |
| Evidence | Canonical JSON, self-contained HTML, secret redaction and baseline comparison |
| Local workspace | Run history, dashboard, synthetic personas and calibration tooling |
| Optional evaluation | Configured local judges; cloud judges require explicit cost approval |
| Licensed surfaces | Offline entitlement verification, draft learning, law mappings and product MCP tools |
| Frontend | Responsive static pages, evidence exploration, smooth scrolling and automatic decorative media |

Read the [product guide](docs/product.md), [architecture](docs/architecture.md),
[backend interfaces](docs/backend.md) and [frontend guide](web/README.md).

## Install and run

Python 3.12+ and [uv](https://docs.astral.sh/uv/) are required. Install from source;
PyPI publishing is intentionally deferred.

```sh
git clone https://github.com/Zahidulislam2222/vitalprobe.git
cd vitalprobe
uv sync --locked --all-extras
uv run vitalprobe --version
uv run vitalprobe validate --suite packs/emergency-core
```

For a complete local container workspace with a scripted synthetic target:

```sh
docker compose up --build
```

Open `http://127.0.0.1:8800`. Host publishing remains pinned to loopback. The
[quickstart](docs/quickstart.md) explains running an audit, reading outcomes, saving a
baseline and configuring your own authorized staging target. No paid model is needed
for deterministic checks.

## Evidence report

![VitalProbe HTML evidence report](docs/assets/report-preview.png)

Each report records the tested inputs, observed responses, checks, verdicts and
limitations. FAIL and ERROR records remain visible. Reports support review decisions;
they are not legal advice, clinical assessments or regulatory approval.

## Engineering and operations

- [Configuration](docs/configuration.md), [test authoring](docs/writing-tests.md),
  [testing](TESTING.md) and [CI](docs/ci.md).
- [Deployment and rollback](docs/deployment.md), [operations](docs/operations.md),
  [security architecture](docs/security.md) and [privacy](docs/privacy.md).
- [Legal responsibilities](docs/legal.md), [contributing](CONTRIBUTING.md),
  [support](docs/support.md), [release status](docs/release-status.md) and [changelog](CHANGELOG.md).

## Growth and reliability

The [scalability plan](docs/scalability.md) defines a future **1M+ concurrent-user**
objective, separating website traffic, authenticated sessions and audit jobs. It covers
CDN delivery, stateless coordination, customer-controlled workers, quotas, storage,
provider limits, staged load tests, failure headroom and cost models.

The [reliability plan](docs/reliability.md) defines an initial **99% availability SLO**,
measurement windows, error budgets, incident response and recovery targets, with a
roadmap toward higher objectives. These are engineering objectives with verification
criteria; current measured evidence is recorded separately in the release status.

## Review and commercial status

Clinical content remains draft pending named qualified review. Counsel review and
50 qualified human calibration labels remain open. Planned paid offerings are described
in [tiers](docs/tiers.md); public checkout is unavailable. The optional Stripe test lane
is disabled by default, localhost-only and separate from production approval.

## Maintainer and license

Maintained by [Zahidul Islam](https://github.com/Zahidulislam2222).
The public code is [Apache-2.0](LICENSE). Separately licensed content is not part of
this public distribution. See [asset provenance](web/ASSETS.md) for frontend media and fonts.
