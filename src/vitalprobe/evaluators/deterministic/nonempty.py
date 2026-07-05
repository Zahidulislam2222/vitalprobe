"""Pass if the response has substantive content (default: at least 1 non-whitespace character)."""

from typing import Any

from vitalprobe.schema import CheckResult, ResponseMeta


def evaluate(response_text: str, meta: ResponseMeta, spec: dict[str, Any]) -> CheckResult:
    min_chars = int(spec.get("min_chars", 1))
    length = len(response_text.strip())
    passed = length >= min_chars
    return CheckResult(
        type="nonempty",
        passed=passed,
        evidence=f"response has {length} non-whitespace-trimmed chars (minimum {min_chars})",
    )
