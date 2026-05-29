from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.agent_instance import AgentInstance
from app.models.agent_profile import AgentProfile
from app.models.group import Group
from app.models.member import Member


def list_agent_instances(db: Session) -> list[AgentInstance]:
    return db.query(AgentInstance).order_by(AgentInstance.id.asc()).all()


def create_agent_instance(db: Session, payload: dict) -> AgentInstance:
    if not db.query(Group).filter(Group.id == payload["group_id"]).first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    if not db.query(AgentProfile).filter(AgentProfile.id == payload["profile_id"]).first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent profile not found")

    instance = AgentInstance(**payload)
    db.add(instance)
    db.flush()

    db.add(
        Member(
            group_id=payload["group_id"],
            kind="agent",
            display_name=payload["display_name"],
            agent_instance_id=instance.id,
        )
    )
    db.commit()
    db.refresh(instance)
    return instance
