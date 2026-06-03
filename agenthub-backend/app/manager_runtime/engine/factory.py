from __future__ import annotations

from app.manager_runtime.engine.base import BaseManagerEngine
from app.manager_runtime.engine.impl_agentscope_react import ManagerAgentScopeReactEngine


def create_engine(engine_type: str) -> BaseManagerEngine:
    _ = engine_type
    return ManagerAgentScopeReactEngine()
