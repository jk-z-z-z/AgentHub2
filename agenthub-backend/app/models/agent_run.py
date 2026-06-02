from __future__ import annotations

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AutoIncrementIdMixin, Base, TimestampMixin


class AgentRun(AutoIncrementIdMixin, TimestampMixin, Base):
    __tablename__ = "agent_runs"
    __table_args__ = (
        Index("idx_agent_runs_group_id", "group_id"),
        Index("idx_agent_runs_agent_instance_id", "agent_instance_id"),
        Index("idx_agent_runs_trigger_message_id", "trigger_message_id"),
        Index("idx_agent_runs_group_task_node_id", "group_task_node_id"),
        Index("idx_agent_runs_status", "status"),
    )

    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"), nullable=False)
    agent_instance_id: Mapped[int] = mapped_column(ForeignKey("agent_instances.id"), nullable=False)
    trigger_message_id: Mapped[int | None] = mapped_column(ForeignKey("messages.id"))

    # Optional DAG linkage
    group_task_run_id: Mapped[int | None] = mapped_column(ForeignKey("group_task_runs.id"))
    group_task_node_id: Mapped[int | None] = mapped_column(ForeignKey("group_task_nodes.id"))

    mode: Mapped[str] = mapped_column(String(24), default="chat", nullable=False)  # chat | dag_node
    status: Mapped[str] = mapped_column(String(24), default="running", nullable=False)  # running|succeeded|failed

    runtime_dir: Mapped[str] = mapped_column(String(500), nullable=False)
    result_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    final_message_id: Mapped[int | None] = mapped_column(ForeignKey("messages.id"))

