# ManagerRuntime 管家运行时包

## 企业级架构重构完成

### 唯一对外入口
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

仅需三个核心参数即可完成完整执行；如果你还想记录过程事件，再额外传 `trace_message_id` 即可，完全隐藏所有内部实现细节。

如果传入 `trace_message_id`，本次执行会把 `manager.start`、`manager.decision`、`manager.tool.call`、`manager.tool.result`、`manager.final` 等过程事件写入对应的 `message_events`。

---

### 目录结构与架构分层

```
app/manager_runtime/
├── README.md                    # 架构说明文档
├── __init__.py                  # 对外公共API暴露（仅3个符号）
├── facade.py                    # ★ Facade层：唯一入口，隐藏所有内部实现
├── schemas.py                   # 全局统一Pydantic DTO
├── trace.py                     # 管家过程事件写入封装
│
├── managerbuilder/
│   ├── __init__.py              # 私有（NOT EXPORTED）
│   └── _builder.py              # 管家上下文构建器
│
├── assistant/
│   ├── __init__.py              # 私有（NOT EXPORTED）
│   ├── decision.py              # 回复/规划决策逻辑
│   ├── doc_update.py            # 文档更新技能
│   ├── planning.py              # 规划生成与落库辅助
│   └── state_store.py           # pending_plan / pending_clarify 状态存储
│
├── tool/
│   ├── __init__.py              # 私有（NOT EXPORTED）
│   ├── _executor.py             # 管家工具执行入口
│   ├── _loader.py               # 工具加载器
│   ├── _registry.py             # 工具注册表
│   └── builtins/                # 管家内置工具实现
│
├── engine/
│   ├── __init__.py              # 兼容保留（主链路已由 facade 统一接管）
│   ├── base.py                  # 引擎抽象基类
│   ├── factory.py               # 自动调度工厂
│   └── impl_internal_llm.py     # 内部LLM引擎
│
└── skill/
    ├── __init__.py              # 私有（NOT EXPORTED）
    └── _loader.py               # 技能加载器
```

---

### 各组件交互流程图

```
外部调用方
    │
    ▼
facade.invoke_manager(group_id, short_term_memory, extra_context)
    │
    ├─> ManagerBuilder.build(group_id, extra_context)
    │    ├─> 读取项目目录 /MEMORY.md / PROFILE.md / knowledge/*
    │    ├─> 组装管家 System Prompt
    │    └─> 构建运行上下文 runtime_context
    │
    ├─> 决策与工具执行
    │    ├─> decide_manager_action(...)
    │    ├─> execute_manager_tool(...)
    │    ├─> run_doc_update_skill(...)
    │    └─> compose_reply_after_tool_calls(...)
    │
    └─> 生成最终回复或规划草案 → 返回标准 ManagerInvokeResult
```

---

### 强制架构约束

1. **禁止任何外部调用方绕过 Facade 层**：所有业务代码仅可从 `app.manager_runtime` 导入 `invoke_manager`、`ManagerInvokeRequest`、`ManagerInvokeResult` 三个符号
2. **所有内部模块以下划线`_`开头命名**：通过 Python 私有模块命名约定防止外部误导入
3. **严格单一职责原则**：每个组件唯一职责明确，无重复冗余逻辑
4. **过程事件与消息强绑定**：通过 `trace_message_id` 把管家本次执行的过程事件落到对应 `message_events`

---

### 支持的核心执行模式

| 执行模式 | purpose字符串标识 | 说明 |
|---------|-------------------|------|
| 对话模式 | `assistant` / `chat` | 解答、规划前置分析、工具执行后总结 |
| 规划模式 | `plan` | 生成 DAG 规划草案并返回结构化 plan |

---

### 你可以这样理解

- `agent_runtime` 负责“数字员工”：回复、工具调用、过程事件、消息落库
- `manager_runtime` 负责“管家”：项目上下文、决策、规划、节点分配、过程事件、消息落库
- 两者现在都收敛成单一 facade，不再要求业务层理解内部模块树
