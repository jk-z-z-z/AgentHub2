from __future__ import annotations

import asyncio
import json

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401
from app.core.config import settings
from app.db.base import Base
from app.event_runtime.context import EventDispatchRequest
from app.event_runtime.facade import create_message_event
from app.event_runtime.handlers.task import (
    _build_agent_execution_reply_text,
    _derive_manager_review_status,
    handle_task_completed,
    handle_node_exec_started,
)
from app.event_runtime.types import MessageEventType
from app.manager_runtime.schemas import ManagerInvokeResult
from app.manager_runtime.tool.base import extract_tool_result
from app.manager_runtime.tool.builtins.dag_apply import DagApplyTool
from app.manager_runtime.tool.builtins.dag_patch import DagPatchTool
from app.manager_runtime.tool.builtins.dag_view import DagViewTool
from app.manager_runtime.assistant.state_store import (
    load_pending_clarify,
    load_pending_plan,
    save_pending_clarify,
    save_pending_plan,
)
from app.models.group import Group
from app.models.message_event import MessageEvent
from app.models.group_task_node import GroupTaskNode
from app.models.member import Member
from app.models.message import Message
from app.services.group_task_service import (
    claim_node,
    complete_node,
    create_run,
    get_dag_view,
    list_nodes,
    list_run_events,
    replace_run_nodes,
    review_node,
)


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)()


def _seed_group(db: Session) -> tuple[Group, Member, Message]:
    group = Group(creator_user_id=1, name="project", description="", type="project")
    db.add(group)
    db.flush()
    member = Member(
        group_id=int(group.id),
        kind="user",
        display_name="User",
        user_ref="1",
        agent_instance_id=None,
        title="owner",
    )
    db.add(member)
    db.flush()
    message = Message(
        group_id=int(group.id),
        sender_member_id=int(member.id),
        message_type="text",
        content="start",
        metadata_json="{}",
    )
    db.add(message)
    db.commit()
    db.refresh(group)
    db.refresh(member)
    db.refresh(message)
    return group, member, message


def test_same_group_allows_multiple_runs_with_isolated_nodes_and_events() -> None:
    db = _session()
    group, member, message = _seed_group(db)

    run_a = create_run(
        db,
        group_id=int(group.id),
        creator_member_id=int(member.id),
        title="Run A",
        goal_text="A goal",
        nodes=[{"node_key": "n1", "title": "A1", "detail": "", "deps": []}],
        trigger_message_id=int(message.id),
    )
    run_b = create_run(
        db,
        group_id=int(group.id),
        creator_member_id=int(member.id),
        title="Run B",
        goal_text="B goal",
        nodes=[{"node_key": "n1", "title": "B1", "detail": "", "deps": []}],
        trigger_message_id=int(message.id),
    )

    assert int(run_a.id) != int(run_b.id)
    assert [node.node_key for node in list_nodes(db, run_id=int(run_a.id))] == ["n1"]
    assert [node.node_key for node in list_nodes(db, run_id=int(run_b.id))] == ["n1"]

    replace_run_nodes(
        db,
        run_id=int(run_a.id),
        nodes=[
            {"node_key": "n1", "title": "A1 updated", "detail": "", "deps": []},
            {"node_key": "n2", "title": "A2", "detail": "", "deps": ["n1"]},
        ],
    )

    graph_a = get_dag_view(db, run_id=int(run_a.id))
    graph_b = get_dag_view(db, run_id=int(run_b.id))
    assert [node["node_key"] for node in graph_a["nodes"]] == ["n1", "n2"]
    assert graph_a["edges"] == [{"from": "n1", "to": "n2"}]
    assert [node["title"] for node in graph_b["nodes"]] == ["B1"]

    node_a = list_nodes(db, run_id=int(run_a.id))[0]
    claim_node(db, node_id=int(node_a.id), member_id=int(member.id))
    complete_node(db, node_id=int(node_a.id), member_id=int(member.id), output_summary="done")
    reviewed = review_node(
        db,
        node_id=int(node_a.id),
        reviewer_member_id=int(member.id),
        manager_review_status="approved",
    )
    assert int(reviewed.run_id) == int(run_a.id)
    assert list_nodes(db, run_id=int(run_b.id))[0].status == "pending"

    create_message_event(
        db,
        message_id=int(message.id),
        event_type=MessageEventType.Task.TASK_COMPLETED,
        payload={"run_id": int(run_a.id), "node_id": int(node_a.id)},
    )
    create_message_event(
        db,
        message_id=int(message.id),
        event_type=MessageEventType.Task.TASK_COMPLETED,
        payload={"run_id": int(run_b.id), "node_id": int(list_nodes(db, run_id=int(run_b.id))[0].id)},
    )

    events_a = list_run_events(db, run_id=int(run_a.id))
    events_b = list_run_events(db, run_id=int(run_b.id))
    assert len(events_a) == 1
    assert len(events_b) == 1
    assert int(events_a[0].run_id) == int(run_a.id)
    assert int(events_b[0].run_id) == int(run_b.id)


