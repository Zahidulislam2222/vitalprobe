"""P8 founder script must keep every product surface and hard gate visible."""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "TESTING-FULL.md"

# The founder script references private-repo paths, so it is deliberately not
# tracked in the public repo; these checks only run where the local copy exists.
pytestmark = pytest.mark.skipif(
    not SCRIPT.is_file(), reason="local-only founder acceptance script absent"
)


def test_full_acceptance_script_covers_every_surface() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    required = [
        "Engine layer and quality gates",
        "Local naive audit",
        "baseline",
        "history",
        "Free tier versus development license",
        "Self-learning loop",
        "Law mapping and private pack",
        "Multi-turn patient simulator",
        "MCP target adapter and paid product MCP server",
        "LangGraph example",
        "Calibration status",
        "Cloud smoke gate",
        "Founder acceptance record",
    ]
    assert [heading for heading in required if heading not in text] == []


def test_full_acceptance_script_keeps_human_and_money_gates() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    assert "Only the founder records ACCEPTED or REJECTED" in text
    assert "fresh founder message explicitly approving that exact amount" in text
    assert "Do **not** execute cloud judges during this script." in text
    assert "human approval is mandatory" in text


def test_full_acceptance_script_does_not_pin_a_local_model_tag() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    concrete_tag = re.compile(
        r"\b(?:qwen|gemma)[a-z0-9.-]*:\d+(?:\.\d+)?b\b",
        re.IGNORECASE,
    )
    assert concrete_tag.search(text) is None
