from sqlalchemy import Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AutoIncrementIdMixin, Base, TimestampMixin


class AgentProfile(AutoIncrementIdMixin, TimestampMixin, Base):
    __tablename__ = "agent_profiles"

    creator_user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    role: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    soul_md: Mapped[str] = mapped_column(Text, nullable=False)
    profile_md: Mapped[str] = mapped_column(Text, default="", nullable=False)
    bootstrap_md: Mapped[str] = mapped_column(Text, default="", nullable=False)
    # Template configs copied into agent workspace on instance creation.
    # tools.json controls builtin tool toggles; skills.json controls skill loading (pool + local folder).
    tools_json: Mapped[str] = mapped_column(Text, default="", nullable=False)
    skills_json: Mapped[str] = mapped_column(Text, default="", nullable=False)
    enabled_files_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    model_name: Mapped[str] = mapped_column(String(120), default="gpt-4.1-mini", nullable=False)
    temperature: Mapped[float] = mapped_column(Float, default=0.7, nullable=False)
    top_p: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    max_output_tokens: Mapped[int | None] = mapped_column(Integer)
    is_active: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
