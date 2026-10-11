# Research and standards references

Reviewed for this documentation on 2026-10-12. These primary sources inform engineering
and review plans; linking a framework does not assert assessment or endorsement.

| Source | How it informs VitalProbe |
|---|---|
| [OWASP ASVS](https://owasp.org/www-project-application-security-verification-standard/) | Versioned security control and verification requirements |
| [OWASP API Security Top 10](https://api-security.owasp.org/editions/2023/en/0x03-introduction/) | Future API authorization, resource-consumption and outbound-request threats |
| [NIST AI RMF](https://www.nist.gov/itl/ai-risk-management-framework) | Risk inventory, measurement, governance and human oversight |
| [HHS de-identification](https://www.hhs.gov/hipaa/for-professionals/special-topics/de-identification/index.html) | Legal distinction between fictional data and processing real health information |
| [EDPB data-protection basics](https://www.edpb.europa.eu/sme/learn-the-basics/data-protection-basics_en) | Personal-data scope and organizational responsibilities |
| [FDA clinical decision-support guidance](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/clinical-decision-support-software) | Intended-use assessment for any later clinical functionality |
| [Google SRE SLOs](https://sre.google/workbook/implementing-slos/) | Availability indicators, windows, error budgets and ownership |
| [Cloudflare cache behavior](https://developers.cloudflare.com/cache/concepts/default-cache-behavior/) | Cache eligibility, static delivery and origin load |
| [Kubernetes horizontal autoscaling](https://kubernetes.io/docs/concepts/workloads/autoscaling/horizontal-pod-autoscale/) | Optional metrics-driven replica scaling in a future service |
| [Grafana k6 large tests](https://grafana.com/docs/k6/latest/testing-guides/running-large-tests/) | Distributed generator capacity and resource constraints |
| [Grafana k6 thresholds](https://grafana.com/docs/k6/latest/using-k6/thresholds/) | Explicit pass/fail performance criteria |
| [GitHub commit identity](https://docs.github.com/en/account-and-profile/how-tos/email-preferences/setting-your-commit-email-address) | Founder attribution of published commits |
| [GitHub secret scanning](https://docs.github.com/en/code-security/concepts/secret-security/secret-scanning) | Publication hygiene and history review |

Recheck provider documentation, limits, pricing and law when implementing a roadmap
phase. Requirements can change; the implementation decision records its review date
and the actual service/jurisdiction involved.
