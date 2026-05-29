from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.common import ApiResponse
from app.schemas.group import GroupCreateRequest, GroupOut
from app.services.group_service import create_group, list_groups


router = APIRouter(prefix="/groups", tags=["groups"])


@router.get("", response_model=ApiResponse[list[GroupOut]])
def list_groups_api(db: Session = Depends(get_db)):
    rows = list_groups(db)
    return ApiResponse(data=[GroupOut.model_validate(row) for row in rows])


@router.post("", response_model=ApiResponse[GroupOut])
def create_group_api(payload: GroupCreateRequest, db: Session = Depends(get_db)):
    row = create_group(db, payload.name, payload.description)
    return ApiResponse(data=GroupOut.model_validate(row))
