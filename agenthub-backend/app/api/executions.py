from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.schemas.common import ApiResponse
from app.schemas.execution import ExecutionJobOut, ExecutionRequest
from app.services.execution_runtime_service import (
    create_execution_job,
    execution_job_payload_for_user,
    run_execution_job,
)


router = APIRouter(prefix="/executions", tags=["executions"])


@router.post("", response_model=ApiResponse[ExecutionJobOut])
def create_execution_api(
    payload: ExecutionRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    row = create_execution_job(
        db,
        workspace_id=int(payload.workspace_id),
        user_id=int(user.id),
        command=payload.command,
        cwd=payload.cwd,
        sandbox_image=payload.sandbox_image,
        network_enabled=bool(payload.network_enabled),
        env=payload.env,
    )
    row = run_execution_job(db, job_id=int(row.id))
    return ApiResponse(data=ExecutionJobOut.model_validate(execution_job_payload_for_user(db, job_id=int(row.id), user_id=int(user.id))))


@router.get("/{execution_id}", response_model=ApiResponse[ExecutionJobOut])
def get_execution_api(
    execution_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    return ApiResponse(
        data=ExecutionJobOut.model_validate(
            execution_job_payload_for_user(db, job_id=int(execution_id), user_id=int(user.id))
        )
    )
