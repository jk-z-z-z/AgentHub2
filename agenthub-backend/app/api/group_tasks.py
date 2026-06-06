from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.event_runtime.context import get_or_create_manager_member
from app.manager_runtime.tool.base import extract_tool_result
from app.manager_runtime.tool.builtins.node_execute import NodeExecuteTool
from app.models.group import Group
from app.models.group_assistant_config import GroupAssistantConfig
from app.models.group_task_run import GroupTaskRun
from app.models.member import Member
from app.schemas.common import ApiResponse
from app.schemas.group_tasks import (
    GroupAssistantConfigOut,
    GroupAssistantConfigUpdateRequest,
    GroupTaskDagUpdateRequest,
    GroupTaskEventOut,
    GroupTaskGraphOut,
    GroupTaskNodeBlockRequest,
    GroupTaskNodeCompleteRequest,
    GroupTaskNodeMemberRequest,
    GroupTaskNodeOut,
    GroupTaskNodeReviewRequest,
    GroupTaskRunCreateRequest,
    GroupTaskRunOut,
)
from app.services.group_task_service import (
    assign_node_to_agent,
    block_role_branch,
    claim_node,
    complete_node,
    create_run,
    get_dag_view,
    get_node,
    list_node_snapshots,
    list_run_events,
    list_runs,
    node_snapshot,
    replace_run_nodes,
    resolve_run,
    review_node,
    unblock_role_branch,
)


router = APIRouter(prefix="/group-tasks", tags=["group-tasks"])


def _assert_group_exists(db: Session, *, group_id: int) -> Group:
    group = db.query(Group).filter(Group.id == int(group_id)).first()
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    return group


def _assert_group_user_member(db: Session, *, group_id: int, user_id: int) -> Member:
    _assert_group_exists(db, group_id=int(group_id))
    member = (
        db.query(Member)
        .filter(Member.group_id == int(group_id), Member.kind == "user", Member.user_ref == str(user_id))
        .first()
    )
    if not member:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return member


def _assert_run_user_member(db: Session, *, run_id: int, user_id: int) -> GroupTaskRun:
    run = resolve_run(db, run_id=int(run_id))
    _assert_group_user_member(db, group_id=int(run.group_id), user_id=int(user_id))
    return run


def _assistant_config_out(db: Session, *, cfg: GroupAssistantConfig) -> GroupAssistantConfigOut:
    manager_member = get_or_create_manager_member(db, group_id=int(cfg.group_id))
    return GroupAssistantConfigOut.model_validate(
        {
            "group_id": str(cfg.group_id),
            "manager_member_id": str(manager_member.id),
            "enabled": int(cfg.enabled),
            "creator_user_id": str(cfg.creator_user_id),
            "created_at": cfg.created_at,
            "updated_at": cfg.updated_at,
        }
    )


def _get_or_create_assistant_config(db: Session, *, group_id: int, creator_user_id: int) -> GroupAssistantConfig:
    cfg = db.query(GroupAssistantConfig).filter(GroupAssistantConfig.group_id == int(group_id)).first()
    if cfg:
        return cfg
    cfg = GroupAssistantConfig(
        group_id=int(group_id),
        assistant_agent_instance_id=None,
        enabled=0,
        creator_user_id=int(creator_user_id),
    )
    db.add(cfg)
    db.commit()
    db.refresh(cfg)
    return cfg


def _node_out(db: Session, *, node_id: int) -> GroupTaskNodeOut:
    row = get_node(db, node_id=int(node_id))
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Node not found")
    return GroupTaskNodeOut.model_validate(node_snapshot(db, node=row))


