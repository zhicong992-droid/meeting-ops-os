from __future__ import annotations

from dataclasses import dataclass
import inspect
from typing import Any


@dataclass
class MCPToolCall:
    tool: str
    action: str
    payload: dict[str, Any]


class MCPGateway:
    def __init__(self) -> None:
        self._handlers: dict[str, Any] = {}

    def register(self, name: str, handler: Any) -> None:
        self._handlers[name] = handler

    async def call(self, call: MCPToolCall) -> dict[str, Any]:
        handler = self._handlers.get(call.tool)
        if handler is None:
            raise ValueError(f"Unknown MCP tool: {call.tool}")
        result = handler.get(call.action)
        if result is None:
            raise ValueError(f"Unknown MCP action: {call.tool}.{call.action}")
        if callable(result):
            out = result(call.payload)
            if inspect.isawaitable(out):
                return await out
            return out
        return result
