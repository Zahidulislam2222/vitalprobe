"""Stripe sandbox orchestration: checkout, authenticated events, and local fulfillment."""

import hashlib
import json
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from vitalprobe.billing.fulfillment import (
    SandboxFulfillmentError,
    SandboxLicenseIssuer,
    parse_features,
)
from vitalprobe.billing.models import BillingPlan, CheckoutSession, EntitlementState, WebhookOutcome
from vitalprobe.billing.store import BillingEventBusyError, BillingStore, BillingSubscriptionRecord
from vitalprobe.billing.stripe_client import (
    StripeSandboxClient,
    StripeSandboxError,
    require_synthetic_email,
)
from vitalprobe.billing.webhooks import (
    WebhookVerificationError,
    object_from_event,
    verify_signature,
)
from vitalprobe.config import Settings

_PAYMENT_REVIEW_EVENT_TYPES = {
    "charge.refunded",
    "refund.created",
    "charge.dispute.created",
    "charge.dispute.closed",
}


class BillingError(Exception):
    """Safe billing-sandbox error for CLI/dashboard display."""


class BillingRetryError(BillingError):
    """Temporary processing conflict; return a retryable HTTP response."""


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _metadata(obj: Mapping[str, Any]) -> Mapping[str, Any]:
    direct = _mapping(obj.get("metadata"))
    if direct:
        return direct
    parent = _mapping(obj.get("parent"))
    details = _mapping(parent.get("subscription_details"))
    return _mapping(details.get("metadata"))


def _subscription_id(obj: Mapping[str, Any], event_type: str) -> str:
    if event_type.startswith("customer.subscription."):
        return str(obj.get("id", ""))
    direct = obj.get("subscription")
    if isinstance(direct, str):
        return direct
    parent = _mapping(obj.get("parent"))
    details = _mapping(parent.get("subscription_details"))
    nested = details.get("subscription")
    if isinstance(nested, str):
        return nested
    metadata_value = _metadata(obj).get("vitalprobe_subscription_id")
    return str(metadata_value) if metadata_value else ""


def _price_id(obj: Mapping[str, Any]) -> str:
    items = _mapping(obj.get("items"))
    lines = _mapping(obj.get("lines"))
    for collection in (items, lines):
        data = collection.get("data")
        if not isinstance(data, list):
            continue
        for item in data:
            item_map = _mapping(item)
            price = _mapping(item_map.get("price"))
            price_id = price.get("id")
            if isinstance(price_id, str):
                return price_id
            pricing = _mapping(item_map.get("pricing"))
            price_details = _mapping(pricing.get("price_details"))
            price_id = price_details.get("price")
            if isinstance(price_id, str):
                return price_id
    return ""


def _period_end(obj: Mapping[str, Any]) -> int:
    direct = obj.get("current_period_end")
    if isinstance(direct, int):
        return direct
    found: list[int] = []
    for key in ("items", "lines"):
        data = _mapping(obj.get(key)).get("data")
        if not isinstance(data, list):
            continue
        for item in data:
            item_map = _mapping(item)
            candidate = item_map.get("current_period_end")
            if isinstance(candidate, int):
                found.append(candidate)
            period = _mapping(item_map.get("period"))
            end = period.get("end")
            if isinstance(end, int):
                found.append(end)
    return max(found, default=0)


def _synthetic_email(obj: Mapping[str, Any]) -> str:
    details = _mapping(obj.get("customer_details"))
    candidates = [
        details.get("email"),
        obj.get("customer_email"),
        obj.get("receipt_email"),
        _metadata(obj).get("synthetic_email"),
    ]
    for candidate in candidates:
        if isinstance(candidate, str) and candidate:
            return require_synthetic_email(candidate)
    return ""


def _email_hash(email: str) -> str:
    return hashlib.sha256(email.encode("utf-8")).hexdigest() if email else ""