def test_pending_state_isolated_by_trigger_message_and_bound_to_run(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "data_root", str(tmp_path))
    db = _session()
    group, member, message_a = _seed_group(db)
    message_b = Message(
        group_id=int(group.id),
        sender_member_id=int(member.id),
        message_type="text",
        content="start another task",
        metadata_json="{}",
    )
    db.add(message_b)
    db.commit()
    db.refresh(message_b)

    save_pending_plan(
        group_id=int(group.id),
        creator_member_id=int(member.id),
        trigger_message_id=int(message_a.id),
        plan={"title": "plan-a"},
    )
    save_pending_plan(
        group_id=int(group.id),
        creator_member_id=int(member.id),
        trigger_message_id=int(message_b.id),
        plan={"title": "plan-b"},
    )
    save_pending_clarify(
        group_id=int(group.id),
        creator_member_id=int(member.id),
        trigger_message_id=int(message_a.id),
        goal_text="goal-a",
        questions=["q-a"],
    )
    save_pending_clarify(
        group_id=int(group.id),
        creator_member_id=int(member.id),
        trigger_message_id=int(message_b.id),
        goal_text="goal-b",
        questions=["q-b"],
    )

    run_a = create_run(
        db,
        group_id=int(group.id),
        creator_member_id=int(member.id),
        title="Run A",
        goal_text="A goal",
        nodes=[{"node_key": "n1", "title": "A1", "detail": "", "deps": []}],
        trigger_message_id=int(message_a.id),
    )
    run_b = create_run(
        db,
        group_id=int(group.id),
        creator_member_id=int(member.id),
        title="Run B",
        goal_text="B goal",
        nodes=[{"node_key": "n1", "title": "B1", "detail": "", "deps": []}],
        trigger_message_id=int(message_b.id),
    )

    pending_plan_a = load_pending_plan(group_id=int(group.id), trigger_message_id=int(message_a.id))
    pending_plan_b = load_pending_plan(group_id=int(group.id), trigger_message_id=int(message_b.id))
    pending_clarify_a = load_pending_clarify(group_id=int(group.id), trigger_message_id=int(message_a.id))
    pending_clarify_b = load_pending_clarify(group_id=int(group.id), trigger_message_id=int(message_b.id))

    assert pending_plan_a and pending_plan_a["plan"]["title"] == "plan-a"
    assert pending_plan_b and pending_plan_b["plan"]["title"] == "plan-b"
    assert pending_plan_a["run_id"] == int(run_a.id)
    assert pending_plan_b["run_id"] == int(run_b.id)
    assert pending_clarify_a and pending_clarify_a["goal_text"] == "goal-a"
    assert pending_clarify_b and pending_clarify_b["goal_text"] == "goal-b"
    assert pending_clarify_a["run_id"] == int(run_a.id)
    assert pending_clarify_b["run_id"] == int(run_b.id)


