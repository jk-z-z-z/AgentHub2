# EventRuntime 事件运行时包

本包负责统一管理 `message_id` 关联的事件日志。

## 职责
- 创建事件
- 更新事件状态
- 按 `message_id` 读取事件链并顺序 dispatch
- 按 `group_id` 拼接短期上下文
- 为 agent / manager / bootstrap 的 trace 提供统一事件写入口

## 事件语义
- `pending`：事件已创建，等待消费
- `done`：事件已被消费或处理完成
- `failed`：事件消费失败，或事件本身无法处理

## 分类
- `input_output`：消息输入、最终回复、消息状态
- `dag`：计划图、节点、边、状态编辑
- `execution`：思考、tool call、tool result、流式执行
- `task`：任务分配、认领、执行请求、完成回写、复核收口、重入队
- `system`：兜底系统事件

## Dispatch Model
- `message.created` 是多数业务链路的统一入口
- dispatcher 会按 `message_id` 扫描 pending 事件并顺序执行 handler
- trace 事件只记录过程，不会再次触发业务链路
- `node.exec.started` 会触发子 agent 执行
- `task.completed` / `task.failed` 会触发管家复核
- `task.reviewed` 作为复核收口事件，用于审计和后续追踪
