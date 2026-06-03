# ManagerRuntime 管家运行时包

本包负责“管家”执行：对话澄清、任务规划、DAG 编辑、节点分配与节点执行。

## 唯一入口
外部只通过 `invoke_manager()` 进入本包。

```python
from app.manager_runtime import invoke_manager

result = await invoke_manager(
    db,
    group_id=123,
    short_term_memory=[{"role": "user", "content": "帮我规划这个项目"}],
    extra_context={"purpose": "assistant", "input_text": "我们需要先做什么"},
)
```

## 当前分层
- `facade.py`：统一入口，只做编排
- `managerbuilder/`：拼装系统提示词、上下文和 `Toolkit`
- `engine/`：统一使用 `agentscope_react`
- `skill/`：放流程规则和最佳实践
- `tool/`：放管家可直接调用的执行工具，直接调用 `group_task_service`
- 短期上下文由群聊事件流拼接，`messages` 只作为展示层
- 项目长期记忆压缩基于事件流抽取，不直接依赖展示消息正文

## 设计口径
- 管家能力全部留在本包，不再依赖旧的分散编排层
- 工具直接按 AgentScope `ToolBase` 方式接入 `Toolkit`
- `group_task_service` 只保留最小的图与节点状态能力
- 本包不调用 `agent_runtime` 的执行入口，运行链路完全独立
- 本包不再保留单次直出式 internal LLM 分支
- 项目记忆压缩默认只由管家自身决策触发；若上下文事件 token 已超过阈值，则会在 `invoke_manager()` 入口自动先压缩一次再继续执行
