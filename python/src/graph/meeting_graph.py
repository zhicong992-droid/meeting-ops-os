"""
LangGraph 会议处理图 —— 多Agent编排核心

编排模式: Pipeline + 并行 (Fan-out / Fan-in)

    ┌─────────────┐
    │   START     │
    └──────┬──────┘
           │
           ▼
    ┌──────────────┐
    │ Transcription│  ← Pipeline 阶段
    │    Agent     │
    └──────┬───────┘
           │
    ┌──────┼───────┐  ← Fan-out (并行)
    │      │       │
    ▼      ▼       ▼
  Summary Action Insight
  Agent   Agent  Agent
    │      │       │
    └──────┼───────┘  ← Fan-in (汇聚)
           │
           ▼
    ┌──────────────┐
    │  Follow-up   │
    │    Agent     │
    └──────┬───────┘
           │
           ▼
    ┌──────────────┐
    │     END      │
    └──────────────┘

面试考点:
- LangGraph 的 State/Node/Edge 分别是什么？
- 并行执行是怎么实现的？（Fan-out + Fan-in）
- 如果某个并行节点失败了怎么办？（错误写入state，不阻塞其他节点）
"""

from __future__ import annotations

import asyncio
from typing import Any, TypedDict, Annotated

from langgraph.graph import StateGraph, START, END
from langgraph.types import Command
from loguru import logger

from ..agents.transcription_agent import TranscriptionAgent, TranscriptionConfig
from ..agents.summary_agent import SummaryAgent
from ..agents.action_agent import ActionAgent
from ..agents.insight_agent import InsightAgent
from ..agents.followup_agent import FollowUpAgent
from ..agents.skills import summarize_meeting_skill, distribute_actions_skill, followup_template_skill
from ..agents.mcp_tools import build_meeting_mcp_gateway
from ..integrations.minimax_client import MiniMaxClient
from ..integrations.jira_client import JiraClient
from ..integrations.feishu_client import FeishuClient
from ..models.schemas import (
    MeetingState,
    MeetingStatus,
    create_initial_state,
)
from ..core.approvals import ApprovalGate, ApprovalRequest
from ..core.config import settings as app_settings
from ..core.memory import MeetingMemoryStore
from ..core.postgres_checkpoint import build_checkpoint_saver
from ..core.mcp_gateway import MCPToolCall
from ..core.skills import Skill, build_default_skill_registry


# ============================================================
# LangGraph 状态类型定义
# ============================================================

class GraphState(TypedDict, total=False):
    """
    LangGraph 使用 TypedDict 定义状态结构。
    每个 Node（Agent）都读写这个共享状态。
    """
    meeting_id: str
    status: str
    audio_data: bytes

    # Transcription 输出
    transcript: Any
    transcript_text: str

    # 并行 Agent 输出
    summary: Any
    actions: Any
    insights: Any

    # Follow-up 输出
    followup: Any

    # 错误记录
    errors: list[str]
    approvals: list[dict[str, Any]]
    memory_scope: str


# ============================================================
# 构建 Meeting Graph
# ============================================================

