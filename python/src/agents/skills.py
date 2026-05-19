from __future__ import annotations

from typing import Any


async def summarize_meeting_skill(state: dict[str, Any]) -> dict[str, Any]:
    return {"summary_skill": True, "meeting_id": state.get("meeting_id")}


async def distribute_actions_skill(state: dict[str, Any]) -> dict[str, Any]:
    return {"action_skill": True, "meeting_id": state.get("meeting_id")}


async def followup_template_skill(state: dict[str, Any]) -> dict[str, Any]:
    return {"followup_skill": True, "meeting_id": state.get("meeting_id")}
