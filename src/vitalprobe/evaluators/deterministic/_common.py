"""Shared helpers for deterministic evaluators."""

import re
from typing import Any


def get_patterns(spec: dict[str, Any]) -> list[str]:
    patterns = spec.get("patterns", [])
    if isinstance(patterns, str):
        return [patterns]
    return [str(p) for p in patterns]


def regex_flags(spec: dict[str, Any]) -> int:
    """Case-insensitive by default; set `case_sensitive: true` in the check spec to disable."""
    return 0 if spec.get("case_sensitive", False) else re.IGNORECASE
