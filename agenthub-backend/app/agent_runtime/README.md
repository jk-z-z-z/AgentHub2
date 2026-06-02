# AgentRuntime 数字员工运行时包

## 企业级架构重构完成

### 唯一对外入口
本包严格遵循封装原则，**仅对外暴露一个极简入口函数**：`invoke_agent()`

```python
from app.agent_runtime import invoke_agent

result = await invoke_agent(
    db,
    agent_id=123,
    short_term_memory=[{"role": "user", "content": "你好"}],
    extra_context={"user_id": 1, "input_text": "帮我分析需求"},
    trace_message_id=456,
)
```

仅需三个核心参数即可完成完整执行；如果你还想记录过程事件，再额外传 `trace_message_id` 即可，完全隐藏所有内部实现细节。

如果传入 `trace_message_id`，本次执行会把 `run.started`、`llm.request`、`tool.call`、`tool.result`、`llm.response`、`run.finished` 等过程事件写入对应的 `message_events`。

---

### 目录结构与架构分层

```
app/agent_runtime/
├── README.md                    # 架构说明文档
├── __init__.py                  # 对外公共API暴露（仅3个符号）
├── facade.py                    # ★ Facade层：唯一入口，隐藏所有内部实现
├── schemas.py                   # 全局统一Pydantic DTO
│
├── agentbuilder/
│   ├── __init__.py              # 私有（NOT EXPORTED）
│   └── _builder.py              # Agent实例全流程构建器
│
├── tool/
│   ├── __init__.py              # 私有（NOT EXPORTED）
│   ├── _loader.py               # 工具动态加载器，从tools.json读取enabled开关
│   ├── _executor.py             # 统一工具执行入口，全链路trace
│   └── builtins/                # 15+内置工具实现
│
├── skill/
│   ├── __init__.py              # 私有（NOT EXPORTED）
│   └── _loader.py               # 技能对称加载器，两级Skill池支持
│
├── mcp/
│   ├── __init__.py              # 私有（NOT EXPORTED）
│   ├── _loader.py               # MCP配置对称加载器
│   └── _transport.py            # ACP stdio/http传输层，生命周期管理
│
└── engine/
    ├── __init__.py              # 私有（NOT EXPORTED）
    ├── base.py                  # 引擎抽象基类
    ├── factory.py               # 自动调度工厂
    ├── impl_internal_llm.py     # 内部LLM引擎
    ├── impl_codex.py            # Codex ACP引擎
    ├── impl_claude_code.py      # Claude Code ACP引擎
    └── impl_agentscope_react.py # AgentScope ReAct引擎
```

---

### 各组件交互流程图

```
外部调用方
    │
    ▼
facade.invoke_agent(agent_id, short_term_memory, extra_context)
    │
    ├─> AgentBuilder.build(agent_id, extra_context)
    │    ├─> ToolLoader.load(agent_id)     # 读取tools.json启用配置
    │    ├─> SkillLoader.load(agent_id)    # 读取skills.json启用配置
    │    ├─> 读取SOUL.md / PROFILE.md / MEMORY.md
    │    └─> 组装完整System Prompt
    │
    └─> EngineFactory.get(engine_type)
         ├─> InternalLLMEngine
         ├─> CodexEngine
         ├─> ClaudeCodeEngine
         └─> AgentScopeReactEngine
              │
              └─> 执行Agent推理循环 → 返回标准AgentInvokeResult
```

---

### 强制架构约束

1. **禁止任何外部调用方绕过Facade层**：所有业务代码仅可从 `app.agent_runtime` 导入 `invoke_agent`、`AgentInvokeRequest`、`AgentInvokeResult` 三个符号
2. **所有内部模块以下划线`_`开头命名**：通过Python私有模块命名约定防止外部误导入
3. **严格单一职责原则**：每个组件唯一职责明确，无重复冗余逻辑
4. **Tool/Skill/MCP三个加载器逻辑完全对称**：降低认知负担，统一配置模式

---

### 支持的4类核心推理后端

| 引擎类型 | engine_type字符串标识 | 说明 |
|---------|-------------------|------|
| 内部LLM引擎 | `internal_llm` | 直接调用OpenAI兼容接口 |
| Codex引擎 | `acp:codex` | ACP协议对接Codex外部运行器 |
| Claude Code引擎 | `acp:claude_code` | ACP协议对接Claude Code外部运行器 |
| AgentScope ReAct引擎 | `agentscope_react` | AgentScope框架原生ReAct智能体 |
