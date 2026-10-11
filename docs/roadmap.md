# Engineering roadmap

This roadmap is ordered by dependencies and acceptance evidence, not promised dates.
Capacity and reliability objectives are defined in [scalability](scalability.md) and
[reliability](reliability.md). Proposed services are not enabled by this documentation.

| Phase | Deliverables | Exit criteria | Status |
|---|---|---|---|
| Foundation | CLI, canonical evidence, local dashboard/history, REST/MCP adapters, offline entitlements, synthetic personas, static website | Reproducible tests, types/lint/security/build; real local workflow and artifact checks | Implemented; evidence in release status |
| Content and review | Named clinical/counsel reviews, localization review, 50 qualified human labels | Versioned review records; draft-release validation; agreement and disagreement analysis | Human gates open |
| Public engineering documentation | Complete guides, threat/data boundaries, release evidence, capacity/reliability plans | Link/example checks, public secret review, passing CI and maintained documentation index | This documentation release |
| Operational baseline | Measured external availability, independent backup/restore cadence, incident ownership, asset budgets | Rolling-window report with coverage; restore and origin-failure evidence; adopted 99% objective | Planned |
| Commercial readiness | Reviewed policies/contracts/support, tested payment lifecycle and fulfillment | Counsel/founder gates plus real Stripe test matrix; separate live-mode approval | Planned; test lane exists |
| Controlled hosted coordination | Authenticated tenant control plane coordinating customer-local workers | Scope/legal review, tenancy and egress tests, durable admission, quotas and deletion policy | Planned |
| Capacity 1k → 10k | Representative session and job workloads; saturation/backpressure controls | Agreed latency/error gates, resource curves, soak/spike tests, cost limits | Planned |
| Capacity 100k | Multi-zone operation, bounded distributed scheduling and storage | Zone-loss/rolling-deploy tests; isolation; backup/restore; load-generator proof | Planned |
| Capacity 1M+ | Regional routing/CDN and approved distributed workloads | Repeatable 1M+ concurrency results; thresholds, failure headroom, operational staffing and budget | Planned |
| Reliability progression | Adopt 99.9% then 99.95% only where justified | Measured windows, redundancy and error-budget policy accepted by owners | Planned |

## Review and product quality

Improve scenario coverage and judge calibration before expanding commercial claims.
Record source provenance, reviewer identity/qualification, version, date and limitations.
Track false positives/negatives and disagreements by severity and language. A single
agreement percentage is insufficient without sample size, class distribution and scope.

## Customer-controlled execution first

Prefer signed, authenticated orchestration of customer-local workers to centralizing
responses. Any later optional hosted artifact or production-conversation workflow
requires a separate data-protection design and scope approval. The current product
continues to process fictional scenarios only.

## Future monitoring

Optional customer-side monitoring remains a separate proposal. It cannot reuse the
current synthetic-only permission boundary to ingest real conversations. Legal review,
data minimization, customer authorization and isolation requirements must be resolved
before implementation. See [monitoring design](monitoring-design.md).

## Release decision records

Each phase records acceptance criteria, code/content versions, executed tests, measured
results, review verdict, remaining risks and an operational owner. A milestone changes
status only when its stated evidence exists. Track issues through [GitHub](https://github.com/Zahidulislam2222/vitalprobe/issues)
and publish verified changes in the [changelog](../CHANGELOG.md).
