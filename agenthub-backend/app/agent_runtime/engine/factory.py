from __future__ import annotations

from typing import Type

from app.agent_runtime.engine.base import BaseAgentEngine
from app.agent_runtime.engine.impl_agentscope_react import AgentScopeReactEngine
from app.agent_runtime.engine.impl_claude_code import ClaudeCodeEngine
from app.agent_runtime.engine.impl_codex import CodexEngine
from app.agent_runtime.engine.impl_internal_llm import InternalLLMEngine


def create_engine(engine_type: str) -> BaseAgentEngine:
    t = str(engine_type or "internal_llm").strip().lower()

    if t == "internal_llm":
        return InternalLLMEngine()
    if t.startswith("acp:"):
        provider = t.split(":", 1)[1].strip().lower()
        if provider == "codex":
            return CodexEngine()
        if provider == "claude_code":
            return ClaudeCodeEngine()
        return CodexEngine()
    if t == "agentscope_react":
        return AgentScopeReactEngine()

    return InternalLLMEngine()
