from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.common import ApiResponse
from app.schemas.message import MessageCreateRequest, MessageOut
from app.services.message_service import create_message, list_messages


router = APIRouter(prefix="/messages", tags=["messages"])


@router.get("", response_model=ApiResponse[list[MessageOut]])
def list_messages_api(
    group_id: str,
    cursor: str | None = None,
    limit: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
):
    rows = list_messages(
        db,
        group_id=int(group_id),
        cursor=int(cursor) if cursor is not None else None,
        limit=limit,
    )
    return ApiResponse(data=[MessageOut.model_validate(row) for row in rows])


@router.post("", response_model=ApiResponse[MessageOut])
async def create_message_api(payload: MessageCreateRequest, db: Session = Depends(get_db)):


    row = await create_message(db, int(payload.group_id),
                                    int(payload.sender_member_id),
                                    payload.message_type,
                                    payload.content,
                                    payload.metadata_json)
    return ApiResponse(data=MessageOut.model_validate(row))
