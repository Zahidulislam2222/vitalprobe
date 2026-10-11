# Stripe sandbox end-to-end acceptance

This procedure proves payment behavior at **$0** with Stripe test mode. It is not a live-mode
launch procedure and does not close any legal, clinical, policy, or production gate.

## Hard boundary

- Use only synthetic customers such as `synthetic-buyer@example.com`.
- Use only Stripe test cards and test keys. The application rejects live keys, live events,
  live Prices, public return URLs, and non-example email domains.
- Run the dashboard and webhook endpoint on localhost. Do not deploy this lane.
- Synthetic test licenses expire at the Stripe paid-through time. Because license checks are
  offline, a refund or dispute marks the local ledger for manual review but cannot instantly
  invalidate a license file that was already delivered.
- Do not paste keys into chat, source, documentation, shell history, or screenshots. Put them
  in the ignored `.env` file only.

## 1. Create Stripe sandbox catalog entries

In the Stripe sandbox Dashboard, create two recurring monthly Prices:

| Product | Amount | Expected local setting |
|---|---:|---|
| VitalProbe Automated — synthetic test | USD 50.00/month | `VITALPROBE_STRIPE_AUTOMATED_PRICE_ID` |
| VitalProbe Clinician-Reviewed — synthetic test only | USD 70.00/month | `VITALPROBE_STRIPE_CLINICIAN_PRICE_ID` |

The application fetches each Price before checkout and rejects it unless `livemode` is false,
the Price is active and recurring, and amount/currency exactly match typed settings.

## 2. Configure ignored local environment

Copy the Stripe sandbox block from `.env.example` into `.env`, then set:

```dotenv
VITALPROBE_BILLING_SANDBOX_ENABLED=true
STRIPE_SECRET_KEY=<sandbox secret or restricted test key>
VITALPROBE_STRIPE_AUTOMATED_PRICE_ID=<test Price ID>
VITALPROBE_STRIPE_CLINICIAN_PRICE_ID=<test Price ID>
```

Do not set a webhook secret yet. `stripe listen` supplies a temporary `whsec_...` value in
the next step. The sandbox Ed25519 seed is generated under the ignored `artifacts/` directory;
it is separate from the production entitlement key and signs only visibly synthetic licenses.

## 3. Start localhost dashboard and webhook forwarding

Terminal 1:

```bash
uv run --extra dashboard vitalprobe dashboard
```

Terminal 2, after installing and authenticating the official Stripe CLI:

```bash
stripe listen --forward-to http://127.0.0.1:8800/billing/webhook
```

Copy the displayed webhook signing secret into `STRIPE_WEBHOOK_SECRET` in `.env`, restart the
dashboard, and open `http://127.0.0.1:8800/billing`.

## 4. Acceptance matrix

Use Stripe's documented test values, never real payment details.

| Scenario | Action | Required evidence |
|---|---|---|
| Successful Automated checkout | Create checkout; complete with successful test card | checkout and subscription recorded; paid invoice creates a sandbox license ending at paid-through time |
| Successful clinician-plan checkout | Repeat with $70 test plan | plan maps to clinician test tier; page continues to say test only |
| Decline | Use generic-decline test card | no paid entitlement; recoverable checkout message |
| Insufficient funds | Use corresponding decline test card | no paid entitlement; subscription/invoice state reconciles |
| 3DS | Use authentication-required test card | success only after simulated authentication |
| Duplicate event | Resend one event from Stripe Workbench | second delivery reports `duplicate`; no second fulfillment |
| Out-of-order event | Resend an older subscription event | ledger reports stale event; newer state remains unchanged |
| Failed renewal | Use a Test Clock and failing renewal method | `payment-failed`; no new license period issued |
| Recovery | Replace payment method and retry invoice | paid event issues the recovered paid-through period once |
| End-of-period cancellation | Cancel in customer portal | no future renewal; current paid-through license stays valid |
| Refund | Refund the sandbox charge | ledger says manual review; no false instant-revocation claim |
| Dispute | Create sandbox dispute event | manual-review state and preserved evidence |
| Webhook outage | Stop listener, generate event, restart and resend | authenticated retry processes once |
| Forged/replayed webhook | Alter payload or use stale signature | HTTP 400; no ledger or license mutation |
| Live-mode attempt | supply live key/event fixture | rejected before Stripe action or state mutation |

## 5. Evidence and cleanup

Evidence remains local and ignored:

- `artifacts/billing-sandbox.db` — minimal event/subscription state, not raw Stripe payloads;
- `artifacts/billing-sandbox/licenses/` — synthetic test licenses;
- `artifacts/billing-sandbox/sandbox-signing-seed.hex` — disposable sandbox-only signer.

After all scenarios pass, rotate the Stripe test key and replace the webhook secret,
delete the ignored sandbox database/licenses/signer, and repeat the full matrix with the rotated
test credentials. Live mode still requires a separate founder preflight and all production
gates; this document intentionally contains no live-mode steps.

## Configuration and release status

The complete setting inventory is in [configuration](configuration.md). Test Price
expectations and website offer copy have separate owners; see [tiers](tiers.md).
All four provider settings (secret key, webhook secret and two Price IDs) must be
configured privately before recording a real-provider result. Public checkout stays
unavailable until the separate commercial gates are satisfied.

References: [Stripe test values](https://docs.stripe.com/testing),
[webhook handling](https://docs.stripe.com/webhooks), and
[subscription Test Clocks](https://docs.stripe.com/billing/testing/test-clocks).
