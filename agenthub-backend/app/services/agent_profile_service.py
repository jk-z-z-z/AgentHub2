from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.agent_profile import AgentProfile


def list_agent_profiles(db: Session, creator_user_id: int) -> list[type[AgentProfile]]:
    return (
        db.query(AgentProfile)
        .filter(AgentProfile.creator_user_id == creator_user_id)
        .order_by(AgentProfile.id.asc())
        .all()
    )


def create_agent_profile(db: Session, payload: dict, creator_user_id: int) -> AgentProfile:
    if db.query(AgentProfile).filter(AgentProfile.name == payload["name"]).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Agent profile name already exists")
    allowed_keys = {
        "name",
        "role",
        "description",
        "soul_md",
        "agents_md",
        "profile_md",
        "bootstrap_md",
        "memory_md",
        "heartbeat_md",
        "enabled_files_json",
        "model_name",
        "temperature",
        "top_p",
        "max_output_tokens",
        "is_active",
    }
    safe_payload = {k: v for k, v in payload.items() if k in allowed_keys}
    item = AgentProfile(**safe_payload)
    item.creator_user_id = creator_user_id
    db.add(item)
    db.commit()
    db.refresh(item)
    return item
