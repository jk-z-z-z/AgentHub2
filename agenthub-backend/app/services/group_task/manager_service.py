from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.group_assistant_config import GroupAssistantConfig
from app.models.member import Member

MANAGER_MEMBER_NAME = "管家"


def get_or_create_manager_member(db: Session, *, group_id: int) -> Member:
    row = (
        db.query(Member)
        .filter(Member.group_id == int(group_id), Member.kind == "system", Member.display_name == MANAGER_MEMBER_NAME)
        .first()
    )
    if row:
        return row
    row = Member(
        group_id=int(group_id),
        kind="system",
        display_name=MANAGER_MEMBER_NAME,
        user_ref=None,
        agent_instance_id=None,
        title="group-manager",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_or_create_group_assistant_config(db: Session, *, group_id: int, creator_user_id: int) -> GroupAssistantConfig:
    row = db.query(GroupAssistantConfig).filter(GroupAssistantConfig.group_id == int(group_id)).first()
    if row:
        return row
    row = GroupAssistantConfig(
        group_id=int(group_id),
        assistant_agent_instance_id=None,
        enabled=0,
        creator_user_id=int(creator_user_id),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_group_assistant_config(
    db: Session,
    *,
    group_id: int,
    creator_user_id: int,
    enabled: int,
) -> GroupAssistantConfig:
    row = get_or_create_group_assistant_config(db, group_id=int(group_id), creator_user_id=int(creator_user_id))
    if int(row.creator_user_id) != int(creator_user_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only creator can update assistant config")
    row.assistant_agent_instance_id = None
    row.enabled = 1 if int(enabled) == 1 else 0
    db.add(row)
    db.commit()
    db.refresh(row)
    if int(row.enabled) == 1:
        get_or_create_manager_member(db, group_id=int(group_id))
    return row
