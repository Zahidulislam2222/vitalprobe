# Changelog

This record separates shipped behavior from objectives in the [roadmap](docs/roadmap.md).
The Python package remains `0.1.0.dev0`; repository publication is not a PyPI release.

## 2026-10-12 — Public documentation

- Added an indexed guide covering the frontend, backend, configuration, security,
  privacy, legal responsibilities, deployment, recovery, support and contribution.
- Defined a future architecture and staged load tests for 1M+ concurrent users.
- Defined a 99% availability objective, its measurement and recovery targets.
- Aligned all component READMEs and planned pricing with the maintained product data.
- Corrected the consumer CI instructions to reject target errors explicitly, in
  addition to checking regressions. Included policies in source distributions.

## 2026-10-12 — Automatic motion

- Removed the header motion switch and hero playback buttons. Decorative video starts
  automatically, muted, looping and inline.
- Preserved initial and changing operating-system reduced-motion preferences,
  keyboard navigation, browser autoplay fallback and the static poster.

## 2026-10-12 — Multipage frontend

- Shipped Home, Product, Evidence, Pricing, Docs and Trust pages with direct routes,
  unique metadata, responsive layouts and accessible navigation.
- Added Motion interactions, Lenis scrolling, and maintained JSON product content.
- Published a fictional evidence report and its canonical JSON, with source and
  verification links. Public checkout remains unavailable.

## Earlier engineering milestones

- Added canonical JSON and HTML reports, REST/MCP target adapters, deterministic
  checks, opt-in semantic judges, regression comparison and local SQLite history.
- Added the loopback dashboard, synthetic-patient simulator, calibration tooling,
  local draft generation, offline entitlements and an isolated Stripe test lane.
- Added configuration, compliance, credential, dependency and security checks.

Clinical, legal, localization and human-calibration review remain separate open gates.
