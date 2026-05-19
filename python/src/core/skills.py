from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable


SkillHandler = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]


@dataclass
class Skill:
    name: str
    description: str
    handler: SkillHandler


class SkillRegistry:
    def __init__(self) -> None:
        self._skills: dict[str, Skill] = {}

    def register(self, skill: Skill) -> None:
        self._skills[skill.name] = skill

    def get(self, name: str) -> Skill | None:
        return self._skills.get(name)

    def list(self) -> list[Skill]:
        return list(self._skills.values())


def build_default_skill_registry() -> SkillRegistry:
    return SkillRegistry()
