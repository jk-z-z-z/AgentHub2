from sqlalchemy import ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, SnowflakeMixin, TimestampMixin


class AgentProfileMCP(SnowflakeMixin, TimestampMixin, Base):
    __tablename__ = "agent_profile_mcps"
    __table_args__ = (UniqueConstraint("agent_profile_id", "mcp_id", name="uq_agent_profile_mcp"),)

    agent_profile_id: Mapped[int] = mapped_column(ForeignKey("agent_profiles.id"), nullable=False)
    mcp_id: Mapped[int] = mapped_column(ForeignKey("mcps.id"), nullable=False)
    policy_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
