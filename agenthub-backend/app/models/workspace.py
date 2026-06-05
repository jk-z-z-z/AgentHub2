from sqlalchemy import ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AutoIncrementIdMixin, Base, TimestampMixin


class Workspace(AutoIncrementIdMixin, TimestampMixin, Base):
    __tablename__ = "workspaces"
    __table_args__ = (
        UniqueConstraint("project_id", name="uq_workspaces_project_id"),
        Index("idx_workspaces_tenant_id", "tenant_id"),
        Index("idx_workspaces_creator_user_id", "creator_user_id"),
    )

    creator_user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(120), nullable=False)
    project_id: Mapped[int] = mapped_column(ForeignKey("groups.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    backend_type: Mapped[str] = mapped_column(String(50), default="local_fs", nullable=False)
    source_path: Mapped[str] = mapped_column(Text, nullable=False)
    last_snapshot_id: Mapped[str | None] = mapped_column(String(120))
    last_snapshot_digest: Mapped[str | None] = mapped_column(String(120))
    last_snapshot_path: Mapped[str | None] = mapped_column(Text)
    last_snapshot_file_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
