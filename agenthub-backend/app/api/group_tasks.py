from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.group import Group
from app.models.group_assistant_config import GroupAssistantConfig
from app.models.member import Member
from app.schemas.common import ApiResponse
from app.schemas.group_tasks import (
    GroupAssistantConfigOut,
    GroupAssistantConfigUpdateRequest,
    GroupTaskClaimRequest,
    GroupTaskDagUpdateRequest,
    GroupTaskEventOut,
    GroupTaskNodeBlockRequest,
    GroupTaskNodeCompleteRequest,
    GroupTaskNodeOut,
    GroupTaskNodeReviewRequest,
    GroupTaskRunCreateRequest,
    GroupTaskRunOut,
)
from app.services.group_task.node_service import (
    block_role_branch_nodes,
    claim_task_node,
    create_group_task_run,
    get_group_task_run,
    list_group_task_nodes,
    list_group_task_events,
    list_group_task_runs,
    review_task_node,
    unblock_role_branch_nodes,
    update_group_task_dag,
)
from app.services.group_task.manager_service import (
    get_or_create_group_assistant_config,
    get_or_create_manager_member,
    update_group_assistant_config,
)
from app.services.group_task.orchestration.node_orchestration import complete_node_with_auto_review


router = APIRouter(prefix="/group-tasks", tags=["group-tasks"])


def _assert_group_user_member(db: Session, *, group_id: int, user_id: int) -> Member:
    member = (
        db.query(Member)
        .filter(Member.group_id == int(group_id), Member.kind == "user", Member.user_ref == str(user_id))
        .first()
    )
    if not member:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return member


