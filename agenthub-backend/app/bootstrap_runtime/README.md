# BootstrapRuntime 初始化运行时包

本包只负责智能体初始化 / bootstrap 流程，不承担普通消息回复或项目任务执行。

## 唯一入口
外部只通过 `invoke_bootstrap()` 进入本包。

## 职责范围
- 读取 agent 工作区中的 `SOUL.md`、`PROFILE.md`、`BOOTSTRAP.md`
- 组装 bootstrap 专用 `system_prompt`
- 挂载 bootstrap 专用 skill loader 与工具后，在本包内直接执行
- 写回 bootstrap 消息并记录过程事件

## 当前分层
- `facade.py`：bootstrap 唯一对外入口
- `bootstrapbuilder/`：bootstrap 上下文与 prompt 构建
- `skill/`：bootstrap 专用规则与技能
- `trace.py`：bootstrap 过程事件写入

## 调用链
`event_runtime.handlers.message` -> `invoke_bootstrap(...)` -> `bootstrapbuilder.build_complete_bootstrap(...)` -> `bootstrap_runtime.engine.run(...)`

## 设计口径
- bootstrap 是独立运行时，不复用 `agent_runtime.invoke_agent()`
- 本包只负责初始化流程，不承担普通群聊回复与项目执行
