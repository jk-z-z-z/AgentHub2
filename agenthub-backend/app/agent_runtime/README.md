# AgentRuntime 数字员工运行时包

本包负责“数字员工”执行：回复、工具调用、过程事件和消息落库。

## 唯一入口
外部只通过 `invoke_agent()` 进入本包。

```python
from app.agent_runtime import invoke_agent

result = await invoke_agent(
    db,
    agent_id=123,
    short_term_memory=[{"role": "user", "content": "你好"}],
    extra_context={"user_id": 1, "input_text": "帮我分析需求"},
)
```

## 当前分层
- `facade.py`：统一入口，只做编排
- `agentbuilder/`：拼装系统提示词、上下文和 `Toolkit`
- `engine/`：负责模型执行与回包
- `skill/`：放数字员工规则和最佳实践
- `tool/`：放数字员工可直接调用的工具

## 设计口径
- 工具、技能、MCP 保持 AgentScope 原生接法
- `Toolkit(skills_or_loaders=..., tools=..., tool_groups=...)` 统一挂载
- `event_runtime` 负责事件路由与回复写回，不承担模型执行细节
- 本包不承担 `manager_runtime` 或 `bootstrap_runtime` 的执行逻辑