def _issued_paid_through(license_path: str) -> int:
    if not license_path:
        return 0
    try:
        payload = json.loads(Path(license_path).read_text(encoding="utf-8"))
        return int(datetime.fromisoformat(payload["expires_at"]).timestamp())
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise BillingError(
            "existing sandbox license expiry is unreadable; reconcile locally"
        ) from exc


def _stripe_id(value: object, prefix: str) -> str:
    if isinstance(value, str) and value.startswith(prefix):
        return value
    mapped = _mapping(value)
    identifier = mapped.get("id")
    return identifier if isinstance(identifier, str) and identifier.startswith(prefix) else ""


def _payment_ids(obj: Mapping[str, Any]) -> tuple[str, str]:
    """Extract modern and legacy invoice/refund/dispute payment references."""
    payment_intent_id = _stripe_id(obj.get("payment_intent"), "pi_")
    charge_id = _stripe_id(obj.get("charge"), "ch_")
    if not charge_id:
        charge_id = _stripe_id(obj.get("latest_charge"), "ch_")
    object_id = obj.get("id")
    if not payment_intent_id:
        payment_intent_id = _stripe_id(object_id, "pi_")
    if not charge_id:
        charge_id = _stripe_id(object_id, "ch_")

    payments = _mapping(obj.get("payments")).get("data")
    if isinstance(payments, list):
        for item in payments:
            item_map = _mapping(item)
            payment = _mapping(item_map.get("payment"))
            if not payment_intent_id:
                payment_intent_id = _stripe_id(
                    payment.get("payment_intent") or item_map.get("payment_intent"), "pi_"
                )
            if not charge_id:
                charge_id = _stripe_id(payment.get("charge") or item_map.get("charge"), "ch_")
            if not charge_id:
                intent = _mapping(payment.get("payment_intent"))
                charge_id = _stripe_id(intent.get("latest_charge"), "ch_")
    return payment_intent_id, charge_id


