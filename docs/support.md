# Support and compatibility

Use [GitHub issues](https://github.com/Zahidulislam2222/vitalprobe/issues) for installation
questions, reproducible non-sensitive defects and feature requests. There is no paid
support contract, guaranteed response time or long-term maintenance branch at present.
Security issues use the private channel in [SECURITY.md](../SECURITY.md).

Include the commit/version, operating system, Python/Node version, command, expected
result and a minimal fictional reproduction. Redact credentials, private endpoints
and target/provider identifiers where sensitive. Do not attach real patient data,
production conversations, full environment files or private clinical content.

Python requires 3.12 or newer; the website toolchain requires Node 24 or newer. Lockfiles
record tested dependencies. Use an isolated environment and the current source rather
than assuming a similarly named public package has been released. Public PyPI publication
remains deferred.

The CLI/schema evolve before 1.0. Pin the source revision in reproducible automation,
retain baseline/report versions and review compatibility notes before upgrading.
Offline signing-key rotation may require upgrading the verification trust root and
reissuing a license; older installations do not automatically inherit a new key.

Start with [troubleshooting](operations.md), [configuration](configuration.md),
[backend interfaces](backend.md) and [release status](release-status.md).
