from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path

from fastapi.testclient import TestClient

from app.agent_runtime.tool._executor import execute_builtin_tool
from app.db.session import SessionLocal
from app.event_runtime.context import get_or_create_manager_member
from app.main import app
from app.manager_runtime.assistant.state_store import save_pending_plan
from app.manager_runtime.schemas import ManagerInvokeResult
from app.models.agent_instance import AgentInstance
from app.models.group_task_node import GroupTaskNode
from app.models.member import Member
from app.models.message import Message
from app.services.preview_runtime_service import DockerPreviewRunner
from app.services.group_task_service import create_run
from app.services.project_code_service import get_project_code_root
from app.services.project_delivery_service import _build_delivery_system_prompt


def _auth_headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "admin123456"},
    )
    assert response.status_code == 200
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _create_project_group(client: TestClient, headers: dict[str, str]) -> tuple[int, int]:
    response = client.post(
        "/api/v1/groups",
        headers=headers,
        json={
            "name": "preview-project",
            "description": "preview conversation test",
            "type": "project",
            "users": [],
            "agents": [],
        },
    )
    assert response.status_code == 200
    data = response.json()["data"]
    return int(data["id"]), int(data["workspace_id"])


def _user_member_id(group_id: int) -> int:
    db = SessionLocal()
    try:
        row = db.query(Member).filter(Member.group_id == int(group_id), Member.kind == "user").first()
        assert row is not None
        return int(row.id)
    finally:
        db.close()


def _manager_member_id(group_id: int) -> int:
    db = SessionLocal()
    try:
        row = get_or_create_manager_member(db, group_id=int(group_id))
        return int(row.id)
    finally:
        db.close()


def _enable_manager(client: TestClient, headers: dict[str, str], group_id: int) -> None:
    response = client.put(
        f"/api/v1/group-tasks/groups/{group_id}/assistant",
        headers=headers,
        json={"enabled": 1},
    )
    assert response.status_code == 200


def _wait_for_manager_reply(group_id: int, *, timeout_seconds: float = 2.0) -> Message:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        db = SessionLocal()
        try:
            row = (
                db.query(Message)
                .filter(Message.group_id == int(group_id), Message.message_type == "ai")
                .order_by(Message.id.desc())
                .first()
            )
            if row and str(row.content or "").strip():
                return row
        finally:
            db.close()
        time.sleep(0.05)
    raise AssertionError("manager reply not found in time")


def test_project_code_write_api_and_tool() -> None:
    with TestClient(app) as client:
        headers = _auth_headers(client)
        group_id, _workspace_id = _create_project_group(client, headers)

        response = client.put(
            f"/api/v1/project-code/{group_id}/pages/index.html",
            headers=headers,
            json={"content": "<h1>hi</h1>"},
        )
        assert response.status_code == 200
        assert response.json()["data"]["path"] == "pages/index.html"
        assert (get_project_code_root(group_id) / "pages" / "index.html").read_text(encoding="utf-8") == "<h1>hi</h1>"

        overwrite = client.put(
            f"/api/v1/project-code/{group_id}/pages/index.html",
            headers=headers,
            json={"content": "<h1>hello</h1>"},
        )
        assert overwrite.status_code == 200
        assert (get_project_code_root(group_id) / "pages" / "index.html").read_text(encoding="utf-8") == "<h1>hello</h1>"

        invalid = client.put(
            f"/api/v1/project-code/{group_id}/..%2Fescape.txt",
            headers=headers,
            json={"content": "nope"},
        )
        assert invalid.status_code == 400

        payload = execute_builtin_tool(
            agent_id=1,
            tool_code="project_code_write",
            args={"path": "hello.txt", "content": "tool write"},
            runtime_context={"group_type": "project", "group_id": group_id},
        )
        assert payload["path"] == "hello.txt"
        assert (get_project_code_root(group_id) / "hello.txt").read_text(encoding="utf-8") == "tool write"


