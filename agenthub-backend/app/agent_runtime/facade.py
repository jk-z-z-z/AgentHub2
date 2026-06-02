from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.agent_runtime.agentbuilder._builder import build_complete_agent
from app.agent_runtime.engine.factory import create_engine
from app.agent_runtime.schemas import AgentInvokeResult


class _StrictAgentRunRequest:
    """严格内部使用的请求对象，禁止外部构造。"""
    def __init__(
        self,
        *,
        agent_id: int,
        input_text: str,
        system_prompt: str,
        runtime_context: dict[str, Any],
        short_term_memory: list[dict[str, Any]],
        toolkit,
    ):
        self.agent_id = agent_id
        self.input_text = input_text
        self.system_prompt = system_prompt
        self.runtime_context = runtime_context
        self.short_term_memory = short_term_memory
        self._toolkit = toolkit


async def invoke_agent(
    db: Session,
    *,
    agent_id: int,
    short_term_memory: list[dict[str, Any]],
    extra_context: dict[str, Any],
) -> AgentInvokeResult:
    """
    数字员工统一极简入口函数。外部系统仅允许调用此函数，禁止访问任何内部模块。

    ==========================================
    严格参数传递边界规则（强制执行）：
    ==========================================

    【外部系统负责提供，传入本函数】
    1. short_term_memory：由群聊message对话体系完成拼接后传入
    2. extra_context：项目信息、个人信息、用户当前输入文本input_text，由外部整理好全部传入

    【agent_runtime包内部自主负责，完全隐藏】
    - 数字员工固有资源：自动从agent工作空间读取 SOUL.md / PROFILE.md / tools.json / skills.json
    - 工具动态加载：根据agent配置自动解析enabled开关生成Toolkit
    - 技能集自动加载：两级Skill池自动加载
    - 推理引擎自动路由：根据agent.engine_type自动选择内部LLM/Codex/ClaudeCode/AgentScope ReAct后端

    ==========================================
    管家Agent说明：管家是群聊的附属属性，不属于独立数字员工实体，
    保留在原有项目位置，无需进入本包。
    ==========================================
    """
    built_agent = build_complete_agent(
        db,
        agent_id=int(agent_id),
        extra_context=extra_context,
        runtime_context={"extra": extra_context},
    )

    engine = create_engine(built_agent.engine_ctx.engine_type)

    wrapped_req = _StrictAgentRunRequest(
        agent_id=int(agent_id),
        input_text=str(extra_context.get("input_text", "")),
        system_prompt=built_agent.system_prompt,
        runtime_context={"extra": extra_context},
        short_term_memory=short_term_memory,
        toolkit=built_agent.toolkit,
    )

    text, meta = await engine.run(
        ctx=built_agent.engine_ctx,
        req=wrapped_req,
        tool_executor=None,
    )

    return AgentInvokeResult(
        text=text,
        engine_type=built_agent.engine_ctx.engine_type,
        meta=meta,
        system_prompt_used=built_agent.system_prompt,
    )
