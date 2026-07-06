"""M8 MCP surfaces: target adapter config/transport and the paid-only product server."""

import sys
from pathlib import Path

import pytest

from vitalprobe.entitlements.features import FeatureFlag, FeatureUnavailableError
from vitalprobe.entitlements.license import EntitlementStatus
from vitalprobe.mcp.server import build_server
from vitalprobe.schema import Turn
from vitalprobe.targets.mcp import (
    McpAdapter,
    load_mcp_adapter_config,
    parse_mcp_adapter_config,
)
from vitalprobe.targets.rest import AdapterError


def test_mcp_config_validation() -> None:
    with pytest.raises(AdapterError, match="requires 'command'"):
        parse_mcp_adapter_config({"kind": "mcp", "transport": "stdio"})
    with pytest.raises(AdapterError, match="requires 'url'"):
        parse_mcp_adapter_config({"kind": "mcp", "transport": "http"})
    with pytest.raises(AdapterError, match="invalid MCP adapter config"):
        parse_mcp_adapter_config({"kind": "mcp", "transport": "carrier-pigeon"})
    config = parse_mcp_adapter_config(
        {"kind": "mcp", "transport": "stdio", "command": ["python", "-m", "x"]}
    )
    assert config.tool_name == "chat"


def test_rest_adapter_yaml_is_not_mcp(tmp_path: Path) -> None:
    rest = tmp_path / "adapter.yaml"
    rest.write_text("method: POST\nresponse_path: reply\n", encoding="utf-8")
    assert load_mcp_adapter_config(rest) is None
    mcp_yaml = tmp_path / "mcp.yaml"
    mcp_yaml.write_text(
        "kind: mcp\ntransport: stdio\ncommand: ['python', '-m', 'x']\n", encoding="utf-8"
    )
    loaded = load_mcp_adapter_config(mcp_yaml)
    assert loaded is not None and loaded.transport == "stdio"


async def test_stdio_mcp_wrapper_round_trip() -> None:
    """Spawn the real MCP demo-bot wrapper over stdio and get a scripted reply through
    the adapter — the full client transport chain, zero network."""
    config = parse_mcp_adapter_config(
        {
            "kind": "mcp",
            "transport": "stdio",
            "command": [sys.executable, "-m", "vitalprobe.demo.mcp_wrapper"],
        }
    )
    adapter = McpAdapter(config)
    try:
        meta = await adapter.send(
            [Turn(role="user", content="I have chest pain and feel dizzy")]
        )
        second = await adapter.send([Turn(role="user", content="hello there")])
    finally:
        await adapter.aclose()
    assert "emergency" in meta.text.lower()
    assert "no matching response" in second.text.lower()
    assert adapter.endpoint_redacted.startswith("mcp+stdio:")


async def test_unknown_tool_name_fails_loudly() -> None:
    config = parse_mcp_adapter_config(
        {
            "kind": "mcp",
            "transport": "stdio",
            "command": [sys.executable, "-m", "vitalprobe.demo.mcp_wrapper"],
            "tool_name": "not-a-tool",
        }
    )
    adapter = McpAdapter(config)
    try:
        with pytest.raises(AdapterError, match="no tool 'not-a-tool'"):
            await adapter.send([Turn(role="user", content="hi")])
    finally:
        await adapter.aclose()


def test_mcp_server_refuses_without_license(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        "vitalprobe.entitlements.license.verify_license",
        lambda _path=None: EntitlementStatus(),
    )
    with pytest.raises(FeatureUnavailableError, match="mcp server"):
        build_server()


async def test_mcp_server_exposes_engine_tools_with_license(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "vitalprobe.entitlements.license.verify_license",
        lambda _path=None: EntitlementStatus(
            tier="dev",
            features=frozenset(
                {FeatureFlag.MCP_SERVER, FeatureFlag.LEARNING}
            ),
            valid=True,
            message="verified",
        ),
    )
    server = build_server()
    tools = await server.list_tools()
    assert {tool.name for tool in tools} == {"run_suite", "history", "compare", "learn"}
