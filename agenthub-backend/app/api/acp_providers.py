from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.acp_provider import ACPProviderCreateRequest, ACPProviderOut
from app.schemas.common import ApiResponse
from app.services.acp_provider_service import create_acp_provider, list_acp_providers


router = APIRouter(prefix="/acp-providers", tags=["acp-providers"])


@router.get("", response_model=ApiResponse[list[ACPProviderOut]])
def list_acp_providers_api(db: Session = Depends(get_db)):
    rows = list_acp_providers(db)
    return ApiResponse(data=[ACPProviderOut.model_validate(row) for row in rows])


@router.post("", response_model=ApiResponse[ACPProviderOut])
def create_acp_provider_api(payload: ACPProviderCreateRequest, db: Session = Depends(get_db)):
    row = create_acp_provider(db, payload.model_dump())
    return ApiResponse(data=ACPProviderOut.model_validate(row))
