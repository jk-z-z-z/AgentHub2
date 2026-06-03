from __future__ import annotations

from typing import Any

from agentscope.tool import ToolBase, ToolChunk
from sqlalchemy.orm import Session

from app.event_runtime.context import EventDispatchRequest
from app.event_runtime.dispatcher import dispatch_message_event_chain
from app.event_runtime.facade import create_message_event
from app.event_runtime.context import get_or_create_manager_member
from app.event_runtime.types import MessageEventStatus, MessageEventType
from app.manager_runtime.tool.base import build_error_chunk, build_tool_chunk
from app.models.member import Member
from app.models.message import Message
from app.services.group_task_service import get_node


def _build_request_payload(*, group_id: int, node_id: int, member_id: int) -> dict[str, Any]:
    return {
        "group_id": int(group_id),
        "node_id": int(node_id),
        "member_id": int(member_id),
    }


def _resolve_node_and_member(db: Session, *, node_id: int, member_id: int) -> tuple[Any | None, Any | None]:
    node = get_node(db, node_id=int(node_id))
    if not node:
        return None, None
    member = db.query(Member).filter(Member.id == int(member_id)).first()
    if not member or not member.agent_instance_id:
        return node, None
    return node, member


class NodeExecuteTool(ToolBase):
    is_mcp = False
    is_external_tool = False
    is_state_injected = False
    is_concurrency_safe = True

    def __init__(self, *, db: Session) -> None:
        self._db = db
        self._trace = None
        self.name = "manager.node_execute"
        self.description = "Emit a node execution request event and dispatch the assigned agent."
        self.input_schema = {
            "type": "object",
            "properties": {
                "node_id": {"type": "integer"},
                "member_id": {"type": "integer"},
            },
            "required": ["node_id", "member_id"],
            "additionalProperties": True,
        }

    def set_trace(self, trace: Any | None) -> None:
        self._trace = trace

    async def check_permissions(self, _tool_input: dict, _context: object) -> object:
        return object()

    async def __call__(self, **kwargs) -> ToolChunk:
        node_id = kwargs.get("node_id")
        member_id = kwargs.get("member_id")
        if node_id in (None, "") or member_id in (None, ""):
            return build_error_chunk("node_id_and_member_id_required")
        node, member = _resolve_node_and_member(self._db, node_id=int(node_id), member_id=int(member_id))
        if not node:
            return build_error_chunk("node_not_found")
        if not member:
            return build_error_chunk("agent_member_not_found")

        trace_message_id = int(getattr(self._trace, "message_id", 0) or 0) or None
        if trace_message_id is not None:
            event = create_message_event(
                self._db,
                message_id=int(trace_message_id),
                event_type=MessageEventType.Task.NODE_EXEC_STARTED,
                payload=_build_request_payload(group_id=int(node.group_id), node_id=int(node.id), member_id=int(member.id)),
                status=MessageEventStatus.PENDING,
            )
            await dispatch_message_event_chain(
                EventDispatchRequest(
                    db=self._db,
                    group_id=int(node.group_id),
                    sender_member_id=int(member.id),
                    message_id=int(trace_message_id),
                    message_type="ai",
                    content=str(node.title or ""),
                    meta_json="{}",
                    event_id=int(event.id),
                )
            )
            completed = get_node(self._db, node_id=int(node.id))
            return build_tool_chunk(
                {
                    "ok": True,
                    "result": {
                        "node_id": int(completed.id) if completed else int(node.id),
                        "node_key": str(completed.node_key) if completed else str(node.node_key),
                        "status": str(completed.status) if completed else "queued",
                        "output_summary": str(completed.output_summary or "") if completed else "",
                    },
                    "error": None,
                }
            )

        system_member = get_or_create_manager_member(self._db, group_id=int(node.group_id))
        control_message = Message(
            group_id=int(node.group_id),
            sender_member_id=int(system_member.id),
            message_type="system",
            content=f"node.execute:{node.node_key}",
            metadata_json="{}",
        )
        self._db.add(control_message)
        self._db.commit()
        self._db.refresh(control_message)
        event = create_message_event(
            self._db,
            message_id=int(control_message.id),
            event_type=MessageEventType.Task.NODE_EXEC_STARTED,
            payload=_build_request_payload(group_id=int(node.group_id), node_id=int(node.id), member_id=int(member.id)),
            status=MessageEventStatus.PENDING,
        )
        await dispatch_message_event_chain(
            EventDispatchRequest(
                db=self._db,
                group_id=int(node.group_id),
                sender_member_id=int(system_member.id),
                message_id=int(control_message.id),
                message_type="system",
                content=str(control_message.content or ""),
                meta_json=str(control_message.metadata_json or "{}"),
                event_id=int(event.id),
            )
        )
        completed = get_node(self._db, node_id=int(node.id))
        return build_tool_chunk(
            {
                "ok": True,
                "result": {
                    "node_id": int(completed.id) if completed else int(node.id),
                    "node_key": str(completed.node_key) if completed else str(node.node_key),
                    "status": str(completed.status) if completed else "queued",
                    "output_summary": str(completed.output_summary or "") if completed else "",
                    "message_id": int(control_message.id),
                    "event_id": int(event.id),
                },
                "error": None,
            }
        )
