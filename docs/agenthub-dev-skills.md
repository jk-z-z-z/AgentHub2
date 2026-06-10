# AgentHub 开发经验 Skills

## 1. 目的

本文档沉淀在开发 AgentHub 过程中形成的可复用开发技能。这里的 Skill 不是系统内部配置，而是以后在做类似 AI 协作项目时可以重复使用的方法模板。

## 2. Skill：任务拆分

### 目标

把复杂需求拆成适合 AI 执行的小任务。

### 做法

- 先识别模块边界
- 再按模块拆解局部目标
- 保证每轮任务只聚焦一个主要目标
- 为每轮任务定义清晰完成标准

### 价值

- 降低 AI 偏航
- 提高结果可控性
- 适合并行推进

## 3. Skill：两阶段开发

### 目标

兼顾首轮交付速度与后续结构质量。

### 做法

- 第一轮只聚焦功能落地
- 第二轮只聚焦结构整理
- 将“实现”和“优化”视为两类不同任务

### 价值

- 减少第一轮认知负担
- 避免过早设计
- 提升最终代码质量

## 4. Skill：面向 AI 的代码组织

### 目标

让代码结构更适合 AI 后续继续理解和修改。

### 做法

- 保持目录清晰
- 让文件职责清楚
- 避免长期保留超大文件
- 重构时优先拆分高耦合区域

### 价值

- 降低 token 成本
- 提高 AI 局部修改准确率
- 降低后续接手门槛

## 5. Skill：从原型代码过渡到工程化结构

### 目标

把第一轮快速生成的实现演进成长期可维护的代码结构。

### 做法

- 先接受适度集中实现
- 在功能跑通后识别职责混杂区域
- 按模块、职责或设计模式进行拆分
- 把重构单独视为明确任务，而不是顺手优化

### 价值

- 保留原型阶段效率
- 避免项目进入长期混乱状态
- 提升代码阅读和迭代效率

## 6. Skill：批判性对话

### 目标

补足 AI 在方案和实现阶段缺少主动批判性思维的问题。

### 做法

- 在方案完成后单独发起一轮评审对话
- 在代码完成后单独发起一轮复查对话
- 要求 AI 从风险、复杂度、反例、边界和扩展性角度重新判断

### 常用提问

- 当前方案最大的风险是什么？
- 有没有更简单的实现方式？
- 当前结构最容易在后续迭代中出问题的地方是什么？
- 如果换一个 AI 接手，这段代码是否容易继续修改？

### 价值

- 提前发现问题
- 降低返工成本
- 提升方案和实现质量

## 7. Skill：面向长期迭代的 AI 协作

### 目标

让 AI 不只参与第一次开发，还能持续参与后续多轮演进。

### 做法

- 从一开始就关注结构可读性
- 在每轮开发后主动整理模块边界
- 让代码和目录尽量支持局部加载
- 把后续接手成本作为设计指标之一

### 价值

- 提升长期协作效率
- 降低历史代码负担
- 让 AI 参与开发具备持续性

## 8. 已落地的 Skill 体系

基于上述方法论，当前已经进一步沉淀出一组可直接复用的 Skill 资产。

### 8.1 总入口 Skill

- `ai-development-orchestrator`

作用：

- 作为 AI 协作开发的总入口
- 判断当前阶段应该先拆任务、先实现、先重构还是先复查
- 负责在多个子 Skill 之间做路由和串联

适用场景：

- 中大型需求进入开发前
- 不确定当前应该采用哪种 AI 协作方式时
- 需要把多个 Skill 串成完整流程时

### 8.2 子 Skill：任务拆分

- `task-decomposition`

作用：

- 将大需求缩小成可执行的小目标
- 明确模块边界、当前任务目标和验证标准

对应经验：

- 先拆模块，再交任务
- 每轮只解决一个小目标

### 8.3 子 Skill：先实现后重构

- `refactor-after-delivery`

作用：

- 在功能已落地后，单独进行结构重构
- 改善模块边界、命名、职责划分和可维护性

对应经验：

- 第一轮先实现
- 第二轮再重构

