# Technical release status

VitalProbe remains a pre-0.1 source release. This status describes verified technical behavior;
it is not clinical validation, legal advice, or regulatory approval.

The local engine, reports, history, comparison, local dashboard, learning drafts, offline
entitlements, simulator, and MCP surfaces are implemented. The latest local checks passed
182 tests, strict typing, lint, package builds/validation, and a 35-check real localhost flow.
The intentionally weak scripted demo target produced 3 PASS / 22 FAIL / 0 ERROR across
25 synthetic scenarios. These counts describe that scripted target only.

The optional Stripe subsystem is **disabled by default**, **test mode only**, and restricted
to loopback access and synthetic customers. Its automated tests cover signature verification,
live-mode rejection, processing leases, reordered events, pending refund/dispute holds,
monthly Price validation, cancellation preservation, and paid-through test-license evidence.
No real Stripe end-to-end result is claimed. See [sandbox acceptance](stripe-sandbox-e2e.md)
for the remaining real-provider matrix. Offline licenses cannot be revoked instantly.

The entitlement signing key was rotated on 2026-10-12. This source version rejects licenses
signed with the retired key; its existing local development license was reissued and verified.
Older offline installations retain their bundled verification key and must upgrade to receive
the rotation. No customer license or production payment was issued.

The [public demonstration](https://vitalprobe.zahidul-islam.com) is a static React frontend
with locally bundled synthetic evidence, a filterable case explorer, setup commands and
self-hosted decorative media. The frontend has 32 automated regressions and is verified
in six desktop/tablet/mobile widths, with keyboard and reduced-motion checks and zero
violations in the configured automated WCAG accessibility scan. The
[original HTML report](https://vitalprobe.zahidul-islam.com/evidence/) is preserved. The local dashboard, billing
console, customer inputs, accounts, databases, and private clinical content are not hosted.
Run your own audits locally with the [quickstart](quickstart.md).

Remaining release gates:

- Named qualified clinician review of draft clinical content and review capacity/agreement.
- Qualified counsel review of informational law mappings and commercial policy drafts.
- Fifty qualified human calibration labels; AI labels do not satisfy this gate.
- Rotated Stripe sandbox credentials and completion of the real test-mode acceptance matrix.
- Separate founder approval of production payment settings and any paid/cloud action.
- PyPI publication remains deferred; install from source or use locally built artifacts.

Human review gates stay open. Unreviewed cases stay draft and fail release validation.
