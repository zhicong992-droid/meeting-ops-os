from __future__ import annotations

from typing import Any

from ..core.mcp_gateway import MCPGateway


def build_meeting_mcp_gateway() -> MCPGateway:
    gateway = MCPGateway()
    gateway.register(
        "jira",
        {
            "create_issue": lambda payload: {"status": "queued", "payload": payload},
            "update_issue": lambda payload: {"status": "queued", "payload": payload},
        },
    )
    gateway.register(
        "feishu",
        {
            "send_message": lambda payload: {"status": "queued", "payload": payload},
            "create_task": lambda payload: {"status": "queued", "payload": payload},
        },
    )
    gateway.register(
        "email",
        {
            "send": lambda payload: {"status": "queued", "payload": payload},
        },
    )
    return gateway
