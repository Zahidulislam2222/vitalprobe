"""Stripe sandbox: hard live-mode stops and full synthetic lifecycle evidence."""

import hashlib
import hmac
import json
import time
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs

import httpx
import pytest
from fastapi.testclient import TestClient
from nacl.signing import SigningKey
from pydantic import SecretStr
from sqlalchemy.pool import StaticPool
from sqlmodel import create_engine

from vitalprobe.billing.fulfillment import SandboxFulfillmentError, parse_features
from vitalprobe.billing.models import BillingPlan, EntitlementState, WebhookOutcome
from vitalprobe.billing.service import BillingError, BillingSandboxService
from vitalprobe.billing.store import BillingStore
from vitalprobe.billing.stripe_client import StripeSandboxClient, StripeSandboxError
from vitalprobe.config import Settings
from vitalprobe.dashboard.app import create_app
from vitalprobe.entitlements.features import FeatureFlag
from vitalprobe.entitlements.license import verify_license
from vitalprobe.experience.store import ExperienceStore


def _settings(tmp_path: Path, **overrides: object) -> Settings:
    settings = Settings(
        _env_file=None,
        billing_sandbox_enabled=True,
        stripe_secret_key=SecretStr("sk_test_synthetic_only_key"),
        stripe_webhook_secret=SecretStr("whsec_test"),
        stripe_automated_price_id="price_test_automated",
        stripe_clinician_price_id="price_test_clinician",
        billing_db_path=tmp_path / "billing.db",
        billing_license_dir=tmp_path / "licenses",
        billing_sandbox_signing_seed_file=tmp_path / "sandbox-seed.hex",
    )
    return settings.model_copy(update=overrides)


def _store() -> BillingStore:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    return BillingStore(engine=engine)


