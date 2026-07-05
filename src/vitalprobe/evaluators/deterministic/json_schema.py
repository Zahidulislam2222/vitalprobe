"""Pass if the response parses as JSON and validates against the given JSON Schema."""

import json
from typing import Any

import jsonschema

from vitalprobe.schema import CheckResult, ResponseMeta


def evaluate(response_text: str, meta: ResponseMeta, spec: dict[str, Any]) -> CheckResult:
    schema = spec.get("schema")
    if not isinstance(schema, dict):
        return CheckResult(
            type="json_schema", passed=False, evidence="check spec is missing a 'schema' mapping"
        )
    try:
        payload = json.loads(response_text)
    except json.JSONDecodeError as exc:
        return CheckResult(
            type="json_schema", passed=False, evidence=f"response is not valid JSON: {exc}"
        )
    try:
        jsonschema.validate(payload, schema)
    except jsonschema.ValidationError as exc:
        return CheckResult(
            type="json_schema", passed=False, evidence=f"schema violation: {exc.message}"
        )
    except jsonschema.SchemaError as exc:
        return CheckResult(
            type="json_schema",
            passed=False,
            evidence=f"the schema itself is invalid: {exc.message}",
        )
    return CheckResult(
        type="json_schema", passed=True, evidence="response validates against schema"
    )
