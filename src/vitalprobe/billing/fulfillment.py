"""Synthetic Ed25519 license evidence for Stripe sandbox payments only."""

import base64
import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from tempfile import NamedTemporaryFile

from nacl.signing import SigningKey

from vitalprobe.billing.models import BillingPlan, IssuedSandboxLicense
from vitalprobe.entitlements.features import FeatureFlag
from vitalprobe.entitlements.license import LicensePayload, canonical_payload

_SAFE_ID = re.compile(r"[^A-Za-z0-9_-]+")


class SandboxFulfillmentError(Exception):
    """Test license issuance could not be completed safely."""


def parse_features(value: str) -> list[FeatureFlag]:
    try:
        features = [FeatureFlag(item.strip()) for item in value.split(",") if item.strip()]
    except ValueError as exc:
        raise SandboxFulfillmentError(f"unknown sandbox feature: {exc}") from None
    if not features:
        raise SandboxFulfillmentError("sandbox feature list cannot be empty")
    return features


class SandboxLicenseIssuer:
    def __init__(self, seed_file: Path, output_dir: Path) -> None:
        self.seed_file = seed_file
        self.output_dir = output_dir

    def _signing_key(self) -> SigningKey:
        self.seed_file.parent.mkdir(parents=True, exist_ok=True)
        if self.seed_file.exists():
            try:
                seed = bytes.fromhex(self.seed_file.read_text(encoding="ascii").strip())
                return SigningKey(seed)
            except (OSError, UnicodeError, ValueError) as exc:
                raise SandboxFulfillmentError("sandbox signing seed is unreadable") from exc
        key = SigningKey.generate()
        self.seed_file.write_text(key.encode().hex(), encoding="ascii")
        try:
            self.seed_file.chmod(0o600)
        except OSError:
            pass
        return key

    def issue(
        self,
        *,
        subscription_id: str,
        email_hash: str,
        plan: BillingPlan,
        paid_through: int,
        features: list[FeatureFlag],
        now: datetime | None = None,
    ) -> IssuedSandboxLicense:
        issued_at = now or datetime.now(UTC)
        expires_at = datetime.fromtimestamp(paid_through, UTC)
        if expires_at <= issued_at:
            raise SandboxFulfillmentError("paid-through timestamp must be in the future")
        payload = LicensePayload(
            licensee=f"SYNTHETIC TEST CUSTOMER {email_hash[:12]}",
            tier=f"sandbox-{plan.value}",
            issued_at=issued_at,
            expires_at=expires_at,
            features=features,
        )
        key = self._signing_key()
        signature = key.sign(canonical_payload(payload)).signature
        document = {
            **payload.model_dump(mode="json"),
            "signature": base64.b64encode(signature).decode("ascii"),
        }
        safe_id = _SAFE_ID.sub("_", subscription_id)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        path = self.output_dir / f"{safe_id}.sandbox-license.json"
        temporary: Path | None = None
        try:
            with NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=self.output_dir, delete=False
            ) as handle:
                temporary = Path(handle.name)
                handle.write(json.dumps(document, indent=2) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            temporary.replace(path)
        except OSError as exc:
            raise SandboxFulfillmentError(
                "sandbox license could not be written atomically"
            ) from exc
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        return IssuedSandboxLicense(
            path=path,
            public_key_hex=key.verify_key.encode().hex(),
            paid_through=paid_through,
        )
