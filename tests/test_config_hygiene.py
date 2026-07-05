"""Guardrails against scattered provider config and committed secrets."""

import re
from pathlib import Path

import pytest

from vitalprobe.config import Settings

ROOT = Path(__file__).parents[1]
PROVIDER_MODULES = [
    ROOT / "src/vitalprobe/judges/openai.py",
    ROOT / "src/vitalprobe/judges/anthropic.py",
    ROOT / "src/vitalprobe/judges/ollama.py",
]


def test_provider_modules_contain_no_environment_specific_config() -> None:
    forbidden = [
        "api.openai.com",
        "api.anthropic.com",
        "localhost:11434",
        "2023-06-01",
        "~1500",
    ]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in PROVIDER_MODULES)
    assert not [value for value in forbidden if value in combined]


def test_scripted_responses_are_data_not_source_constants() -> None:
    source = (ROOT / "src/vitalprobe/demo/demo_health_bot.py").read_text(encoding="utf-8")
    assert "SCRIPTED_RESPONSES" not in source
    assert "probably nothing" not in source.casefold()
    assert (ROOT / "src/vitalprobe/demo/scripted_responses.yaml").is_file()


def test_tracked_text_files_contain_no_obvious_private_keys() -> None:
    secret_patterns = [
        re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
        re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
        re.compile(r"BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY"),
    ]
    hits: list[str] = []
    for path in (ROOT / "src").rglob("*"):
        if path.is_file() and path.suffix != ".hex":
            text = path.read_text(encoding="utf-8", errors="ignore")
            if any(pattern.search(text) for pattern in secret_patterns):
                hits.append(str(path.relative_to(ROOT)))
    assert hits == []


def test_standard_provider_key_environment_names(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "openai-test")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "anthropic-test")
    settings = Settings()
    assert settings.openai_api_key == "openai-test"
    assert settings.anthropic_api_key == "anthropic-test"
