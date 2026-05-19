from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from langgraph.types import interrupt


@dataclass
class ApprovalRequest:
    tool: str
    action: str
    payload: dict[str, Any]
    reason: str = ""


@dataclass
class ApprovalDecision:
    approved: bool
    reviewer: str = "human"
    note: str = ""


@dataclass
class ApprovalGate:
    required_tools: set[str] = field(default_factory=set)

    def needs_approval(self, tool: str) -> bool:
        return tool in self.required_tools

    def request(self, request: ApprovalRequest) -> ApprovalDecision:
        decision = interrupt(
            {
                "tool": request.tool,
                "action": request.action,
                "payload": request.payload,
                "reason": request.reason,
                "message": f"Approve {request.tool}.{request.action}?",
            }
        )
        if isinstance(decision, dict):
            return ApprovalDecision(
                approved=bool(decision.get("approved", False)),
                reviewer=str(decision.get("reviewer", "human")),
                note=str(decision.get("note", "")),
            )
        return ApprovalDecision(approved=bool(decision))
