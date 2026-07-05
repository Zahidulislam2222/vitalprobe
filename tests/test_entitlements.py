"""E2 offline license verification and feature-guard tests."""

import base64
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from nacl.signing import SigningKey

from vitalprobe.entitlements import features as feature_module
from vitalprobe.entitlements.features import (
    FeatureFlag,
    FeatureUnavailableError,
    require,
)
from vitalprobe.entitlements.license import (
    EntitlementStatus,
    LicensePayload,
    canonical_payload,
    verify_license,
)


def _write_license(
    path: Path,
    signing_key: SigningKey,
    *,
    expires_at: datetime,
    features: list[FeatureFlag] | None = None,
) -> None:
    payload = LicensePayload(
        licensee="Test Clinic",
        tier="professional",
        issued_at=datetime.now(UTC) - timedelta(minutes=1),
        expires_at=expires_at,
        features=features or [FeatureFlag.LEARNING],
    )
    signature = signing_key.sign(canonical_payload(payload)).signature
    document = {
        **payload.model_dump(mode="json"),
        "signature": base64.b64encode(signature).decode("ascii"),
    }
    path.write_text(json.dumps(document), encoding="utf-8")


def test_valid_license_unlocks_signed_features(tmp_path: Path) -> None:
    signing_key = SigningKey.generate()
    path = tmp_path / "license.json"
    _write_license(
        path,
        signing_key,
        expires_at=datetime.now(UTC) + timedelta(days=30),
        features=[FeatureFlag.LEARNING, FeatureFlag.PRIVATE_PACKS],
    )

    status = verify_license(path, public_key_hex=signing_key.verify_key.encode().hex())

    assert status.valid
    assert status.tier == "professional"
    assert FeatureFlag.LEARNING in status.features
    assert FeatureFlag.PRIVATE_PACKS in status.features


def test_expired_license_degrades_to_free(tmp_path: Path) -> None:
    signing_key = SigningKey.generate()
    path = tmp_path / "expired.json"
    _write_license(path, signing_key, expires_at=datetime.now(UTC) - timedelta(days=1))

    status = verify_license(path, public_key_hex=signing_key.verify_key.encode().hex())

    assert not status.valid
    assert status.tier == "free"
    assert not status.features
    assert "expired" in status.message.lower()


def test_tampered_license_degrades_to_free(tmp_path: Path) -> None:
    signing_key = SigningKey.generate()
    path = tmp_path / "tampered.json"
    _write_license(path, signing_key, expires_at=datetime.now(UTC) + timedelta(days=30))
    document = json.loads(path.read_text(encoding="utf-8"))
    document["tier"] = "tampered-tier"
    path.write_text(json.dumps(document), encoding="utf-8")

    status = verify_license(path, public_key_hex=signing_key.verify_key.encode().hex())

    assert not status.valid
    assert status.tier == "free"
    assert not status.features
    assert "invalid or tampered" in status.message.lower()


def test_absent_license_degrades_cleanly_to_free(tmp_path: Path) -> None:
    status = verify_license(tmp_path / "missing.json")

    assert not status.valid
    assert status.tier == "free"
    assert not status.features
    assert "not found" in status.message.lower()


def test_non_utf8_license_degrades_cleanly_to_free(tmp_path: Path) -> None:
    path = tmp_path / "binary.license"
    path.write_bytes(b"\xff\xfe\x00\x80")

    status = verify_license(path)

    assert not status.valid
    assert status.tier == "free"
    assert "invalid or tampered" in status.message.lower()


def test_feature_guard_allows_entitled_feature(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    status = EntitlementStatus(
        tier="professional",
        features=frozenset({FeatureFlag.REBRANDING}),
        valid=True,
        message="verified",
    )
    monkeypatch.setattr(
        "vitalprobe.entitlements.license.verify_license",
        lambda _path=None: status,
    )

    require(FeatureFlag.REBRANDING)


def test_feature_guard_has_clean_upgrade_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "vitalprobe.entitlements.license.verify_license",
        lambda _path=None: EntitlementStatus(),
    )

    with pytest.raises(FeatureUnavailableError, match="requires a paid VitalProbe license"):
        feature_module.require(FeatureFlag.MCP_SERVER)
