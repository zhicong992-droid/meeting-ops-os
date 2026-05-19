from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class MemoryItem:
    scope: str
    key: str
    value: dict[str, Any]


class MeetingMemoryStore:
    def __init__(self) -> None:
        self._items: list[MemoryItem] = []

    def remember(self, scope: str, key: str, value: dict[str, Any]) -> None:
        self._items.append(MemoryItem(scope=scope, key=key, value=value))

    def recall(self, scope: str, key: str | None = None) -> list[dict[str, Any]]:
        out = []
        for item in self._items:
            if item.scope != scope:
                continue
            if key and item.key != key:
                continue
            out.append(item.value)
        return out
