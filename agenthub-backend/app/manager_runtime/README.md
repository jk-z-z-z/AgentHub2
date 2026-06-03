# ManagerRuntime 管家运行时包

本包负责“管家”执行：对话澄清、任务规划、DAG 编辑、节点分配、执行请求发起、节点复核。

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
- `tool/`：放管家可直接调用的工具，节点执行以事件驱动方式下发，不直接越过 dispatcher
- 短期上下文由群聊事件流拼接，`messages` 只作为展示层

## 设计口径
- 管家能力全部留在本包，不再依赖旧的分散编排层
- 工具直接按 AgentScope `ToolBase` 方式接入 `Toolkit`
- `group_task_service` 只保留最小的图与节点状态能力
- `node_execute` 只写执行请求事件；事件解析器负责调用子 agent；复核结果再回写节点状态
- 本包不再保留单次直出式 internal LLM 分支
- 管家可以复核 `task.completed` / `task.failed`，必要时通过 `node_requeue` 或 `node_complete` 兜底
