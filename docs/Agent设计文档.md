# AgentHub Agent 设计文档

## 1. 设计目标

AgentHub 的 Agent 体系是一个分层协作系统。核心目标有三点：

- 让不同职责的 Agent 有清晰边界。
- 让复杂任务可由上层规划、下层执行。
- 让子 Agent 的执行不阻塞主流程。

当前系统将 Agent 运行时拆为三类：`manager agent`、`worker agent`、`bootstrap agent`。

## 2. 协作机制总览

### 2.1 AgentHub 的重点是协作

AgentHub 的设计重点是让多个 Agent 在一个真实团队场景中能够稳定协作。

因此在 Agent 设计上，优先级最高的是：

- 如何分层职责
- 如何共享上下文
- 如何分发任务
- 如何异步回收执行结果
- 如何让 manager 对 worker 形成治理闭环

### 2.2 两种核心协作路径

当前系统支持两种核心路径：

- `复杂任务路径`：manager 负责 `Plan and Execute`
- `简单任务路径`：用户直接 `@worker agent`

这两种路径共同组成了多人多 Agent 协作的完整体验。

### 2.3 为什么采用事件驱动

如果 manager 在发起任务后同步等待 worker 返回，系统会很快失去可扩展性。因此当前 Agent 体系建立在事件驱动机制之上：

- manager 发送执行请求事件
- worker 异步执行
- worker 写回完成/失败事件
- manager 再做复核与后续安排

这保证了 manager 以调度者角色持续推进协作流程。

## 3. 角色划分

### 3.1 Manager Agent

Manager Agent 是项目群聊中的管家，核心职责是治理协作过程、组织任务推进和结果收口。

职责包括：

- 理解和澄清用户目标
- 将复杂任务拆为可执行 DAG
- 根据角色要求分配节点
- 触发节点执行
- 在子 Agent 完成后复核结果
- 必要时修改 DAG、返工或重新分派

设计原则：

- Manager 是群聊附属能力，不建模为普通独立数字员工。
- Manager 主要面向项目全局。
- Manager 通过事件触发执行，不同步等待子 Agent 完成。

### 3.2 Worker Agent

Worker Agent 是执行型数字员工，面向具体任务和工具操作。

职责包括：

- 响应单聊中的用户请求
- 响应项目群聊中的 `@提及`
- 执行 DAG 节点
- 调用工具、读写代码、运行命令、预览和部署

设计原则：

- Worker 关注“做事”，不负责全局规划。
- Worker 的结果会写入事件流，供 Manager 或用户后续消费。
- Worker 可以有不同引擎实现，如 internal llm、codex、claude code、agentscope react。

### 3.3 Bootstrap Agent

Bootstrap Agent 是初始化阶段的专用执行体。

职责包括：

- 读取 Agent 启动资料
- 初始化运行空间
- 为正式协作准备必要文件与上下文

设计原则：

- Bootstrap 与普通执行隔离。
- 初始化完成后，正式任务交由 Worker / Manager 处理。

## 4. 上下文设计

### 4.1 基本原则

AgentHub 采用“外部注入运行时上下文，内部装配角色材料”的模式。

外部注入：

- 会话类型
- 用户输入
- group_id / project_id / user_id
- run_id / node_id / source_message_id
- trace_message_id

内部装配：

- Agent 的 `SOUL.md`
- Agent 的 `PROFILE.md`
- User / Project 的 `PROFILE.md`
- User / Project 的 `MEMORY.md`
- bootstrap 的 `BOOTSTRAP.md`
- runtime 对应的 skill / tool / MCP

这样可以保证：

- 业务链路可控制当前任务上下文。
- Agent 角色资源由各 runtime 自治，便于演进。

### 4.2 Manager 上下文

Manager 上下文更偏项目治理，主要包含：

- 项目信息与根目录
- 长期记忆摘要
- README 与知识文档预览
- 当前短期对话摘要
- 可分配 Agent 成员列表
- 管家技能说明
- 当前任务目的，如 `assistant`、`evaluation`、`node_review`

Manager 围绕“当前项目目标是否被正确推进”运转。

### 4.3 Worker 上下文

Worker 上下文按场景分两种：

- 单聊：Agent + User 维度上下文
- 项目群聊：Agent + Project 维度上下文

在项目场景中，Worker 可以带上 `run_id`、`node_id` 等任务上下文，从而把对话执行与 DAG 节点绑定起来。

### 4.4 Bootstrap 上下文

Bootstrap 上下文强调“初始化资料完整性”，包括：

- Agent 人设
- Agent 初始化说明
- User 基础画像与记忆
- bootstrap 专属工具和技能

## 5. 协作模式

### 5.1 复杂任务协作

复杂任务采用 `Plan and Execute`：

1. 用户 `@管家`
2. Manager 分析需求
3. Manager 产出或更新 DAG
4. Manager 分配节点并发送执行事件
5. Worker 执行节点
6. Worker 回写结果事件
7. Manager 复核并决定通过、返工或重排

这个流程体现的是“上层负责规划，下层负责执行”。

### 5.2 简单任务协作

简单任务支持直接 `@子 Agent`：

1. 用户 `@Agent`
2. Worker 直接接收并执行
3. 结果写回群聊
4. 如带任务上下文，Manager 可在后续介入评估

这个流程适合短平快任务，不必每次都经过完整规划链路。

## 6. 事件驱动机制

### 6.1 事件驱动原因

如果主 Agent 在发出任务后必须一直等待子 Agent 完成，会出现几个问题：

- 用户等待时间变长
- 管家无法并行调度其他节点
- 长任务和失败恢复难以处理
- 系统很难准确记录执行过程

因此当前设计采用事件驱动：

- Manager 发出 `node.exec.started` 或相关任务事件
- Dispatcher 异步触发 Worker 执行
- Worker 完成后写入 `task.completed` / `task.failed`
- Manager 再收到事件并做复核

### 6.2 事件驱动收益

- 主流程与执行流程解耦
- 适合并行子任务
- 容易支持重试、重入队和审计
- 用户能持续获得“已开始执行”的即时反馈

## 7. 工具与能力边界

### 7.1 Manager 工具边界

Manager 工具主要用于：

- DAG 查看与编辑
- 节点状态管理
- 节点执行下发
- 项目治理辅助

Manager 负责治理和编排，Worker 负责具体执行。

### 7.2 Worker 工具边界

Worker 工具主要用于：

- 文件读写
- 项目代码读写
- 命令执行
- 预览与部署
- Agent 资料更新

Worker 可以执行具体动作，但不负责全局调度。

### 7.3 Bootstrap 工具边界

Bootstrap 工具只服务初始化，不进入正式项目执行链路。

## 8. 当前代码中的落地特征

从现有实现看，Agent 设计已经具备以下特征：

- 三类 runtime 都有各自独立 facade、builder、engine、tool/skill 装配入口。
- Manager 与 Worker 的上下文拼接方案明显不同。
- 短期上下文来自事件流。
- 节点执行完成与否会结合真实产物判定，而非只信模型文本。
- 项目群聊已经具备 Run、节点、流程图和复核 UI。

## 9. 后续优化建议

- 为 Worker 增加更清晰的角色标签与能力标签，提升自动分派准确率。
- 为 Manager 增加跨轮目标跟踪能力，减少复杂需求反复偏航。
- 为 Bootstrap 增加模板化初始化流程，支持不同 Agent 类型的快速入场。
- 引入更强的事件恢复与幂等控制，支撑更复杂的并发执行场景。
- 将 Agent 评估指标体系化，例如完成率、返工率、平均执行时长、工具成功率。
