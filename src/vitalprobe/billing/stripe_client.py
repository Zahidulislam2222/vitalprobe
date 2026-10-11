"""Small Stripe HTTP client with test-mode and localhost enforcement."""

from collections.abc import Mapping
from urllib.parse import urlsplit

import httpx

from vitalprobe.billing.models import BillingPlan, CheckoutSession
from vitalprobe.config import Settings

_LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}
_SYNTHETIC_EMAIL_DOMAINS = {"example.com", "example.net", "example.org", "example.test"}


class StripeSandboxError(Exception):
    """Safe Stripe sandbox failure that never includes a credential."""


def require_test_key(value: str) -> str:
    if not value.startswith(("sk_test_", "rk_test_")):
        raise StripeSandboxError("Stripe sandbox requires an sk_test_ or rk_test_ key")
    return value


def require_local_url(value: str) -> str:
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or parsed.hostname not in _LOCAL_HOSTS:
        raise StripeSandboxError("sandbox return URLs must use localhost or loopback")
    return value


def require_synthetic_email(value: str) -> str:
    normalized = value.strip().casefold()
    if "@" not in normalized or normalized.rsplit("@", 1)[1] not in _SYNTHETIC_EMAIL_DOMAINS:
        raise StripeSandboxError("use a synthetic email under an example domain")
    return normalized


class StripeSandboxClient:
    def __init__(
        self,
        settings: Settings,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        key = require_test_key(settings.stripe_secret_key.get_secret_value())
        self.settings = settings
        self._client = httpx.AsyncClient(
            base_url=settings.stripe_api_base_url.rstrip("/"),
            auth=(key, ""),
            timeout=settings.stripe_timeout_s,
            transport=transport,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _json(
        self,
        method: str,
        path: str,
        *,
        data: Mapping[str, str] | None = None,
    ) -> dict[str, object]:
        try:
            response = await self._client.request(method, path, data=data)
        except httpx.HTTPError as exc:
            raise StripeSandboxError(
                f"Stripe sandbox request failed: {type(exc).__name__}"
            ) from None
        if response.status_code >= 400:
            code = "stripe_error"
            try:
                body = response.json()
                error = body.get("error", {}) if isinstance(body, dict) else {}
                if isinstance(error, dict):
                    code = str(error.get("code") or error.get("type") or code)
            except ValueError:
                pass
            raise StripeSandboxError(
                f"Stripe sandbox returned HTTP {response.status_code} ({code})"
            )
        body = response.json()
        if not isinstance(body, dict):
            raise StripeSandboxError("Stripe sandbox returned an invalid response")
        return body

    def _plan_config(self, plan: BillingPlan) -> tuple[str, int]:
        if plan is BillingPlan.AUTOMATED:
            return (
                self.settings.stripe_automated_price_id,
                self.settings.stripe_automated_unit_amount,
            )
        return (
            self.settings.stripe_clinician_price_id,
            self.settings.stripe_clinician_unit_amount,
        )

    async def validate_price(self, plan: BillingPlan) -> str:
        price_id, expected_amount = self._plan_config(plan)
        if not price_id.startswith("price_"):
            raise StripeSandboxError(f"sandbox Price ID is not configured for {plan.value}")
        price = await self._json("GET", f"/prices/{price_id}")
        recurring = price.get("recurring")
        if price.get("livemode") is not False:
            raise StripeSandboxError("live Stripe Prices are rejected by the sandbox")
        if price.get("active") is not True or not isinstance(recurring, dict):
            raise StripeSandboxError("sandbox Price must be active and recurring")
        if (
            recurring.get("interval") != self.settings.stripe_recurring_interval
            or recurring.get("interval_count") != self.settings.stripe_recurring_interval_count
        ):
            raise StripeSandboxError("sandbox Price interval does not match configuration")
        if price.get("unit_amount") != expected_amount:
            raise StripeSandboxError("sandbox Price amount does not match the approved plan")
        if str(price.get("currency", "")).casefold() != self.settings.stripe_currency.casefold():
            raise StripeSandboxError("sandbox Price currency does not match configuration")
        return price_id

    async def retrieve_invoice_payment_refs(self, invoice_id: str) -> dict[str, object]:
        if not invoice_id.startswith("in_"):
            raise StripeSandboxError("invalid sandbox invoice ID")
        invoice = await self._json(
            "GET", f"/invoices/{invoice_id}?expand[]=payments.data.payment.payment_intent"
        )
        if invoice.get("livemode") is not False or invoice.get("id") != invoice_id:
            raise StripeSandboxError("live or mismatched invoice rejected")
        return invoice

    async def create_checkout_session(
        self,
        plan: BillingPlan,
        *,
        synthetic_email: str,
        success_url: str,
        cancel_url: str,
    ) -> CheckoutSession:
        email = require_synthetic_email(synthetic_email)
        success = require_local_url(success_url)
        cancel = require_local_url(cancel_url)
        price_id = await self.validate_price(plan)
        form = {
            "mode": "subscription",
            "line_items[0][price]": price_id,
            "line_items[0][quantity]": "1",
            "customer_email": email,
            "success_url": success,
            "cancel_url": cancel,
            "metadata[vitalprobe_sandbox]": "true",
            "metadata[vitalprobe_plan]": plan.value,
            "subscription_data[metadata][vitalprobe_sandbox]": "true",
            "subscription_data[metadata][vitalprobe_plan]": plan.value,
        }
        session = await self._json("POST", "/checkout/sessions", data=form)
        if session.get("livemode") is not False:
            raise StripeSandboxError("live Checkout Sessions are rejected by the sandbox")
        session_id = str(session.get("id", ""))
        url = str(session.get("url", ""))
        if not session_id.startswith("cs_test_") or not url.startswith("https://"):
            raise StripeSandboxError("Stripe sandbox returned an invalid Checkout Session")
        return CheckoutSession(session_id=session_id, url=url)

    async def create_portal_session(self, customer_id: str, return_url: str) -> str:
        if not customer_id.startswith("cus_"):
            raise StripeSandboxError("invalid synthetic Stripe customer id")
        session = await self._json(
            "POST",
            "/billing_portal/sessions",
            data={"customer": customer_id, "return_url": require_local_url(return_url)},
        )
        if session.get("livemode") is not False:
            raise StripeSandboxError("live portal Sessions are rejected by the sandbox")
        url = str(session.get("url", ""))
        if not url.startswith("https://"):
            raise StripeSandboxError("Stripe sandbox returned an invalid portal URL")
        return url