@router.get("/groups/{group_id}/assistant", response_model=ApiResponse[GroupAssistantConfigOut])
def get_group_assistant_api(
    group_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    group = db.query(Group).filter(Group.id == int(group_id)).first()
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    _assert_group_user_member(db, group_id=int(group_id), user_id=int(user.id))
    row = get_or_create_group_assistant_config(db, group_id=int(group_id), creator_user_id=int(user.id))
    manager = get_or_create_manager_member(db, group_id=int(group_id))
    return ApiResponse(
        data=GroupAssistantConfigOut(
            group_id=str(row.group_id),
            manager_member_id=str(manager.id),
            enabled=int(row.enabled),
            creator_user_id=str(row.creator_user_id),
        )
    )


@router.put("/groups/{group_id}/assistant", response_model=ApiResponse[GroupAssistantConfigOut])
def update_group_assistant_api(
    group_id: int,
    payload: GroupAssistantConfigUpdateRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    group = db.query(Group).filter(Group.id == int(group_id)).first()
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    _assert_group_user_member(db, group_id=int(group_id), user_id=int(user.id))
    row = update_group_assistant_config(
        db,
        group_id=int(group_id),
        creator_user_id=int(user.id),
        enabled=int(payload.enabled),
    )
    manager = get_or_create_manager_member(db, group_id=int(group_id))
    return ApiResponse(
        data=GroupAssistantConfigOut(
            group_id=str(row.group_id),
            manager_member_id=str(manager.id),
            enabled=int(row.enabled),
            creator_user_id=str(row.creator_user_id),
        )
    )


@router.post("/runs", response_model=ApiResponse[GroupTaskRunOut])
def create_group_task_run_api(
    payload: GroupTaskRunCreateRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    member = _assert_group_user_member(db, group_id=int(payload.group_id), user_id=int(user.id))
    if int(member.id) != int(payload.creator_member_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="creator_member_id must be current user's member id")
    run = create_group_task_run(
        db,
        group_id=int(payload.group_id),
        creator_member_id=int(payload.creator_member_id),
        title=payload.title,
        goal_text=payload.goal_text,
        nodes=[n.model_dump() for n in payload.nodes],
        trigger_message_id=int(payload.trigger_message_id) if payload.trigger_message_id is not None else None,
    )
    return ApiResponse(data=GroupTaskRunOut.model_validate(run))


@router.get("/groups/{group_id}/runs", response_model=ApiResponse[list[GroupTaskRunOut]])
def list_group_task_runs_api(
    group_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    _assert_group_user_member(db, group_id=int(group_id), user_id=int(user.id))
    rows = list_group_task_runs(db, group_id=int(group_id))
    return ApiResponse(data=[GroupTaskRunOut.model_validate(r) for r in rows])


@router.get("/runs/{run_id}", response_model=ApiResponse[GroupTaskRunOut])
def get_group_task_run_api(
    run_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    run = get_group_task_run(db, run_id=int(run_id))
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    _assert_group_user_member(db, group_id=int(run.group_id), user_id=int(user.id))
    return ApiResponse(data=GroupTaskRunOut.model_validate(run))


@router.get("/runs/{run_id}/nodes", response_model=ApiResponse[list[GroupTaskNodeOut]])
def list_group_task_nodes_api(
    run_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    run = get_group_task_run(db, run_id=int(run_id))
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    _assert_group_user_member(db, group_id=int(run.group_id), user_id=int(user.id))
    rows = list_group_task_nodes(db, run_id=int(run.id))
    out = [
        GroupTaskNodeOut(
            id=str(row.id),
            run_id=str(row.run_id),
            node_key=row.node_key,
            title=row.title,
            detail=row.detail,
            role_required=row.role_required,
            deps=json.loads(row.deps_json or "[]"),
            status=row.status,
            assignee_kind=row.assignee_kind,
            assignee_member_id=str(row.assignee_member_id) if row.assignee_member_id is not None else None,
            output_summary=row.output_summary,
            manager_review_status=row.manager_review_status,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
        for row in rows
    ]
    return ApiResponse(data=out)


@router.get("/runs/{run_id}/events", response_model=ApiResponse[list[GroupTaskEventOut]])
def list_group_task_events_api(
    run_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    run = get_group_task_run(db, run_id=int(run_id))
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    _assert_group_user_member(db, group_id=int(run.group_id), user_id=int(user.id))
    rows = list_group_task_events(db, run_id=int(run.id))
    return ApiResponse(data=[GroupTaskEventOut.model_validate(r) for r in rows])


@router.put("/runs/{run_id}/dag", response_model=ApiResponse[GroupTaskRunOut])
def update_group_task_dag_api(
    run_id: int,
    payload: GroupTaskDagUpdateRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    run = get_group_task_run(db, run_id=int(run_id))
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    _assert_group_user_member(db, group_id=int(run.group_id), user_id=int(user.id))
    updated = update_group_task_dag(db, run_id=int(run.id), nodes=[n.model_dump() for n in payload.nodes])
    return ApiResponse(data=GroupTaskRunOut.model_validate(updated))


@router.post("/nodes/{node_id}/claim", response_model=ApiResponse[GroupTaskNodeOut])
def claim_group_task_node_api(
    node_id: int,
    payload: GroupTaskClaimRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    node = claim_task_node(db, node_id=int(node_id), member_id=int(payload.member_id))
    run = get_group_task_run(db, run_id=int(node.run_id))
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    _assert_group_user_member(db, group_id=int(run.group_id), user_id=int(user.id))
    out = GroupTaskNodeOut(
        **{
            **GroupTaskNodeOut.model_validate(node).model_dump(),
            "deps": json.loads(node.deps_json or "[]"),
        }
    )
    return ApiResponse(data=out)


@router.post("/nodes/{node_id}/complete", response_model=ApiResponse[GroupTaskNodeOut])
async def complete_group_task_node_api(
    node_id: int,
    payload: GroupTaskNodeCompleteRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    node, err = await complete_node_with_auto_review(
        db,
        node_id=int(node_id),
        user_id=int(user.id),
        output_summary=payload.output_summary,
    )
    if err:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=err)

    out = GroupTaskNodeOut(
        **{
            **GroupTaskNodeOut.model_validate(node).model_dump(),
            "deps": json.loads(node.deps_json or "[]"),
        }
    )
    return ApiResponse(data=out)


@router.post("/nodes/{node_id}/review", response_model=ApiResponse[GroupTaskNodeOut])
def review_group_task_node_api(
    node_id: int,
    payload: GroupTaskNodeReviewRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    _ = user
    node = review_task_node(
        db,
        node_id=int(node_id),
        manager_review_status=payload.manager_review_status,
        note=payload.note,
    )
    out = GroupTaskNodeOut(
        **{
            **GroupTaskNodeOut.model_validate(node).model_dump(),
            "deps": json.loads(node.deps_json or "[]"),
        }
    )
    return ApiResponse(data=out)


@router.post("/runs/{run_id}/branches/{role_required}/block", response_model=ApiResponse[int])
def block_role_branch_api(
    run_id: int,
    role_required: str,
    payload: GroupTaskNodeBlockRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    run = get_group_task_run(db, run_id=int(run_id))
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    _assert_group_user_member(db, group_id=int(run.group_id), user_id=int(user.id))
    changed = block_role_branch_nodes(
        db,
        run_id=int(run.id),
        role_required=role_required,
        reason=payload.reason,
    )
    return ApiResponse(data=int(changed))


@router.post("/runs/{run_id}/branches/{role_required}/unblock", response_model=ApiResponse[int])
def unblock_role_branch_api(
    run_id: int,
    role_required: str,
    payload: GroupTaskNodeBlockRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    run = get_group_task_run(db, run_id=int(run_id))
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    _assert_group_user_member(db, group_id=int(run.group_id), user_id=int(user.id))
    changed = unblock_role_branch_nodes(
        db,
        run_id=int(run.id),
        role_required=role_required,
        reason=payload.reason,
    )
    return ApiResponse(data=int(changed))
