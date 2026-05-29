from fastapi import APIRouter, Body, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.agent_profile import AgentProfileCreateRequest, AgentProfileOut
from app.schemas.common import ApiResponse
from app.schemas.mcp import MCPOut
from app.schemas.skill import SkillOut
from app.schemas.tool import ToolOut
from app.schemas.acp_provider import ACPProviderOut
from app.services.agent_profile_service import (
    bind_profile_acps,
    bind_profile_mcps,
    bind_profile_skills,
    bind_profile_tools,
    create_agent_profile,
    list_agent_profiles,
)


router = APIRouter(prefix="/agent-profiles", tags=["agent-profiles"])


@router.get("", response_model=ApiResponse[list[AgentProfileOut]])
def list_agent_profiles_api(db: Session = Depends(get_db)):
    rows = list_agent_profiles(db)
    return ApiResponse(data=[AgentProfileOut.model_validate(row) for row in rows])


@router.post("", response_model=ApiResponse[AgentProfileOut])
def create_agent_profile_api(payload: AgentProfileCreateRequest, db: Session = Depends(get_db)):
    row = create_agent_profile(db, payload.model_dump())
    return ApiResponse(data=AgentProfileOut.model_validate(row))


@router.put("/{profile_id}/tools", response_model=ApiResponse[list[ToolOut]])
def set_profile_tools(profile_id: int, tool_ids: list[int] = Body(default=[]), db: Session = Depends(get_db)):
    rows = bind_profile_tools(db, profile_id, tool_ids)
    return ApiResponse(data=[ToolOut.model_validate(row) for row in rows])


@router.put("/{profile_id}/mcps", response_model=ApiResponse[list[MCPOut]])
def set_profile_mcps(profile_id: int, mcp_ids: list[int] = Body(default=[]), db: Session = Depends(get_db)):
    rows = bind_profile_mcps(db, profile_id, mcp_ids)
    return ApiResponse(data=[MCPOut.model_validate(row) for row in rows])


@router.put("/{profile_id}/skills", response_model=ApiResponse[list[SkillOut]])
def set_profile_skills(profile_id: int, skill_ids: list[int] = Body(default=[]), db: Session = Depends(get_db)):
    rows = bind_profile_skills(db, profile_id, skill_ids)
    return ApiResponse(data=[SkillOut.model_validate(row) for row in rows])


@router.put("/{profile_id}/acp-providers", response_model=ApiResponse[list[ACPProviderOut]])
def set_profile_acps(profile_id: int, provider_ids: list[int] = Body(default=[]), db: Session = Depends(get_db)):
    rows = bind_profile_acps(db, profile_id, provider_ids)
    return ApiResponse(data=[ACPProviderOut.model_validate(row) for row in rows])
