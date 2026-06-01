from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.agent_run import AgentRun
from app.models.agent_run_event import AgentRunEvent


def get_agent_run(db: Session, *, run_id: int) -> AgentRun | None:
    return db.query(AgentRun).filter(AgentRun.id == int(run_id)).first()


def list_agent_run_events(db: Session, *, run_id: int) -> list[AgentRunEvent]:
    return (
        db.query(AgentRunEvent)
        .filter(AgentRunEvent.agent_run_id == int(run_id))
        .order_by(AgentRunEvent.seq.asc(), AgentRunEvent.id.asc())
        .all()
    )

