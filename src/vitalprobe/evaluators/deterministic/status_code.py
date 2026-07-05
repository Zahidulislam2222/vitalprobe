"""Pass if the HTTP status is an expected value (`expected: 200` or `expected: [200, 201]`)."""

from typing import Any

from vitalprobe.schema import CheckResult, ResponseMeta


def evaluate(response_text: str, meta: ResponseMeta, spec: dict[str, Any]) -> CheckResult:
    expected = spec.get("expected", 200)
    expected_list = [int(e) for e in expected] if isinstance(expected, list) else [int(expected)]
    if meta.status_code is None:
        return CheckResult(
            type="status_code", passed=False, evidence="no HTTP status code was observed"
        )
    passed = meta.status_code in expected_list
    return CheckResult(
        type="status_code",
        passed=passed,
        evidence=f"got {meta.status_code}, expected {expected_list}",
    )
