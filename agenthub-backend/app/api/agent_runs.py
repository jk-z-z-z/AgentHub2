from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.member import Member
from app.schemas.agent_runs import AgentRunEventOut, AgentRunOut
from app.schemas.common import ApiResponse
from app.services.agent_run_query_service import get_agent_run, list_agent_run_events


router = APIRouter(prefix="/agent-runs", tags=["agent-runs"])


def _assert_group_user_member(db: Session, *, group_id: int, user_id: int) -> Member:
    member = (
        db.query(Member)
        .filter(Member.group_id == int(group_id), Member.kind == "user", Member.user_ref == str(user_id))
        .first()
    )
    if not member:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return member


@router.get("/{run_id}", response_model=ApiResponse[AgentRunOut])
def get_agent_run_api(
    run_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    run = get_agent_run(db, run_id=int(run_id))
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    _assert_group_user_member(db, group_id=int(run.group_id), user_id=int(user.id))
    return ApiResponse(data=AgentRunOut.model_validate(run))


@router.get("/{run_id}/events", response_model=ApiResponse[list[AgentRunEventOut]])
def list_agent_run_events_api(
    run_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    run = get_agent_run(db, run_id=int(run_id))
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    _assert_group_user_member(db, group_id=int(run.group_id), user_id=int(user.id))
    rows = list_agent_run_events(db, run_id=int(run.id))
    return ApiResponse(data=[AgentRunEventOut.model_validate(r) for r in rows])

