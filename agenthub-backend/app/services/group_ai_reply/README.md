# Group AI Reply 模块说明

本目录负责“消息落库后，是否触发 AI 回复、由谁回复、如何回复”的编排逻辑。
当前采用：

- 工厂模式：角色 Agent 组装
- 策略模式：回复触发与分支处理
- 执行器入口：统一回复调用与失败上报
- 记忆策略：personal / project 两种加载方式

## 统一入口

- `reply_executor.py` 中的 `ReplyExecutor.execute(...)`
- 由 `app/services/message_service.py` 在 `create_message_and_trigger_ai(...)` 中调用
- 执行器内部调用 `GroupAiReplyEngine`，并统一上报 `reply.failed` 事件

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
     - 先生成规划草案，等待“确认/同意”
     - 仅草案发起人可确认落库
     - 确认后执行 DAG upsert + 自动分配 + agent 节点执行

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
- `agent_factory.py`: 角色 Agent 工厂（Assistant / Manager）
- `reply_executor.py`: 统一执行入口（包含异常事件广播）
- `engine.py`: 策略选择与调度
- `reply_utils.py`: AI 回复消息封装（metadata 构造与发送）
- `strategies/base.py`: 策略接口
- `strategies/*.py`: 各场景策略实现
- `agents/base.py`: 角色 Agent 基类
- `agents/assistant_agent.py`: 助手 Agent（personal/project 回复）
- `agents/manager_agent.py`: 管家 Agent（规划草案生成）
- `memory/base.py`: 记忆策略接口
- `memory/personal.py`: 私聊记忆加载
- `memory/project.py`: 项目记忆加载

## 调用链

`message_service.create_message_and_trigger_ai`  
-> `ReplyExecutor.execute(ctx)`  
-> `GroupAiReplyEngine.handle(ctx)`  
-> 命中策略（personal / manager / mentions / noop）  
-> `AgentFactory` 组装角色 Agent  
-> 角色 Agent 加载对应记忆策略  
-> `ai_chat(...)` / 规划工具  
-> `reply_utils.emit_ai_reply(...)`

## 扩展建议

- 新增规则时优先新增策略类，避免在现有策略中追加大量 `if/else`
- 跨策略共用逻辑放在 `helpers.py`
- 保持“匹配条件”与“执行逻辑”分离，便于测试
