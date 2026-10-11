"""Typed contracts for the isolated Stripe sandbox lane."""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class BillingPlan(StrEnum):
    AUTOMATED = "automated"
    CLINICIAN = "clinician-reviewed"


class EntitlementState(StrEnum):
    PENDING = "pending"
    ACTIVE = "active-until-paid-through"
    PAYMENT_FAILED = "payment-failed"
    ENDED = "ended"
    MANUAL_REVIEW = "manual-review"


@dataclass(frozen=True, slots=True)
class CheckoutSession:
    session_id: str
    url: str


@dataclass(frozen=True, slots=True)
class IssuedSandboxLicense:
    path: Path
    public_key_hex: str
    paid_through: int


@dataclass(frozen=True, slots=True)
class WebhookOutcome:
    event_id: str
    event_type: str
    outcome: str
    duplicate: bool = False
