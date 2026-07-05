"""Pass if ANY plain substring is present (case-insensitive)."""

from typing import Any

from vitalprobe.evaluators.deterministic._common import get_patterns
from vitalprobe.schema import CheckResult, ResponseMeta


def evaluate(response_text: str, meta: ResponseMeta, spec: dict[str, Any]) -> CheckResult:
    needles = get_patterns(spec)
    haystack = response_text.lower()
    for needle in needles:
        if needle.lower() in haystack:
            return CheckResult(
                type="contains_any", passed=True, evidence=f"found substring '{needle}'"
            )
    return CheckResult(
        type="contains_any",
        passed=False,
        evidence=f"none of {len(needles)} expected substrings found: {needles}",
    )
