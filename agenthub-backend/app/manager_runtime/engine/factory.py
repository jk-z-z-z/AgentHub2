from __future__ import annotations

from app.manager_runtime.engine.base import BaseManagerEngine
from app.manager_runtime.engine.impl_internal_llm import ManagerInternalLLMEngine


def create_engine(engine_type: str) -> BaseManagerEngine:
    _ = engine_type
    return ManagerInternalLLMEngine()
