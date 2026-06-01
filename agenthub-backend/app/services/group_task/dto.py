from __future__ import annotations

import json

from app.models.group_task_node import GroupTaskNode
from app.schemas.group_tasks import GroupTaskNodeOut


def to_group_task_node_out(row: GroupTaskNode) -> GroupTaskNodeOut:
    return GroupTaskNodeOut(
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
        attempt=int(getattr(row, "attempt", 0) or 0),
        input_json=str(getattr(row, "input_json", "{}") or "{}"),
        result_json=str(getattr(row, "result_json", "{}") or "{}"),
        error=str(getattr(row, "error", "") or ""),
        receipt_message_id=str(getattr(row, "receipt_message_id", "")) if getattr(row, "receipt_message_id", None) is not None else None,
        agent_run_id=str(getattr(row, "agent_run_id", "")) if getattr(row, "agent_run_id", None) is not None else None,
        output_summary=row.output_summary,
        manager_review_status=row.manager_review_status,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )
