from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.agent_instance import AgentInstance
from app.models.member import Member
from app.schemas.agent_instance import AgentInstanceCreateRequest, AgentInstanceOut, AgentInstanceSoulOut
from app.schemas.agent_skills import AgentSkillConfigOut, AgentSkillConfigUpdateRequest, SkillPoolItemOut
from app.schemas.common import ApiResponse
from app.schemas.fs import FsEntryOut, TextFileOut, TextFileWriteRequest
from app.services.agent_instance_service import (
    create_agent_instance,
    get_bootstrap_group_for_agent,
    list_agent_instances,
)
from app.services.agent_fs_service import delete_agent_file, list_agent_fs, read_agent_text_file, write_agent_text_file
from app.schemas.agent_tools import AgentToolTogglesOut, AgentToolTogglesUpdateRequest
from app.services.agent_tool_service import get_agent_tool_toggles, update_agent_tool_toggles
from app.services.agent_workspace_service import load_agent_soul, save_agent_soul
from app.schemas.group import GroupOut
from app.services.message_service import create_message_and_trigger_ai
from app.services.skill_runtime_service import (
    list_skill_pool,
    load_agent_skills_config,
    save_agent_skills_config,
)


router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("", response_model=ApiResponse[list[AgentInstanceOut]])
def list_agents_api(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    rows = list_agent_instances(db, creator_user_id=int(user.id))
    return ApiResponse(data=[AgentInstanceOut.model_validate(row) for row in rows])


@router.post("", response_model=ApiResponse[AgentInstanceOut])
def create_agent_api(
    payload: AgentInstanceCreateRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    row = create_agent_instance(db, payload.model_dump(), creator_user_id=int(user.id))
    return ApiResponse(data=AgentInstanceOut.model_validate(row))


@router.get("/{agent_id}/bootstrap-group", response_model=ApiResponse[GroupOut | None])
def get_agent_bootstrap_group_api(
    agent_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    instance = db.query(AgentInstance).filter(AgentInstance.id == agent_id).first()
    if not instance:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    if int(instance.creator_user_id) != int(user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    g = get_bootstrap_group_for_agent(db, agent_instance_id=int(agent_id), creator_user_id=int(user.id))
    return ApiResponse(data=GroupOut.model_validate(g) if g else None)


@router.post("/{agent_id}/bootstrap/start", response_model=ApiResponse[bool])
async def start_agent_bootstrap_api(
    agent_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    instance = db.query(AgentInstance).filter(AgentInstance.id == agent_id).first()
    if not instance:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    if int(instance.creator_user_id) != int(user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    g = get_bootstrap_group_for_agent(db, agent_instance_id=int(agent_id), creator_user_id=int(user.id))
    if not g:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bootstrap group not found")
    sender = (
        db.query(Member)
        .filter(Member.group_id == int(g.id), Member.kind == "user", Member.user_ref == str(user.id))
        .first()
    )
    if not sender:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bootstrap user member not found")
    await create_message_and_trigger_ai(
        db,
        group_id=int(g.id),
        sender_member_id=int(sender.id),
        message_type="text",
        content="开始初始化（bootstrap）。请按 BOOTSTRAP.md 引导我完善配置。",
        meta_json="{}",
    )
    return ApiResponse(data=True)


@router.get("/{agent_id}/soul", response_model=ApiResponse[AgentInstanceSoulOut])
def get_agent_soul_api(
    agent_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    instance = db.query(AgentInstance).filter(AgentInstance.id == agent_id).first()
    if not instance:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    if int(instance.creator_user_id) != int(user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    soul = load_agent_soul(int(agent_id))
    if soul is None:
        soul = ""
    return ApiResponse(data=AgentInstanceSoulOut(soul_md=soul))


@router.put("/{agent_id}/soul", response_model=ApiResponse[AgentInstanceSoulOut])
def update_agent_soul_api(
    agent_id: int,
    payload: AgentInstanceSoulOut,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    instance = db.query(AgentInstance).filter(AgentInstance.id == agent_id).first()
    if not instance:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    if int(instance.creator_user_id) != int(user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    save_agent_soul(int(agent_id), payload.soul_md)
    return ApiResponse(data=AgentInstanceSoulOut(soul_md=payload.soul_md))


@router.get("/{agent_id}/fs", response_model=ApiResponse[list[FsEntryOut]])
def list_agent_fs_api(
    agent_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    instance = db.query(AgentInstance).filter(AgentInstance.id == agent_id).first()
    if not instance:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    if int(instance.creator_user_id) != int(user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    entries = list_agent_fs(int(agent_id))
    return ApiResponse(data=[FsEntryOut.model_validate(e) for e in entries])


@router.get("/{agent_id}/fs/{path:path}", response_model=ApiResponse[TextFileOut])
def read_agent_fs_api(
    agent_id: int,
    path: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    instance = db.query(AgentInstance).filter(AgentInstance.id == agent_id).first()
    if not instance:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    if int(instance.creator_user_id) != int(user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    try:
        content = read_agent_text_file(int(agent_id), path)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    return ApiResponse(data=TextFileOut(path=path, content=content))


@router.put("/{agent_id}/fs/{path:path}", response_model=ApiResponse[TextFileOut])
def write_agent_fs_api(
    agent_id: int,
    path: str,
    payload: TextFileWriteRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    instance = db.query(AgentInstance).filter(AgentInstance.id == agent_id).first()
    if not instance:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    if int(instance.creator_user_id) != int(user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    try:
        write_agent_text_file(int(agent_id), path, payload.content)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    return ApiResponse(data=TextFileOut(path=path, content=payload.content))


@router.delete("/{agent_id}/fs/{path:path}", response_model=ApiResponse[bool])
def delete_agent_fs_api(
    agent_id: int,
    path: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    instance = db.query(AgentInstance).filter(AgentInstance.id == agent_id).first()
    if not instance:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    if int(instance.creator_user_id) != int(user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    try:
        delete_agent_file(int(agent_id), path)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    return ApiResponse(data=True)


@router.get("/{agent_id}/tools/toggles", response_model=ApiResponse[AgentToolTogglesOut])
def get_agent_tool_toggles_api(
    agent_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enabled = get_agent_tool_toggles(db, agent_id=int(agent_id), creator_user_id=int(user.id))
    return ApiResponse(data=AgentToolTogglesOut(enabled=enabled))


@router.put("/{agent_id}/tools/toggles", response_model=ApiResponse[AgentToolTogglesOut])
def update_agent_tool_toggles_api(
    agent_id: int,
    payload: AgentToolTogglesUpdateRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enabled = update_agent_tool_toggles(db, agent_id=int(agent_id), creator_user_id=int(user.id), enabled=payload.enabled)
    return ApiResponse(data=AgentToolTogglesOut(enabled=enabled))


@router.get("/skill-pool", response_model=ApiResponse[list[SkillPoolItemOut]])
def list_skill_pool_api(
    user=Depends(get_current_user),
):
    _ = user
    items = list_skill_pool()
    return ApiResponse(data=[SkillPoolItemOut.model_validate(item) for item in items])


@router.get("/{agent_id}/skills/config", response_model=ApiResponse[AgentSkillConfigOut])
def get_agent_skill_config_api(
    agent_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    instance = db.query(AgentInstance).filter(AgentInstance.id == agent_id).first()
    if not instance:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    if int(instance.creator_user_id) != int(user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    cfg = load_agent_skills_config(int(agent_id))
    return ApiResponse(data=AgentSkillConfigOut.model_validate(cfg))


@router.put("/{agent_id}/skills/config", response_model=ApiResponse[AgentSkillConfigOut])
def update_agent_skill_config_api(
    agent_id: int,
    payload: AgentSkillConfigUpdateRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    instance = db.query(AgentInstance).filter(AgentInstance.id == agent_id).first()
    if not instance:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    if int(instance.creator_user_id) != int(user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    cfg = save_agent_skills_config(
        int(agent_id),
        enable_agent_local_skills=payload.enable_agent_local_skills,
        pool_skill_codes=payload.pool_skill_codes,
    )
    return ApiResponse(data=AgentSkillConfigOut.model_validate(cfg))
