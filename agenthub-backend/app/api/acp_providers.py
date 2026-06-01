from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.schemas.common import ApiResponse
from app.schemas.acp_provider import ACPProviderOut
from app.agent_runtime.acp.provider_service import (
    ensure_default_acp_providers_seeded,
    list_acp_providers,
    set_acp_provider_active,
)


router = APIRouter(tags=["acp_providers"])


@router.get("/acp-providers", response_model=ApiResponse[list[ACPProviderOut]])
def list_acp_providers_api(db: Session = Depends(get_db), user=Depends(get_current_user)):
    ensure_default_acp_providers_seeded(db, creator_user_id=int(user.id))
    rows = list_acp_providers(db, creator_user_id=int(user.id))
    data = [ACPProviderOut.model_validate(r).model_dump() for r in rows]
    return ApiResponse(data=data)


@router.put("/acp-providers/{provider_type}/active", response_model=ApiResponse[ACPProviderOut])
def set_acp_provider_active_api(
    provider_type: str,
    payload: dict,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    is_active = int(payload.get("is_active", 0))
    try:
        row = set_acp_provider_active(
            db,
            creator_user_id=int(user.id),
            provider_type=str(provider_type),
            is_active=is_active,
        )
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ACP provider not found")
    return ApiResponse(data=ACPProviderOut.model_validate(row).model_dump())
