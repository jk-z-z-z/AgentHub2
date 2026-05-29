from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.common import ApiResponse
from app.schemas.member import AgentMemberCreateRequest, MemberOut, MemberUpdateRequest, UserMemberCreateRequest
from app.services.member_service import create_agent_member, create_user_member, delete_member, list_members, update_member


router = APIRouter(prefix="/members", tags=["members"])


@router.get("", response_model=ApiResponse[list[MemberOut]])
def list_members_api(group_id: str | None = Query(None), db: Session = Depends(get_db)):
    rows = list_members(db, int(group_id) if group_id is not None else None)
    return ApiResponse(data=[MemberOut.model_validate(row) for row in rows])


@router.post("/users", response_model=ApiResponse[MemberOut])
def create_user_member_api(payload: UserMemberCreateRequest, db: Session = Depends(get_db)):
    row = create_user_member(db, payload.group_id,payload.display_name,payload.user_ref,payload.title)
    return ApiResponse(data=MemberOut.model_validate(row))


@router.post("/agents", response_model=ApiResponse[MemberOut])
def create_agent_member_api(payload: AgentMemberCreateRequest, db: Session = Depends(get_db)):
    row = create_agent_member(db, payload.group_id,payload.display_name,payload.agent_instance_id,payload.title)
    return ApiResponse(data=MemberOut.model_validate(row))


@router.put("/{member_id}", response_model=ApiResponse[MemberOut])
def update_member_api(member_id: str, payload: MemberUpdateRequest, db: Session = Depends(get_db)):
    row = update_member(db, int(member_id), payload.display_name,payload.title)
    return ApiResponse(data=MemberOut.model_validate(row))


@router.delete("/{member_id}", response_model=ApiResponse[bool])
def delete_member_api(member_id: str, db: Session = Depends(get_db)):
    delete_member(db, int(member_id))
    return ApiResponse(data=True)
