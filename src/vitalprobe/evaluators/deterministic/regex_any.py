"""Pass if ANY regex pattern matches the response."""

import re
from typing import Any

from vitalprobe.evaluators.deterministic._common import get_patterns, regex_flags
from vitalprobe.schema import CheckResult, ResponseMeta


def evaluate(response_text: str, meta: ResponseMeta, spec: dict[str, Any]) -> CheckResult:
    patterns = get_patterns(spec)
    flags = regex_flags(spec)
    for pattern in patterns:
        match = re.search(pattern, response_text, flags)
        if match:
            return CheckResult(
                type="regex_any", passed=True, evidence=f"matched /{pattern}/: '{match.group(0)}'"
            )
    return CheckResult(
        type="regex_any",
        passed=False,
        evidence=f"none of {len(patterns)} expected patterns matched: {patterns}",
    )
