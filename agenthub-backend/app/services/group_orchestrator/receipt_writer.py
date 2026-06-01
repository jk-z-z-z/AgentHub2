from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.common.event_types import GroupTaskEventType
from app.models.group_task_node import GroupTaskNode
from app.models.group_task_run import GroupTaskRun
from app.models.member import Member
from app.services.group_orchestrator.node_protocol import format_receipt_message, parse_node_result
from app.services.group_task.event_service import log_group_task_event
from app.services.message_writer_service import create_message


async def post_node_receipt_message(
    db: Session,
    *,
    run: GroupTaskRun,
    node: GroupTaskNode,
    assignee_member: Member,
    reply_to_message_id: int | None,
) -> int:
    """
    Post one compact receipt message (human + machine block), and store message id on node.
    """
    nr = parse_node_result(node.output_summary or "")
    human = f"【节点回执】{node.node_key}：{node.title}\n状态：{nr.status}\n摘要：{(nr.summary or '').strip()[:200]}"
    payload = {
        "run_id": int(run.id),
        "group_id": int(run.group_id),
        "node_id": int(node.id),
        "node_key": node.node_key,
        "status": nr.status,
        "deliverables": nr.deliverables,
        "evidence": nr.evidence,
        "confidence": nr.confidence,
        "issues": nr.issues,
        "suggested_ops": nr.suggested_ops,
        "receipt_message_id": None,
    }
    content = format_receipt_message(human_text=human, payload=payload)
    meta = json.dumps({"reply_to_message_id": reply_to_message_id, "trigger": "node_receipt"}, ensure_ascii=False)
    msg = await create_message(
        db,
        group_id=int(run.group_id),
        sender_member_id=int(assignee_member.id),
        message_type="ai",
        content=content,
        meta_json=meta,
    )
    node.receipt_message_id = int(msg.id)
    db.add(node)
    db.commit()
    log_group_task_event(
        db,
        run=run,
        run_id=int(run.id),
        node_id=int(node.id),
        event_type=GroupTaskEventType.NODE_RECEIPT_POSTED,
        payload={"message_id": int(msg.id)},
    )
    return int(msg.id)

