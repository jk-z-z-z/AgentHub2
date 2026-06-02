# Group AI Reply 模块说明

本目录负责“消息落库后，是否触发 AI 回复、由谁回复、如何回复”的编排逻辑。
当前采用：

- 策略模式：回复触发与分支处理
- 执行器入口：统一回复调用与失败上报
- 记忆策略：personal / project 两种加载方式

## 统一入口

- `reply_executor.py` 中的 `ReplyExecutor.execute(...)`
- 由 `app/services/message_service.py` 在 `create_message_and_trigger_ai(...)` 中调用
- 执行器内部直接做策略调度，并统一上报 `reply.failed` 事件

## 触发顺序（策略链）

1. `PersonalAutoReplyStrategy`
   - 场景：`group.type == personal`
   - 规则：
     - personal 不支持 `@`
     - 若成员为 `user + agent`，自动触发 agent 回复
     - 若为 `user + user`，仅存消息不触发 AI

2. `ProjectManagerMentionStrategy`
   - 场景：`group.type == project` 且 `@管家`
   - 规则：
     - 管家启用时才生效
     - 由 `app.manager_runtime.facade.invoke_manager(...)` 统一处理回复、规划、落库与节点执行
     - 规划草案、确认执行、任务分配都在 `manager_runtime` 内部完成

3. `ProjectMentionedAgentsStrategy`
   - 场景：`group.type == project` 且 `@agent`
   - 规则：
     - 对被 @ 的 agent 成员并发触发回复
     - 若被 @ 成员是管家，则跳过（由管家策略处理）

4. `NoopStrategy`
   - 兜底策略，不触发任何 AI 回复

## 文件职责

- `context.py`: `ReplyContext` 与消息发射函数签名
- `helpers.py`: mention 解析、短期记忆构建
- `reply_executor.py`: 统一执行入口（包含异常事件广播）
- `reply_utils.py`: AI 回复消息封装（metadata 构造与发送）
- `strategies/base.py`: 策略接口
- `strategies/*.py`: 各场景策略实现
- `memory/base.py`: 记忆策略接口
- `memory/personal.py`: 私聊记忆加载
- `memory/project.py`: 项目记忆加载

## 调用链

`message_service.create_message_and_trigger_ai`  
-> `ReplyExecutor.execute(ctx)`  
-> `ReplyExecutor` 内部策略调度  
-> 命中策略（personal / manager / mentions / noop）  
-> 策略直接拼装上下文并调用 `agent_runtime`  
-> `ai_chat(...)` / `app.manager_runtime.facade.invoke_manager(...)`  
-> `reply_utils.emit_ai_reply(...)`

## 扩展建议

- 新增规则时优先新增策略类，避免在现有策略中追加大量 `if/else`
- 跨策略共用逻辑放在 `helpers.py`
- 保持“匹配条件”与“执行逻辑”分离，便于测试
