from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.ai import AIChatRequest, AIChatResponse
from app.schemas.common import ApiResponse
from app.services._zero_deps_ai_helpers import simple_internal_llm_chat as internal_llm_chat


router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/chat", response_model=ApiResponse[AIChatResponse])
async def ai_chat_api(
    payload: AIChatRequest,
    db: Session = Depends(get_db),
):
    _ = db
    agent_instance_id = int(payload.agent_instance_id) if payload.agent_instance_id else None
    reply = await internal_llm_chat(
        payload.message,
        system_prompt=payload.system_prompt,
        agent_instance_id=agent_instance_id,
        runtime_context=payload.runtime_context or None,
    )
    return ApiResponse(data=AIChatResponse(reply=reply))