def test_dag_apply_can_create_run_from_manager_runtime_context() -> None:
    db = _session()
    group, member, message = _seed_group(db)
    tool = DagApplyTool(db=db)
    tool.set_runtime_context(
        {
            "group_id": int(group.id),
            "sender_id": int(member.id),
            "user_message_id": int(message.id),
            "input_text": "创建一个任务流程图，覆盖用户登录全链路",
        }
    )

    chunk = asyncio.run(
        tool(
            graph={
                "nodes": [
                    {"node_key": "n1", "title": "梳理登录入口与前置条件", "detail": "", "deps": []},
                    {"node_key": "n2", "title": "设计认证与会话校验流程", "detail": "", "deps": ["n1"]},
                ]
            }
        )
    )
    payload = extract_tool_result(chunk)

    assert payload["ok"] is True
    assert payload["result"]["action"] == "created"
    run_id = int(payload["result"]["run_id"])
    graph = get_dag_view(db, run_id=run_id)
    assert [node["node_key"] for node in graph["nodes"]] == ["n1", "n2"]
    assert graph["edges"] == [{"from": "n1", "to": "n2"}]


def test_dag_apply_accepts_stringified_graph_payload() -> None:
    db = _session()
    group, member, message = _seed_group(db)
    tool = DagApplyTool(db=db)
    tool.set_runtime_context(
        {
            "group_id": int(group.id),
            "sender_id": int(member.id),
            "user_message_id": int(message.id),
        }
    )

    chunk = asyncio.run(
        tool(
            graph=json.dumps(
                {
                    "title": "登录流程图",
                    "goal": "覆盖登录主链路",
                    "nodes": [
                        {"node_key": "n1", "title": "确认入口", "detail": "", "deps": []},
                        {"node_key": "n2", "title": "确认校验", "detail": "", "deps": ["n1"]},
                    ],
                },
                ensure_ascii=False,
            )
        )
    )
    payload = extract_tool_result(chunk)

    assert payload["ok"] is True
    assert payload["result"]["action"] == "created"


def test_dag_apply_rejects_non_object_node_items_with_clear_error() -> None:
    db = _session()
    group, member, message = _seed_group(db)
    tool = DagApplyTool(db=db)
    tool.set_runtime_context(
        {
            "group_id": int(group.id),
            "sender_id": int(member.id),
            "user_message_id": int(message.id),
        }
    )

    chunk = asyncio.run(tool(graph={"nodes": ["not-a-node-object"]}))
    payload = extract_tool_result(chunk)

    assert payload["ok"] is False
    assert payload["error"] == "graph_nodes_must_be_array_of_objects"


def test_dag_view_without_run_id_returns_available_runs_instead_of_failing() -> None:
    db = _session()
    group, member, message = _seed_group(db)
    run = create_run(
        db,
        group_id=int(group.id),
        creator_member_id=int(member.id),
        title="Run A",
        goal_text="A goal",
        nodes=[{"node_key": "n1", "title": "A1", "detail": "", "deps": []}],
        trigger_message_id=int(message.id),
    )
    tool = DagViewTool(db=db)
    tool.set_runtime_context({"group_id": int(group.id)})

    chunk = asyncio.run(tool())
    payload = extract_tool_result(chunk)

    assert payload["ok"] is True
    assert payload["result"]["resolved_run_id"] is None
    assert payload["result"]["nodes"] == []
    assert payload["result"]["available_runs"][0]["run_id"] == int(run.id)


