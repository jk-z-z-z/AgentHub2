# Group AI Reply 路由层

本目录负责“用户消息落库后，是否触发 AI，以及路由到哪个 runtime”的最外层分派，不承担具体执行细节。

## 唯一入口
- `handle_group_ai_reply(...)`
- 对外通过 `app.services.group_ai_reply` 导入

## 路由职责
1. `bootstrap` 群
   - 路由到 `app.bootstrap_runtime.invoke_bootstrap(...)`
   - 负责初始化对话与 bootstrap 相关内容

2. `personal` 群
   - 路由到 `agent_runtime`
   - 由路由层拼好短期上下文后交给数字员工 runtime

3. `project` 群
   - `@管家` 时路由到 `manager_runtime`
   - `@agent` 时路由到 `agent_runtime`
   - 未命中时不触发 AI

## 目录说明
- `facade.py`: 唯一调度入口，负责上下文构建、路由和兜底广播
- `reply_utils.py`: AI 回复消息写回与元数据构造

## 调用链
`message_service.create_message_and_trigger_ai` -> `handle_group_ai_reply(...)` -> `bootstrap_runtime / agent_runtime / manager_runtime`

## 说明
- 外部代码不应再直接依赖旧的策略、记忆、执行器抽象
- bootstrap 逻辑已经拆到 `bootstrap_runtime`
- 该层只负责判断、路由和兜底广播，不做任务执行
