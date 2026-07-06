"""Thin MCP (stdio) wrapper around the demo health bot (M8 step 3 test target).

Same reply logic as the REST demo bot — scripted by default, Ollama when
DEMOBOT_PROVIDER=ollama — so an MCP-adapter run must produce the same verdicts
as a REST run against the same configuration.

Run: python -m vitalprobe.demo.mcp_wrapper
"""

from mcp.server.fastmcp import FastMCP

from vitalprobe.config import get_settings
from vitalprobe.demo.demo_health_bot import load_scripted_config, ollama_reply

server = FastMCP("vitalprobe-demo-health-bot")


@server.tool()
async def chat(message: str) -> str:
    """Send one user message to the demo health bot and get its reply."""
    settings = get_settings()
    if settings.demo_provider == "ollama":
        return await ollama_reply(message, settings)
    scripted = load_scripted_config()
    lowered = message.casefold()
    for trigger, reply in scripted.responses.items():
        if trigger in lowered:
            return reply
    return scripted.default_response


if __name__ == "__main__":
    server.run()
