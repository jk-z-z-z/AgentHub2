from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AutoIncrementIdMixin, Base, TimestampMixin


class GroupTaskEvent(AutoIncrementIdMixin, TimestampMixin, Base):
    __tablename__ = "group_task_events"
    __table_args__ = (
        Index("idx_group_task_events_run_id", "run_id"),
        Index("idx_group_task_events_node_id", "node_id"),
        Index("idx_group_task_events_type", "event_type"),
    )

    run_id: Mapped[int] = mapped_column(ForeignKey("group_task_runs.id"), nullable=False)
    node_id: Mapped[int | None] = mapped_column(ForeignKey("group_task_nodes.id"))
    seq: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    event_type: Mapped[str] = mapped_column(String(60), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
