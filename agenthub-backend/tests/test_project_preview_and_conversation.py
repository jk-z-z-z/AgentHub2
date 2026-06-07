from __future__ import annotations

import json
import time
from pathlib import Path

from fastapi.testclient import TestClient

from app.agent_runtime.schemas import AgentInvokeResult
from app.agent_runtime.tool._executor import execute_builtin_tool
from app.db.session import SessionLocal
from app.event_runtime.context import get_or_create_manager_member
from app.main import app
from app.models.member import Member
from app.models.message import Message
from app.services.deployment_runtime_service import DockerDeploymentRunner
from app.services.execution_runtime_service import CommandExecutionResult, DockerSandboxExecutor
from app.services.preview_runtime_service import DockerPreviewRunner
from app.services.project_code_service import get_project_code_root
from app.services.project_conversation_service import is_project_feature_delivery_request
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


def test_manager_conversation_creates_hello_preview(monkeypatch) -> None:
    def fake_preview_run(self, **kwargs):  # type: ignore[no-untyped-def]
        job = kwargs["job"]
        return {
            "logs": [{"step": "docker_run", "exit_code": 0}],
            "container_id": "preview-hello",
            "url": f"http://127.0.0.1:{job.host_port}",
        }

    monkeypatch.setattr(DockerPreviewRunner, "run", fake_preview_run)

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
                "content": "@管家 本地预览，纯 html，做一个 Hello 页面",
                "metadata_json": json.dumps({"mentions": [{"kind": "agent", "member_id": manager_member_id}]}, ensure_ascii=False),
            },
        )
        assert response.status_code == 200

        reply = _wait_for_manager_reply(group_id)
        metadata = json.loads(str(reply.metadata_json or "{}"))
        assert metadata["preview_result"]["url"].startswith("http://127.0.0.1:")
        assert metadata["delivery_result"]["mode"] == "static_page_shortcut"
        assert metadata["delivery_result"]["status"] == "succeeded"
        assert metadata["code_diff"]["status"] in {"ready", "no_changes"}
        assert int(metadata["code_diff"]["message_id"]) > 0
        assert "index.html" in str(reply.content)
        html_content = (get_project_code_root(group_id) / "index.html").read_text(encoding="utf-8")
        assert "<h1>Hello</h1>" in html_content

        diff_response = client.get(
            f"/api/v1/messages/{metadata['code_diff']['message_id']}/code-diff",
            headers=headers,
        )
        assert diff_response.status_code == 200
        diff_data = diff_response.json()["data"]
        assert diff_data["status"] in {"ready", "no_changes"}
        if diff_data["status"] == "ready":
            assert diff_data["summary"]["changed_file_count"] >= 1
            assert any(item["path"] == "index.html" for item in diff_data["files"])


def test_manager_conversation_updates_preview_text_to_google(monkeypatch) -> None:
    def fake_preview_run(self, **kwargs):  # type: ignore[no-untyped-def]
        job = kwargs["job"]
        return {
            "logs": [{"step": "docker_run", "exit_code": 0}],
            "container_id": "preview-google",
            "url": f"http://127.0.0.1:{job.host_port}",
        }

    monkeypatch.setattr(DockerPreviewRunner, "run", fake_preview_run)

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
                "content": "@管家 修改这个页面，打印 Google",
                "metadata_json": json.dumps({"mentions": [{"kind": "agent", "member_id": manager_member_id}]}, ensure_ascii=False),
            },
        )
        assert response.status_code == 200

        reply = _wait_for_manager_reply(group_id)
        metadata = json.loads(str(reply.metadata_json or "{}"))
        assert metadata["preview_result"]["url"].startswith("http://127.0.0.1:")
        html_content = (get_project_code_root(group_id) / "index.html").read_text(encoding="utf-8")
        assert "<h1>Google</h1>" in html_content
        assert "页面已创建" not in html_content


