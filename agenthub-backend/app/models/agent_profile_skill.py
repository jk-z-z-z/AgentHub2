from sqlalchemy import ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, SnowflakeMixin, TimestampMixin


class AgentProfileSkill(SnowflakeMixin, TimestampMixin, Base):
    __tablename__ = "agent_profile_skills"
    __table_args__ = (UniqueConstraint("agent_profile_id", "skill_id", name="uq_agent_profile_skill"),)

    agent_profile_id: Mapped[int] = mapped_column(ForeignKey("agent_profiles.id"), nullable=False)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id"), nullable=False)
    policy_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
