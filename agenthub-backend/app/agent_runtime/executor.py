from __future__ import annotations

from sqlalchemy.orm import Session

from app.agent_runtime.engine import EngineContext
from app.agent_runtime.engine_factory import create_engine
from app.agent_runtime.types import AgentRunRequest, AgentRunResult
from app.models.agent_instance import AgentInstance


async def run_agent(db: Session, *, req: AgentRunRequest, tool_executor=None) -> AgentRunResult:
    row = db.query(AgentInstance).filter(AgentInstance.id == int(req.agent_id)).first()
    if not row:
        raise ValueError("Agent not found")
    engine_type = str(getattr(row, "engine_type", "internal_llm") or "internal_llm")
    engine_cfg = str(getattr(row, "engine_config_json", "{}") or "{}")
    engine = create_engine(engine_type)
    text, meta = await engine.run(
        ctx=EngineContext(agent_id=int(req.agent_id), engine_type=engine_type, engine_config_json=engine_cfg),
        req=req,
        tool_executor=tool_executor,
    )
    return AgentRunResult(text=text, engine_type=engine_type, meta=meta or {})

