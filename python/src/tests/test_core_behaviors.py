import pytest

pytest.importorskip("langgraph")

from core.approvals import ApprovalGate
from core.memory import MeetingMemoryStore
from core.postgres_checkpoint import build_checkpoint_saver


def test_approval_gate_only_blocks_configured_tools():
    gate = ApprovalGate(required_tools={"jira.create_issue"})

    assert gate.needs_approval("jira.create_issue") is True
    assert gate.needs_approval("feishu.create_task") is False


def test_memory_store_filters_by_scope_and_key():
    store = MeetingMemoryStore()
    store.remember("meeting", "m-1", {"summary": "one"})
    store.remember("meeting", "m-2", {"summary": "two"})
    store.remember("user", "m-1", {"summary": "other"})

    assert store.recall("meeting") == [{"summary": "one"}, {"summary": "two"}]
    assert store.recall("meeting", "m-2") == [{"summary": "two"}]


def test_checkpoint_falls_back_to_in_memory_without_dsn():
    saver = build_checkpoint_saver(None)

    assert saver.__class__.__name__ == "InMemorySaver"
