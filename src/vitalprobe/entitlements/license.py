"""Offline Ed25519 license verification for the open-core feature gate."""

import base64
import binascii
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from nacl.exceptions import BadSignatureError
from nacl.signing import VerifyKey
from pydantic import BaseModel, ConfigDict, ValidationError, field_validator

from vitalprobe.config import get_settings
from vitalprobe.entitlements.features import FeatureFlag

PUBLIC_VERIFY_KEY_HEX = "83878938221c28c352f869f6f54d22a4a3d6de8c4cbe25a52bae7d7d7f51cdc0"


class LicensePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    licensee: str
    tier: str
    issued_at: datetime
    expires_at: datetime
    features: list[FeatureFlag]

    @field_validator("issued_at", "expires_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("timestamp must include a timezone")
        return value


class SignedLicense(LicensePayload):
    signature: str

    def payload(self) -> LicensePayload:
        return LicensePayload.model_validate(self.model_dump(exclude={"signature"}))


@dataclass(frozen=True, slots=True)
class EntitlementStatus:
    tier: str = "free"
    licensee: str | None = None
    issued_at: datetime | None = None
    expires_at: datetime | None = None
    features: frozenset[FeatureFlag] = frozenset()
    valid: bool = False
    message: str = "No license configured; using the free tier."


def canonical_payload(payload: LicensePayload) -> bytes:
    """Return the stable bytes signed by the founder-side issuing tool."""
    data: dict[str, Any] = payload.model_dump(mode="json")
    return json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _free(message: str) -> EntitlementStatus:
    return EntitlementStatus(message=message)


def verify_license(
    path: Path | None = None,
    *,
    public_key_hex: str = PUBLIC_VERIFY_KEY_HEX,
    now: datetime | None = None,
) -> EntitlementStatus:
    """Verify a license offline. Every failure degrades safely to the free tier."""
    license_path = path if path is not None else get_settings().license_file
    if license_path is None:
        return _free("No license configured; using the free tier.")
    if not license_path.is_file():
        return _free(f"License file not found: {license_path}; using the free tier.")

    try:
        document = SignedLicense.model_validate_json(license_path.read_text(encoding="utf-8"))
        signature = base64.b64decode(document.signature, validate=True)
        VerifyKey(bytes.fromhex(public_key_hex)).verify(
            canonical_payload(document.payload()), signature
        )
    except (
        OSError,
        UnicodeError,
        ValidationError,
        ValueError,
        binascii.Error,
        BadSignatureError,
    ) as exc:
        return _free(f"License is invalid or tampered ({type(exc).__name__}); using the free tier.")

    current = now or datetime.now(UTC)
    if document.expires_at <= current:
        return _free(
            f"License expired on {document.expires_at.isoformat()}; using the free tier."
        )
    if document.issued_at > current:
        return _free("License issue date is in the future; using the free tier.")

    return EntitlementStatus(
        tier=document.tier,
        licensee=document.licensee,
        issued_at=document.issued_at,
        expires_at=document.expires_at,
        features=frozenset(document.features),
        valid=True,
        message="License signature and validity period verified offline.",
    )
