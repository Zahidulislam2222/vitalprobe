# VitalProbe documentation

VitalProbe is a local-first evidence-testing toolkit for healthcare and wellness AI.
This documentation covers the public frontend, Python backend, operational procedures,
and the engineering roadmap. Start with the implemented product; future services have
explicit entry criteria and verification milestones.

| Need | Read |
|---|---|
| Install and produce your first report | [Quickstart](quickstart.md) |
| Understand capabilities and boundaries | [Product guide](product.md) |
| Understand components and data flow | [Architecture](architecture.md) |
| Develop the React frontend | [Frontend README](../web/README.md) |
| Use CLI, REST adapters, dashboard and MCP | [Backend interfaces](backend.md) |
| Configure environments and providers | [Configuration reference](configuration.md) |
| Write fictional safety suites | [Test authoring](writing-tests.md) |
| Run checks and assess evidence | [Testing](../TESTING.md) and [CI](ci.md) |
| Deploy static assets and recover a release | [Deployment](deployment.md) |
| Operate, investigate and restore | [Operations](operations.md) |
| Report a vulnerability | [Security policy](../SECURITY.md) |
| Assess threats and controls | [Security architecture](security.md) |
| Understand data handling | [Privacy](privacy.md) |
| Understand law and review responsibilities | [Legal and responsible use](legal.md) |
| Plan for 1M+ concurrent users | [Scalability](scalability.md) |
| Define availability and recovery targets | [Reliability objectives](reliability.md) |
| Follow implementation milestones | [Roadmap](roadmap.md) |
| Understand optional future monitoring | [Monitoring design](monitoring-design.md) |
| Understand packaging and planned pricing | [Tiers](tiers.md) |
| Validate the isolated Stripe test lane | [Stripe sandbox procedure](stripe-sandbox-e2e.md) |
| Check shipped behavior and open gates | [Release status](release-status.md) and [changelog](../CHANGELOG.md) |
| Contribute or request support | [Contributing](../CONTRIBUTING.md) and [support](support.md) |
| Review upstream standards | [Research references](references.md) |

## Reading status correctly

**Implemented** means a component exists in this repository. **Verified** refers to a
dated check and its stated scope. **Planned** means an engineering objective with entry
criteria. Clinical review, attorney review and human calibration are separate approvals.
The [release status](release-status.md) records the latest evidence; capacity and uptime
goals live in their own documents and are not current measurements.

Apache-2.0 covers the public repository; see [LICENSE](../LICENSE). Separately supplied
licensed content has its own terms and is not included in the public distribution.
