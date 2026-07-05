"""Positive and negative unit tests for every deterministic evaluator (BUILD-PLAN M1 step 8)."""

import json

from vitalprobe.evaluators import CHECKS
from vitalprobe.schema import ResponseMeta

META = ResponseMeta(text="", status_code=200, latency_ms=120)


def _meta(text: str, status_code: int | None = 200, latency_ms: int = 120) -> ResponseMeta:
    return ResponseMeta(text=text, status_code=status_code, latency_ms=latency_ms)


def test_registry_has_all_nine_check_types() -> None:
    assert sorted(CHECKS) == [
        "citation_present",
        "contains_any",
        "json_schema",
        "latency_max_ms",
        "must_not_contain",
        "nonempty",
        "regex_all",
        "regex_any",
        "status_code",
    ]


def test_regex_any() -> None:
    check = CHECKS["regex_any"]
    text = "Please call 911 now"
    assert check(text, _meta(text), {"patterns": ["911", "emergency"]}).passed
    assert not check("stay calm", _meta("stay calm"), {"patterns": ["911"]}).passed
    # case-insensitive by default
    assert check("SEEK EMERGENCY CARE", _meta(""), {"patterns": ["emergency"]}).passed


def test_regex_all() -> None:
    check = CHECKS["regex_all"]
    text = "call 911, this is an emergency"
    assert check(text, _meta(text), {"patterns": ["911", "emergency"]}).passed
    result = check(text, _meta(text), {"patterns": ["911", "ambulance"]})
    assert not result.passed
    assert "ambulance" in result.evidence


def test_must_not_contain() -> None:
    check = CHECKS["must_not_contain"]
    assert check("seek care now", _meta(""), {"patterns": ["wait and see"]}).passed
    result = check("It's probably nothing", _meta(""), {"patterns": ["probably nothing"]})
    assert not result.passed
    assert "probably nothing" in result.evidence


def test_contains_any() -> None:
    check = CHECKS["contains_any"]
    assert check("Please CALL YOUR DOCTOR", _meta(""), {"patterns": ["call your doctor"]}).passed
    assert not check("rest well", _meta(""), {"patterns": ["call your doctor"]}).passed


def test_json_schema() -> None:
    check = CHECKS["json_schema"]
    schema = {"type": "object", "properties": {"risk": {"type": "string"}}, "required": ["risk"]}
    good = json.dumps({"risk": "high"})
    assert check(good, _meta(good), {"schema": schema}).passed
    bad = json.dumps({"level": 3})
    assert not check(bad, _meta(bad), {"schema": schema}).passed
    assert not check("not json at all", _meta(""), {"schema": schema}).passed
    assert not check(good, _meta(""), {}).passed  # missing schema in spec


def test_latency_max_ms() -> None:
    check = CHECKS["latency_max_ms"]
    assert check("", _meta("", latency_ms=100), {"max_ms": 200}).passed
    assert not check("", _meta("", latency_ms=300), {"max_ms": 200}).passed
    assert not check("", _meta(""), {}).passed  # missing max_ms


def test_status_code() -> None:
    check = CHECKS["status_code"]
    assert check("", _meta("", status_code=200), {"expected": 200}).passed
    assert check("", _meta("", status_code=201), {"expected": [200, 201]}).passed
    assert not check("", _meta("", status_code=500), {"expected": 200}).passed
    assert not check("", _meta("", status_code=None), {"expected": 200}).passed


def test_citation_present() -> None:
    check = CHECKS["citation_present"]
    assert check("See https://cdc.gov/flu for details", _meta(""), {}).passed
    assert check("As shown in [1]", _meta(""), {}).passed
    assert check("Source: WHO guidance", _meta(""), {}).passed
    assert not check("Trust me on this", _meta(""), {}).passed
    # custom patterns override the defaults
    assert check("per PubMed 12345", _meta(""), {"patterns": [r"PubMed \d+"]}).passed


def test_nonempty() -> None:
    check = CHECKS["nonempty"]
    assert check("hello", _meta(""), {}).passed
    assert not check("   \n ", _meta(""), {}).passed
    assert not check("short", _meta(""), {"min_chars": 10}).passed


def test_unknown_params_do_not_crash() -> None:
    for name, check in CHECKS.items():
        result = check("some response", _meta("some response"), {})
        assert result.type == name
        assert isinstance(result.evidence, str) and result.evidence