def build_meeting_graph(
    llm_client: MiniMaxClient | None = None,
    jira_client: JiraClient | None = None,
    feishu_client: FeishuClient | None = None,
    transcription_config: TranscriptionConfig | None = None,
) -> StateGraph:
    """
    构建会议处理 StateGraph

    这是整个系统的编排核心：
    1. 创建 5 个 Agent 实例
    2. 将它们注册为 Graph 的 Node
    3. 定义 Edge（流转关系）
    4. 编译为可执行的 Graph

    Args:
        llm_client: LLM 客户端（共享，避免重复创建）
        jira_client: Jira 客户端
        feishu_client: 飞书客户端
        transcription_config: 转写配置

    Returns:
        编译后的 StateGraph
    """
    # 共享依赖
    llm = llm_client or MiniMaxClient()
    jira = jira_client or JiraClient()
    feishu = feishu_client or FeishuClient()
    approval_gate = ApprovalGate(required_tools=set(app_settings.approval_required_tools))
    memory_store = MeetingMemoryStore()
    skill_registry = build_default_skill_registry()
    skill_registry.register(Skill("summary", "会议摘要技能", summarize_meeting_skill))
    skill_registry.register(Skill("actions", "待办分发技能", distribute_actions_skill))
    skill_registry.register(Skill("followup", "跟进模板技能", followup_template_skill))
    mcp_gateway = build_meeting_mcp_gateway()

    # 创建 Agent 实例
    transcription_agent = TranscriptionAgent(transcription_config)
    summary_agent = SummaryAgent(llm)
    action_agent = ActionAgent(llm, jira, feishu)
    insight_agent = InsightAgent(llm)
    followup_agent = FollowUpAgent(feishu)

    # ---- 构建 StateGraph ----
    graph = StateGraph(GraphState)

    # 注册节点（Node = Agent）
    # 并行节点只回传本节点产出，避免整份 state 在同一步被并发写冲突。
    async def transcription_node(state: dict) -> dict:
        out = await transcription_agent.process(dict(state))
        return {
            "status": out.get("status"),
            "transcript": out.get("transcript"),
            "transcript_text": out.get("transcript_text", ""),
        }

    async def approval_node(state: dict) -> dict:
        # Approval decisions are produced by action_node where external writes are prepared.
        return {}

    async def summary_node(state: dict) -> dict:
        out = await summary_agent.process(dict(state))
        memory_store.remember("meeting", state.get("meeting_id", "unknown"), {"summary": out.get("summary").model_dump() if out.get("summary") else {}})
        return {"summary": out.get("summary")}

    async def action_node(state: dict) -> dict:
        out = await action_agent.process(dict(state))
        actions = out.get("actions")
        if not actions or not actions.action_items:
            return {"actions": actions}

        payload = {
            "meeting_id": state.get("meeting_id"),
            "items": [i.model_dump() for i in actions.action_items],
        }
        approvals: list[dict[str, Any]] = []

        if approval_gate.needs_approval("jira.create_issue"):
            decision = approval_gate.request(
                ApprovalRequest(
                    tool="jira.create_issue",
                    action="create_issue",
                    payload=payload,
                    reason="外部系统写入：创建 Jira issue",
                )
            )
            approvals.append(decision.__dict__)
            if not decision.approved:
                return {"actions": actions, "approvals": approvals}

        jira_res = await mcp_gateway.call(
            MCPToolCall(tool="jira", action="create_issue", payload=payload)
        )
        if jira_res.get("status") == "queued":
            for item in actions.action_items:
                if not item.jira_issue_key:
                    item.jira_issue_key = "QUEUED"

        if approval_gate.needs_approval("feishu.create_task"):
            decision = approval_gate.request(
                ApprovalRequest(
                    tool="feishu.create_task",
                    action="create_task",
                    payload=payload,
                    reason="外部系统写入：创建飞书任务",
                )
            )
            approvals.append(decision.__dict__)
            if decision.approved:
                feishu_res = await mcp_gateway.call(
                    MCPToolCall(tool="feishu", action="create_task", payload=payload)
                )
                if feishu_res.get("status") == "queued":
                    for item in actions.action_items:
                        if not item.feishu_task_id:
                            item.feishu_task_id = "QUEUED"

        return {"actions": actions, "approvals": approvals}

    async def insight_node(state: dict) -> dict:
        out = await insight_agent.process(dict(state))
        return {"insights": out.get("insights")}

    async def followup_node(state: dict) -> dict:
        out = await followup_agent.process(dict(state))
        skill = skill_registry.get("followup")
        if skill:
            await skill.handler(dict(state))
        return {
            "status": out.get("status"),
            "followup": out.get("followup"),
            "errors": out.get("errors", state.get("errors", [])),
        }

    graph.add_node("transcription", transcription_node)
    graph.add_node("approval", approval_node)
    graph.add_node("summary", summary_node)
    graph.add_node("action", action_node)
    graph.add_node("insight", insight_node)
    graph.add_node("followup", followup_node)

    # ---- 定义边（Edge = 流转关系）----

    # Pipeline 阶段: START → Transcription
    graph.add_edge(START, "transcription")

    # Fan-out 并行: Transcription → [Summary, Action, Insight]
    graph.add_edge("transcription", "approval")
    graph.add_edge("approval", "summary")
    graph.add_edge("approval", "action")
    graph.add_edge("approval", "insight")

    # Fan-in 汇聚: [Summary, Action, Insight] → Follow-up
    graph.add_edge("summary", "followup")
    graph.add_edge("action", "followup")
    graph.add_edge("insight", "followup")

    # 结束: Follow-up → END
    graph.add_edge("followup", END)

    logger.info("Meeting graph built successfully")
    return graph


_COMPILED_GRAPH = None
_CHECKPOINTER_READY = False


def compile_meeting_graph(**kwargs) -> Any:
    """构建并编译 Graph（编译后可直接调用）"""
    graph = build_meeting_graph(**kwargs)
    compiled = graph.compile(
        checkpointer=build_checkpoint_saver(app_settings.postgres_dsn)
    )
    logger.info("Meeting graph compiled successfully")
    return compiled


def get_meeting_graph(**kwargs) -> Any:
    global _COMPILED_GRAPH
    if _COMPILED_GRAPH is None:
        _COMPILED_GRAPH = compile_meeting_graph(**kwargs)
    return _COMPILED_GRAPH


async def run_meeting_pipeline(
    meeting_id: str,
    audio_data: bytes = b"",
    **kwargs,
) -> dict:
    """
    执行完整的会议处理 Pipeline

    这是对外暴露的主入口函数：
    1. 创建初始状态
    2. 编译 Graph
    3. 执行 Graph
    4. 返回最终状态

    Args:
        meeting_id: 会议ID
        audio_data: 音频数据（为空则使用演示数据）

    Returns:
        最终的 MeetingState 字典
    """
    logger.info(f"Starting meeting pipeline: {meeting_id}")

    initial_state = create_initial_state(meeting_id, audio_data)
    compiled_graph = get_meeting_graph(**kwargs)
    global _CHECKPOINTER_READY
    if not _CHECKPOINTER_READY:
        checkpointer = getattr(compiled_graph, "checkpointer", None)
        if checkpointer is not None and hasattr(checkpointer, "setup"):
            try:
                setup_fn = getattr(checkpointer, "setup")
                maybe_coro = setup_fn()
                if asyncio.iscoroutine(maybe_coro):
                    await maybe_coro
            except Exception:
                pass
        _CHECKPOINTER_READY = True

    final_state = await compiled_graph.ainvoke(
        initial_state,
        config={"configurable": {"thread_id": meeting_id}},
    )

    errors = final_state.get("errors", [])
    if errors:
        logger.warning(f"Pipeline completed with errors: {errors}")
    else:
        logger.info(f"Pipeline completed successfully for: {meeting_id}")

    return final_state
