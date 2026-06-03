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
- `engine/`：目前以 `agentscope_react` 为主
- `skill/`：放流程规则和最佳实践
- `tool/`：放管家可直接调用的执行工具

## 设计口径
- 管家能力全部留在本包，不再依赖旧的分散编排层
- 工具直接按 AgentScope `ToolBase` 方式接入 `Toolkit`
- `group_task` 只保留最小的图与节点状态能力，后续再继续瘦身
