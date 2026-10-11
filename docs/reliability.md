# Reliability and availability objectives

Status: **operating objectives and future service requirements**. A successful health
check or release verification is a point-in-time result. No historical 99% availability
measurement or contractual service-level agreement is asserted by this document.

## Initial 99% availability objective

The initial public-website objective is at least 99.0% successful eligible requests over
a rolling 30-day window. An eligible request is a legitimate GET/HEAD to a documented
page or required asset, excluding documented bot abuse and requests for unknown URLs.
Success means the expected HTTP response and required page content within 5 seconds.
Count DNS, TLS, edge and origin failures when they affect the user journey. Planned
maintenance affecting eligible requests consumes the same budget.

```text
availability = successful eligible requests / all eligible requests
error budget = 1 - target availability
```

| Objective | Request error budget | Equivalent unavailable time in 30 days, for a time-based indicator |
|---|---:|---:|
| Initial 99.0% | 1.0% | 7 hours 12 minutes |
| Proposed next 99.9% | 0.1% | 43 minutes 12 seconds |
| Proposed later 99.95% | 0.05% | 21 minutes 36 seconds |

Time-based probe availability and request-based availability are different indicators;
publish their denominators separately. The time equivalence above does not convert a
request error ratio into measured downtime. Higher objectives require redundancy,
measured failure behavior and staffed response before adoption.

## Measurement and reporting

Planned measurement uses external probes from at least three independent locations,
once per minute, checking DNS/TLS, critical routes and required content. Add a periodic
browser journey for JavaScript rendering, navigation and the evidence explorer. Retain
probe timestamps, total/failed samples, region coverage and missing-sample rules.
Missing probe coverage must be reported as unknown rather than counted as success.

Combine these with aggregated edge/origin request status and latency where available.
Infrastructure health data must exclude audit inputs, target responses, credentials and
personal identifiers; it is not permission to add CLI telemetry or visitor tracking.
Publish coverage and window dates with any availability result. Monitoring enrollment,
public status tooling and paid plans are separate implementation decisions.

## Separate future service indicators

| Future service | Indicator and proposed objective |
|---|---|
| Authenticated metadata API | 99.0% eligible operations succeed over 30 days; latency objectives in scalability plan |
| Job admission | Accepted work gets one durable job identity; distinguish rejection from lost admission |
| Audit completion | Completion/error/cancellation ratios by workload class; downstream target failures visible |
| Artifact retrieval, if approved | Correct tenant-scoped object returned; missing/corrupt results are failures |

An API uptime objective does not establish audit correctness or clinical safety.
Third-party target/model outages must remain visible in job outcomes and dependency
reports rather than being relabeled as successful audits.

## Error-budget policy

Assign an operational owner before declaring an objective active. Review the rolling
budget at each release and weekly. Freeze nonessential rollout when the budget is
exhausted or a fast-burn incident is active; prioritize restoration and root cause fixes.
Use proposed fast/slow alerts of 14.4× budget burn over 1 hour and 6× over 6 hours, respectively,
paired with shorter confirmation windows to avoid paging on a single sample. Validate
these thresholds against the actual monitoring cadence before activation.

## Recovery targets

| Component | Proposed recovery time objective | Proposed recovery point objective | Prerequisite |
|---|---|---|---|
| Static website | 30 minutes | 0 lost published source revisions | Remote source plus independently stored immutable release and tested rollback |
| Customer-local reports/history | Operator-defined | Operator-defined | Operator backups; VitalProbe does not host or back up these files |
| Future hosted metadata | 60 minutes | 15 minutes | Approved replicated storage, point-in-time backups and tested restore |
| Future queue/work coordinator | 30 minutes | No lost acknowledged admissions | Durable admission ledger, deduplication and replay proof |

These are planning targets. Source recovery does not imply zero downtime; restored
metadata can be stale even if artifacts survived. Document reconciliation of jobs
admitted after the last recovery point. Test key recovery separately from data recovery.

## Release and incident controls

Build locally, verify the artifact, deploy a new immutable directory, smoke-check it,
then switch routing. Retain the last verified release and an independent backup.
Confirm all local/live hashes after rollout and after rollback. Do not edit live source.

For an incident: detect and classify, appoint an owner, contain impact, restore the
last verified state, confirm externally, communicate scope, and record a blameless
post-incident analysis with corrective tests. See [operations](operations.md).

Reference: [Google SRE: Implementing SLOs](https://sre.google/workbook/implementing-slos/).
