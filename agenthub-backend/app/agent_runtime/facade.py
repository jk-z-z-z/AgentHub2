from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.agent_runtime.agentbuilder._builder import build_complete_agent
from app.agent_runtime.engine.factory import create_engine
from app.agent_runtime.trace import AgentRuntimeTrace
from app.agent_runtime.tool._executor import execute_builtin_tool
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
        trace,
    ):
        self.agent_id = agent_id
        self.input_text = input_text
        self.system_prompt = system_prompt
        self.runtime_context = runtime_context
        self.short_term_memory = short_term_memory
        self._toolkit = toolkit
        self.trace = trace


def _normalize_short_term_memory(short_term_memory: list[dict[str, Any]] | list[Any]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for item in short_term_memory or []:
        if isinstance(item, dict):
            normalized.append(
                {
                    "role": str(item.get("role", "user")),
                    "content": item.get("content", ""),
                    "name": item.get("name"),
                }
            )
            continue
        role = str(getattr(item, "role", "user"))
        content = getattr(item, "content", "")
        name = getattr(item, "name", None)
        normalized.append({"role": role, "content": content, "name": name})
    return normalized


async def invoke_agent(
    db: Session,
    *,
    agent_id: int,
    short_term_memory: list[dict[str, Any]],
    extra_context: dict[str, Any],
    system_prompt: str | None = None,
    trace_message_id: int | None = None,
    tool_executor: Any | None = None,
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
    runtime_context = dict(extra_context or {})
    trace_id = trace_message_id
    if trace_id is None:
        maybe_trace_id = runtime_context.get("trace_message_id")
        try:
            trace_id = int(maybe_trace_id) if maybe_trace_id not in (None, "") else None
        except (TypeError, ValueError):
            trace_id = None

    trace = AgentRuntimeTrace(db=db, message_id=int(trace_id) if trace_id else None)

    built_agent = build_complete_agent(
        db,
        agent_id=int(agent_id),
        extra_context=runtime_context,
        runtime_context=runtime_context,
        trace=trace,
    )

    engine = create_engine(built_agent.engine_ctx.engine_type)

    wrapped_req = _StrictAgentRunRequest(
        agent_id=int(agent_id),
        input_text=str(extra_context.get("input_text", "")),
        system_prompt=system_prompt if system_prompt is not None else built_agent.system_prompt,
        runtime_context=runtime_context,
        short_term_memory=_normalize_short_term_memory(short_term_memory),
        toolkit=built_agent.toolkit,
        trace=trace,
    )

    def _trace_tool_executor(tool_code: str, args: dict[str, Any]) -> dict[str, Any]:
        payload_args = args or {}
        trace.emit("tool.call", {"tool_code": str(tool_code), "args": payload_args})
        try:
            executor = tool_executor
            if executor is None:
                result = execute_builtin_tool(
                    agent_id=int(agent_id),
                    tool_code=str(tool_code),
                    args=payload_args,
                    runtime_context=runtime_context,
                )
            else:
                result = executor(str(tool_code), payload_args)
            trace.emit("tool.result", {"tool_code": str(tool_code), "result": result})
            return result
        except Exception as exc:
            trace.emit("tool.result", {"tool_code": str(tool_code), "error": str(exc)})
            raise

    trace.emit(
        "run.started",
        {
            "agent_id": int(agent_id),
            "engine_type": built_agent.engine_ctx.engine_type,
            "has_toolkit": bool(getattr(built_agent, "toolkit", None)),
        },
    )
    try:
        text, meta = await engine.run(
            ctx=built_agent.engine_ctx,
            req=wrapped_req,
            tool_executor=_trace_tool_executor,
        )
        trace.emit("run.finished", {"status": "succeeded", "engine_type": built_agent.engine_ctx.engine_type})
        return AgentInvokeResult(
            text=text,
            engine_type=built_agent.engine_ctx.engine_type,
            meta=meta,
            system_prompt_used=wrapped_req.system_prompt,
        )
    except Exception as exc:
        trace.emit("error", {"error": str(exc), "engine_type": built_agent.engine_ctx.engine_type})
        trace.emit("run.finished", {"status": "failed", "engine_type": built_agent.engine_ctx.engine_type})
        raise
