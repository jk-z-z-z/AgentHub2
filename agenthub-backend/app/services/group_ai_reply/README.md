# Group AI Reply 模块说明

本目录负责“消息落库后，是否触发 AI 回复、由谁回复、如何回复”的编排逻辑。

## 入口

- `engine.py` 中的 `GroupAiReplyEngine.handle(...)`
- 由 `app/services/message_service.py` 在 `create_message_and_trigger_ai(...)` 中调用

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
- `engine.py`: 策略选择与调度
- `strategies/base.py`: 策略接口
- `strategies/*.py`: 各场景策略实现

## 扩展建议

- 新增规则时优先新增策略类，避免在现有策略中追加大量 `if/else`
- 跨策略共用逻辑放在 `helpers.py`
- 保持“匹配条件”与“执行逻辑”分离，便于测试
