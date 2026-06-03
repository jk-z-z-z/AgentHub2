from __future__ import annotations

from app.bootstrap_runtime.engine.base import BaseBootstrapEngine
from app.bootstrap_runtime.engine.impl_agentscope_react import BootstrapAgentScopeEngine


def create_bootstrap_engine(_engine_type: str) -> BaseBootstrapEngine:
    return BootstrapAgentScopeEngine()