def test_dag_patch_uses_runtime_bound_run_id() -> None:
    db = _session()
    group, member, message = _seed_group(db)
    run = create_run(
        db,
        group_id=int(group.id),
        creator_member_id=int(member.id),
        title="Run A",
        goal_text="A goal",
        nodes=[{"node_key": "n1", "title": "A1", "detail": "", "deps": []}],
        trigger_message_id=int(message.id),
    )
    tool = DagPatchTool(db=db)
    tool.set_runtime_context({"run_id": int(run.id), "group_id": int(group.id)})

    chunk = asyncio.run(
        tool(
            ops=[
                {
                    "op": "add_node",
                    "node": {"node_key": "n2", "title": "A2", "detail": "", "deps": ["n1"]},
                }
            ]
        )
    )
    payload = extract_tool_result(chunk)

    assert payload["ok"] is True
    assert payload["result"]["run_id"] == int(run.id)
    graph = get_dag_view(db, run_id=int(run.id))
    assert graph["edges"] == [{"from": "n1", "to": "n2"}]


def test_agent_execution_reply_text_prefers_summary_over_raw_json() -> None:
    text = _build_agent_execution_reply_text(
        {
            "output_summary": "",
            "result_payload": {
                "summary": "",
                "parsed_result": {
                    "summary": "已完成登录页修复，并补充了会话校验。",
                },
                "agent_output": '{"summary":"raw-json"}',
            },
        }
    )

    assert text == "已完成登录页修复，并补充了会话校验。"


def test_handle_node_exec_started_writes_task_event_before_final_message(monkeypatch) -> None:
    db = _session()
    group, user_member, user_message = _seed_group(db)
    agent_member = Member(
        group_id=int(group.id),
        kind="agent",
        display_name="Worker",
        user_ref=None,
        agent_instance_id=1,
        title="executor",
    )
    db.add(agent_member)
    db.commit()
    db.refresh(agent_member)

    run = create_run(
        db,
        group_id=int(group.id),
        creator_member_id=int(user_member.id),
        title="Run A",
        goal_text="A goal",
        nodes=[{"node_key": "n1", "title": "A1", "detail": "", "deps": []}],
        trigger_message_id=int(user_message.id),
    )
    node = db.query(GroupTaskNode).filter(GroupTaskNode.run_id == int(run.id)).first()
    assert node is not None

    event = create_message_event(
        db,
        message_id=int(user_message.id),
        event_type=MessageEventType.Task.NODE_EXEC_STARTED,
        payload={
            "group_id": int(group.id),
            "run_id": int(run.id),
            "node_id": int(node.id),
            "member_id": int(agent_member.id),
        },
    )

    async def fake_execute_node_task(*_args, **_kwargs):
        return {
            "node_id": int(node.id),
            "run_id": int(run.id),
            "node_key": str(node.node_key),
            "status": "completed",
            "output_summary": "节点已完成总结",
            "error": "",
            "result_payload": {
                "summary": "节点已完成总结",
                "parsed_result": {"summary": "节点已完成总结"},
            },
        }

    async def fake_emit_ai_reply(
        _db,
        *,
        group_id,
        user_message_id,
        sender_member_id,
        content,
        trigger,
        ai_message_id=None,
        status="done",
        extra_metadata=None,
        auto_dispatch_on_done=True,
    ):
        assert group_id == int(group.id)
        assert user_message_id == int(user_message.id)
        assert sender_member_id == int(agent_member.id)
        assert content == "节点已完成总结"
        assert trigger == f"node_execute:{int(node.id)}"
        assert status == "done"
        assert auto_dispatch_on_done is True
        events = db.query(MessageEvent).filter(MessageEvent.message_id == int(ai_message_id)).all()
        assert any(str(item.event_type) == MessageEventType.Task.TASK_COMPLETED for item in events)
        return db.query(Message).filter(Message.id == int(ai_message_id)).first()

    monkeypatch.setattr("app.event_runtime.handlers.task.execute_node_task", fake_execute_node_task)
    monkeypatch.setattr("app.event_runtime.handlers.task.emit_ai_reply", fake_emit_ai_reply)

    asyncio.run(
        handle_node_exec_started(
            EventDispatchRequest(
                db=db,
                group_id=int(group.id),
                sender_member_id=int(user_member.id),
                message_id=int(user_message.id),
                message_type="text",
                content=str(user_message.content or ""),
                meta_json=str(user_message.metadata_json or "{}"),
                event_id=int(event.id),
            ),
            event,
        )
    )


