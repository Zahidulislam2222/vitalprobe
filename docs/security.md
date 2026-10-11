# Security architecture

The current design minimizes hosted exposure: fictional inputs, local execution,
optional explicit provider egress, offline entitlements and a static public website.
Controls and limitations below describe the current boundary. Additional controls for
a future hosted service are requirements, not assertions about an existing service.

## Assets and boundaries

Protect target/provider credentials, signing material, synthetic report integrity,
baseline provenance, local history and separately licensed content. Treat target
responses, imported suites and generated drafts as untrusted input. The operator's
machine and authorized target are separate trust boundaries even on the same network.

| Threat | Implemented boundary or practice | Limitation and required verification |
|---|---|---|
| Credential exposure | Environment-based settings, output token redaction, ignored local secrets, scanner gates | Inspect all artifacts before sharing; redaction is not complete personal-data detection |
| Untrusted YAML/content | Safe loading and validated case/adapter contracts | Run only trusted suites; regex complexity and excessive input still require operator limits |
| Target/provider abuse | Configured endpoints, bounded runner concurrency, timeouts and capped retries | Operator authorizes target traffic; local tooling is not a hosted SSRF firewall |
| Prompt injection | Fictional adversarial cases and inspectable evidence | Judges and targets can still be manipulated; case coverage is not a universal defense |
| HTML injection | Report templating and tests for untrusted content handling | Review custom branding/templates and newly introduced output surfaces |
| Entitlement forgery | Offline Ed25519 signature verification and feature guards | Public-source checks can be bypassed; protect the private signing seed and licensed content |
| Local dashboard exposure | Loopback default, no public hosting; billing enforces loopback peer/origin boundary | No login/tenant authorization exists for general dashboard use; do not expose it |
| Forged/reordered payment events | Signed test webhooks, deduplication/leases and ordering/recovery tests | Test lane only; real-provider acceptance and commercial gates remain open |
| Supply-chain change | Lockfiles, pinned CI action revisions, dependency/security scans and build validation | A clean scan is bounded evidence, not proof of absence of vulnerabilities |
| Website compromise | Static assets, no forms/accounts, restrictive serving policy and release parity checks | DNS/CDN/server administration is a separate privileged control surface |

## Current limitations

Do not run the local dashboard behind a public proxy or bind it to a shared network.
Container-internal binding is permitted only with host publishing pinned to loopback.
Local file/history access assumes a trusted operator and operating-system account.
No claim of multi-tenant access control follows from license checks.

Configured external judges transmit their supplied synthetic evaluation content to the
selected provider. Configure data policies and spending explicitly. Never provide real
patient data. Target-generated content may itself contain personal data and must be
reviewed before provider transmission or report distribution.

## Secret and signing-key operations

Keep credentials out of source, images, logs, generated reports, issues and screenshots.
Use short-lived scoped credentials where available, separate test/live material, and
rotate compromised values. A clean working tree does not establish clean Git history;
inspect history before publication. Never publish a private signing seed.

Public verification keys are intended package data. Signing-key rotation requires
distributing the new verification key; old offline installations retain old trust roots
until upgraded. Cancellation prevents future renewal but cannot instantly invalidate
an already issued offline license. Record these limits in customer-facing terms.

## Future hosted requirements

Before any hosted control plane: implement authenticated identity, explicit tenant and
object authorization, safe outbound destination policy, CSRF protection for session
flows, bounded request bodies, pagination, quotas and rate limiting. Separate worker,
control-plane and administrative roles. Isolate secrets per tenant and restrict worker
egress. Use encryption in transit/at rest, key recovery procedures and retention/deletion
rules approved for the chosen data boundary.

Add security audit trails without request/response content or credentials. Test negative
authorization paths, replay/idempotency, malformed payloads, SSRF destinations, dependency
failure and recovery. Review against [OWASP ASVS](https://owasp.org/www-project-application-security-verification-standard/)
and [OWASP API Security](https://api-security.owasp.org/editions/2023/en/0x03-introduction/),
tracking each applicable control as implemented, tested, planned or not applicable.

## Verification and disclosure

CI runs Python/frontend tests, types/lint, Bandit, Gitleaks, Semgrep, dependency audits
and builds. The installed edit-time scanner is an additional developer control and
must not be disabled to pass a change. Preserve all findings and remediation evidence.
Security reporting and support expectations are in [SECURITY.md](../SECURITY.md).
