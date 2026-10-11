# Security policy

## Reporting a vulnerability

Use the repository's **Security → Report a vulnerability** workflow when available:
[private reporting](https://github.com/Zahidulislam2222/vitalprobe/security/advisories/new).
If that workflow is unavailable, contact the maintainer through the
[GitHub profile](https://github.com/Zahidulislam2222) to arrange a private channel.
Do not put exploit details, credentials, real patient data or customer artifacts in a
public issue. No bug-bounty or guaranteed response time is currently offered.

Include the affected commit/version, component, expected/observed behavior, a minimal
fictional reproduction, impact and any safe mitigation. Keep reproduction traffic
local or on infrastructure you own. Do not perform intrusive tests against the public
site, other users, external model providers or shared hosting.

## Supported scope

Security fixes target the latest public `main` source and its associated frontend.
There is no published long-term support branch or PyPI release policy yet. Reports
about older revisions are welcome when the issue persists on current source.

Maintainer: Zahidul Islam. Reports are triaged as maintainer capacity permits; publication
timing and any coordinated disclosure plan are agreed through the private report.

## Product boundaries

Fictional inputs only. The dashboard is local-only and has no public authentication or
tenant isolation. Stripe validation is disabled by default, test-only and loopback-only.
No real patient data should appear in issues or vulnerability reports.

See [security architecture](docs/security.md), [privacy](docs/privacy.md),
[legal responsibilities](docs/legal.md) and [operations](docs/operations.md) for controls,
known limits, credential rotation and incident handling.
