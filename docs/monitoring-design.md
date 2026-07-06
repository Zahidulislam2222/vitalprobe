# Production-trace sampled evaluation — DESIGN ONLY

Status: **design document, deliberately not implemented** (BUILD-PLAN M8 step 5; the
Not-building list excludes production-conversation storage and hosted infrastructure).
Nothing in this document exists in code. It records the intended shape of a future
monitoring tier so the design survives until that tier is opened.

## Problem

Pre-release suites test synthetic scenarios. Once a bot is live, its real conversations
drift away from the test distribution (new prompts, new model versions, new retrieval
data). Teams want a signal that safety behavior is holding in production without paying
for full evaluation of every conversation and without VitalProbe ever hosting PHI.

## Intended architecture (three cost layers)

1. **Heuristics — 100% of traffic.** Deterministic checks (the existing evaluator
   registry) run on every sampled-in conversation turn: crisis-pattern presence,
   forbidden-phrase hits, disclosure markers. Cheap, local, no LLM.
2. **LLM judge — 10–20% sample.** A configured judge (local by default) scores a random
   sample plus every heuristic-flagged conversation against the same rubrics used in
   pre-release runs. Sampling rate is configuration, never code.
3. **Human labels — periodic.** A small periodic batch goes to a human reviewer using the
   existing calibration flow (labels CSV → agreement metrics), keeping the judge honest
   over time.

## Data-protection posture (binding for any future implementation)

- Runs INSIDE the customer's infrastructure (their CI/cron, their storage). VitalProbe
  ships the tool; it never receives conversations. The no-PHI architecture statement in
  BUILD-PLAN §7 must remain true.
- Redaction before judging: the customer configures PII scrubbing on ingest; raw text
  never leaves their boundary.
- Only aggregate verdicts/metrics would ever be exportable, and only by customer action.

## Interfaces it would reuse (nothing new invented)

- Evaluators: `vitalprobe.evaluators.CHECKS` unchanged.
- Judges: the existing judge backends + rubrics, judge choice by settings.
- Calibration: `vitalprobe calibrate` artifacts for the human-label layer.
- Reporting: RunResult-shaped periodic summaries → the existing dossier renderer.
- Experience store: per-period rows for trend/regression detection, like `--track`.

## Explicit non-goals

Hosted dashboards, streaming ingestion, alerting infrastructure, storing raw production
conversations in the experience store, any real-PHI handling. Opening any of these is a
§7 scope-entry trigger and a founder decision.
