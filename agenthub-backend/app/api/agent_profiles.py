from fastapi import APIRouter, Body, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies.auth import get_current_user
from app.db.session import get_db
from app.schemas.agent_profile import AgentProfileCreateRequest, AgentProfileOut
from app.schemas.common import ApiResponse
from app.schemas.workspace import WorkspaceFileContentOut, WorkspaceFileTogglesOut, WorkspaceFileWriteRequest
from app.services.agent_profile_files import (
    PROFILE_FILE_MAP,
    get_profile_enabled_files,
    get_profile_file_content,
    set_profile_enabled_files,
    set_profile_file_content,
)
from app.services.agent_profile_service import create_agent_profile, list_agent_profiles
from app.models.agent_profile import AgentProfile


router = APIRouter(prefix="/agent-profiles", tags=["agent-profiles"])


@router.get("", response_model=ApiResponse[list[AgentProfileOut]])
def list_agent_profiles_api(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    rows = list_agent_profiles(db, creator_user_id=int(user.id))
    return ApiResponse(data=[AgentProfileOut.model_validate(row) for row in rows])


@router.post("", response_model=ApiResponse[AgentProfileOut])
def create_agent_profile_api(
    payload: AgentProfileCreateRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    row = create_agent_profile(db, payload.model_dump(), creator_user_id=int(user.id))
    return ApiResponse(data=AgentProfileOut.model_validate(row))

@router.get("/{profile_id}/files", response_model=ApiResponse[list[str]])
def list_profile_files_api(
    profile_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    profile = db.query(AgentProfile).filter(AgentProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent profile not found")
    if int(profile.creator_user_id) != int(user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return ApiResponse(data=sorted(PROFILE_FILE_MAP.keys()))


@router.get("/{profile_id}/files/{filename}", response_model=ApiResponse[WorkspaceFileContentOut])
def get_profile_file_api(
    profile_id: int,
    filename: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    profile = db.query(AgentProfile).filter(AgentProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent profile not found")
    if int(profile.creator_user_id) != int(user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    try:
        content = get_profile_file_content(profile, filename)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    return ApiResponse(data=WorkspaceFileContentOut(name=filename, content=content))


@router.put("/{profile_id}/files/{filename}", response_model=ApiResponse[WorkspaceFileContentOut])
def update_profile_file_api(
    profile_id: int,
    filename: str,
    payload: WorkspaceFileWriteRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    profile = db.query(AgentProfile).filter(AgentProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent profile not found")
    if int(profile.creator_user_id) != int(user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    try:
        set_profile_file_content(profile, filename, payload.content)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    db.add(profile)
    db.commit()
    return ApiResponse(data=WorkspaceFileContentOut(name=filename, content=payload.content))


@router.get("/{profile_id}/file-toggles", response_model=ApiResponse[WorkspaceFileTogglesOut])
def get_profile_toggles_api(
    profile_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    profile = db.query(AgentProfile).filter(AgentProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent profile not found")
    if int(profile.creator_user_id) != int(user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return ApiResponse(data=WorkspaceFileTogglesOut(enabled_files=get_profile_enabled_files(profile)))


@router.put("/{profile_id}/file-toggles", response_model=ApiResponse[WorkspaceFileTogglesOut])
def update_profile_toggles_api(
    profile_id: int,
    payload: dict[str, bool] = Body(default={}),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    profile = db.query(AgentProfile).filter(AgentProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent profile not found")
    if int(profile.creator_user_id) != int(user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    set_profile_enabled_files(profile, payload)
    db.add(profile)
    db.commit()
    return ApiResponse(data=WorkspaceFileTogglesOut(enabled_files=get_profile_enabled_files(profile)))