class BillingSandboxService:
    """Opt-in sandbox. It cannot accept a live key, live event, or non-synthetic email."""

    def __init__(
        self,
        settings: Settings,
        *,
        store: BillingStore | None = None,
        issuer: SandboxLicenseIssuer | None = None,
        client: StripeSandboxClient | None = None,
    ) -> None:
        self.settings = settings
        self.store = store or BillingStore(settings.billing_db_path)
        self.issuer = issuer or SandboxLicenseIssuer(
            settings.billing_sandbox_signing_seed_file,
            settings.billing_license_dir,
        )
        self._client = client

    def _require_enabled(self) -> None:
        if not self.settings.billing_sandbox_enabled:
            raise BillingError("Stripe sandbox is disabled")

    def configuration_status(self) -> dict[str, bool]:
        key = self.settings.stripe_secret_key.get_secret_value()
        webhook = self.settings.stripe_webhook_secret.get_secret_value()
        return {
            "enabled": self.settings.billing_sandbox_enabled,
            "test_key": key.startswith(("sk_test_", "rk_test_")),
            "webhook_secret": webhook.startswith("whsec_"),
            "automated_price": self.settings.stripe_automated_price_id.startswith("price_"),
            "clinician_price": self.settings.stripe_clinician_price_id.startswith("price_"),
        }

    def _stripe(self) -> StripeSandboxClient:
        self._require_enabled()
        if self._client is None:
            try:
                self._client = StripeSandboxClient(self.settings)
            except StripeSandboxError as exc:
                raise BillingError(str(exc)) from None
        return self._client

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()

    async def create_checkout(
        self,
        plan: BillingPlan,
        *,
        synthetic_email: str,
        success_url: str,
        cancel_url: str,
    ) -> CheckoutSession:
        try:
            return await self._stripe().create_checkout_session(
                plan,
                synthetic_email=synthetic_email,
                success_url=success_url,
                cancel_url=cancel_url,
            )
        except StripeSandboxError as exc:
            raise BillingError(str(exc)) from None

    async def create_portal(self, customer_id: str, return_url: str) -> str:
        self._require_enabled()
        if not any(
            row.stripe_customer_id == customer_id and row.synthetic_email_hash
            for row in self.store.subscriptions()
        ):
            raise BillingError("portal requires a locally verified synthetic customer")
        try:
            return await self._stripe().create_portal_session(customer_id, return_url)
        except StripeSandboxError as exc:
            raise BillingError(str(exc)) from None

    def _plan(
        self,
        obj: Mapping[str, Any],
        existing: BillingSubscriptionRecord | None,
    ) -> BillingPlan:
        price = _price_id(obj)
        if price:
            if price == self.settings.stripe_automated_price_id:
                return BillingPlan.AUTOMATED
            if price == self.settings.stripe_clinician_price_id:
                return BillingPlan.CLINICIAN
            raise BillingError("Stripe event has an unconfigured sandbox Price")
        plan_value = _metadata(obj).get("vitalprobe_plan")
        if isinstance(plan_value, str):
            try:
                return BillingPlan(plan_value)
            except ValueError:
                pass
        if existing is not None:
            return BillingPlan(existing.plan)
        raise BillingError("Stripe event does not map to a configured sandbox plan")

    def _features(self, plan: BillingPlan) -> str:
        if plan is BillingPlan.AUTOMATED:
            return self.settings.billing_automated_features
        return self.settings.billing_clinician_features

    def _event_allowed(
        self, obj: Mapping[str, Any], existing: BillingSubscriptionRecord | None
    ) -> bool:
        return _metadata(obj).get("vitalprobe_sandbox") == "true" or existing is not None

    async def handle_webhook(self, payload: bytes, signature_header: str) -> WebhookOutcome:
        self._require_enabled()
        try:
            event = verify_signature(
                payload,
                signature_header,
                self.settings.stripe_webhook_secret.get_secret_value(),
                tolerance_s=self.settings.stripe_webhook_tolerance_s,
            )
            obj = object_from_event(event)
            if obj.get("livemode") is True:
                raise WebhookVerificationError("live-mode Stripe objects are rejected")
        except WebhookVerificationError as exc:
            raise BillingError(str(exc)) from None
        event_id = str(event.get("id", ""))
        event_type = str(event.get("type", ""))
        event_created = event.get("created")
        if not event_id.startswith("evt_") or not event_type or not isinstance(event_created, int):
            raise BillingError("Stripe event identity is missing")
        object_id = str(obj.get("id", ""))
        try:
            claimed = self.store.claim_event(
                event_id,
                event_type,
                event_created,
                object_id,
                lease_s=self.settings.stripe_processing_lease_s,
            )
        except BillingEventBusyError as exc:
            raise BillingRetryError(str(exc)) from None
        if not claimed:
            return WebhookOutcome(event_id, event_type, "duplicate", duplicate=True)
        try:
            if event_type == "invoice.paid" and not any(_payment_ids(obj)):
                expanded = await self._stripe().retrieve_invoice_payment_refs(object_id)
                obj = {**obj, "payments": expanded.get("payments", {})}
                if not any(_payment_ids(obj)):
                    raise BillingError("sandbox invoice payment references are not available yet")
            outcome = self._apply_event(event_id, event_type, event_created, obj)
        except (BillingError, SandboxFulfillmentError, StripeSandboxError, ValueError) as exc:
            self.store.complete_event(event_id, "error", type(exc).__name__)
            raise BillingError(str(exc)) from None
        retryable = outcome == "manual-review-unmatched-payment-event"
        self.store.complete_event(event_id, "retry-required" if retryable else outcome)
        return WebhookOutcome(event_id, event_type, outcome)

    def _apply_event(
        self,
        event_id: str,
        event_type: str,
        event_created: int,
        obj: Mapping[str, Any],
    ) -> str:
        subscription_id = _subscription_id(obj, event_type)
        if event_type == "checkout.session.completed":
            subscription_id = str(obj.get("subscription", ""))
        if not subscription_id and event_type in _PAYMENT_REVIEW_EVENT_TYPES:
            payment_intent_id, charge_id = _payment_ids(obj)
            subscription_id = self.store.subscription_for_payment(
                payment_intent_id=payment_intent_id,
                charge_id=charge_id,
            )
        existing = self.store.subscription(subscription_id) if subscription_id else None
        if not self._event_allowed(obj, existing):
            if event_type in _PAYMENT_REVIEW_EVENT_TYPES:
                self.store.record_pending_review(event_id, *_payment_ids(obj))
                return "manual-review-unmatched-payment-event"
            return "ignored-non-sandbox-object"
        if (
            existing is not None
            and event_created < existing.last_event_created
            and event_type not in _PAYMENT_REVIEW_EVENT_TYPES | {"invoice.paid"}
        ):
            return "ignored-stale-event"

        if event_type == "checkout.session.completed":
            if not subscription_id.startswith("sub_") or obj.get("mode") != "subscription":
                raise BillingError("sandbox Checkout Session has no subscription")
            email = _synthetic_email(obj)
            if not email:
                raise BillingError("sandbox Checkout Session has no synthetic email")
            if existing is not None:
                return "checkout-already-recorded"
            plan = self._plan(obj, existing)
            self.store.upsert_subscription(
                subscription_id=subscription_id,
                customer_id=str(obj.get("customer", "")),
                email_hash=_email_hash(email),
                plan=plan,
                price_id="",
                status="checkout-complete",
                current_period_end=0,
                cancel_at_period_end=False,
                entitlement_state=EntitlementState.PENDING,
                event_id=event_id,
                event_created=event_created,
            )
            return "checkout-recorded"

        if event_type.startswith("customer.subscription."):
            if not subscription_id.startswith("sub_"):
                raise BillingError("sandbox subscription event has no subscription id")
            plan = self._plan(obj, existing)
            status = str(obj.get("status", "unknown"))
            if (
                existing is not None
                and event_created <= existing.last_event_created
                and existing.status in {"canceled", "unpaid", "incomplete_expired"}
            ):
                status = existing.status
            period_end = _period_end(obj)
            if (
                existing is not None
                and existing.entitlement_state == EntitlementState.MANUAL_REVIEW
            ):
                state = EntitlementState.MANUAL_REVIEW
            elif status in {"canceled", "unpaid", "incomplete_expired"}:
                state = (
                    EntitlementState.ACTIVE
                    if period_end > int(datetime.now(UTC).timestamp())
                    else EntitlementState.ENDED
                )
            elif (
                existing is not None
                and existing.license_path
                and event_created <= existing.last_event_created
                and existing.entitlement_state == EntitlementState.ACTIVE
            ):
                state = EntitlementState.ACTIVE
            elif status in {"past_due", "incomplete", "paused"}:
                state = EntitlementState.PAYMENT_FAILED
            elif existing is not None and existing.license_path:
                state = EntitlementState.ACTIVE
            else:
                state = EntitlementState.PENDING
            self.store.upsert_subscription(
                subscription_id=subscription_id,
                customer_id=str(obj.get("customer", "")),
                email_hash=existing.synthetic_email_hash if existing else "",
                plan=plan,
                price_id=_price_id(obj),
                status=status,
                current_period_end=period_end,
                cancel_at_period_end=(
                    bool(obj.get("cancel_at_period_end", False))
                    or (
                        existing is not None
                        and event_created <= existing.last_event_created
                        and existing.cancel_at_period_end
                    )
                ),
                entitlement_state=state,
                event_id=event_id,
                event_created=event_created,
            )
            return "subscription-reconciled"

        if event_type == "invoice.paid":
            if existing is None:
                raise BillingError("paid invoice arrived before its sandbox subscription")
            if existing.entitlement_state == EntitlementState.MANUAL_REVIEW:
                return "manual-review-issuance-held"
            if self.store.payment_for_invoice(str(obj.get("id", ""))) is not None:
                return "invoice-already-fulfilled"
            plan = self._plan(obj, existing)
            paid_through = _period_end(obj) or existing.current_period_end
            if paid_through < _issued_paid_through(existing.license_path):
                return "ignored-stale-paid-period"
            if not existing.synthetic_email_hash:
                email = _synthetic_email(obj)
                email_hash = _email_hash(email)
            else:
                email_hash = existing.synthetic_email_hash
            if not email_hash:
                raise BillingError("paid invoice has no synthetic customer identity")
            payment_intent_id, charge_id = _payment_ids(obj)
            if self.store.has_pending_review(payment_intent_id, charge_id):
                self.store.record_payment_mapping(
                    invoice_id=str(obj.get("id", "")),
                    subscription_id=subscription_id,
                    payment_intent_id=payment_intent_id,
                    charge_id=charge_id,
                )
                self.store.upsert_subscription(
                    subscription_id=subscription_id,
                    customer_id=existing.stripe_customer_id,
                    email_hash=email_hash,
                    plan=plan,
                    price_id=_price_id(obj),
                    status="payment-risk-review",
                    current_period_end=paid_through,
                    cancel_at_period_end=existing.cancel_at_period_end,
                    entitlement_state=EntitlementState.MANUAL_REVIEW,
                    event_id=event_id,
                    event_created=event_created,
                    accept_older_event=True,
                )
                return "manual-review-issuance-held"
            issued = self.issuer.issue(
                subscription_id=subscription_id,
                email_hash=email_hash,
                plan=plan,
                paid_through=paid_through,
                features=parse_features(self._features(plan)),
            )
            self.store.upsert_subscription(
                subscription_id=subscription_id,
                customer_id=str(obj.get("customer", "")),
                email_hash=email_hash,
                plan=plan,
                price_id=_price_id(obj),
                status=(
                    existing.status if existing.last_event_created >= event_created else "active"
                ),
                current_period_end=max(paid_through, existing.current_period_end),
                cancel_at_period_end=existing.cancel_at_period_end,
                entitlement_state=EntitlementState.ACTIVE,
                event_id=event_id,
                event_created=event_created,
                license_path=str(issued.path),
                accept_older_event=True,
            )
            payment_intent_id, charge_id = _payment_ids(obj)
            self.store.record_payment_mapping(
                invoice_id=str(obj.get("id", "")),
                subscription_id=subscription_id,
                payment_intent_id=payment_intent_id,
                charge_id=charge_id,
            )
            return "sandbox-license-issued"

        if event_type == "invoice.payment_failed":
            if existing is None:
                raise BillingError("failed invoice arrived before its sandbox subscription")
            if existing.entitlement_state == EntitlementState.MANUAL_REVIEW:
                return "manual-review-issuance-held"
            if self.store.payment_for_invoice(str(obj.get("id", ""))) is not None:
                return "ignored-already-paid-invoice"
            plan = self._plan(obj, existing)
            self.store.upsert_subscription(
                subscription_id=subscription_id,
                customer_id=str(obj.get("customer", "")),
                email_hash=existing.synthetic_email_hash,
                plan=plan,
                price_id=_price_id(obj),
                status="past_due",
                current_period_end=existing.current_period_end,
                cancel_at_period_end=existing.cancel_at_period_end,
                entitlement_state=EntitlementState.PAYMENT_FAILED,
                event_id=event_id,
                event_created=event_created,
            )
            return "payment-failure-recorded"

        if event_type in _PAYMENT_REVIEW_EVENT_TYPES:
            if existing is None:
                return "manual-review-unmatched-payment-event"
            plan = self._plan(obj, existing)
            self.store.upsert_subscription(
                subscription_id=subscription_id,
                customer_id=existing.stripe_customer_id,
                email_hash=existing.synthetic_email_hash,
                plan=plan,
                price_id=existing.price_id,
                status=event_type,
                current_period_end=existing.current_period_end,
                cancel_at_period_end=existing.cancel_at_period_end,
                entitlement_state=EntitlementState.MANUAL_REVIEW,
                event_id=event_id,
                event_created=event_created,
                accept_older_event=True,
            )
            return "manual-review-offline-license-not-revoked"

        return "ignored-unhandled-event"