def test_manager_conversation_deploy_generates_dockerfile(monkeypatch) -> None:
    def fake_deploy_run(self, **kwargs):  # type: ignore[no-untyped-def]
        job = kwargs["job"]
        return {
            "logs": [{"step": "docker_run", "exit_code": 0}],
            "deployed_container_id": "deploy-123",
            "rollback_image_ref": None,
            "rollback_status": None,
        }

    def fake_command_run(self, **kwargs):  # type: ignore[no-untyped-def]
        work_dir = Path(kwargs.get("work_dir") or (Path(kwargs["snapshot_path"]).parent / "build-workdir"))
        work_dir.mkdir(parents=True, exist_ok=True)
        return CommandExecutionResult(
            exit_code=0,
            stdout="ok",
            stderr="",
            work_dir=work_dir.as_posix(),
            docker_command=["docker", "run", "fake"],
        )

    monkeypatch.setattr(DockerSandboxExecutor, "run_command", fake_command_run)
    monkeypatch.setattr(DockerDeploymentRunner, "run", fake_deploy_run)

    with TestClient(app) as client:
        headers = _auth_headers(client)
        group_id, _workspace_id = _create_project_group(client, headers)
        _enable_manager(client, headers, group_id)
        sender_member_id = _user_member_id(group_id)
        manager_member_id = _manager_member_id(group_id)
        (get_project_code_root(group_id) / "index.html").write_text("<h1>deploy</h1>", encoding="utf-8")

        response = client.post(
            "/api/v1/messages",
            json={
                "group_id": str(group_id),
                "sender_member_id": str(sender_member_id),
                "message_type": "text",
                "content": "@管家 部署这个页面",
                "metadata_json": json.dumps({"mentions": [{"kind": "agent", "member_id": manager_member_id}]}, ensure_ascii=False),
            },
        )
        assert response.status_code == 200

        reply = _wait_for_manager_reply(group_id)
        metadata = json.loads(str(reply.metadata_json or "{}"))
        assert metadata["deploy_result"]["status"] == "succeeded"
        assert (get_project_code_root(group_id) / "Dockerfile").exists()


def test_manager_conversation_deploy_repairs_bare_nginx_dockerfile(monkeypatch) -> None:
    def fake_deploy_run(self, **kwargs):  # type: ignore[no-untyped-def]
        return {
            "logs": [{"step": "docker_run", "exit_code": 0}],
            "deployed_container_id": "deploy-456",
            "rollback_image_ref": None,
            "rollback_status": None,
        }

    def fake_command_run(self, **kwargs):  # type: ignore[no-untyped-def]
        work_dir = Path(kwargs.get("work_dir") or (Path(kwargs["snapshot_path"]).parent / "repair-workdir"))
        work_dir.mkdir(parents=True, exist_ok=True)
        return CommandExecutionResult(
            exit_code=0,
            stdout="ok",
            stderr="",
            work_dir=work_dir.as_posix(),
            docker_command=["docker", "run", "fake"],
        )

    monkeypatch.setattr(DockerSandboxExecutor, "run_command", fake_command_run)
    monkeypatch.setattr(DockerDeploymentRunner, "run", fake_deploy_run)

    with TestClient(app) as client:
        headers = _auth_headers(client)
        group_id, _workspace_id = _create_project_group(client, headers)
        _enable_manager(client, headers, group_id)
        sender_member_id = _user_member_id(group_id)
        manager_member_id = _manager_member_id(group_id)
        root = get_project_code_root(group_id)
        (root / "index.html").write_text("<h1>Hello</h1>", encoding="utf-8")
        (root / "Dockerfile").write_text("FROM nginx:alpine\n", encoding="utf-8")

        response = client.post(
            "/api/v1/messages",
            json={
                "group_id": str(group_id),
                "sender_member_id": str(sender_member_id),
                "message_type": "text",
                "content": "@管家 我想要部署一个打印 hello 的页面",
                "metadata_json": json.dumps({"mentions": [{"kind": "agent", "member_id": manager_member_id}]}, ensure_ascii=False),
            },
        )
        assert response.status_code == 200

        reply = _wait_for_manager_reply(group_id)
        metadata = json.loads(str(reply.metadata_json or "{}"))
        assert metadata["deploy_result"]["status"] == "succeeded"
        assert (root / "Dockerfile").read_text(encoding="utf-8") == "FROM nginx:alpine\nCOPY index.html /usr/share/nginx/html/index.html\n"


