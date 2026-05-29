from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.agent_instance import AgentInstanceCreateRequest, AgentInstanceOut
from app.schemas.common import ApiResponse
from app.services.agent_instance_service import create_agent_instance, list_agent_instances


router = APIRouter(prefix="/agent-instances", tags=["agent-instances"])


@router.get("", response_model=ApiResponse[list[AgentInstanceOut]])
def list_agent_instances_api(db: Session = Depends(get_db)):
    rows = list_agent_instances(db)
    return ApiResponse(data=[AgentInstanceOut.model_validate(row) for row in rows])


@router.post("", response_model=ApiResponse[AgentInstanceOut])
def create_agent_instance_api(payload: AgentInstanceCreateRequest, db: Session = Depends(get_db)):
    row = create_agent_instance(db, payload.model_dump())
    return ApiResponse(data=AgentInstanceOut.model_validate(row))
