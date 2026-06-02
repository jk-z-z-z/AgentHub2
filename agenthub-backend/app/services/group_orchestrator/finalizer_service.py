from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.services._zero_deps_ai_helpers import simple_internal_llm_chat as internal_llm_chat
from app.common.event_types import GroupTaskEventType
from app.models.group_task_run import GroupTaskRun
from app.services.group_task.event_service import log_group_task_event
from app.services.group_task.node_service import list_group_task_nodes
from app.services.group_task.manager_service import get_or_create_manager_member
from app.agent_runtime.message_store import create_message


def _can_finalize(run: GroupTaskRun, nodes: list) -> bool:
    if not run or not nodes:
        return False
    if getattr(run, "final_message_id", None):
        return False
    # "可收口"：所有节点 completed 且 manager_review_status=approved
    for n in nodes:
        if str(getattr(n, "status", "")) != "completed":
            return False
        if str(getattr(n, "manager_review_status", "")) != "approved":
            return False
    return True


def _extract_node_receipt_summary(nodes: list) -> list[dict]:
    out: list[dict] = []
    for n in nodes:
        try:
            obj = json.loads(str(getattr(n, "result_json", "") or "{}"))
            if isinstance(obj, dict) and obj:
                out.append(
                    {
                        "node_key": str(getattr(n, "node_key", "")),
                        "title": str(getattr(n, "title", "")),
                        "summary": str(obj.get("summary") or "")[:400],
                        "deliverables": obj.get("deliverables") if isinstance(obj.get("deliverables"), list) else [],
                        "confidence": obj.get("confidence"),
                    }
                )
                continue
        except Exception:
            pass
        out.append(
            {
                "node_key": str(getattr(n, "node_key", "")),
                "title": str(getattr(n, "title", "")),
                "summary": str(getattr(n, "output_summary", "") or "")[:400],
                "deliverables": [],
                "confidence": None,
            }
        )
    return out


async def maybe_finalize_run(db: Session, *, run_id: int) -> int | None:
    """
    If a run is in a "closable" state, have manager generate ONE final summary message,
    post it in group as manager member, and store message_id to run.final_message_id.
    """
    run = db.query(GroupTaskRun).filter(GroupTaskRun.id == int(run_id)).first()
    if not run:
        return None
    nodes = list_group_task_nodes(db, run_id=int(run.id))
    if not _can_finalize(run, nodes):
        return None

    manager_member = get_or_create_manager_member(db, group_id=int(run.group_id))
    receipts = _extract_node_receipt_summary(nodes)

    prompt = (
        "你是群聊项目的管家Agent，请基于节点产出汇总最终结论。\n"
        "要求：\n"
        "1) 只输出一条简洁总结（不刷屏），结构清晰。\n"
        "2) 包含：目标、已完成节点概览、关键产物/结论、不确定项(若无则写无)。\n"
        "3) 不要重复长文本，不要贴大段代码。\n\n"
        f"项目目标：{run.goal_text}\n\n"
        f"节点回执摘要(JSON)：{json.dumps(receipts, ensure_ascii=False)}\n"
    )

    try:
        text = await internal_llm_chat(prompt, system_prompt="你是严谨的项目管家，总结要短且可执行。")
    except Exception:
        text = ""
    final_text = (text or "").strip() or f"【最终总结】已完成全部节点：{', '.join([str(n.node_key) for n in nodes])}"

    msg = await create_message(
        db,
        int(run.group_id),
        int(manager_member.id),
        "ai",
        final_text,
        '{"trigger":"manager_final_summary"}',
    )
    run.final_message_id = int(msg.id)
    run.status = "completed"
    db.add(run)
    db.commit()
    db.refresh(run)

    log_group_task_event(
        db,
        run_id=int(run.id),
        node_id=None,
        event_type=GroupTaskEventType.RUN_FINALIZED,
        payload={"final_message_id": int(msg.id)},
    )
    return int(msg.id)