def test_manager_conversation_deploy_google_page_content(monkeypatch) -> None:
    def fake_deploy_run(self, **kwargs):  # type: ignore[no-untyped-def]
        return {
            "logs": [{"step": "docker_run", "exit_code": 0}],
            "deployed_container_id": "deploy-google",
            "rollback_image_ref": None,
            "rollback_status": None,
        }

    def fake_command_run(self, **kwargs):  # type: ignore[no-untyped-def]
        work_dir = Path(kwargs.get("work_dir") or (Path(kwargs["snapshot_path"]).parent / "google-workdir"))
        work_dir.mkdir(parents=True, exist_ok=True)
        return CommandExecutionResult(
            exit_code=0,
            stdout="ok",
            stderr="",
            work_dir=work_dir.as_posix(),
            docker_command=["docker", "run", "fake"],
        )

    monkeypatch.setattr(DockerSandboxExecutor, "run_command", fake_command_run)
    monkeypatch.setattr(DockerDeploymentRunner, "run", fake_deploy_run)

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
                "content": "@管家 我想要部署一个打印 Google 的页面",
                "metadata_json": json.dumps({"mentions": [{"kind": "agent", "member_id": manager_member_id}]}, ensure_ascii=False),
            },
        )
        assert response.status_code == 200

        reply = _wait_for_manager_reply(group_id)
        metadata = json.loads(str(reply.metadata_json or "{}"))
        assert metadata["deploy_result"]["status"] == "succeeded"
        html_content = (get_project_code_root(group_id) / "index.html").read_text(encoding="utf-8")
        assert "<h1>Google</h1>" in html_content


def test_manager_conversation_feature_delivery_fails_without_real_file_writes(monkeypatch) -> None:
    async def fake_invoke_agent(*args, **kwargs):  # type: ignore[no-untyped-def]
        _ = args
        _ = kwargs
        return AgentInvokeResult(text="登录流程已全部完成", engine_type="agentscope_react", meta={}, system_prompt_used="")

    monkeypatch.setattr("app.services.project_delivery_service.invoke_agent", fake_invoke_agent)

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
        assert metadata["delivery_result"]["mode"] == "project_feature_delivery"
        assert metadata["delivery_result"]["status"] == "failed"
        assert metadata["delivery_result"]["changed_file_count"] == 0
        assert metadata["applied_files"] == []
        assert metadata["validation_result"]["ok"] is False
        assert "preview_result" not in metadata
        assert "deploy_result" not in metadata
        assert "代码尚未落盘" in str(reply.content)
        assert not (get_project_code_root(group_id) / "index.html").exists()


def test_login_interface_request_routes_to_feature_delivery() -> None:
    assert is_project_feature_delivery_request("我想要创建一个完整的登录界面，写入项目里，然后给我预览地址") is True


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


def test_manager_conversation_feature_delivery_deploys_to_requested_port(monkeypatch) -> None:
    async def fake_invoke_agent(*args, **kwargs):  # type: ignore[no-untyped-def]
        tool_executor = kwargs["tool_executor"]
        tool_executor(
            "project_code_write",
            {
                "path": "dist/index.html",
                "content": "<!DOCTYPE html><html><body><h1>Google</h1></body></html>",
            },
        )
        tool_executor(
            "project_code_write",
            {
                "path": "Dockerfile",
                "content": "FROM nginx:alpine\nCOPY dist/ /usr/share/nginx/html/\n",
            },
        )
        tool_executor("project_deploy_run", {"ports": [{"container_port": 80, "protocol": "tcp"}]})
        return AgentInvokeResult(text="done", engine_type="agentscope_react", meta={}, system_prompt_used="")

    def fake_deploy_run(self, **kwargs):  # type: ignore[no-untyped-def]
        return {
            "logs": [{"step": "docker_run", "exit_code": 0}],
            "deployed_container_id": "deploy-feature",
            "rollback_image_ref": None,
            "rollback_status": None,
        }

    def fake_command_run(self, **kwargs):  # type: ignore[no-untyped-def]
        work_dir = Path(kwargs.get("work_dir") or (Path(kwargs["snapshot_path"]).parent / "feature-workdir"))
        work_dir.mkdir(parents=True, exist_ok=True)
        return CommandExecutionResult(
            exit_code=0,
            stdout="ok",
            stderr="",
            work_dir=work_dir.as_posix(),
            docker_command=["docker", "run", "fake"],
        )

    monkeypatch.setattr("app.services.project_delivery_service.invoke_agent", fake_invoke_agent)
    monkeypatch.setattr(DockerSandboxExecutor, "run_command", fake_command_run)
    monkeypatch.setattr(DockerDeploymentRunner, "run", fake_deploy_run)

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
        assert metadata["delivery_result"]["mode"] == "project_feature_delivery"
        assert metadata["delivery_result"]["status"] == "succeeded"
        assert metadata["delivery_result"]["changed_file_count"] == 2
        assert metadata["validation_result"]["kind"] == "deploy"
        assert metadata["validation_result"]["ok"] is True
        assert metadata["deploy_result"]["status"] == "succeeded"
        assert metadata["deploy_result"]["url"] == "http://127.0.0.1:5175"
        assert len(metadata["applied_files"]) == 2
        assert (get_project_code_root(group_id) / "dist" / "index.html").read_text(encoding="utf-8").find("Google") >= 0
