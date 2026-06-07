from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.schemas.common import ApiResponse
from app.schemas.preview import PreviewJobOut, PreviewRequest
from app.services.preview_runtime_service import (
    close_preview_job,
    create_or_update_preview_job,
    preview_job_payload_for_user,
    run_preview_job,
)


router = APIRouter(tags=["previews"])


@router.post("/previews", response_model=ApiResponse[PreviewJobOut])
def create_preview_api(
    payload: PreviewRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    create_or_update_preview_job(
        db,
        workspace_id=int(payload.workspace_id),
        user_id=int(user.id),
        source_path=payload.source_path,
        sandbox_image=payload.sandbox_image,
        install_command=payload.install_command,
        build_command=payload.build_command,
        env=payload.env,
        host_port=payload.host_port,
    )
    row = run_preview_job(db, workspace_id=int(payload.workspace_id))
    return ApiResponse(
        data=PreviewJobOut.model_validate(
            preview_job_payload_for_user(db, workspace_id=int(row.workspace_id), user_id=int(user.id))
        )
    )


@router.get("/workspaces/{workspace_id}/preview", response_model=ApiResponse[PreviewJobOut])
def get_workspace_preview_api(
    workspace_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    return ApiResponse(
        data=PreviewJobOut.model_validate(
            preview_job_payload_for_user(db, workspace_id=int(workspace_id), user_id=int(user.id))
        )
    )


@router.delete("/workspaces/{workspace_id}/preview", response_model=ApiResponse[PreviewJobOut])
def delete_workspace_preview_api(
    workspace_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    row = close_preview_job(db, workspace_id=int(workspace_id), user_id=int(user.id))
    return ApiResponse(
        data=PreviewJobOut.model_validate(
            preview_job_payload_for_user(db, workspace_id=int(row.workspace_id), user_id=int(user.id))
        )
    )
