from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.member import Member
from app.services.group_task.manager_service import get_or_create_manager_member
from app.services.group_task.node_service import auto_review_completed_node, complete_task_node, get_group_task_run
from app.services.message_writer_service import create_message
from app.services.group_orchestrator.finalizer_service import maybe_finalize_run
from app.services.group_orchestrator.replanner_service import maybe_replan_unstarted_nodes


async def complete_node_with_auto_review(
    db: Session,
    *,
    node_id: int,
    user_id: int,
    output_summary: str,
):
    member = db.query(Member).filter(Member.kind == "user", Member.user_ref == str(user_id)).first()
    if not member:
        return None, "No user member"

    node = complete_task_node(
        db,
        node_id=int(node_id),
        member_id=int(member.id),
        output_summary=output_summary,
    )
    pre_review_status = str(node.manager_review_status)
    try:
        reviewed = await auto_review_completed_node(db, node_id=int(node.id))
        if reviewed is not None:
            node = reviewed
    except Exception:
        pass

    try:
        if pre_review_status == "pending" and node.manager_review_status in {"approved", "rework"}:
            run = get_group_task_run(db, run_id=int(node.run_id))
            if run:
                manager_member = get_or_create_manager_member(db, group_id=int(run.group_id))
                verdict_text = "通过" if node.manager_review_status == "approved" else "需返工"
                content = (
                    f"【管家复核】节点「{node.title}」复核结果：{verdict_text}\n"
                    f"节点Key：{node.node_key}\n"
                    f"说明：{(node.output_summary or '').strip()[:300]}"
                )
                await create_message(
                    db,
                    int(run.group_id),
                    int(manager_member.id),
                    "ai",
                    content,
                    '{"trigger":"manager_auto_review"}',
                )
    except Exception:
        pass

    # If completion/review indicates problems or suggested ops, trigger one replan for unstarted nodes.
    try:
        run = get_group_task_run(db, run_id=int(node.run_id))
        if run:
            await maybe_replan_unstarted_nodes(
                db,
                run_id=int(run.id),
                trigger="node.completed",
                reason=f"node_key={node.node_key} review={node.manager_review_status}",
            )
    except Exception:
        pass

    # If the run becomes closable after this completion/review, finalize with ONE manager summary message.
    try:
        run = get_group_task_run(db, run_id=int(node.run_id))
        if run:
            await maybe_finalize_run(db, run_id=int(run.id))
    except Exception:
        pass
    return node, None
