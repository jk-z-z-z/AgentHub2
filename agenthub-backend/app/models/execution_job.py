from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AutoIncrementIdMixin, Base, TimestampMixin


class ExecutionJob(AutoIncrementIdMixin, TimestampMixin, Base):
    __tablename__ = "execution_jobs"
    __table_args__ = (
        Index("idx_execution_jobs_workspace_id", "workspace_id"),
        Index("idx_execution_jobs_project_id", "project_id"),
        Index("idx_execution_jobs_tenant_id", "tenant_id"),
        Index("idx_execution_jobs_status", "status"),
    )

    creator_user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(120), nullable=False)
    project_id: Mapped[int] = mapped_column(ForeignKey("groups.id"), nullable=False)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    sandbox_run_id: Mapped[int | None] = mapped_column(ForeignKey("sandbox_runs.id"))
    requested_by_user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    job_type: Mapped[str] = mapped_column(String(40), default="command", nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)
    command: Mapped[str] = mapped_column(Text, nullable=False)
    cwd: Mapped[str] = mapped_column(String(255), default=".", nullable=False)
    sandbox_image: Mapped[str] = mapped_column(String(255), nullable=False)
    network_enabled: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    stdout: Mapped[str] = mapped_column(Text, default="", nullable=False)
    stderr: Mapped[str] = mapped_column(Text, default="", nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)
    spec_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    context_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    result_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
