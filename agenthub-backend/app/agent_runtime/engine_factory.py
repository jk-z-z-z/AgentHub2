from __future__ import annotations

from app.agent_runtime.engine import AgentEngine
from app.agent_runtime.engines.acp_engine import ACPToolLoopEngine
from app.agent_runtime.engines.internal_llm_engine import InternalLLMEngine


def create_engine(engine_type: str) -> AgentEngine:
    t = str(engine_type or "internal_llm").strip().lower()
    if t.startswith("acp:"):
        return ACPToolLoopEngine()
    return InternalLLMEngine()

