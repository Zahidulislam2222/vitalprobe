"""MCP target adapter (BUILD-PLAN M8 step 3): test a bot exposed as an MCP server tool.

Adapter config YAML (`kind: mcp` selects this adapter):

    kind: mcp
    transport: stdio            # or http
    command: ["python", "-m", "vitalprobe.demo.mcp_wrapper"]   # stdio only
    url: "http://127.0.0.1:8902/mcp"                           # http only
    tool_name: chat
    message_argument: message
    timeout_s: 60

The session opens lazily on the first send and stays open across cases; `aclose`
tears it down. This adapter TESTS an MCP target — it is distinct from the paid
product-side MCP server in `vitalprobe.mcp.server`.
"""

import asyncio
import time
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Literal, cast

import yaml
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamablehttp_client
from mcp.types import CallToolResult
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from vitalprobe.schema import ResponseMeta, Turn
from vitalprobe.targets.rest import AdapterError, redact_endpoint


class McpAdapterConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["mcp"] = "mcp"
    transport: Literal["stdio", "http"]
    command: list[str] = Field(default_factory=list)
    url: str = ""
    tool_name: str = "chat"
    message_argument: str = "message"
    timeout_s: float = 60.0


def parse_mcp_adapter_config(raw: dict[str, object]) -> McpAdapterConfig:
    try:
        config = McpAdapterConfig.model_validate(raw)
    except ValidationError as exc:
        raise AdapterError(f"invalid MCP adapter config: {exc}") from exc
    if config.transport == "stdio" and not config.command:
        raise AdapterError("MCP adapter with transport 'stdio' requires 'command'")
    if config.transport == "http" and not config.url:
        raise AdapterError("MCP adapter with transport 'http' requires 'url'")
    return config


_CLOSE = object()

_QueueItem = tuple[dict[str, str], "asyncio.Future[CallToolResult]"]


class McpAdapter:
    """The MCP session's async context managers (anyio cancel scopes) must be entered
    and exited by the SAME task, but the runner calls `send` from many tasks and
    `aclose` from another. A dedicated worker task therefore owns the whole session
    lifecycle; `send` hands it work through a queue."""

    name = "mcp"

    def __init__(self, config: McpAdapterConfig) -> None:
        self.config = config
        self._queue: asyncio.Queue[object] = asyncio.Queue()
        self._worker: asyncio.Task[None] | None = None
        self._ready: asyncio.Future[None] | None = None

    @property
    def endpoint_redacted(self) -> str:
        if self.config.transport == "http":
            return f"mcp+http:{redact_endpoint(self.config.url)}"
        return f"mcp+stdio:{' '.join(self.config.command)}"

    async def _worker_loop(self, ready: asyncio.Future[None]) -> None:
        try:
            async with AsyncExitStack() as stack:
                if self.config.transport == "stdio":
                    params = StdioServerParameters(
                        command=self.config.command[0], args=self.config.command[1:]
                    )
                    read, write = await stack.enter_async_context(stdio_client(params))
                else:
                    read, write, _ = await stack.enter_async_context(
                        streamablehttp_client(self.config.url)
                    )
                session = await stack.enter_async_context(ClientSession(read, write))
                await session.initialize()
                tools = await session.list_tools()
                names = [tool.name for tool in tools.tools]
                if self.config.tool_name not in names:
                    raise AdapterError(
                        f"MCP target has no tool '{self.config.tool_name}' (available: {names})"
                    )
                ready.set_result(None)
                while True:
                    item = await self._queue.get()
                    if item is _CLOSE:
                        return
                    arguments, future = cast(_QueueItem, item)
                    try:
                        result = await session.call_tool(self.config.tool_name, arguments)
                        future.set_result(result)
                    except Exception as exc:  # delivered to the caller, worker stays up
                        future.set_exception(
                            AdapterError(f"MCP tool call failed: {exc!r}")
                        )
        except Exception as exc:
            if not ready.done():
                if isinstance(exc, AdapterError):
                    ready.set_exception(exc)
                else:
                    ready.set_exception(
                        AdapterError(f"cannot connect to MCP target: {exc!r}")
                    )

    async def _ensure_worker(self) -> None:
        if self._worker is None:
            self._ready = asyncio.get_running_loop().create_future()
            self._worker = asyncio.create_task(self._worker_loop(self._ready))
        assert self._ready is not None
        await asyncio.shield(self._ready)

    async def aclose(self) -> None:
        if self._worker is not None:
            await self._queue.put(_CLOSE)
            await self._worker
            self._worker = None
            self._ready = None

    async def send(self, turns: list[Turn]) -> ResponseMeta:
        await self._ensure_worker()
        last_user = next((t.content for t in reversed(turns) if t.role == "user"), "")
        started = time.perf_counter()
        future: asyncio.Future[CallToolResult] = asyncio.get_running_loop().create_future()
        await self._queue.put(({self.config.message_argument: last_user}, future))
        result = await future
        latency_ms = int((time.perf_counter() - started) * 1000)
        texts = [block.text for block in result.content if hasattr(block, "text")]
        if result.isError:
            raise AdapterError(f"MCP tool returned an error: {' '.join(texts) or 'no detail'}")
        return ResponseMeta(text="\n".join(texts), status_code=None, latency_ms=latency_ms)


def load_mcp_adapter_config(path: Path) -> McpAdapterConfig | None:
    """Peek at an adapter YAML: return the MCP config when `kind: mcp`, else None
    (caller falls back to the REST adapter)."""
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise AdapterError(f"cannot read adapter config {path}: {exc}") from exc
    if isinstance(raw, dict) and raw.get("kind") == "mcp":
        return parse_mcp_adapter_config(raw)
    return None