def _stripe_transport(
    *, live_price: bool = False, live_session: bool = False
) -> httpx.MockTransport:
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET" and request.url.path.startswith("/v1/prices/"):
            amount = 7000 if request.url.path.endswith("price_test_clinician") else 5000
            return httpx.Response(
                200,
                json={
                    "id": request.url.path.rsplit("/", 1)[1],
                    "livemode": live_price,
                    "active": True,
                    "unit_amount": amount,
                    "currency": "usd",
                    "recurring": {"interval": "month", "interval_count": 1},
                },
            )
        if request.url.path == "/v1/checkout/sessions":
            form = parse_qs(request.content.decode("utf-8"))
            assert form["mode"] == ["subscription"]
            assert form["metadata[vitalprobe_sandbox]"] == ["true"]
            return httpx.Response(
                200,
                json={
                    "id": "cs_test_synthetic",
                    "url": "https://checkout.stripe.test/session",
                    "livemode": live_session,
                },
            )
        if request.url.path == "/v1/billing_portal/sessions":
            return httpx.Response(
                200,
                json={"url": "https://billing.stripe.test/portal", "livemode": False},
            )
        return httpx.Response(404, json={"error": {"code": "not_found"}})

    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_checkout_validates_test_price_amount_and_synthetic_identity(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    client = StripeSandboxClient(settings, transport=_stripe_transport())
    try:
        checkout = await client.create_checkout_session(
            BillingPlan.AUTOMATED,
            synthetic_email="buyer@example.com",
            success_url="http://127.0.0.1:8800/billing?ok=1",
            cancel_url="http://localhost:8800/billing?cancel=1",
        )
    finally:
        await client.aclose()
    assert checkout.session_id == "cs_test_synthetic"
    assert checkout.url.startswith("https://")


@pytest.mark.asyncio
async def test_checkout_rejects_live_key_price_session_and_real_email(tmp_path: Path) -> None:
    with pytest.raises(StripeSandboxError, match="requires an sk_test_"):
        StripeSandboxClient(
            _settings(tmp_path, stripe_secret_key=SecretStr("sk_live_never_allowed"))
        )

    settings = _settings(tmp_path)
    live_price_client = StripeSandboxClient(settings, transport=_stripe_transport(live_price=True))
    with pytest.raises(StripeSandboxError, match="live Stripe Prices"):
        await live_price_client.validate_price(BillingPlan.AUTOMATED)
    await live_price_client.aclose()

    live_session_client = StripeSandboxClient(
        settings, transport=_stripe_transport(live_session=True)
    )
    with pytest.raises(StripeSandboxError, match="live Checkout Sessions"):
        await live_session_client.create_checkout_session(
            BillingPlan.AUTOMATED,
            synthetic_email="buyer@example.com",
            success_url="http://localhost:8800/billing",
            cancel_url="http://localhost:8800/billing",
        )
    await live_session_client.aclose()

    email_client = StripeSandboxClient(settings, transport=_stripe_transport())
    with pytest.raises(StripeSandboxError, match="synthetic email"):
        await email_client.create_checkout_session(
            BillingPlan.AUTOMATED,
            synthetic_email="real-person@gmail.com",
            success_url="http://localhost:8800/billing",
            cancel_url="http://localhost:8800/billing",
        )
    await email_client.aclose()


@pytest.mark.asyncio
async def test_checkout_rejects_nonlocal_return_url(tmp_path: Path) -> None:
    client = StripeSandboxClient(_settings(tmp_path), transport=_stripe_transport())
    with pytest.raises(StripeSandboxError, match="localhost"):
        await client.create_checkout_session(
            BillingPlan.AUTOMATED,
            synthetic_email="buyer@example.com",
            success_url="https://public.example.com/success",
            cancel_url="http://localhost:8800/billing",
        )
    await client.aclose()


def _event_payload(
    event_id: str,
    event_type: str,
    obj: dict[str, Any],
    *,
    created: int,
    livemode: bool = False,
) -> bytes:
    return json.dumps(
        {
            "id": event_id,
            "type": event_type,
            "created": created,
            "livemode": livemode,
            "data": {"object": obj},
        },
        separators=(",", ":"),
    ).encode()


def _signature(payload: bytes, secret: str, timestamp: int) -> str:
    digest = hmac.new(
        secret.encode(), f"{timestamp}.".encode() + payload, hashlib.sha256
    ).hexdigest()
    return f"t={timestamp},v1={digest}"


async def _deliver(
    service: BillingSandboxService,
    event_id: str,
    event_type: str,
    obj: dict[str, Any],
    *,
    created: int,
    livemode: bool = False,
) -> WebhookOutcome:
    payload = _event_payload(event_id, event_type, obj, created=created, livemode=livemode)
    secret = service.settings.stripe_webhook_secret.get_secret_value()
    return await service.handle_webhook(payload, _signature(payload, secret, int(time.time())))


def _checkout_object() -> dict[str, Any]:
    return {
        "id": "cs_test_synthetic",
        "mode": "subscription",
        "subscription": "sub_synthetic",
        "customer": "cus_synthetic",
        "customer_details": {"email": "buyer@example.com"},
        "metadata": {"vitalprobe_sandbox": "true", "vitalprobe_plan": "automated"},
    }


def _subscription_object(period_end: int, status: str = "active") -> dict[str, Any]:
    return {
        "id": "sub_synthetic",
        "customer": "cus_synthetic",
        "status": status,
        "current_period_end": period_end,
        "cancel_at_period_end": status == "canceled",
        "metadata": {"vitalprobe_sandbox": "true", "vitalprobe_plan": "automated"},
        "items": {"data": [{"price": {"id": "price_test_automated"}}]},
    }


def _invoice_object(period_end: int) -> dict[str, Any]:
    return {
        "id": "in_synthetic",
        "subscription": "sub_synthetic",
        "customer": "cus_synthetic",
        "metadata": {"vitalprobe_sandbox": "true", "vitalprobe_plan": "automated"},
        "payments": {
            "data": [
                {
                    "payment": {
                        "type": "payment_intent",
                        "payment_intent": "pi_synthetic",
                        "charge": "ch_synthetic",
                    }
                }
            ]
        },
        "lines": {
            "data": [
                {
                    "price": {"id": "price_test_automated"},
                    "period": {"end": period_end},
                }
            ]
        },
    }


@pytest.mark.asyncio
async def test_webhook_lifecycle_is_idempotent_and_issues_paid_through_license(
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path)
    store = _store()
    service = BillingSandboxService(settings, store=store)
    now = int(time.time())
    paid_through = now + 30 * 24 * 60 * 60

    checkout = await _deliver(
        service, "evt_checkout", "checkout.session.completed", _checkout_object(), created=now
    )
    assert checkout.outcome == "checkout-recorded"
    await _deliver(
        service,
        "evt_subscription",
        "customer.subscription.created",
        _subscription_object(paid_through),
        created=now + 1,
    )
    paid = await _deliver(
        service, "evt_paid", "invoice.paid", _invoice_object(paid_through), created=now + 2
    )
    assert paid.outcome == "sandbox-license-issued"

    duplicate = await _deliver(
        service, "evt_paid", "invoice.paid", _invoice_object(paid_through), created=now + 2
    )
    assert duplicate.duplicate is True
    assert len(store.events()) == 3

    subscription = store.subscription("sub_synthetic")
    assert subscription is not None
    assert subscription.entitlement_state == EntitlementState.ACTIVE
    assert subscription.current_period_end == paid_through
    assert Path(subscription.license_path).is_file()
    seed = bytes.fromhex(settings.billing_sandbox_signing_seed_file.read_text().strip())
    public_key = SigningKey(seed).verify_key.encode().hex()
    verified = verify_license(Path(subscription.license_path), public_key_hex=public_key)
    assert verified.valid
    assert verified.tier == "sandbox-automated"
    assert verified.licensee is not None
    assert verified.licensee.startswith("SYNTHETIC TEST CUSTOMER")
    assert FeatureFlag.PRIVATE_PACKS in verified.features


@pytest.mark.asyncio
async def test_failure_cancellation_refund_and_stale_event_reconcile_honestly(
    tmp_path: Path,
) -> None:
    service = BillingSandboxService(settings := _settings(tmp_path), store=_store())
    now = int(time.time())
    paid_through = now + 3600
    await _deliver(
        service, "evt_checkout", "checkout.session.completed", _checkout_object(), created=now
    )
    await _deliver(
        service,
        "evt_sub",
        "customer.subscription.created",
        _subscription_object(paid_through),
        created=now + 1,
    )
    await _deliver(
        service, "evt_paid", "invoice.paid", _invoice_object(paid_through), created=now + 2
    )
    await _deliver(
        service,
        "evt_failed",
        "invoice.payment_failed",
        {**_invoice_object(paid_through), "id": "in_failed_renewal"},
        created=now + 3,
    )
    row = service.store.subscription("sub_synthetic")
    assert row is not None and row.entitlement_state == EntitlementState.PAYMENT_FAILED
    license_path = row.license_path

    cancelled = _subscription_object(paid_through, status="canceled")
    await _deliver(
        service,
        "evt_cancelled",
        "customer.subscription.deleted",
        cancelled,
        created=now + 4,
    )
    row = service.store.subscription("sub_synthetic")
    assert row is not None and row.entitlement_state == EntitlementState.ACTIVE
    assert row.license_path == license_path

    # Real refund/dispute payloads need not repeat Checkout metadata. The paid
    # invoice's non-sensitive payment IDs provide the reconciliation link.
    refund = {"id": "re_synthetic", "payment_intent": "pi_synthetic"}
    outcome = await _deliver(service, "evt_refund", "refund.created", refund, created=now + 5)
    assert outcome.outcome == "manual-review-offline-license-not-revoked"
    row = service.store.subscription("sub_synthetic")
    assert row is not None and row.entitlement_state == EntitlementState.MANUAL_REVIEW
    assert Path(row.license_path).is_file()

    dispute = {"id": "dp_synthetic", "charge": "ch_synthetic"}
    disputed = await _deliver(
        service,
        "evt_dispute",
        "charge.dispute.created",
        dispute,
        created=now + 6,
    )
    assert disputed.outcome == "manual-review-offline-license-not-revoked"

    stale = await _deliver(
        service,
        "evt_stale",
        "customer.subscription.updated",
        _subscription_object(paid_through, status="active"),
        created=now + 1,
    )
    assert stale.outcome == "ignored-stale-event"
    assert settings.billing_sandbox_enabled


@pytest.mark.asyncio
async def test_unmatched_refund_is_recorded_for_manual_reconciliation(tmp_path: Path) -> None:
    service = BillingSandboxService(_settings(tmp_path), store=_store())
    outcome = await _deliver(
        service,
        "evt_unmatched_refund",
        "refund.created",
        {"id": "re_unknown", "payment_intent": "pi_unknown"},
        created=int(time.time()),
    )
    assert outcome.outcome == "manual-review-unmatched-payment-event"


@pytest.mark.asyncio
async def test_webhook_rejects_live_bad_signature_stale_and_non_synthetic_data(
    tmp_path: Path,
) -> None:
    service = BillingSandboxService(_settings(tmp_path), store=_store())
    now = int(time.time())
    payload = _event_payload(
        "evt_live", "checkout.session.completed", _checkout_object(), created=now, livemode=True
    )
    secret = service.settings.stripe_webhook_secret.get_secret_value()
    with pytest.raises(BillingError, match="live-mode"):
        await service.handle_webhook(payload, _signature(payload, secret, now))
    with pytest.raises(BillingError, match="signature is invalid"):
        await service.handle_webhook(
            payload.replace(b"true", b"false"), _signature(payload, secret, now)
        )
    with pytest.raises(BillingError, match="outside tolerance"):
        await service.handle_webhook(payload, _signature(payload, secret, now - 9999))

    real_identity = _checkout_object()
    real_identity["customer_details"] = {"email": "person@gmail.com"}
    with pytest.raises(BillingError, match="synthetic email"):
        await _deliver(
            service,
            "evt_real_identity",
            "checkout.session.completed",
            real_identity,
            created=now,
        )


def test_local_ledger_does_not_store_raw_synthetic_email(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    store = BillingStore(settings.billing_db_path)
    email = "buyer@example.com"
    store.upsert_subscription(
        subscription_id="sub_synthetic",
        customer_id="cus_synthetic",
        email_hash=hashlib.sha256(email.encode()).hexdigest(),
        plan=BillingPlan.AUTOMATED,
        price_id="price_test_automated",
        status="active",
        current_period_end=int(time.time()) + 3600,
        cancel_at_period_end=False,
        entitlement_state=EntitlementState.ACTIVE,
        event_id="evt_synthetic",
        event_created=int(time.time()),
    )
    assert email.encode() not in settings.billing_db_path.read_bytes()


def test_feature_parser_rejects_empty_or_unknown_configuration() -> None:
    with pytest.raises(SandboxFulfillmentError, match="cannot be empty"):
        parse_features("")
    with pytest.raises(SandboxFulfillmentError, match="unknown sandbox feature"):
        parse_features("made_up_feature")


def _experience_store() -> ExperienceStore:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    return ExperienceStore(engine=engine)


def test_dashboard_billing_page_is_disabled_by_default() -> None:
    settings = Settings(_env_file=None)
    client = TestClient(
        create_app(_experience_store(), settings=settings),
        base_url="http://127.0.0.1:8800",
        client=("127.0.0.1", 50000),
    )
    page = client.get("/billing")
    assert page.status_code == 200
    assert "$0 technical validation only" in page.text
    assert "missing / disabled" in page.text
    assert client.post("/billing/webhook", content=b"{}").status_code == 404


def test_dashboard_creates_checkout_and_rejects_cross_site_form(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    stripe_client = StripeSandboxClient(settings, transport=_stripe_transport())
    service = BillingSandboxService(settings, store=_store(), client=stripe_client)
    client = TestClient(
        create_app(_experience_store(), settings=settings, billing=service),
        base_url="http://127.0.0.1:8800",
        client=("127.0.0.1", 50000),
    )
    response = client.post(
        "/billing/checkout",
        data={"plan": "automated", "synthetic_email": "buyer@example.com"},
    )
    assert response.status_code == 200
    assert "continue in Stripe test mode" in response.text
    blocked = client.post(
        "/billing/checkout",
        data={"plan": "automated", "synthetic_email": "buyer@example.com"},
        headers={"origin": "https://attacker.example"},
    )
    assert blocked.status_code == 403


def test_dashboard_webhook_authenticates_and_deduplicates(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    service = BillingSandboxService(settings, store=_store())
    client = TestClient(
        create_app(_experience_store(), settings=settings, billing=service),
        base_url="http://127.0.0.1:8800",
        client=("127.0.0.1", 50000),
    )
    now = int(time.time())
    payload = _event_payload(
        "evt_dashboard",
        "checkout.session.completed",
        _checkout_object(),
        created=now,
    )
    signature = _signature(payload, settings.stripe_webhook_secret.get_secret_value(), now)
    first = client.post(
        "/billing/webhook",
        content=payload,
        headers={"stripe-signature": signature},
    )
    assert first.status_code == 200
    assert first.json()["outcome"] == "checkout-recorded"
    duplicate = client.post(
        "/billing/webhook",
        content=payload,
        headers={"stripe-signature": signature},
    )
    assert duplicate.status_code == 200
    assert duplicate.json()["duplicate"] is True


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "recurring",
    [
        {"interval": "year", "interval_count": 1},
        {"interval": "month", "interval_count": 2},
    ],
)
async def test_checkout_rejects_wrong_billing_cadence(
    tmp_path: Path, recurring: dict[str, object]
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "id": "price_test_automated",
                "livemode": False,
                "active": True,
                "unit_amount": 5000,
                "currency": "usd",
                "recurring": recurring,
            },
        )

    client = StripeSandboxClient(_settings(tmp_path), transport=httpx.MockTransport(handler))
    try:
        with pytest.raises(StripeSandboxError, match="interval"):
            await client.validate_price(BillingPlan.AUTOMATED)
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_delayed_checkout_preserves_paid_entitlement(tmp_path: Path) -> None:
    service = BillingSandboxService(_settings(tmp_path), store=_store())
    now = int(time.time())
    await _deliver(
        service, "evt_checkout", "checkout.session.completed", _checkout_object(), created=now
    )
    await _deliver(
        service, "evt_paid", "invoice.paid", _invoice_object(now + 3600), created=now + 1
    )
    await _deliver(
        service,
        "evt_checkout_delayed",
        "checkout.session.completed",
        _checkout_object(),
        created=now + 1,
    )
    row = service.store.subscription("sub_synthetic")
    assert row is not None
    assert row.entitlement_state == EntitlementState.ACTIVE


@pytest.mark.asyncio
async def test_refund_review_survives_subscription_update(tmp_path: Path) -> None:
    service = BillingSandboxService(_settings(tmp_path), store=_store())
    now = int(time.time())
    await _deliver(
        service, "evt_checkout", "checkout.session.completed", _checkout_object(), created=now
    )
    await _deliver(
        service, "evt_paid", "invoice.paid", _invoice_object(now + 3600), created=now + 1
    )
    await _deliver(
        service,
        "evt_refund",
        "refund.created",
        {"id": "re_synthetic", "payment_intent": "pi_synthetic"},
        created=now + 2,
    )
    await _deliver(
        service,
        "evt_updated",
        "customer.subscription.updated",
        _subscription_object(now + 3600),
        created=now + 3,
    )
    row = service.store.subscription("sub_synthetic")
    assert row is not None
    assert row.entitlement_state == EntitlementState.MANUAL_REVIEW


@pytest.mark.asyncio
async def test_webhook_nonascii_signature_is_safe_rejection(tmp_path: Path) -> None:
    service = BillingSandboxService(_settings(tmp_path), store=_store())
    payload = _event_payload(
        "evt_bad", "checkout.session.completed", _checkout_object(), created=int(time.time())
    )
    with pytest.raises(BillingError, match="signature is invalid"):
        await service.handle_webhook(payload, f"t={int(time.time())},v1=é")


@pytest.mark.asyncio
async def test_paid_invoice_retries_after_newer_subscription_snapshot(tmp_path: Path) -> None:
    service = BillingSandboxService(_settings(tmp_path), store=_store())
    now = int(time.time())
    invoice = _invoice_object(now + 3600)
    with pytest.raises(BillingError, match="before its sandbox subscription"):
        await _deliver(service, "evt_early_paid", "invoice.paid", invoice, created=now)
    await _deliver(
        service, "evt_checkout", "checkout.session.completed", _checkout_object(), created=now + 1
    )
    outcome = await _deliver(service, "evt_early_paid", "invoice.paid", invoice, created=now)
    assert outcome.outcome == "sandbox-license-issued"


@pytest.mark.asyncio
async def test_refund_hold_survives_failure_then_recovery(tmp_path: Path) -> None:
    service = BillingSandboxService(_settings(tmp_path), store=_store())
    now = int(time.time())
    await _deliver(
        service, "evt_checkout", "checkout.session.completed", _checkout_object(), created=now
    )
    await _deliver(
        service, "evt_paid", "invoice.paid", _invoice_object(now + 3600), created=now + 1
    )
    await _deliver(
        service,
        "evt_refund",
        "refund.created",
        {"id": "re_synthetic", "payment_intent": "pi_synthetic"},
        created=now + 2,
    )
    await _deliver(
        service,
        "evt_failed",
        "invoice.payment_failed",
        _invoice_object(now + 3600),
        created=now + 3,
    )
    await _deliver(
        service, "evt_recovery", "invoice.paid", _invoice_object(now + 3600), created=now + 4
    )
    row = service.store.subscription("sub_synthetic")
    assert row is not None and row.entitlement_state == EntitlementState.MANUAL_REVIEW


@pytest.mark.asyncio
async def test_equal_timestamp_failure_does_not_undo_paid_invoice(tmp_path: Path) -> None:
    service = BillingSandboxService(_settings(tmp_path), store=_store())
    now = int(time.time())
    await _deliver(
        service, "evt_checkout", "checkout.session.completed", _checkout_object(), created=now
    )
    await _deliver(
        service, "evt_paid", "invoice.paid", _invoice_object(now + 3600), created=now + 1
    )
    await _deliver(
        service,
        "evt_failed",
        "invoice.payment_failed",
        _invoice_object(now + 3600),
        created=now + 1,
    )
    row = service.store.subscription("sub_synthetic")
    assert row is not None and row.entitlement_state == EntitlementState.ACTIVE


@pytest.mark.asyncio
async def test_price_change_takes_precedence_over_checkout_metadata(tmp_path: Path) -> None:
    service = BillingSandboxService(_settings(tmp_path), store=_store())
    now = int(time.time())
    await _deliver(
        service, "evt_checkout", "checkout.session.completed", _checkout_object(), created=now
    )
    obj = _subscription_object(now + 3600)
    obj["items"] = {"data": [{"price": {"id": "price_test_clinician"}}]}
    await _deliver(service, "evt_upgrade", "customer.subscription.updated", obj, created=now + 1)
    row = service.store.subscription("sub_synthetic")
    assert row is not None and row.plan == BillingPlan.CLINICIAN


@pytest.mark.asyncio
async def test_unmatched_refund_is_retryable_after_payment_mapping(tmp_path: Path) -> None:
    service = BillingSandboxService(_settings(tmp_path), store=_store())
    now = int(time.time())
    refund = {"id": "re_synthetic", "payment_intent": "pi_synthetic"}
    first = await _deliver(service, "evt_early_refund", "refund.created", refund, created=now + 2)
    assert first.outcome == "manual-review-unmatched-payment-event"
    await _deliver(
        service, "evt_checkout", "checkout.session.completed", _checkout_object(), created=now
    )
    await _deliver(
        service, "evt_paid", "invoice.paid", _invoice_object(now + 3600), created=now + 1
    )
    retried = await _deliver(service, "evt_early_refund", "refund.created", refund, created=now + 2)
    assert retried.outcome == "manual-review-offline-license-not-revoked"


@pytest.mark.asyncio
async def test_interrupted_event_claim_recovers_after_lease(tmp_path: Path) -> None:
    from sqlmodel import Session

    from vitalprobe.billing.service import BillingRetryError
    from vitalprobe.billing.store import BillingEventRecord

    settings = _settings(tmp_path)
    store = _store()
    service = BillingSandboxService(settings, store=store)
    now = int(time.time())
    assert store.claim_event(
        "evt_interrupted",
        "checkout.session.completed",
        now,
        "cs_test_synthetic",
        lease_s=settings.stripe_processing_lease_s,
    )
    with pytest.raises(BillingRetryError):
        await _deliver(
            service,
            "evt_interrupted",
            "checkout.session.completed",
            _checkout_object(),
            created=now,
        )
    with Session(store.engine) as session:
        row = session.get(BillingEventRecord, 1)
        assert row is not None
        row.processed_at = "2000-01-01T00:00:00+00:00"
        session.add(row)
        session.commit()
    retried = await _deliver(
        service, "evt_interrupted", "checkout.session.completed", _checkout_object(), created=now
    )
    assert retried.outcome == "checkout-recorded"


@pytest.mark.asyncio
async def test_unexpanded_invoice_fetches_payment_refs_before_fulfillment(tmp_path: Path) -> None:
    now = int(time.time())
    invoice = _invoice_object(now + 3600)
    expanded = {**invoice, "livemode": False}
    del invoice["payments"]
    requests: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(str(request.url))
        return httpx.Response(200, json=expanded)

    settings = _settings(tmp_path)
    client = StripeSandboxClient(settings, transport=httpx.MockTransport(handler))
    service = BillingSandboxService(settings, store=_store(), client=client)
    try:
        await _deliver(
            service, "evt_checkout", "checkout.session.completed", _checkout_object(), created=now
        )
        outcome = await _deliver(service, "evt_paid", "invoice.paid", invoice, created=now + 1)
        assert outcome.outcome == "sandbox-license-issued"
        assert "expand" in requests[0]
        mapped = service.store.subscription_for_payment(payment_intent_id="pi_synthetic")
        assert mapped == "sub_synthetic"
    finally:
        await service.aclose()


def test_enabled_billing_rejects_nonlocal_host_and_peer(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    service = BillingSandboxService(settings, store=_store())
    app = create_app(_experience_store(), settings=settings, billing=service)
    with TestClient(app, base_url="http://attacker.example", client=("127.0.0.1", 50000)) as client:
        assert client.get("/billing").status_code == 403
    with TestClient(app, base_url="http://localhost", client=("192.0.2.1", 50000)) as client:
        assert client.get("/billing").status_code == 403


def test_billing_sandbox_rejects_public_bind() -> None:
    with pytest.raises(ValueError, match="loopback"):
        Settings(_env_file=None, billing_sandbox_enabled=True, dashboard_host="192.0.2.1")


@pytest.mark.asyncio
async def test_same_timestamp_snapshot_cannot_clear_cancellation(tmp_path: Path) -> None:
    service = BillingSandboxService(_settings(tmp_path), store=_store())
    now = int(time.time())
    await _deliver(
        service, "evt_checkout", "checkout.session.completed", _checkout_object(), created=now - 1
    )
    obj = _subscription_object(now + 3600, "canceled")
    obj["cancel_at_period_end"] = True
    await _deliver(service, "evt_cancel", "customer.subscription.updated", obj, created=now)
    obj["cancel_at_period_end"] = False
    obj["status"] = "active"
    await _deliver(service, "evt_old_snapshot", "customer.subscription.updated", obj, created=now)
    row = service.store.subscription("sub_synthetic")
    assert row is not None and row.cancel_at_period_end
    assert row.status == "canceled"
    await _deliver(
        service, "evt_equal_paid", "invoice.paid", _invoice_object(now + 3600), created=now
    )
    row = service.store.subscription("sub_synthetic")
    assert row is not None and row.status == "canceled" and row.cancel_at_period_end


@pytest.mark.asyncio
async def test_paid_renewal_uses_license_expiry_not_unpaid_snapshot(tmp_path: Path) -> None:
    service = BillingSandboxService(_settings(tmp_path), store=_store())
    now = int(time.time())
    await _deliver(
        service, "evt_checkout", "checkout.session.completed", _checkout_object(), created=now
    )
    await _deliver(
        service, "evt_paid_first", "invoice.paid", _invoice_object(now + 3600), created=now + 1
    )
    await _deliver(
        service,
        "evt_future_snapshot",
        "customer.subscription.updated",
        _subscription_object(now + 10800, "past_due"),
        created=now + 3,
    )
    invoice = {**_invoice_object(now + 7200), "id": "in_second_paid"}
    outcome = await _deliver(service, "evt_renewal", "invoice.paid", invoice, created=now + 2)
    assert outcome.outcome == "sandbox-license-issued"
    row = service.store.subscription("sub_synthetic")
    assert row is not None
    assert row.current_period_end == now + 10800
    document = json.loads(Path(row.license_path).read_text(encoding="utf-8"))
    from datetime import datetime

    assert int(datetime.fromisoformat(document["expires_at"]).timestamp()) == now + 7200


@pytest.mark.asyncio
async def test_portal_rejects_unrecorded_customer_before_network(tmp_path: Path) -> None:
    service = BillingSandboxService(_settings(tmp_path), store=_store())
    with pytest.raises(BillingError, match="verified synthetic"):
        await service.create_portal("cus_unrecorded", "http://localhost/billing")


@pytest.mark.asyncio
async def test_delayed_invoice_preserves_cancellation(tmp_path: Path) -> None:
    service = BillingSandboxService(_settings(tmp_path), store=_store())
    now = int(time.time())
    await _deliver(
        service, "evt_checkout", "checkout.session.completed", _checkout_object(), created=now
    )
    obj = _subscription_object(now + 3600)
    obj["cancel_at_period_end"] = True
    await _deliver(service, "evt_cancel", "customer.subscription.updated", obj, created=now + 2)
    await _deliver(
        service, "evt_paid", "invoice.paid", _invoice_object(now + 3600), created=now + 1
    )
    row = service.store.subscription("sub_synthetic")
    assert row is not None and row.cancel_at_period_end


@pytest.mark.asyncio
async def test_paid_entitlement_survives_same_timestamp_subscription_failure(
    tmp_path: Path,
) -> None:
    service = BillingSandboxService(_settings(tmp_path), store=_store())
    now = int(time.time())
    await _deliver(
        service, "evt_checkout", "checkout.session.completed", _checkout_object(), created=now
    )
    await _deliver(
        service, "evt_paid", "invoice.paid", _invoice_object(now + 3600), created=now + 1
    )
    await _deliver(
        service,
        "evt_snapshot",
        "customer.subscription.updated",
        _subscription_object(now + 3600, "past_due"),
        created=now + 1,
    )
    row = service.store.subscription("sub_synthetic")
    assert row is not None and row.entitlement_state == EntitlementState.ACTIVE
