"""Pass only if EVERY regex pattern matches the response."""

import re
from typing import Any

from vitalprobe.evaluators.deterministic._common import get_patterns, regex_flags
from vitalprobe.schema import CheckResult, ResponseMeta


def evaluate(response_text: str, meta: ResponseMeta, spec: dict[str, Any]) -> CheckResult:
    patterns = get_patterns(spec)
    flags = regex_flags(spec)
    missing = [p for p in patterns if not re.search(p, response_text, flags)]
    if missing:
        return CheckResult(
            type="regex_all", passed=False, evidence=f"required patterns not found: {missing}"
        )
    return CheckResult(
        type="regex_all", passed=True, evidence=f"all {len(patterns)} required patterns matched"
    )
