
from sqlalchemy import ForeignKey, Index, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, SnowflakeMixin, TimestampMixin


class GroupTaskGraph(SnowflakeMixin, TimestampMixin, Base):
    __tablename__ = "group_task_graphs"
    __table_args__ = (
        Index("idx_group_task_graphs_run_id", "run_id"),
        Index("idx_group_task_graphs_run_ver", "run_id", "version"),
    )

    run_id: Mapped[int] = mapped_column(ForeignKey("group_task_runs.id"), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    snapshot_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)

