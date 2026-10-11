# Privacy and data handling

This document describes product data flows and responsibilities. It is not a substitute
for a reviewed commercial privacy policy or data-processing agreement. The current
audit architecture accepts fictional patients only and does not host customer audits.

## Data inventory

| Data class | Current location/use | Retention responsibility |
|---|---|---|
| Fictional scenario inputs | User-selected local suite and configured target request | Operator controls files and target policy |
| Target responses and verdict evidence | Local JSON/HTML; optional local SQLite history | Operator reviews, retains and deletes artifacts |
| Baselines | Operator-selected local files | Operator versions and protects them |
| Judge inputs | Local model, or explicitly selected remote provider | Operator reviews provider policy and egress authorization |
| Credentials | Ignored local environment or operator secret store | Operator manages access and rotation |
| License data | Local signed license file | Operator controls sharing and expiry handling |
| Payment test records | Disabled-by-default localhost test ledger; synthetic identities | Operator controls test cleanup; no live customer collection |
| Public website content | Bundled fictional evidence and static assets | Maintainer controls published versions |

The application adds no visitor analytics, account login, tracking cookies or browser
storage. DNS/CDN/hosting providers still process network requests and may retain
operational metadata under their own policies. A no-tracking application is not a
claim that every infrastructure provider retains no access logs.

## Synthetic-data rules

Create fictional identities from scratch. Do not paste production conversations,
patient charts or real contact details into suites, reports, support requests or issues.
Removing names from a real record does not turn it into fictional data. A target can
return sensitive information despite a synthetic prompt; inspect and handle that result
under the operator's data rules before sharing or forwarding it.

Token redaction protects configured secrets in supported output surfaces. It is not
a complete personal-data scrubber. HTML/JSON reports should be reviewed as a whole,
including target endpoint identifiers, content and custom branding.

## Local retention and deletion

Set a retention period for reports, baselines, history, drafts and local backups.
Delete or archive them according to that period; the current product does not claim
automatic retention enforcement. Deleting a report does not delete copies in the local
history database, exported files, backups or a recipient's copy. Stop active writers
before restoring/replacing a database. See [operations](operations.md).

## Expansion prerequisites

A future account, coordination, hosted storage or payment service introduces additional
personal-data processing even if audit cases stay fictional. Before activation, identify
controller/processor roles, purposes and lawful basis, data classes, residency, retention,
subprocessors, international transfers, rights handling and incident response. Review
contracts and publish a reviewed policy for the actual deployed service.

Current synthetic-only boundaries do not authorize real-patient processing. Consult the
[legal guide](legal.md) for scope-entry gates and authoritative references.
