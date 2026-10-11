# Future customer-controlled monitoring

Status: proposal only. The implemented toolkit evaluates fictional scenarios locally.
It does not ingest real production conversations, send telemetry or host a monitoring
service. Implementing this proposal would cross the existing data/legal boundary and
requires a separate scope decision, qualified legal review and privacy prerequisites.

## Purpose and proposed flow

Production distributions can differ from a fictional test suite after a model,
retrieval source or policy changes. A future customer-controlled evaluation system
could identify shifts without centralizing conversation content in the vendor's service.

A candidate design runs inside the customer's environment:

1. Customer-defined eligibility and retention rules select permitted inputs.
2. Deterministic checks inspect eligible traffic locally.
3. An approved sample and flagged cases receive configured local semantic judging.
4. Authorized human reviewers label a bounded set and assess judge agreement.
5. Approved aggregate metrics support trends and incident investigation.

Sample rates, cost ceilings, retention, access, encryption, model choice and confidence
thresholds must be owned by validated configuration. Do not inherit an illustrative
sampling percentage as a production default.

## Data and legal entry requirements

Real health conversations remain outside current scope, even when processed on a
customer machine. Scrubbing alone does not establish anonymization. Before any such
implementation, determine legal roles, lawful basis, HIPAA applicability where relevant,
contracts, residency, retention/deletion, reviewer access, subprocessor behavior and
incident obligations. See [privacy](privacy.md) and [legal responsibilities](legal.md).

A customer-hosted data plane is a proposed architectural boundary, not permission to
process real patient data in the present product. No conversation, identifier or
metric should leave that boundary by default. Aggregates also require review for
re-identification risk before an explicit export.

## Potential component reuse

Existing deterministic evaluators, configured judges, calibration artifacts and report
schemas may be reusable after validating their suitability. The current local history
store is not a production conversation database or tenant isolation system.

## Acceptance before launch

Require a threat model, legal approval, patient-data exclusion or formally approved
handling model, a documented sampling policy, human calibration, privacy-preserving
metrics, authorized access, deletion/restore tests, provider budgets and rollback.
Measure drift and false positives against an agreed baseline; do not promise clinical
outcomes from an automated score.

This proposal belongs after the entry gates in the [roadmap](roadmap.md). Capacity and
operating objectives are defined separately in [scalability](scalability.md) and
[reliability](reliability.md).
