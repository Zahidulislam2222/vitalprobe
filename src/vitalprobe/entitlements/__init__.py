"""Offline license verification and paid-feature guards."""

from vitalprobe.entitlements.features import (
    FeatureFlag,
    FeatureUnavailableError,
    require,
)
from vitalprobe.entitlements.license import (
    EntitlementStatus,
    LicensePayload,
    verify_license,
)

__all__ = [
    "EntitlementStatus",
    "FeatureFlag",
    "FeatureUnavailableError",
    "LicensePayload",
    "require",
    "verify_license",
]