def test_preview_api_reuses_container_and_port(monkeypatch) -> None:
    run_ports: list[int] = []

    def fake_preview_run(self, **kwargs):  # type: ignore[no-untyped-def]
        job = kwargs["job"]
        preview_root = Path(kwargs["preview_root"])
        assert (preview_root / "index.html").exists()
        run_ports.append(int(job.host_port))
        return {
            "logs": [{"step": "docker_run", "exit_code": 0}],
            "container_id": f"preview-{job.host_port}",
            "url": f"http://127.0.0.1:{job.host_port}",
        }

    monkeypatch.setattr(DockerPreviewRunner, "run", fake_preview_run)

    with TestClient(app) as client:
        headers = _auth_headers(client)
        group_id, workspace_id = _create_project_group(client, headers)
        (get_project_code_root(group_id) / "index.html").write_text("<h1>preview</h1>", encoding="utf-8")

        first = client.post("/api/v1/previews", headers=headers, json={"workspace_id": workspace_id})
        assert first.status_code == 200
        first_data = first.json()["data"]
        assert first_data["status"] == "active"
        assert first_data["container_name"] == f"agenthub-preview-{workspace_id}"

        second = client.post("/api/v1/previews", headers=headers, json={"workspace_id": workspace_id})
        assert second.status_code == 200
        second_data = second.json()["data"]
        assert second_data["host_port"] == first_data["host_port"]
        assert run_ports[0] == run_ports[1]


def test_preview_api_supports_dist_and_missing_entry(monkeypatch) -> None:
    def fake_preview_run(self, **kwargs):  # type: ignore[no-untyped-def]
        preview_root = Path(kwargs["preview_root"])
        return {
            "logs": [{"step": "docker_run", "exit_code": 0}],
            "container_id": "preview-ok",
            "url": f"http://127.0.0.1:{kwargs['job'].host_port}",
            "preview_root": preview_root.as_posix(),
        }

    monkeypatch.setattr(DockerPreviewRunner, "run", fake_preview_run)

    with TestClient(app) as client:
        headers = _auth_headers(client)
        group_id, workspace_id = _create_project_group(client, headers)
        root = get_project_code_root(group_id)
        if (root / "index.html").exists():
            (root / "index.html").unlink()
        (root / "dist").mkdir(parents=True, exist_ok=True)
        (root / "dist" / "index.html").write_text("<h1>dist</h1>", encoding="utf-8")

        dist_response = client.post("/api/v1/previews", headers=headers, json={"workspace_id": workspace_id})
        assert dist_response.status_code == 200
        assert dist_response.json()["data"]["preview_root_path"].endswith("/dist")

        (root / "dist" / "index.html").unlink()
        (root / "notes.txt").write_text("missing", encoding="utf-8")
        failed_response = client.post("/api/v1/previews", headers=headers, json={"workspace_id": workspace_id})
        assert failed_response.status_code == 200
        assert failed_response.json()["data"]["status"] == "failed"
        assert "缺少可预览入口文件" in str(failed_response.json()["data"]["error_message"])


