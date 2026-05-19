# MeetingOpsOS

- 作者：`zhicong992-droid`
- 版权：`Copyright © 2026 zhicong992-droid. All rights reserved.`
- 版本：`2.0.0`
- 更新时间：`2026-05-19`

MeetingOpsOS 是一个面向会议执行与会后协同的多智能体系统。它把转写、摘要、行动项提取、洞察分析、跟进生成、工具调用审批和会话恢复放进同一个运行框架里，重点是把“会议结束后的人工整理动作”压缩成可审计、可恢复的自动化流程。

## 核心目标

- 接收真实音频或直接运行演示链路
- 输出结构化纪要、待办、洞察与跟进结果
- 对 Jira、飞书、邮件等写操作设置人工确认
- 支持恢复中断会议，而不是从头重复执行
- 为会议流程保留上下文、审计和工具调用边界

## 执行路径

`Audio -> Transcription -> Approval -> Summary / Action / Insight -> Follow-up`

主要能力拆分如下：

- `Checkpoint`：把会议状态写入持久化存储，支持恢复
- `Approval Gate`：所有外部写入先过人工闸门
- `MCP Gateway`：统一管理工具调用入口
- `Skill Registry`：把常用会议业务逻辑抽成可复用模块
- `Memory Layer`：保存会议上下文与后续复用信息

## 当前实现

- 语言与运行时：Python
- 服务接口：FastAPI + WebSocket
- 编排框架：LangGraph
- 存储：Postgres + Redis
- 模型接入：OpenAI 兼容接口 / MiniMax
- 语音链路：WhisperX
- 外部系统：Jira / Feishu / HTTP 工具

## 项目布局

- `python/src/graph`：会议流程图与编排逻辑
- `python/src/agents`：转写、摘要、行动、洞察、跟进等智能体
- `python/src/core`：审批、配置、MCP、记忆、checkpoint
- `python/src/integrations`：第三方服务适配层
- `python/src/websocket`：实时会话接口

## 启动方式

```bash
cd python
source .venv/bin/activate
uvicorn src.websocket.server:app --host 0.0.0.0 --port 18000
```

常用配置项：

- `MINIMAX_API_KEY`
- `MINIMAX_GROUP_ID`
- `OPENAI_API_KEY`
- `OPENAI_BASE_URL`
- `POSTGRES_DSN`
- `DATABASE_URL`
- `MEETING_MEMORY_DSN`
- `REDIS_URL`
- `SERVER_PORT`

公开模板：

```env
MINIMAX_API_KEY=your_minimax_api_key_here
MINIMAX_GROUP_ID=your_minimax_group_id_here
MINIMAX_MODEL=abab6.5s-chat
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o
POSTGRES_DSN=postgresql://postgres:password@localhost:5432/meeting_ops_os
DATABASE_URL=postgresql://postgres:password@localhost:5432/meeting_ops_os
MEETING_MEMORY_DSN=postgresql://postgres:password@localhost:5432/meeting_ops_os
REDIS_URL=redis://localhost:6379/0
SERVER_HOST=0.0.0.0
SERVER_PORT=18000
WEBSOCKET_PORT=8001
LOG_LEVEL=INFO
```

## 主要接口

REST：

- `GET /`
- `POST /api/v1/meeting/start`
- `POST /api/v1/meeting/{meeting_id}/upload`
- `POST /api/v1/meeting/{meeting_id}/demo`
- `POST /api/v1/meeting/{meeting_id}/resume`
- `GET /api/v1/meeting/{meeting_id}/transcript`
- `GET /api/v1/meeting/{meeting_id}/summary`
- `GET /api/v1/meeting/{meeting_id}/actions`
- `GET /api/v1/meeting/{meeting_id}/insights`
- `GET /api/v1/meeting/{meeting_id}/report`

WebSocket：

- `ws://host/ws/meeting/{meeting_id}`

## 系统行为

- 会议可以从已保存状态继续执行
- 外部写入不会直接放行，而是先进入审批步骤
- 报告接口会汇总 `transcript`、`summary`、`actions`、`insights` 与 `followup`
- 当语音环境缺依赖时，系统可以降级，但不会让整体流程直接中断

## 适用对象

- 需要自动生成会后输出的会议组织者
- 需要追踪任务分发和审批动作的项目负责人
- 负责接入企业工具系统的平台工程师
- 想展示 LangGraph、MCP、技能化设计和工具安全治理能力的作品集作者

## 设计原则

- 把外部副作用和智能体逻辑分开，避免业务节点直接写第三方系统
- 把审批做成运行时能力，而不是额外的人肉流程
- 把恢复能力放在工作流层，而不是靠脚本补救
- 把高频会议逻辑抽成技能，降低重复 prompt 和重复分发逻辑
