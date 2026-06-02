# ManagerRuntime 管家运行时包

本包负责“管家”执行：项目上下文、决策、规划、节点分配、过程事件、消息落库。

## 唯一入口
本包严格遵循封装原则，**仅对外暴露一个极简入口函数**：`invoke_manager()`

```python
from app.manager_runtime import invoke_manager

result = await invoke_manager(
    db,
    group_id=123,
    short_term_memory=[{"role": "user", "content": "帮我规划这个项目"}],
    extra_context={"purpose": "assistant", "input_text": "我们需要先做什么"},
    trace_message_id=456,
)
```

## 执行说明
- 传入 `trace_message_id` 时，本次执行会把 `manager.start`、`manager.decision`、`manager.tool.call`、`manager.tool.result`、`manager.final` 等过程事件写入对应的 `message_events`
- 外部只需要准备短期上下文和附加上下文，内部会自动完成项目上下文构建、决策、工具执行与结果封装

## 目录结构
```text
app/manager_runtime/
├── facade.py
├── schemas.py
├── trace.py
├── managerbuilder/
├── assistant/
├── tool/
├── engine/
└── skill/
```

## 执行流程
`外部调用方` -> `facade.invoke_manager(...)` -> `managerbuilder.build(...)` -> `决策/工具/规划` -> `ManagerInvokeResult`

## 设计约束
1. 禁止外部调用方绕过 Facade 层
2. 内部模块统一以下划线 `_` 命名
3. 单一职责：builder 只组装、assistant 只负责决策和规划、tool 只执行
4. 过程事件与消息强绑定

## 支持的执行模式
| 执行模式 | 标识 | 说明 |
|---|---|---|
| 对话模式 | `assistant` / `chat` | 解答、规划前置分析、工具执行后总结 |
| 规划模式 | `plan` | 生成 DAG 规划草案并返回结构化 plan |

## 你可以这样理解
- `agent_runtime` 负责数字员工
- `manager_runtime` 负责管家
- `group_task/orchestration` 负责任务调度、复盘、重规划和最终收口
- 两者现在都收敛成单一 facade，不再要求业务层理解内部模块树
