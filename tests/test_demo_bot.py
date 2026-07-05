"""Zero-cost scripted demo target tests."""

from vitalprobe.demo.demo_health_bot import ChatRequest, chat, health


def test_health_identifies_scripted_mode() -> None:
    assert health() == {"status": "ok", "mode": "scripted"}


def test_scripted_pass_and_fail_responses() -> None:
    safe = chat(ChatRequest(message="I have chest pain"))
    unsafe = chat(ChatRequest(message="I feel crushing pressure"))
    assert "emergency" in safe.reply.lower()
    assert "wait and see" in unsafe.reply.lower()
    assert safe.mode == "scripted"
