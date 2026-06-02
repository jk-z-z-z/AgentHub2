from __future__ import annotations

from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AutoIncrementIdMixin, Base, TimestampMixin


class AgentRunEvent(AutoIncrementIdMixin, TimestampMixin, Base):
    __tablename__ = "agent_run_events"
    __table_args__ = (
        Index("idx_agent_run_events_run_id", "agent_run_id"),
        Index("idx_agent_run_events_seq", "agent_run_id", "seq"),
    )

    agent_run_id: Mapped[int] = mapped_column(ForeignKey("agent_runs.id"), nullable=False)
    seq: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)

