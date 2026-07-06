"""Guardrails against scattered provider config and committed secrets."""

import re
import subprocess
from pathlib import Path

import pytest
from pydantic import AliasChoices

from vitalprobe.config import Settings

ROOT = Path(__file__).parents[1]
PROVIDER_MODULES = [
    ROOT / "src/vitalprobe/judges/openai.py",
    ROOT / "src/vitalprobe/judges/anthropic.py",
    ROOT / "src/vitalprobe/judges/ollama.py",
]


def _tracked_text_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return [
        ROOT / path
        for path in result.stdout.decode().split("\0")
        if path and (ROOT / path).is_file()
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
    assert "friendly health assistant" not in source.casefold()
    assert (ROOT / "src/vitalprobe/demo/scripted_responses.yaml").is_file()
    assert (ROOT / "src/vitalprobe/demo/naive_system_prompt.txt").is_file()


def test_tracked_text_files_contain_no_obvious_private_keys() -> None:
    secret_patterns = [
        re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
        re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
        re.compile(r"BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY"),
    ]
    hits: list[str] = []
    for path in _tracked_text_files():
        if path.suffix == ".hex":
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if any(pattern.search(text) for pattern in secret_patterns):
            hits.append(str(path.relative_to(ROOT)))
    assert hits == []


def test_tracked_files_do_not_pin_concrete_local_model_tags() -> None:
    model_tag = re.compile(r"\b(?:qwen|gemma)[a-z0-9.-]*:\d+(?:\.\d+)?b\b", re.IGNORECASE)
    hits: list[str] = []
    for path in _tracked_text_files():
        text = path.read_text(encoding="utf-8", errors="ignore")
        if model_tag.search(text):
            hits.append(str(path.relative_to(ROOT)))
    assert hits == []


def test_standard_provider_key_environment_names(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "openai-test")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "anthropic-test")
    settings = Settings()
    assert settings.openai_api_key == "openai-test"
    assert settings.anthropic_api_key == "anthropic-test"


def test_documented_demo_environment_names(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEMOBOT_PROVIDER", "ollama")
    monkeypatch.setenv("DEMOBOT_MODEL", "test-local-model")
    monkeypatch.setenv("OLLAMA_HOST", "http://ollama.test")
    settings = Settings()
    assert settings.demo_provider == "ollama"
    assert settings.demo_model == "test-local-model"
    assert settings.ollama_host == "http://ollama.test"


def test_every_typed_setting_is_documented_in_env_example() -> None:
    documented = {
        line.split("=", 1)[0]
        for line in (ROOT / ".env.example").read_text(encoding="utf-8").splitlines()
        if line and not line.startswith("#") and "=" in line
    }
    missing: list[str] = []
    for name, field in Settings.model_fields.items():
        alias = field.validation_alias
        if isinstance(alias, AliasChoices):
            accepted = {str(choice) for choice in alias.choices}
        elif isinstance(alias, str):
            accepted = {alias}
        else:
            accepted = {f"VITALPROBE_{name.upper()}"}
        if documented.isdisjoint(accepted):
            missing.append(name)
    assert missing == []
