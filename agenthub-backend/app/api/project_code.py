from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.fs import FsEntryOut, TextFileOut
from app.services.project_code_service import (
    ensure_user_can_access_project_code,
    list_project_code_fs,
    normalize_project_rel_path,
    read_project_code_file,
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
