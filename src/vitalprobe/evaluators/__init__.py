"""Deterministic evaluators (§2.2). `CHECKS` maps check-type name → evaluate function.

Every evaluator implements:
    evaluate(response_text: str, meta: ResponseMeta, spec: dict) -> CheckResult
and returns evidence text saying what matched or what was expected.
"""

from collections.abc import Callable
from typing import Any

from vitalprobe.evaluators.deterministic import (
    citation_present,
    contains_any,
    json_schema,
    latency_max_ms,
    must_not_contain,
    nonempty,
    regex_all,
    regex_any,
    status_code,
)
from vitalprobe.schema import CheckResult, ResponseMeta

Evaluator = Callable[[str, ResponseMeta, dict[str, Any]], CheckResult]

CHECKS: dict[str, Evaluator] = {
    "regex_any": regex_any.evaluate,
    "regex_all": regex_all.evaluate,
    "must_not_contain": must_not_contain.evaluate,
    "contains_any": contains_any.evaluate,
    "json_schema": json_schema.evaluate,
    "latency_max_ms": latency_max_ms.evaluate,
    "status_code": status_code.evaluate,
    "citation_present": citation_present.evaluate,
    "nonempty": nonempty.evaluate,
}

__all__ = ["CHECKS", "Evaluator"]
