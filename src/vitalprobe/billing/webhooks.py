"""Stripe webhook authentication for the local sandbox endpoint."""

import hashlib
import hmac
import json
import time
from collections.abc import Mapping
from typing import Any


class WebhookVerificationError(Exception):
    """The event is unauthenticated, stale, malformed, or live-mode."""


def verify_signature(
    payload: bytes,
    signature_header: str,
    secret: str,
    *,
    tolerance_s: int,
    now: int | None = None,
) -> dict[str, Any]:
    if not secret.startswith("whsec_"):
        raise WebhookVerificationError("sandbox webhook secret is missing or invalid")
    values: dict[str, list[str]] = {}
    for part in signature_header.split(","):
        key, separator, value = part.partition("=")
        if separator:
            values.setdefault(key, []).append(value)
    try:
        timestamp = int(values["t"][0])
    except (KeyError, ValueError, IndexError):
        raise WebhookVerificationError("Stripe-Signature timestamp is missing") from None
    current = int(time.time()) if now is None else now
    if abs(current - timestamp) > tolerance_s:
        raise WebhookVerificationError("Stripe webhook timestamp is outside tolerance")
    expected = hmac.new(
        secret.encode("utf-8"),
        str(timestamp).encode("ascii") + b"." + payload,
        hashlib.sha256,
    ).hexdigest()
    if not any(
        candidate.isascii() and hmac.compare_digest(expected, candidate)
        for candidate in values.get("v1", [])
    ):
        raise WebhookVerificationError("Stripe webhook signature is invalid")
    try:
        event = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise WebhookVerificationError("Stripe webhook payload is invalid JSON") from None
    if not isinstance(event, dict):
        raise WebhookVerificationError("Stripe webhook event must be an object")
    if event.get("livemode") is not False:
        raise WebhookVerificationError("live-mode Stripe events are rejected")
    return event


def object_from_event(event: Mapping[str, Any]) -> dict[str, Any]:
    data = event.get("data")
    if not isinstance(data, Mapping):
        raise WebhookVerificationError("Stripe event data is missing")
    obj = data.get("object")
    if not isinstance(obj, dict):
        raise WebhookVerificationError("Stripe event object is missing")
    return obj