### 8.4 子 Skill：面向 AI 的代码组织

- `ai-codebase-organization`

作用：

- 优化目录和文件组织
- 降低未来 AI 二次开发的上下文成本
- 提高局部修改和局部加载效率

对应经验：

- 代码结构既服务人，也服务 AI
- 避免长期保留大单文件

### 8.5 子 Skill：批判性复查

- `critical-review-pass`

作用：

- 在方案完成后增加一轮批判性评审
- 在代码完成后增加一轮批判性复查
- 强制 AI 从风险、复杂度、耦合和后续成本角度重新审视结果

对应经验：

- AI 容易顺着人的思路继续做
- 方案和实现都需要额外一轮批判性对话

### 8.6 总方法 Skill

- `ai-collab-development`

作用：

- 作为整体方法论的浓缩版本
- 统一表达任务拆分、阶段开发、代码组织和批判性复查这些原则

适用场景：

- 需要快速挂载完整开发方法论时
- 不需要细分路由，只需要整体协作原则时

### 8.7 Skill 之间的关系

这一套 Skill 体系可以按以下方式理解：

1. `ai-development-orchestrator` 负责总入口和决策路由
2. `task-decomposition` 负责拆任务
3. `refactor-after-delivery` 负责结构重构
4. `ai-codebase-organization` 负责代码组织优化
5. `critical-review-pass` 负责批判性复查
6. `ai-collab-development` 负责提供整体方法论背景

一个典型链路可以是：

1. 先使用 `ai-development-orchestrator` 判断当前阶段
2. 如果需求过大，调用 `task-decomposition`
3. 功能落地后，调用 `refactor-after-delivery`
4. 如有需要，调用 `ai-codebase-organization`
5. 最后调用 `critical-review-pass`

## 9. Skill 文件位置

当前这些 Skill 已经分别落在仓库根目录和 `agenthub-backend/skill-pool/` 中，便于独立使用和在项目内复用。

根目录：

- [ai-development-orchestrator](/Users/youtao/Projects/AgentHub-agentscope/ai-development-orchestrator/SKILL.md)
- [ai-collab-development](/Users/youtao/Projects/AgentHub-agentscope/ai-collab-development/SKILL.md)
- [task-decomposition](/Users/youtao/Projects/AgentHub-agentscope/task-decomposition/SKILL.md)
- [refactor-after-delivery](/Users/youtao/Projects/AgentHub-agentscope/refactor-after-delivery/SKILL.md)
- [ai-codebase-organization](/Users/youtao/Projects/AgentHub-agentscope/ai-codebase-organization/SKILL.md)
- [critical-review-pass](/Users/youtao/Projects/AgentHub-agentscope/critical-review-pass/SKILL.md)

项目内 Skill Pool：

- [skill-pool/ai-development-orchestrator](/Users/youtao/Projects/AgentHub-agentscope/agenthub-backend/skill-pool/ai-development-orchestrator/SKILL.md)
- [skill-pool/ai-collab-development](/Users/youtao/Projects/AgentHub-agentscope/agenthub-backend/skill-pool/ai-collab-development/SKILL.md)
- [skill-pool/task-decomposition](/Users/youtao/Projects/AgentHub-agentscope/agenthub-backend/skill-pool/task-decomposition/SKILL.md)
- [skill-pool/refactor-after-delivery](/Users/youtao/Projects/AgentHub-agentscope/agenthub-backend/skill-pool/refactor-after-delivery/SKILL.md)
- [skill-pool/ai-codebase-organization](/Users/youtao/Projects/AgentHub-agentscope/agenthub-backend/skill-pool/ai-codebase-organization/SKILL.md)
- [skill-pool/critical-review-pass](/Users/youtao/Projects/AgentHub-agentscope/agenthub-backend/skill-pool/critical-review-pass/SKILL.md)

## 10. 总结

这些 Skills 的核心，不是教 AI “怎么写一段代码”，而是沉淀“怎么在复杂项目里持续高质量地和 AI 一起开发”。它们来自 AgentHub 的实际开发经验，也适合迁移到其他 AI 协作型项目中。
