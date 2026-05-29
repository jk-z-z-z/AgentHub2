from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.acp_provider import ACPProvider
from app.models.agent_profile import AgentProfile
from app.models.agent_profile_acp_binding import AgentProfileACPBinding
from app.models.agent_profile_mcp import AgentProfileMCP
from app.models.agent_profile_skill import AgentProfileSkill
from app.models.agent_profile_tool import AgentProfileTool
from app.models.mcp import MCP
from app.models.skill import Skill
from app.models.tool import Tool


def list_agent_profiles(db: Session) -> list[AgentProfile]:
    return db.query(AgentProfile).order_by(AgentProfile.id.asc()).all()


def create_agent_profile(db: Session, payload: dict) -> AgentProfile:
    if db.query(AgentProfile).filter(AgentProfile.name == payload["name"]).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Agent profile name already exists")
    item = AgentProfile(**payload)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def bind_profile_tools(db: Session, profile_id: int, tool_ids: list[int]) -> list[Tool]:
    _get_or_404(db, AgentProfile, profile_id, "Agent profile not found")
    db.query(AgentProfileTool).filter(AgentProfileTool.agent_profile_id == profile_id).delete()
    if tool_ids:
        valid_ids = {item.id for item in db.query(Tool).filter(Tool.id.in_(tool_ids)).all()}
        missing = [tool_id for tool_id in tool_ids if tool_id not in valid_ids]
        if missing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Tools not found: {missing}")
        db.add_all([AgentProfileTool(agent_profile_id=profile_id, tool_id=tool_id) for tool_id in sorted(set(tool_ids))])
    db.commit()
    return (
        db.query(Tool)
        .join(AgentProfileTool, AgentProfileTool.tool_id == Tool.id)
        .filter(AgentProfileTool.agent_profile_id == profile_id)
        .order_by(Tool.id.asc())
        .all()
    )


def bind_profile_mcps(db: Session, profile_id: int, mcp_ids: list[int]) -> list[MCP]:
    _get_or_404(db, AgentProfile, profile_id, "Agent profile not found")
    db.query(AgentProfileMCP).filter(AgentProfileMCP.agent_profile_id == profile_id).delete()
    if mcp_ids:
        valid_ids = {item.id for item in db.query(MCP).filter(MCP.id.in_(mcp_ids)).all()}
        missing = [mcp_id for mcp_id in mcp_ids if mcp_id not in valid_ids]
        if missing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"MCPs not found: {missing}")
        db.add_all([AgentProfileMCP(agent_profile_id=profile_id, mcp_id=mcp_id) for mcp_id in sorted(set(mcp_ids))])
    db.commit()
    return (
        db.query(MCP)
        .join(AgentProfileMCP, AgentProfileMCP.mcp_id == MCP.id)
        .filter(AgentProfileMCP.agent_profile_id == profile_id)
        .order_by(MCP.id.asc())
        .all()
    )


def bind_profile_skills(db: Session, profile_id: int, skill_ids: list[int]) -> list[Skill]:
    _get_or_404(db, AgentProfile, profile_id, "Agent profile not found")
    db.query(AgentProfileSkill).filter(AgentProfileSkill.agent_profile_id == profile_id).delete()
    if skill_ids:
        valid_ids = {item.id for item in db.query(Skill).filter(Skill.id.in_(skill_ids)).all()}
        missing = [skill_id for skill_id in skill_ids if skill_id not in valid_ids]
        if missing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Skills not found: {missing}")
        db.add_all(
            [AgentProfileSkill(agent_profile_id=profile_id, skill_id=skill_id) for skill_id in sorted(set(skill_ids))]
        )
    db.commit()
    return (
        db.query(Skill)
        .join(AgentProfileSkill, AgentProfileSkill.skill_id == Skill.id)
        .filter(AgentProfileSkill.agent_profile_id == profile_id)
        .order_by(Skill.id.asc())
        .all()
    )


def bind_profile_acps(db: Session, profile_id: int, acp_provider_ids: list[int]) -> list[ACPProvider]:
    _get_or_404(db, AgentProfile, profile_id, "Agent profile not found")
    db.query(AgentProfileACPBinding).filter(AgentProfileACPBinding.agent_profile_id == profile_id).delete()
    if acp_provider_ids:
        valid_ids = {item.id for item in db.query(ACPProvider).filter(ACPProvider.id.in_(acp_provider_ids)).all()}
        missing = [provider_id for provider_id in acp_provider_ids if provider_id not in valid_ids]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"ACP providers not found: {missing}",
            )
        db.add_all(
            [
                AgentProfileACPBinding(agent_profile_id=profile_id, acp_provider_id=provider_id)
                for provider_id in sorted(set(acp_provider_ids))
            ]
        )
    db.commit()
    return (
        db.query(ACPProvider)
        .join(AgentProfileACPBinding, AgentProfileACPBinding.acp_provider_id == ACPProvider.id)
        .filter(AgentProfileACPBinding.agent_profile_id == profile_id)
        .order_by(ACPProvider.id.asc())
        .all()
    )


def _get_or_404(db: Session, model, entity_id: int, detail: str):
    item = db.query(model).filter(model.id == entity_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
    return item
