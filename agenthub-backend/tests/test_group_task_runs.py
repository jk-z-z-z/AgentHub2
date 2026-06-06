from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401
from app.core.config import settings
from app.db.base import Base
from app.event_runtime.facade import create_message_event
from app.event_runtime.types import MessageEventType
from app.manager_runtime.assistant.state_store import (
    load_pending_clarify,
    load_pending_plan,
    save_pending_clarify,
    save_pending_plan,
)
from app.models.group import Group
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
