from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.schemas.common import ApiResponse
from app.schemas.deployment import DeploymentJobOut, DeploymentRequest
from app.services.deployment_runtime_service import (
    create_deployment_job,
    deployment_job_payload_for_user,
    retry_deployment_job,
    run_deployment_job,
)


router = APIRouter(prefix="/deployments", tags=["deployments"])


@router.post("", response_model=ApiResponse[DeploymentJobOut])
def create_deployment_api(
    payload: DeploymentRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    row = create_deployment_job(
        db,
        workspace_id=int(payload.workspace_id),
        user_id=int(user.id),
        image_ref=payload.image_ref,
        container_name=payload.container_name,
        sandbox_image=payload.sandbox_image,
        dockerfile_path=payload.dockerfile_path,
        build_context_path=payload.build_context_path,
        install_command=payload.install_command,
        test_command=payload.test_command,
        build_command=payload.build_command,
        env=payload.env,
        ports=[item.model_dump() for item in payload.ports],
        container_command=payload.container_command,
    )
    row = run_deployment_job(db, deployment_id=int(row.id))
    return ApiResponse(
        data=DeploymentJobOut.model_validate(
            deployment_job_payload_for_user(db, deployment_id=int(row.id), user_id=int(user.id))
        )
    )


@router.get("/{deployment_id}", response_model=ApiResponse[DeploymentJobOut])
def get_deployment_api(
    deployment_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    return ApiResponse(
        data=DeploymentJobOut.model_validate(
            deployment_job_payload_for_user(db, deployment_id=int(deployment_id), user_id=int(user.id))
        )
    )


@router.post("/{deployment_id}/retry", response_model=ApiResponse[DeploymentJobOut])
def retry_deployment_api(
    deployment_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    row = retry_deployment_job(db, deployment_id=int(deployment_id), user_id=int(user.id))
    return ApiResponse(
        data=DeploymentJobOut.model_validate(
            deployment_job_payload_for_user(db, deployment_id=int(row.id), user_id=int(user.id))
        )
    )
