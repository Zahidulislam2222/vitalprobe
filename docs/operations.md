# Operations, troubleshooting and recovery

## Operating responsibilities

The maintainer operates the static website and source release. Each operator owns
their local execution environment, target permission, secrets, model costs, report
retention and backups. No hosted audit service or staffed availability SLA is currently
offered. Proposed service objectives are in [reliability](reliability.md).

## Routine checks

Before a run, validate the suite, check that the target is authorized for fictional
traffic, verify environment/configuration, and confirm the output location and cost
boundary. After a run, inspect ERROR/FAIL/WARN records, redaction and report limitations.
Before a release, run all CI/security/build gates and the actual documented journey.

For the website, monitor route/asset status, TLS validity and browser behavior. Record
uptime coverage rather than inferring a monthly percentage from a successful request.
Review dependencies and current security advisories before each release. Keep an
independent last-known-good artifact and source revision.

## Troubleshooting

| Symptom | Check and next action |
|---|---|
| No target URL / configuration exit 2 | Export the variable named by adapter `url_env`; verify YAML and current directory |
| Missing response path | Inspect the synthetic target's JSON shape and configure `response_path` |
|401/403 from target | Confirm permission and a scoped staging token; unset variables may omit a header |
| Timeouts or server errors | Check target health, configured timeout/retries and concurrency; do not create a retry storm |
| Expected fixture failures | Inspect per-case evidence; weak scripted responses intentionally exercise failure paths |
| Draft-release validation fails | Obtain qualified content review; do not flip status to make the gate pass |
| Entitlement unavailable | Check license path, signature trust root, expiry and feature set; never share signing material |
| Local model missing or invalid judge JSON | Check installed configured tag and local service; inspect bounded retry failure evidence |
| Empty dashboard history | Use `--track`; verify CLI/dashboard share the intended local DB configuration |
| Website nested route 404 | Verify all emitted HTML entries, server routing and release parity |
| Hero stays still | Check system reduced-motion, media delivery and browser autoplay policy; poster fallback is supported |
| Stripe lane unavailable | Keep it local/test-only; verify opt-in and required settings using the dedicated procedure |

## Backup and restore

Back up source/artifact manifests, operator-managed reports/baselines, local history
and necessary recovery configuration. Keep secrets separate with restricted access
and a documented recovery path. Do not publish private recovery material with code.

Stop local history writers before copying/restoring SQLite, or use SQLite's supported
backup mechanism so a live database and its journal are not copied inconsistently.
Restore into a separate temporary location first; check integrity, schema, representative
runs and report rendering. Only replace the active database after verification and
preserving the last working copy. The operator chooses retention and recovery targets.

The static release archive must be independently stored, hash-verified and actually
started during a restore rehearsal. See [deployment](deployment.md). Future hosted
metadata needs separately reviewed point-in-time recovery and job reconciliation.

## Incident procedure

1. Record the symptom, affected revision, time, scope and last known working state.
2. Appoint an owner and contain impact; protect evidence and avoid recording secrets.
3. Restore the verified release or isolate the affected local workflow.
4. Confirm recovery using real external/user flows and file/data integrity checks.
5. For exposed credentials, revoke/rotate them and identify downstream copies; deleting
   a source line alone does not invalidate a leaked credential.
6. Record root cause, fix, proof, follow-up ownership and the gate that should have
   caught it. Communicate only verified impact.

Any notification duty depends on the actual incident, data and jurisdiction; consult
qualified counsel rather than assuming a universal deadline. Use private reporting
for vulnerabilities; [SECURITY.md](../SECURITY.md) explains the channel.

## Session continuity

Keep a private project-scoped checkpoint before work and at milestones: objective,
authorization, source/artifact revision, changes, tests, remaining steps and blockers.
Keep a private recovery source for current credentials, never in public Git history.
Public release notes should contain verified product facts and scrubbed operational
lessons, not infrastructure identities or sensitive incident evidence.
