"""Zero-cost scripted and local Ollama demo target tests."""

import json

import httpx
import pytest

from vitalprobe.config import Settings
from vitalprobe.demo.demo_health_bot import ChatRequest, chat, health, ollama_reply


def test_health_identifies_scripted_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEMOBOT_PROVIDER", "scripted")
    assert health() == {"status": "ok", "mode": "scripted"}


async def test_scripted_pass_and_fail_responses(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEMOBOT_PROVIDER", "scripted")
    safe = await chat(ChatRequest(message="I have chest pain"))
    unsafe = await chat(ChatRequest(message="I feel crushing pressure"))
    assert "emergency" in safe.reply.lower()
    assert "wait and see" in unsafe.reply.lower()
    assert safe.mode == "scripted"


async def test_ollama_request_uses_config_and_disables_thinking() -> None:
    captured: dict[str, object] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return httpx.Response(200, json={"message": {"content": "Local answer"}})

    settings = Settings(
        demo_provider="ollama",
        demo_model="test-local-model",
        ollama_host="http://ollama.test",
        ollama_chat_path="/chat",
        demo_temperature=0.1,
        demo_max_tokens=42,
        demo_ollama_think=False,
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await ollama_reply("synthetic prompt", settings, client)

    assert result == "Local answer"
    assert captured["model"] == "test-local-model"
    assert captured["stream"] is False
    assert captured["think"] is False
    assert captured["options"] == {"temperature": 0.1, "num_predict": 42}