def test_manager_complex_feature_request_routes_to_manager_runtime(monkeypatch) -> None:
    captured_contexts: list[dict] = []

    async def fake_invoke_manager(*args, **kwargs):  # type: ignore[no-untyped-def]
        _ = args
        captured_contexts.append(dict(kwargs["extra_context"]))
        return ManagerInvokeResult(
            text="我会先拆解需求并创建任务规划。",
            action="assistant",
            engine_type="agentscope_react",
            plan={},
            meta={"mode": "manager"},
            system_prompt_used="",
        )

    async def fail_feature_delivery(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("manager requests should not route to feature delivery directly")

    monkeypatch.setattr("app.manager_runtime.invoke_manager", fake_invoke_manager)
    monkeypatch.setattr("app.services.project_delivery_service.invoke_agent", fail_feature_delivery)

    with TestClient(app) as client:
        headers = _auth_headers(client)
        group_id, _workspace_id = _create_project_group(client, headers)
        _enable_manager(client, headers, group_id)
        sender_member_id = _user_member_id(group_id)
        manager_member_id = _manager_member_id(group_id)

        response = client.post(
            "/api/v1/messages",
            json={
                "group_id": str(group_id),
                "sender_member_id": str(sender_member_id),
                "message_type": "text",
                "content": "@管家 实现这个登录的流程",
                "metadata_json": json.dumps({"mentions": [{"kind": "agent", "member_id": manager_member_id}]}, ensure_ascii=False),
            },
        )
        assert response.status_code == 200

        reply = _wait_for_manager_reply(group_id)
        metadata = json.loads(str(reply.metadata_json or "{}"))
        assert "delivery_result" not in metadata
        assert "我会先拆解需求并创建任务规划" in str(reply.content)
        assert any(ctx.get("input_text") == "@管家 实现这个登录的流程" for ctx in captured_contexts)


def test_feature_delivery_prompt_for_plan_file_forbids_workspace_run_paths() -> None:
    prompt = _build_delivery_system_prompt(
        input_text="创建一个计划，写入文件中，我需要去完成一个登录流程，登出的流程写入项目，然后给我预览地址，后端使用 go，前端使用 vue",
        wants_deploy=False,
        requested_port=None,
    )

    assert "project_code_write" in prompt
    assert "plan.md" in prompt
    assert "/workspace/run/" in prompt
    assert "不能代替真实代码修改" in prompt


def test_manager_deploy_request_routes_to_manager_runtime_without_bound_run(monkeypatch) -> None:
    captured_contexts: list[dict] = []

    async def fake_invoke_manager(*args, **kwargs):  # type: ignore[no-untyped-def]
        _ = args
        captured_contexts.append(dict(kwargs["extra_context"]))
        return ManagerInvokeResult(
            text="请先创建或选择任务规划，再继续部署。",
            action="assistant",
            engine_type="agentscope_react",
            plan={},
            meta={"mode": "manager"},
            system_prompt_used="",
        )

    async def fail_feature_delivery(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("deploy requests should not route to feature delivery")

    monkeypatch.setattr("app.manager_runtime.invoke_manager", fake_invoke_manager)
    monkeypatch.setattr("app.services.project_delivery_service.invoke_agent", fail_feature_delivery)

    with TestClient(app) as client:
        headers = _auth_headers(client)
        group_id, _workspace_id = _create_project_group(client, headers)
        _enable_manager(client, headers, group_id)
        sender_member_id = _user_member_id(group_id)
        manager_member_id = _manager_member_id(group_id)

        response = client.post(
            "/api/v1/messages",
            json={
                "group_id": str(group_id),
                "sender_member_id": str(sender_member_id),
                "message_type": "text",
                "content": "@管家 实现这个流程，然后部署这个小功能到 5175，让我可以直接看到",
                "metadata_json": json.dumps({"mentions": [{"kind": "agent", "member_id": manager_member_id}]}, ensure_ascii=False),
            },
        )
        assert response.status_code == 200

        reply = _wait_for_manager_reply(group_id)
        metadata = json.loads(str(reply.metadata_json or "{}"))
        assert "delivery_result" not in metadata
        assert "请先创建或选择任务规划" in str(reply.content)
        assert any(ctx.get("input_text") == "@管家 实现这个流程，然后部署这个小功能到 5175，让我可以直接看到" and ctx.get("run_id") is None for ctx in captured_contexts)


def test_manager_task_planning_request_routes_to_manager_runtime(monkeypatch) -> None:
    captured_contexts: list[dict] = []

    async def fake_invoke_manager(*args, **kwargs):  # type: ignore[no-untyped-def]
        _ = args
        captured_contexts.append(dict(kwargs["extra_context"]))
        return ManagerInvokeResult(
            text="我会创建任务规划图。",
            action="assistant",
            engine_type="agentscope_react",
            plan={},
            meta={"mode": "manager"},
            system_prompt_used="",
        )

    async def fail_feature_delivery(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("task planning requests should not route to feature delivery")

    monkeypatch.setattr("app.manager_runtime.invoke_manager", fake_invoke_manager)
    monkeypatch.setattr("app.services.project_delivery_service.invoke_agent", fail_feature_delivery)

    with TestClient(app) as client:
        headers = _auth_headers(client)
        group_id, _workspace_id = _create_project_group(client, headers)
        _enable_manager(client, headers, group_id)
        sender_member_id = _user_member_id(group_id)
        manager_member_id = _manager_member_id(group_id)

        response = client.post(
            "/api/v1/messages",
            json={
                "group_id": str(group_id),
                "sender_member_id": str(sender_member_id),
                "message_type": "text",
                "content": "@管家 创建一个任务规划，我的目标是创建一个极简仿微信 im 聊天室，打通聊天的核心链路，后端使用 golang，前端使用 vue",
                "metadata_json": json.dumps({"mentions": [{"kind": "agent", "member_id": manager_member_id}]}, ensure_ascii=False),
            },
        )
        assert response.status_code == 200

        reply = _wait_for_manager_reply(group_id)
        metadata = json.loads(str(reply.metadata_json or "{}"))
        assert "delivery_result" not in metadata
        assert "我会创建任务规划图" in str(reply.content)
        assert any(
            str(ctx.get("input_text") or "").startswith("@管家 创建一个任务规划") and ctx.get("run_id") is None
            for ctx in captured_contexts
        )


def test_manager_deploy_request_passes_bound_run_id_from_reply_chain(monkeypatch) -> None:
    captured_contexts: list[dict] = []

    async def fake_invoke_manager(*args, **kwargs):  # type: ignore[no-untyped-def]
        _ = args
        captured_contexts.append(dict(kwargs["extra_context"]))
        return ManagerInvokeResult(
            text="开始部署当前任务规划。",
            action="assistant",
            engine_type="agentscope_react",
            plan={},
            meta={"mode": "manager"},
            system_prompt_used="",
        )

    async def fail_feature_delivery(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("deploy requests should not route to feature delivery")

    monkeypatch.setattr("app.manager_runtime.invoke_manager", fake_invoke_manager)
    monkeypatch.setattr("app.services.project_delivery_service.invoke_agent", fail_feature_delivery)

    with TestClient(app) as client:
        headers = _auth_headers(client)
        group_id, _workspace_id = _create_project_group(client, headers)
        _enable_manager(client, headers, group_id)
        sender_member_id = _user_member_id(group_id)
        manager_member_id = _manager_member_id(group_id)

        db = SessionLocal()
        try:
            seed_message = Message(
                group_id=int(group_id),
                sender_member_id=int(sender_member_id),
                message_type="text",
                content="为这个任务创建流程图",
                metadata_json="{}",
            )
            db.add(seed_message)
            db.commit()
            db.refresh(seed_message)

            save_pending_plan(
                group_id=int(group_id),
                creator_member_id=int(sender_member_id),
                trigger_message_id=int(seed_message.id),
                plan={"title": "deploy run"},
            )
            run = create_run(
                db,
                group_id=int(group_id),
                creator_member_id=int(sender_member_id),
                title="Deploy Run",
                goal_text="deploy goal",
                nodes=[{"node_key": "build", "title": "Build", "detail": "", "deps": []}],
                trigger_message_id=int(seed_message.id),
            )
            run_id = int(run.id)

            manager_reply = Message(
                group_id=int(group_id),
                sender_member_id=int(manager_member_id),
                message_type="ai",
                content="流程图已经创建好了",
                metadata_json=json.dumps({"reply_to": str(seed_message.id), "trigger": "manager_runtime"}, ensure_ascii=False),
            )
            db.add(manager_reply)
            db.commit()
            db.refresh(manager_reply)
        finally:
            db.close()

        response = client.post(
            "/api/v1/messages",
            json={
                "group_id": str(group_id),
                "sender_member_id": str(sender_member_id),
                "message_type": "text",
                "content": "@管家 请部署这个任务规划",
                "metadata_json": json.dumps(
                    {
                        "reply_to": str(manager_reply.id),
                        "mentions": [{"kind": "agent", "member_id": manager_member_id}],
                    },
                    ensure_ascii=False,
                ),
            },
        )
        assert response.status_code == 200

        reply = _wait_for_manager_reply(group_id)
        metadata = json.loads(str(reply.metadata_json or "{}"))
        assert "delivery_result" not in metadata
        assert "开始部署当前任务规划" in str(reply.content)
        assert any(int(ctx.get("run_id") or 0) == int(run_id) for ctx in captured_contexts)


def test_manager_deploy_request_resolves_run_id_from_task_run_record(monkeypatch) -> None:
    captured_contexts: list[dict] = []

    async def fake_invoke_manager(*args, **kwargs):  # type: ignore[no-untyped-def]
        _ = args
        captured_contexts.append(dict(kwargs["extra_context"]))
        return ManagerInvokeResult(
            text="开始部署当前任务规划。",
            action="assistant",
            engine_type="agentscope_react",
            plan={},
            meta={"mode": "manager"},
            system_prompt_used="",
        )

    async def fail_feature_delivery(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("deploy requests should not route to feature delivery")

    monkeypatch.setattr("app.manager_runtime.invoke_manager", fake_invoke_manager)
    monkeypatch.setattr("app.services.project_delivery_service.invoke_agent", fail_feature_delivery)

    with TestClient(app) as client:
        headers = _auth_headers(client)
        group_id, _workspace_id = _create_project_group(client, headers)
        _enable_manager(client, headers, group_id)
        sender_member_id = _user_member_id(group_id)
        manager_member_id = _manager_member_id(group_id)

        db = SessionLocal()
        try:
            seed_message = Message(
                group_id=int(group_id),
                sender_member_id=int(sender_member_id),
                message_type="text",
                content="为这个任务创建规划",
                metadata_json="{}",
            )
            db.add(seed_message)
            db.commit()
            db.refresh(seed_message)

            run = create_run(
                db,
                group_id=int(group_id),
                creator_member_id=int(sender_member_id),
                title="Deploy Run",
                goal_text="deploy goal",
                nodes=[{"node_key": "build", "title": "Build", "detail": "", "deps": []}],
                trigger_message_id=int(seed_message.id),
            )
            run_id = int(run.id)

            manager_reply = Message(
                group_id=int(group_id),
                sender_member_id=int(manager_member_id),
                message_type="ai",
                content="规划已经创建好了",
                metadata_json=json.dumps({"reply_to": str(seed_message.id), "trigger": "manager_runtime"}, ensure_ascii=False),
            )
            db.add(manager_reply)
            db.commit()
            db.refresh(manager_reply)
        finally:
            db.close()

        response = client.post(
            "/api/v1/messages",
            json={
                "group_id": str(group_id),
                "sender_member_id": str(sender_member_id),
                "message_type": "text",
                "content": "@管家 请部署这个任务规划",
                "metadata_json": json.dumps(
                    {
                        "reply_to": str(manager_reply.id),
                        "mentions": [{"kind": "agent", "member_id": manager_member_id}],
                    },
                    ensure_ascii=False,
                ),
            },
        )
        assert response.status_code == 200

        reply = _wait_for_manager_reply(group_id)
        metadata = json.loads(str(reply.metadata_json or "{}"))
        assert "delivery_result" not in metadata
        assert "开始部署当前任务规划" in str(reply.content)
        assert any(int(ctx.get("run_id") or 0) == int(run_id) for ctx in captured_contexts)


def test_manager_reply_returns_before_background_node_execution_finishes(monkeypatch) -> None:
    holder: dict[str, int] = {}

    class FastReturnEngine:
        async def run(self, *, ctx, req, tool_executor=None):  # type: ignore[no-untyped-def]
            _ = ctx
            _ = tool_executor
            tool = await req.toolkit.get_tool("manager.node_execute")
            assert tool is not None
            await tool(node_id=int(holder["node_id"]), member_id=int(holder["agent_member_id"]))
            return "已开始执行任务。", {"mode": "manager"}

    async def slow_dispatch_message_event_for_message(*, group_id, sender_member_id, message_id, message_type, content, meta_json):  # type: ignore[no-untyped-def]
        _ = (group_id, sender_member_id, message_id, message_type, content, meta_json)
        await asyncio.sleep(0.8)

    monkeypatch.setattr("app.manager_runtime.facade.create_engine", lambda _engine_type: FastReturnEngine())
    monkeypatch.setattr(
        "app.agent_runtime.message_store.dispatch_message_event_for_message",
        slow_dispatch_message_event_for_message,
    )

    with TestClient(app) as client:
        headers = _auth_headers(client)
        group_id, _workspace_id = _create_project_group(client, headers)
        _enable_manager(client, headers, group_id)
        sender_member_id = _user_member_id(group_id)
        manager_member_id = _manager_member_id(group_id)

        db = SessionLocal()
        try:
            sender_member = db.query(Member).filter(Member.id == int(sender_member_id)).first()
            assert sender_member is not None

            agent_instance = AgentInstance(
                creator_user_id=int(sender_member.user_ref or 1),
                display_name="worker",
                description="",
                base_url=None,
                api_key_ref=None,
                engine_type="internal_llm",
                engine_config_json="{}",
                status="active",
            )
            db.add(agent_instance)
            db.commit()
            db.refresh(agent_instance)

            agent_member = Member(
                group_id=int(group_id),
                kind="agent",
                display_name="worker",
                user_ref=None,
                agent_instance_id=int(agent_instance.id),
                title="backend",
            )
            db.add(agent_member)
            db.commit()
            db.refresh(agent_member)

            run = create_run(
                db,
                group_id=int(group_id),
                creator_member_id=int(sender_member_id),
                title="Async Execute Run",
                goal_text="verify quick manager reply",
                nodes=[{"node_key": "build", "title": "Build", "detail": "", "deps": []}],
            )
            holder["agent_member_id"] = int(agent_member.id)
            actual_node = db.query(GroupTaskNode).filter(GroupTaskNode.run_id == int(run.id)).order_by(GroupTaskNode.id.asc()).first()
            assert actual_node is not None
            holder["node_id"] = int(actual_node.id)
        finally:
            db.close()

        start = time.time()
        response = client.post(
            "/api/v1/messages",
            json={
                "group_id": str(group_id),
                "sender_member_id": str(sender_member_id),
                "message_type": "text",
                "content": "@管家 执行这个任务",
                "metadata_json": json.dumps({"mentions": [{"kind": "agent", "member_id": manager_member_id}]}, ensure_ascii=False),
            },
        )
        assert response.status_code == 200

        reply = _wait_for_manager_reply(group_id, timeout_seconds=0.4)
        elapsed = time.time() - start
        assert "已开始执行任务" in str(reply.content)
        assert elapsed < 0.75

        db = SessionLocal()
        try:
            node_row = db.query(GroupTaskNode).filter(GroupTaskNode.id == int(holder["node_id"])).first()
            assert node_row is not None
            assert str(node_row.status) == "pending"
        finally:
            db.close()
