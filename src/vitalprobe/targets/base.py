"""Target adapter protocol: anything that can carry a conversation to the tested bot."""

from typing import Protocol

from vitalprobe.schema import ResponseMeta, Turn


class TargetAdapter(Protocol):
    name: str

    @property
    def endpoint_redacted(self) -> str: ...

    async def send(self, turns: list[Turn]) -> ResponseMeta: ...

    async def aclose(self) -> None: ...
