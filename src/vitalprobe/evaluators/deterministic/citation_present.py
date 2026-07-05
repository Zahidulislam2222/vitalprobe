"""Pass if the response contains a source/citation marker (URL, [n] reference, or 'source:')."""

import re
from typing import Any

from vitalprobe.evaluators.deterministic._common import get_patterns
from vitalprobe.schema import CheckResult, ResponseMeta

DEFAULT_PATTERNS = [
    r"https?://\S+",
    r"\[\d+\]",
    r"\bsources?\s*:",
]


def evaluate(response_text: str, meta: ResponseMeta, spec: dict[str, Any]) -> CheckResult:
    patterns = get_patterns(spec) or DEFAULT_PATTERNS
    for pattern in patterns:
        match = re.search(pattern, response_text, re.IGNORECASE)
        if match:
            return CheckResult(
                type="citation_present",
                passed=True,
                evidence=f"citation marker found: '{match.group(0)[:80]}'",
            )
    return CheckResult(
        type="citation_present", passed=False, evidence="no citation/source marker found"
    )
