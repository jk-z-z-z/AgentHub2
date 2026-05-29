from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, SnowflakeMixin, TimestampMixin


class AgentProfile(SnowflakeMixin, TimestampMixin, Base):
    __tablename__ = "agent_profiles"

    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    role: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    default_model_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    planning_mode: Mapped[str | None] = mapped_column(String(50))
    is_active: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
