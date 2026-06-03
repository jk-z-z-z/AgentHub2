from __future__ import annotations

from app.manager_runtime.engine.base import BaseManagerEngine
from app.manager_runtime.engine.impl_agentscope_react import ManagerAgentScopeReactEngine
from app.manager_runtime.engine.impl_internal_llm import ManagerInternalLLMEngine


def create_engine(engine_type: str) -> BaseManagerEngine:
    if str(engine_type or "").strip().lower() in {"agentscope_react", "react", "agent_scope_react"}:
        return ManagerAgentScopeReactEngine()
    return ManagerInternalLLMEngine()
