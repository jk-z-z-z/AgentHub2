# BootstrapRuntime 初始化运行时包

本包只负责智能体初始化 / bootstrap 流程，不承担普通消息回复或项目任务执行。

## 唯一入口
- `invoke_bootstrap()`

## 职责范围
- 读取 agent 工作区中的 `SOUL.md`、`PROFILE.md`、`BOOTSTRAP.md`
- 组装 bootstrap 专用 `system_prompt`
- 调用 `agent_runtime` 执行初始化对话
- 写回 bootstrap 消息并记录过程事件

## 目录结构
- `facade.py`: bootstrap 唯一对外入口，负责编排
- `bootstrapbuilder/`: bootstrap 上下文与 prompt 构建
- `schemas.py`: 对外请求与结果结构
- `trace.py`: bootstrap 过程事件写入

## 调用链
`group_ai_reply` -> `invoke_bootstrap(...)` -> `bootstrapbuilder.build_complete_bootstrap(...)` -> `agent_runtime.invoke_agent(...)` -> `message_store.update_message(...)`

## 设计原则
- 上层只负责路由，bootstrap 细节全部留在本包
- facade 只编排，不拼 prompt、不拼上下文细节
- 后续 bootstrap 规则变化，优先放进 `bootstrapbuilder`