def test_manager_review_status_derivation_falls_back_from_node_status() -> None:
    db = _session()
    group, member, message = _seed_group(db)
    run = create_run(
        db,
        group_id=int(group.id),
        creator_member_id=int(member.id),
        title="Run A",
        goal_text="A goal",
        nodes=[{"node_key": "n1", "title": "A1", "detail": "", "deps": []}],
        trigger_message_id=int(message.id),
    )
    node = db.query(GroupTaskNode).filter(GroupTaskNode.run_id == int(run.id)).first()
    assert node is not None

    node.status = "completed"
    db.add(node)
    db.commit()
    db.refresh(node)
    assert _derive_manager_review_status(node=node, payload={}) == "approved"

    node.status = "failed"
    db.add(node)
    db.commit()
    db.refresh(node)
    assert _derive_manager_review_status(node=node, payload={}) == "rework"


def test_task_completed_routes_into_manager_message_flow(monkeypatch) -> None:
    db = _session()
    group, user_member, child_message = _seed_group(db)
    run = create_run(
        db,
        group_id=int(group.id),
        creator_member_id=int(user_member.id),
        title="Run A",
        goal_text="A goal",
        nodes=[{"node_key": "n1", "title": "A1", "detail": "", "deps": []}],
        trigger_message_id=int(child_message.id),
    )
    node = db.query(GroupTaskNode).filter(GroupTaskNode.run_id == int(run.id)).first()
    assert node is not None

    event = create_message_event(
        db,
        message_id=int(child_message.id),
        event_type=MessageEventType.Task.TASK_COMPLETED,
        payload={
            "node_id": int(node.id),
            "run_id": int(run.id),
            "node_key": str(node.node_key),
            "member_id": int(user_member.id),
            "status": "completed",
            "output_summary": "子 agent 已完成总结",
            "error": "",
        },
    )

    seen: dict[str, object] = {}

    async def fake_invoke_manager(*_args, **kwargs):
        seen["extra_context"] = dict(kwargs["extra_context"])
        return ManagerInvokeResult(
            text="管家已复核，通过。",
            action="assistant",
            engine_type="agentscope_react",
            plan={},
            meta={"manager_review_status": "approved"},
            system_prompt_used="",
        )

    async def fake_emit_ai_reply(
        _db,
        *,
        group_id,
        user_message_id,
        sender_member_id,
        content,
        trigger,
        ai_message_id=None,
        status="done",
        extra_metadata=None,
        auto_dispatch_on_done=True,
    ):
        seen["reply"] = {
            "group_id": group_id,
            "user_message_id": user_message_id,
            "sender_member_id": sender_member_id,
            "content": content,
            "trigger": trigger,
            "ai_message_id": ai_message_id,
            "status": status,
            "extra_metadata": extra_metadata,
            "auto_dispatch_on_done": auto_dispatch_on_done,
        }
        return db.query(Message).filter(Message.id == int(ai_message_id)).first()

    monkeypatch.setattr("app.manager_runtime.invoke_manager", fake_invoke_manager)
    monkeypatch.setattr("app.event_runtime.handlers.task.emit_ai_reply", fake_emit_ai_reply)

    asyncio.run(
        handle_task_completed(
            EventDispatchRequest(
                db=db,
                group_id=int(group.id),
                sender_member_id=int(user_member.id),
                message_id=int(child_message.id),
                message_type="ai",
                content=str(child_message.content or ""),
                meta_json=str(child_message.metadata_json or "{}"),
                event_id=int(event.id),
            ),
            event,
        )
    )

    extra_context = seen["extra_context"]
    assert isinstance(extra_context, dict)
    assert int(extra_context["source_message_id"]) == int(child_message.id)
    reply = seen["reply"]
    assert isinstance(reply, dict)
    assert reply["trigger"] == "manager_runtime"
    assert reply["content"] == "管家已复核，通过。"
    assert reply["auto_dispatch_on_done"] is True
