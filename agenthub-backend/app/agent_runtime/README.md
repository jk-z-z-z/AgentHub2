# AgentRuntime 数字员工运行时包

本包负责“数字员工”执行：回复、工具调用、过程事件、消息落库。

## 唯一入口
本包严格遵循封装原则，**仅对外暴露一个极简入口函数**：`invoke_agent()`

```python
from app.agent_runtime import invoke_agent

result = await invoke_agent(
    db,
    agent_id=123,
    short_term_memory=[{"role": "user", "content": "你好"}],
    extra_context={"user_id": 1, "input_text": "帮我分析需求"},
    trace_message_id=456,
)
```

## 执行说明
- 传入 `trace_message_id` 时，本次执行会把 `run.started`、`tool.call`、`tool.result`、`run.finished` 等过程事件写入对应的 `message_events`
- 外部只需要准备短期上下文和附加上下文，内部会自动完成 agent 构建、工具加载、引擎路由和结果封装

## 目录结构
```text
app/agent_runtime/
├── facade.py
├── schemas.py
├── agentbuilder/
├── tool/
├── skill/
├── mcp/
└── engine/
```

## 执行流程
`外部调用方` -> `facade.invoke_agent(...)` -> `agentbuilder.build(...)` -> `engine.run(...)` -> `AgentInvokeResult`

## 设计约束
1. 禁止外部调用方绕过 Facade 层
2. 内部模块统一以下划线 `_` 命名
3. 单一职责：builder 只组装、engine 只推理、tool 只执行
4. Tool / Skill / MCP 三类加载器保持对称

## 支持的推理后端
| 引擎类型 | 标识 | 说明 |
|---|---|---|
| 内部 LLM | `internal_llm` | 直接调用 OpenAI 兼容接口 |
| Codex | `acp:codex` | ACP 协议对接外部运行器 |
| Claude Code | `acp:claude_code` | ACP 协议对接外部运行器 |
| AgentScope ReAct | `agentscope_react` | AgentScope 原生 ReAct 智能体 |

## 你可以这样理解
- `group_ai_reply` 负责路由
- `agent_runtime` 负责数字员工执行
- `trace_message_id` 绑定的是这次执行过程，不是路由层
