from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.fs import DirectoryCreateRequest, FsEntryOut, TextFileOut, TextFileWriteRequest
from app.services.project_code_service import (
    create_project_code_directory,
    delete_project_code_entry,
    ensure_user_can_access_project_code,
    list_project_code_fs,
    normalize_project_rel_path,
    read_project_code_file,
    write_project_code_file,
)


router = APIRouter(prefix="/project-code", tags=["project-code"])


@router.get("/{group_id}", response_model=ApiResponse[list[FsEntryOut]])
def list_project_code_api(
    group_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ensure_user_can_access_project_code(db, group_id=group_id, user_id=int(user.id))
    rows = list_project_code_fs(group_id)
    return ApiResponse(data=[FsEntryOut.model_validate(row) for row in rows])


@router.get("/{group_id}/{path:path}", response_model=ApiResponse[TextFileOut])
def read_project_code_api(
    group_id: int,
    path: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ensure_user_can_access_project_code(db, group_id=group_id, user_id=int(user.id))
    try:
        content = read_project_code_file(group_id, path)
        rel = normalize_project_rel_path(path)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    return ApiResponse(data=TextFileOut(path=rel, content=content))


@router.put("/{group_id}/{path:path}", response_model=ApiResponse[TextFileOut])
def write_project_code_api(
    group_id: int,
    path: str,
    payload: TextFileWriteRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ensure_user_can_access_project_code(db, group_id=group_id, user_id=int(user.id))
    try:
        data = write_project_code_file(group_id, path, payload.content)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    return ApiResponse(data=TextFileOut.model_validate(data))


@router.post("/{group_id}/directories", response_model=ApiResponse[FsEntryOut])
def create_project_code_dir_api(
    group_id: int,
    payload: DirectoryCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ensure_user_can_access_project_code(db, group_id=group_id, user_id=int(user.id))
    try:
        data = create_project_code_directory(group_id, payload.path)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    return ApiResponse(data=FsEntryOut.model_validate(data))


@router.delete("/{group_id}/{path:path}", response_model=ApiResponse[FsEntryOut])
def delete_project_code_api(
    group_id: int,
    path: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ensure_user_can_access_project_code(db, group_id=group_id, user_id=int(user.id))
    try:
        data = delete_project_code_entry(group_id, path)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    return ApiResponse(data=FsEntryOut.model_validate(data))
