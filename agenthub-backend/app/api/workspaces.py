from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.schemas.common import ApiResponse
from app.schemas.workspace_runtime import WorkspaceOut, WorkspaceSnapshotCreateRequest, WorkspaceSnapshotOut
from app.services.workspace_runtime_service import (
    assert_workspace_access,
    create_workspace_snapshot_for_user,
)


router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.get("/{workspace_id}", response_model=ApiResponse[WorkspaceOut])
def get_workspace_api(
    workspace_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    row = assert_workspace_access(db, workspace_id=int(workspace_id), user_id=int(user.id))
    return ApiResponse(data=WorkspaceOut.model_validate(row))


@router.post("/{workspace_id}/snapshots", response_model=ApiResponse[WorkspaceSnapshotOut])
def create_workspace_snapshot_api(
    workspace_id: int,
    payload: WorkspaceSnapshotCreateRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    try:
        workspace, snapshot = create_workspace_snapshot_for_user(
            db,
            workspace_id=int(workspace_id),
            user_id=int(user.id),
            label=payload.label,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return ApiResponse(
        data=WorkspaceSnapshotOut(
            workspace_id=int(workspace.id),
            snapshot_id=snapshot.snapshot_id,
            snapshot_path=snapshot.snapshot_path,
            source_path=snapshot.source_path,
            digest=snapshot.digest,
            file_count=int(snapshot.file_count),
            created_at=snapshot.created_at,
        )
    )
