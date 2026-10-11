# Contributing to VitalProbe

Use [GitHub issues](https://github.com/Zahidulislam2222/vitalprobe/issues) for feature
proposals and non-sensitive defects. Read the [documentation index](docs/README.md),
[architecture](docs/architecture.md), [security policy](SECURITY.md) and repository
[agent rules](AGENTS.md) before changing behavior.

## Workflow

1. Describe the problem and acceptance criteria before implementation.
2. Work on one focused branch; preserve unrelated changes and existing tooling.
3. Keep secrets in the environment, changeable configuration in its owning module/data
   file, and all patient scenarios fictional.
4. Add meaningful regressions for changed behavior and update relevant documentation.
5. Run [TESTING.md](TESTING.md), security checks and builds; exercise the real flow.
6. Request an independent review. Include results and remaining limitations in the PR.

Do not weaken compliance/configuration guards, disable scanning or mark human-review
gates complete. Do not add telemetry, hosted account/storage/billing or real-patient
processing as an incidental implementation detail; propose scope changes first.

## Review checklist

Verify public links and CLI examples, configuration ownership, redaction, error paths,
access boundaries, dependency provenance and package contents. For frontend changes,
check direct routes, keyboard behavior, responsive widths and system reduced motion.
For operational changes, prove rollback/restore and artifact parity. See [CI](docs/ci.md).

## Content and licensing

Submit only material you have the right to share. Keep scenario provenance and review
status accurate. Public changes are contributed under the repository's Apache-2.0
license; do not add separately licensed clinical content or private customer artifacts.
External assets retain their own license notices and provenance.
