from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.schemas.common import ApiResponse
from app.schemas.group import GroupCreateRequest, GroupOut
from app.schemas.memory import ProjectMemoryCompressRunOut, ProjectMemoryCompressorStatusOut
from app.schemas.memory_config import ProjectMemoryCompressorConfigOut, ProjectMemoryCompressorConfigUpdateRequest
from app.memory_runtime import (
    get_project_memory_compressor_config,
    get_project_memory_compressor_status,
    maybe_compress_project_memory,
    update_project_memory_compressor_config,
)
from app.services.group_service import create_group, delete_group, get_group, list_groups
from app.services.member_service import create_agent_member, create_user_member
from app.services.workspace_runtime_service import get_workspace_for_project
from app.models.member import Member


router = APIRouter(prefix="/groups", tags=["groups"])


@router.get("", response_model=ApiResponse[list[GroupOut]])
def list_groups_api(db: Session = Depends(get_db)):
    rows = list_groups(db)
    data: list[GroupOut] = []
    for row in rows:
        workspace = get_workspace_for_project(db, project_id=int(row.id)) if str(row.type) == "project" else None
        item = GroupOut.model_validate(row).model_copy(update={"workspace_id": str(workspace.id) if workspace else None})
        data.append(item)
    return ApiResponse(data=data)

@router.delete("/{group_id}", response_model=ApiResponse[bool])
def delete_group_api(
    group_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    group = get_group(db, int(group_id))
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")

    # Only members can delete a group (MVP rule)
    member = (
        db.query(Member)
        .filter(Member.group_id == int(group_id), Member.kind == "user", Member.user_ref == str(user.id))
        .first()
    )
    if not member:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    delete_group(db, group_id=int(group_id))
    return ApiResponse(data=True)


@router.post("", response_model=ApiResponse[GroupOut])
def create_group_api(
    payload: GroupCreateRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    row = create_group(
        db,
        payload.name,
        payload.description,
        creator_user_id=int(user.id),
        group_type=payload.type,
    )

    # The creator is always a member (both project & personal)
    creator_display = str(user.display_name or user.username or user.email)
    create_user_member(db, str(row.id), creator_display, str(user.id), None)

    if payload.type == "personal":
        # With creator included, personal group can only have 1 more member.
        total_to_add = len(payload.users) + len(payload.agents)
        if total_to_add > 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Personal group can only have 1 additional member besides creator",
            )

    for u in payload.users:
        create_user_member(db, str(row.id), u.display_name, str(u.user_id), u.title)
    for a in payload.agents:
        create_agent_member(db, str(row.id), a.display_name, str(a.agent_id), a.title)
    workspace = get_workspace_for_project(db, project_id=int(row.id)) if payload.type == "project" else None
    out = GroupOut.model_validate(row).model_copy(update={"workspace_id": str(workspace.id) if workspace else None})
    return ApiResponse(data=out)


def _assert_group_member(db: Session, *, group_id: int, user_id: int) -> None:
    member = (
        db.query(Member)
        .filter(Member.group_id == int(group_id), Member.kind == "user", Member.user_ref == str(user_id))
        .first()
    )
    if not member:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


@router.get("/{group_id}/memory/compressor-status", response_model=ApiResponse[ProjectMemoryCompressorStatusOut])
def get_group_memory_compressor_status_api(
    group_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    group = get_group(db, int(group_id))
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    _assert_group_member(db, group_id=int(group_id), user_id=int(user.id))
    status_data = get_project_memory_compressor_status(db, project_id=int(group_id))
    return ApiResponse(data=ProjectMemoryCompressorStatusOut.model_validate(status_data))


@router.get("/{group_id}/memory/compressor-config", response_model=ApiResponse[ProjectMemoryCompressorConfigOut])
def get_group_memory_compressor_config_api(
    group_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    group = get_group(db, int(group_id))
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    _assert_group_member(db, group_id=int(group_id), user_id=int(user.id))
    cfg = get_project_memory_compressor_config(int(group_id))
    return ApiResponse(data=ProjectMemoryCompressorConfigOut.model_validate(cfg))


@router.put("/{group_id}/memory/compressor-config", response_model=ApiResponse[ProjectMemoryCompressorConfigOut])
def update_group_memory_compressor_config_api(
    group_id: int,
    payload: ProjectMemoryCompressorConfigUpdateRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    group = get_group(db, int(group_id))
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    _assert_group_member(db, group_id=int(group_id), user_id=int(user.id))
    cfg = update_project_memory_compressor_config(int(group_id), payload.model_dump())
    return ApiResponse(data=ProjectMemoryCompressorConfigOut.model_validate(cfg))


@router.post("/{group_id}/memory/compress", response_model=ApiResponse[ProjectMemoryCompressRunOut])
async def run_group_memory_compress_api(
    group_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    group = get_group(db, int(group_id))
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    _assert_group_member(db, group_id=int(group_id), user_id=int(user.id))

    result = await maybe_compress_project_memory(
        db,
        project_id=int(group_id),
    )
    return ApiResponse(data=ProjectMemoryCompressRunOut.model_validate(result))
