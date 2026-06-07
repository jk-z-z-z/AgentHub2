from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AutoIncrementIdMixin, Base, TimestampMixin


class PreviewJob(AutoIncrementIdMixin, TimestampMixin, Base):
    __tablename__ = "preview_jobs"
    __table_args__ = (
        UniqueConstraint("workspace_id", name="uq_preview_jobs_workspace_id"),
        Index("idx_preview_jobs_workspace_id", "workspace_id"),
        Index("idx_preview_jobs_project_id", "project_id"),
        Index("idx_preview_jobs_tenant_id", "tenant_id"),
        Index("idx_preview_jobs_status", "status"),
    )

    creator_user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(120), nullable=False)
    project_id: Mapped[int] = mapped_column(ForeignKey("groups.id"), nullable=False)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    sandbox_run_id: Mapped[int | None] = mapped_column(ForeignKey("sandbox_runs.id"))
    requested_by_user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)
    container_name: Mapped[str] = mapped_column(String(120), nullable=False)
    container_id: Mapped[str | None] = mapped_column(String(255))
    sandbox_image: Mapped[str] = mapped_column(String(255), nullable=False)
    source_path: Mapped[str] = mapped_column(String(255), default=".", nullable=False)
    host_port: Mapped[int] = mapped_column(Integer, nullable=False)
    preview_root_path: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(String(255))
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    logs_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)
    spec_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    context_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    result_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
