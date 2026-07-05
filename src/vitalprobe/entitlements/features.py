"""Paid feature names and the shared entitlement guard."""

from enum import StrEnum
from pathlib import Path


class FeatureFlag(StrEnum):
    PRIVATE_PACKS = "private_packs"
    LAW_MAPPING = "law_mapping"
    LEARNING = "learning"
    REBRANDING = "rebranding"
    MCP_SERVER = "mcp_server"


class FeatureUnavailableError(Exception):
    """A paid feature was requested without a valid entitlement."""


def require(flag: FeatureFlag, license_path: Path | None = None) -> None:
    """Require a paid feature, with a clean upgrade-oriented error."""
    # Local import avoids a module cycle: license documents validate FeatureFlag values.
    from vitalprobe.entitlements.license import verify_license

    status = verify_license(license_path)
    if flag not in status.features:
        display = flag.value.replace("_", " ")
        raise FeatureUnavailableError(
            f"'{display}' requires a paid VitalProbe license. "
            f"Current tier: {status.tier}. {status.message}"
        )
