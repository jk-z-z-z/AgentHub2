# ManagerRuntime 管家运行时包

`manager_runtime` 独立于 `agent_runtime`，用于群聊项目管家的上下文拼装、对话与规划入口。
外部只通过 `facade.py` 进入，内部模块仅供运行时调用。

## 目录结构

```text
app/manager_runtime/
├── README.md
├── __init__.py
├── facade.py
├── schemas.py
├── managerbuilder/
│   ├── __init__.py
│   └── _builder.py
├── assistant/
│   ├── __init__.py
│   ├── decision.py
│   ├── doc_update.py
│   ├── planning.py
│   ├── state_store.py
├── engine/
│   ├── __init__.py
│   ├── base.py
│   ├── factory.py
│   └── impl_internal_llm.py
├── skill/
│   ├── __init__.py
│   └── _loader.py
└── tool/
    ├── __init__.py
    ├── _executor.py
    ├── _loader.py
    ├── _registry.py
    └── builtins/
        ├── __init__.py
        ├── delegate_node.py
        ├── pending_state.py
        ├── plan_apply.py
        └── project_md.py
```
