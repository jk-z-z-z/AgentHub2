from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import Member
from app.models.agent_instance import AgentInstance
from app.models.group import Group
from app.models.member import Member


def list_members(db: Session, group_id: int | None = None) -> list[type[Member]]:
    query = db.query(Member)
    if group_id is not None:
        query = query.filter(Member.group_id == group_id)
    return query.order_by(Member.id.asc()).all()


def create_user_member(db: Session, group_id: str,display_name: str,user_ref: str,title: str|None) -> Member:
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    if group.type == "personal":
        existing_count = db.query(Member).filter(Member.group_id == group_id).count()
        if existing_count >= 2:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Personal group can only have 2 members")
    item = Member(
        group_id=group_id,
        kind="user",
        display_name=display_name,
        user_ref=user_ref,
        title=title,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def create_agent_member(db: Session, group_id: str,display_name: str,agent_instance_id: str,title: str|None) -> Member:
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    if not db.query(AgentInstance).filter(AgentInstance.id == agent_instance_id).first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent instance not found")
    if group.type == "personal":
        existing_count = db.query(Member).filter(Member.group_id == group_id).count()
        if existing_count >= 2:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Personal group can only have 2 members")
    item = Member(
        group_id=group_id,
        kind="agent",
        display_name=display_name,
        agent_instance_id=agent_instance_id,
        title=title,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update_member(db: Session, member_id: int, display_name:str,title:str|None) -> type[Member]:
    item = db.query(Member).filter(Member.id == member_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
    item.display_name = display_name
    item.title = title
    db.commit()
    db.refresh(item)
    return item


def delete_member(db: Session, member_id: int) -> None:
    item = db.query(Member).filter(Member.id == member_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
    db.delete(item)
    db.commit()
