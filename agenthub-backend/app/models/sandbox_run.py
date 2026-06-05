from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AutoIncrementIdMixin, Base, TimestampMixin


class SandboxRun(AutoIncrementIdMixin, TimestampMixin, Base):
    __tablename__ = "sandbox_runs"
    __table_args__ = (
        Index("idx_sandbox_runs_workspace_id", "workspace_id"),
        Index("idx_sandbox_runs_project_id", "project_id"),
        Index("idx_sandbox_runs_tenant_id", "tenant_id"),
        Index("idx_sandbox_runs_sandbox_id", "sandbox_id"),
    )

    creator_user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(120), nullable=False)
    project_id: Mapped[int] = mapped_column(ForeignKey("groups.id"), nullable=False)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    requested_by_user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    sandbox_id: Mapped[str] = mapped_column(String(120), nullable=False)
    backend_type: Mapped[str] = mapped_column(String(50), default="docker", nullable=False)
    sandbox_image: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)
    snapshot_id: Mapped[str | None] = mapped_column(String(120))
    snapshot_path: Mapped[str | None] = mapped_column(Text)
    working_dir: Mapped[str | None] = mapped_column(Text)
    network_enabled: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    command: Mapped[str | None] = mapped_column(Text)
    stdout: Mapped[str] = mapped_column(Text, default="", nullable=False)
    stderr: Mapped[str] = mapped_column(Text, default="", nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)
    result_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
