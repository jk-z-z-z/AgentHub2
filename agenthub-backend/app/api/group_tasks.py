from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.group import Group
from app.models.member import Member
from app.services.group_task.dag_service import get_node
from app.schemas.common import ApiResponse
from app.schemas.group_tasks import (
    GroupTaskNodeCompleteRequest,
    GroupTaskNodeCreateRequest,
    GroupTaskNodeMemberRequest,
    GroupTaskNodeOut,
)
from app.services.group_task.dag_service import create_nodes, get_dag_view, list_nodes
from app.services.group_task.node_status_service import assign_node_to_agent, claim_node, complete_node
from app.manager_runtime.tool.builtins.node_execute import NodeExecuteTool


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


@router.get("/groups/{group_id}/graph", response_model=ApiResponse[dict])
def get_group_task_graph_api(group_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    group = db.query(Group).filter(Group.id == int(group_id)).first()
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    _assert_group_user_member(db, group_id=int(group_id), user_id=int(user.id))
    return ApiResponse(data=get_dag_view(db, group_id=int(group_id)))


@router.get("/groups/{group_id}/nodes", response_model=ApiResponse[list[GroupTaskNodeOut]])
def list_group_task_nodes_api(group_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    _assert_group_user_member(db, group_id=int(group_id), user_id=int(user.id))
    rows = list_nodes(db, group_id=int(group_id))
    return ApiResponse(data=[GroupTaskNodeOut.model_validate(r) for r in rows])


@router.post("/groups/{group_id}/nodes", response_model=ApiResponse[list[GroupTaskNodeOut]])
def create_group_task_nodes_api(
    group_id: int,
    payload: GroupTaskNodeCreateRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    member = _assert_group_user_member(db, group_id=int(group_id), user_id=int(user.id))
    rows = create_nodes(db, group_id=int(group_id), creator_member_id=int(member.id), nodes=[n.model_dump() for n in payload.nodes])
    return ApiResponse(data=[GroupTaskNodeOut.model_validate(r) for r in rows])


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
    node = claim_node(db, node_id=int(node_id), member_id=int(payload.member_id))
    return ApiResponse(data=GroupTaskNodeOut.model_validate(node))


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
    _assert_group_user_member(db, group_id=int(node.group_id), user_id=int(user.id))
    row = complete_node(db, node_id=int(node_id), member_id=int(payload.member_id), output_summary=payload.output_summary)
    return ApiResponse(data=GroupTaskNodeOut.model_validate(row))


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
    node = assign_node_to_agent(db, node_id=int(node_id), member_id=int(payload.member_id))
    return ApiResponse(data=GroupTaskNodeOut.model_validate(node))


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
    result = await tool(node_id=int(node_id), member_id=int(payload.member_id))
    if not result.ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.error or "node_execute_failed")
    row = get_node(db, node_id=int(node_id))
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Node not found after execution")
    return ApiResponse(data=GroupTaskNodeOut.model_validate(row))
