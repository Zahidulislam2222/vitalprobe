"""Pass if the observed latency is at or below `max_ms`."""

from typing import Any

from vitalprobe.schema import CheckResult, ResponseMeta


def evaluate(response_text: str, meta: ResponseMeta, spec: dict[str, Any]) -> CheckResult:
    max_ms = spec.get("max_ms")
    if not isinstance(max_ms, int | float):
        return CheckResult(
            type="latency_max_ms", passed=False, evidence="check spec is missing numeric 'max_ms'"
        )
    passed = meta.latency_ms <= max_ms
    return CheckResult(
        type="latency_max_ms",
        passed=passed,
        evidence=f"latency {meta.latency_ms}ms vs limit {int(max_ms)}ms",
    )
