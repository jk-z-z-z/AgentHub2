from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.schemas.common import ApiResponse
from app.schemas.message_events import MessageEventOut
from app.schemas.message_code_diff import MessageCodeDiffOut
from app.schemas.message import MessageCreateRequest, MessageOut
from app.event_runtime.facade import list_message_events
from app.services.message_code_diff_service import get_message_code_diff
from app.services.message_service import create_message_and_trigger_ai, list_messages


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
    row = await create_message_and_trigger_ai(
        db,
        group_id=int(payload.group_id),
        sender_member_id=int(payload.sender_member_id),
        message_type=payload.message_type,
        content=payload.content,
        meta_json=payload.metadata_json,
    )
    return ApiResponse(data=MessageOut.model_validate(row))


@router.get("/{message_id}/events", response_model=ApiResponse[list[MessageEventOut]])
def list_message_events_api(message_id: int, db: Session = Depends(get_db)):
    rows = list_message_events(db, message_id=int(message_id))
    return ApiResponse(data=[MessageEventOut.model_validate(row) for row in rows])


@router.get("/{message_id}/code-diff", response_model=ApiResponse[MessageCodeDiffOut])
def get_message_code_diff_api(
    message_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    data = get_message_code_diff(db, message_id=int(message_id), user_id=int(user.id))
    return ApiResponse(data=data)
