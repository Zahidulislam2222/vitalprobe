# Technical release status

## Current publication — 2026-10-12

The [website](https://vitalprobe.zahidul-islam.com) and public source provide the
frontend and local Python backend. The Python package is `0.1.0.dev0`; PyPI publication
is deferred. This record concerns engineering evidence. It is not clinical validation,
not legal advice and not a regulatory approval.

The public documentation now covers product interfaces, configuration, security,
privacy and law, release operations, recovery, support, a phased 1M+ user architecture,
and a 99% availability objective. Capacity and availability are future engineering
objectives with defined verification gates, not measured service results.

## Verified runtime baseline

[Source ef1d3d2](https://github.com/Zahidulislam2222/vitalprobe/commit/ef1d3d296245eac255050da7e933bbac77fe6f8a)
and its [four successful CI jobs](https://github.com/Zahidulislam2222/vitalprobe/actions/runs/38171580947)
record the deployed runtime baseline. Documentation-only publication does not replace
the deployed artifact or change its source identity. For subsequent commits, consult
[the current workflow](https://github.com/Zahidulislam2222/vitalprobe/actions/workflows/ci.yml).

- 182 Python tests, strict typing across 86 files, lint, package build and validation.
- 39 frontend tests, TypeScript, lint, dependency audit and static build.
- All six website pages exercised with configured accessibility scans at four widths;
  keyboard, navigation, evidence filtering and responsive layouts exercised separately.
- Automatic muted hero playback, blocked-autoplay poster, and changing system
  reduced-motion preferences exercised. Playback/motion controls were removed.
- Immutable artifact parity, HTTP/TLS, static allowlisting, isolation, archive restore
  and rollback checked. These checks do not establish historical uptime or load capacity.
- The 25-case scripted target produced 3 PASS / 22 FAIL / 0 ERROR. This describes the
  intentionally weak target, not clinical accuracy of the toolkit.

The website includes Home, Product, Evidence, Pricing, Docs and Trust pages, bundled
fictional evidence and self-hosted decorative media. Local dashboards, billing tools,
accounts, databases and licensed content are not hosted. Planned $50/$70 monthly
pricing is informational; public checkout is unavailable.

## Implemented local components

The engine, deterministic/optional semantic checks, canonical reports, comparison,
history, loopback dashboard, local draft generation, calibration, offline entitlements,
patient simulator and MCP interfaces exist. See [backend interfaces](backend.md) for
configuration and licensing boundaries.

The isolated Stripe subsystem is disabled by default, accepts test mode only and is
restricted to loopback and synthetic identities. Mocked tests cover signatures,
live-mode rejection, Price validation, reordered events, processing leases, refund/
dispute holds and cancellation preservation. Real Stripe acceptance is not complete;
see [the matrix](stripe-sandbox-e2e.md). Offline licenses cannot be revoked instantly.

The entitlement verification key was rotated on 2026-10-12. This version rejects the
retired signer. Existing offline installations require an upgrade to receive the new
verification key. No customer license or production payment was issued.

## Open gates

- Named qualified clinician review of clinical content and an agreed review service.
- Qualified counsel review of law mappings and commercial policies.
- Fifty qualified human calibration labels, plus localization review where applicable.
- Configured Stripe test credentials/Prices and the complete real-provider test matrix.
- Production commercial policies and explicit approval before any production payment.
- Measured reliability, monitoring coverage, approved load tests and staged scale gates.
- A separately approved package publication process.

Human gates remain open; draft content fails release validation. The [roadmap](roadmap.md)
defines the dependencies rather than assigning unsupported completion dates.
