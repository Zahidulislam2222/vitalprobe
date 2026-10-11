# Legal responsibilities and responsible use

Not legal advice. This documentation was drafted with AI assistance and has not been
reviewed by an attorney. Qualified counsel must assess the actual product, customers,
jurisdictions and contracts before a commercial or expanded data-processing launch.

## Current product boundary

VitalProbe evaluates fictional healthcare/wellness conversations and produces evidence
of observed software behavior. It does not diagnose, prescribe, provide patient care or
replace clinical judgment. Reports are not a regulatory approval, legal opinion or
clinical assessment. A pass applies to tested cases and configuration, not all possible
behavior of an assistant.

The audit data plane stays local/customer-controlled. No real patient records, production
conversations, public account system or hosted audit storage are part of the current
product. The public website publishes fictional evidence and product information.
Infrastructure providers can process operational request metadata; see [privacy](privacy.md).

## Review areas before expansion

| Area | Current boundary | Prerequisite for relevant future expansion |
|---|---|---|
| HIPAA / US health information | No-PHI audit architecture; fictional inputs only | Counsel assesses covered-entity/business-associate roles, permitted use and any necessary agreements before PHI handling |
| GDPR / personal data | No real personal data accepted in audit inputs | Assess account/contact/payment/network metadata, lawful basis, notices, rights, processors and transfers for the actual service |
| Clinical software regulation | Software testing evidence, no patient-care decision service | Intended-use and jurisdiction assessment before any clinical decision functionality |
| AI governance | Inspectable checks and declared limitations | Risk assessment, version/provenance records, human oversight and incident procedures |
| Consumer/commercial terms | Public source under Apache-2.0; planned paid offerings unavailable | Counsel-approved terms, cancellation/refund policy, support commitments and sales representations |
| Content and intellectual property | Public code license; separate licensed content excluded | Confirm rights/provenance, reviewer agreements and licenses for supplied material |
| Accessibility | Automated and manual checks with stated scope | Broader assistive-technology review and jurisdiction/customer requirements before conformance commitments |

HIPAA depends on the parties, information and activities involved. HHS describes
de-identification methods for real health information; that is a separate process from
creating fictional scenarios. The [HHS guidance](https://www.hhs.gov/hipaa/for-professionals/special-topics/de-identification/index.html)
is a reference for counsel, not permission to import real records into VitalProbe.

The [EDPB data-protection guide](https://www.edpb.europa.eu/sme/learn-the-basics/data-protection-basics_en)
helps identify personal-data processing. Synthetic audit content does not settle the
legal treatment of a future customer's identity, billing record or support submission.

The [FDA clinical decision-support guidance](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/clinical-decision-support-software)
is relevant to intended-use assessment. No device classification conclusion is made here.

## Human review and law mappings

Clinical content remains draft until named qualified reviewers approve the relevant
version and scope. Counsel review of informational law mappings is open. Fifty qualified
human calibration labels remain required; AI-generated prelabels are not human validation.
Report citations connect observed evidence to informational requirements and do not
establish that a target satisfies a law.

The runtime law disclaimer and report Methodology & limitations block must remain intact.
Review language/localization separately; emergency advice and jurisdictional assumptions
cannot be transferred between markets without qualified review.

## Commercial and hosted entry gates

Before public accounts, billing or hosted artifacts: record scope approval, reviewed
privacy/terms and processor agreements, data residency, incident/rights handling,
security authorization tests, provider test acceptance and support ownership. Real
patient data and production-conversation ingestion require a separate legal and
architecture decision before implementation.

The localhost Stripe test lane does not close any of these gates. No live payment,
clinician review or legally valid attestation is delivered through that lane.

## Responsible AI practice

Maintain an inventory of target/judge/model versions, rubric versions, fictional
scenario coverage and limitations. Review severe failures and judge disagreements.
Separate deterministic evidence from model interpretation. Keep generated variants
draft and require review before promotion. Use the voluntary
[NIST AI RMF](https://www.nist.gov/itl/ai-risk-management-framework) as a risk-management
reference, without presenting framework use as an endorsement or external approval.