@router.get("/groups/{group_id}/assistant", response_model=ApiResponse[GroupAssistantConfigOut])
def get_group_assistant_config_api(
    group_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    _assert_group_user_member(db, group_id=int(group_id), user_id=int(user.id))
    cfg = _get_or_create_assistant_config(db, group_id=int(group_id), creator_user_id=int(user.id))
    return ApiResponse(data=_assistant_config_out(db, cfg=cfg))


@router.put("/groups/{group_id}/assistant", response_model=ApiResponse[GroupAssistantConfigOut])
def update_group_assistant_config_api(
    group_id: int,
    payload: GroupAssistantConfigUpdateRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    _assert_group_user_member(db, group_id=int(group_id), user_id=int(user.id))
    cfg = _get_or_create_assistant_config(db, group_id=int(group_id), creator_user_id=int(user.id))
    cfg.enabled = int(payload.enabled)
    db.add(cfg)
    db.commit()
    db.refresh(cfg)
    return ApiResponse(data=_assistant_config_out(db, cfg=cfg))


@router.post("/runs", response_model=ApiResponse[GroupTaskRunOut])
def create_group_task_run_api(
    payload: GroupTaskRunCreateRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    _assert_group_user_member(db, group_id=int(payload.group_id), user_id=int(user.id))
    creator_member = db.query(Member).filter(Member.id == int(payload.creator_member_id)).first()
    if not creator_member or int(creator_member.group_id) != int(payload.group_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Creator member not in group")
    run = create_run(
        db,
        group_id=int(payload.group_id),
        creator_member_id=int(payload.creator_member_id),
        title=payload.title,
        goal_text=payload.goal_text,
        nodes=[node.model_dump() for node in payload.nodes],
        trigger_message_id=int(payload.trigger_message_id) if payload.trigger_message_id not in (None, "") else None,
    )
    return ApiResponse(data=GroupTaskRunOut.model_validate(run))


@router.get("/groups/{group_id}/runs", response_model=ApiResponse[list[GroupTaskRunOut]])
def list_group_task_runs_api(
    group_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    _assert_group_user_member(db, group_id=int(group_id), user_id=int(user.id))
    return ApiResponse(data=[GroupTaskRunOut.model_validate(row) for row in list_runs(db, group_id=int(group_id))])


@router.get("/runs/{run_id}", response_model=ApiResponse[GroupTaskRunOut])
def get_group_task_run_api(
    run_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    run = _assert_run_user_member(db, run_id=int(run_id), user_id=int(user.id))
    return ApiResponse(data=GroupTaskRunOut.model_validate(run))


@router.get("/runs/{run_id}/nodes", response_model=ApiResponse[list[GroupTaskNodeOut]])
def list_group_task_run_nodes_api(
    run_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    _assert_run_user_member(db, run_id=int(run_id), user_id=int(user.id))
    return ApiResponse(data=[GroupTaskNodeOut.model_validate(item) for item in list_node_snapshots(db, run_id=int(run_id))])


@router.get("/runs/{run_id}/events", response_model=ApiResponse[list[GroupTaskEventOut]])
def list_group_task_run_events_api(
    run_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    _assert_run_user_member(db, run_id=int(run_id), user_id=int(user.id))
    return ApiResponse(data=[GroupTaskEventOut.model_validate(row) for row in list_run_events(db, run_id=int(run_id))])


@router.get("/runs/{run_id}/graph", response_model=ApiResponse[GroupTaskGraphOut])
def get_group_task_run_graph_api(
    run_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    _assert_run_user_member(db, run_id=int(run_id), user_id=int(user.id))
    return ApiResponse(data=GroupTaskGraphOut.model_validate(get_dag_view(db, run_id=int(run_id))))


@router.put("/runs/{run_id}/dag", response_model=ApiResponse[GroupTaskRunOut])
def update_group_task_run_dag_api(
    run_id: int,
    payload: GroupTaskDagUpdateRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    _assert_run_user_member(db, run_id=int(run_id), user_id=int(user.id))
    run = replace_run_nodes(db, run_id=int(run_id), nodes=[node.model_dump() for node in payload.nodes])
    return ApiResponse(data=GroupTaskRunOut.model_validate(run))


@router.post("/runs/{run_id}/branches/{role_required}/block", response_model=ApiResponse[int])
def block_group_task_role_branch_api(
    run_id: int,
    role_required: str,
    payload: GroupTaskNodeBlockRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    _assert_run_user_member(db, run_id=int(run_id), user_id=int(user.id))
    count = block_role_branch(db, run_id=int(run_id), role_required=role_required, reason=payload.reason)
    return ApiResponse(data=count)


@router.post("/runs/{run_id}/branches/{role_required}/unblock", response_model=ApiResponse[int])
def unblock_group_task_role_branch_api(
    run_id: int,
    role_required: str,
    payload: GroupTaskNodeBlockRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    _assert_run_user_member(db, run_id=int(run_id), user_id=int(user.id))
    count = unblock_role_branch(db, run_id=int(run_id), role_required=role_required, reason=payload.reason)
    return ApiResponse(data=count)


@router.post("/nodes/{node_id}/claim", response_model=ApiResponse[GroupTaskNodeOut])
def claim_group_task_node_api(
    node_id: int,
    payload: GroupTaskNodeMemberRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    node = get_node(db, node_id=int(node_id))
    if not node:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Node not found")
    _assert_group_user_member(db, group_id=int(node.group_id), user_id=int(user.id))
    row = claim_node(db, node_id=int(node_id), member_id=int(payload.member_id))
    return ApiResponse(data=GroupTaskNodeOut.model_validate(node_snapshot(db, node=row)))


@router.post("/nodes/{node_id}/complete", response_model=ApiResponse[GroupTaskNodeOut])
def complete_group_task_node_api(
    node_id: int,
    payload: GroupTaskNodeCompleteRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    node = get_node(db, node_id=int(node_id))
    if not node:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Node not found")
    member_id = payload.member_id
    if member_id in (None, ""):
        member_id = _assert_group_user_member(db, group_id=int(node.group_id), user_id=int(user.id)).id
    else:
        _assert_group_user_member(db, group_id=int(node.group_id), user_id=int(user.id))
    row = complete_node(db, node_id=int(node_id), member_id=int(member_id), output_summary=payload.output_summary)
    return ApiResponse(data=GroupTaskNodeOut.model_validate(node_snapshot(db, node=row)))


@router.post("/nodes/{node_id}/review", response_model=ApiResponse[GroupTaskNodeOut])
def review_group_task_node_api(
    node_id: int,
    payload: GroupTaskNodeReviewRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    node = get_node(db, node_id=int(node_id))
    if not node:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Node not found")
    reviewer = _assert_group_user_member(db, group_id=int(node.group_id), user_id=int(user.id))
    row = review_node(
        db,
        node_id=int(node_id),
        reviewer_member_id=int(reviewer.id),
        manager_review_status=payload.manager_review_status,
        note=payload.note,
    )
    return ApiResponse(data=GroupTaskNodeOut.model_validate(node_snapshot(db, node=row)))


@router.post("/nodes/{node_id}/assign-agent", response_model=ApiResponse[GroupTaskNodeOut])
def assign_group_task_node_to_agent_api(
    node_id: int,
    payload: GroupTaskNodeMemberRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    node = get_node(db, node_id=int(node_id))
    if not node:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Node not found")
    _assert_group_user_member(db, group_id=int(node.group_id), user_id=int(user.id))
    row = assign_node_to_agent(db, node_id=int(node_id), member_id=int(payload.member_id))
    return ApiResponse(data=GroupTaskNodeOut.model_validate(node_snapshot(db, node=row)))


@router.post("/nodes/{node_id}/execute", response_model=ApiResponse[GroupTaskNodeOut])
async def execute_group_task_node_api(
    node_id: int,
    payload: GroupTaskNodeMemberRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    node = get_node(db, node_id=int(node_id))
    if not node:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Node not found")
    _assert_group_user_member(db, group_id=int(node.group_id), user_id=int(user.id))
    tool = NodeExecuteTool(db=db)
    result = extract_tool_result(await tool(node_id=int(node_id), member_id=int(payload.member_id)))
    if not result["ok"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.get("error") or "node_execute_failed")
    return ApiResponse(data=_node_out(db, node_id=int(node_id)))
