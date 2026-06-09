from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.db.session import SessionLocal
from app.models.deployment_job import DeploymentJob
from app.agent_runtime.tool._executor import execute_builtin_tool
from app.services.execution_runtime_service import CommandExecutionResult, DockerSandboxExecutor
from app.services.project_code_service import get_project_code_root
from app.services.deployment_runtime_service import DockerDeploymentRunner


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
            "name": "deploy-project",
            "description": "runtime pipeline test",
            "type": "project",
            "users": [],
            "agents": [],
        },
    )
    assert response.status_code == 200
    data = response.json()["data"]
    return int(data["id"]), int(data["workspace_id"])


def test_workspace_snapshot_copies_project_code() -> None:
    with TestClient(app) as client:
        headers = _auth_headers(client)
        group_id, workspace_id = _create_project_group(client, headers)
        root = get_project_code_root(group_id)
        target = root / "README.md"
        target.write_text("snapshot me", encoding="utf-8")

        response = client.post(
            f"/api/v1/workspaces/{workspace_id}/snapshots",
            headers=headers,
            json={"label": "manual"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        snapshot_path = Path(data["snapshot_path"])
        assert snapshot_path.exists()
        assert (snapshot_path / "README.md").read_text(encoding="utf-8") == "snapshot me"


def test_execution_endpoint_runs_through_workspace_snapshot(monkeypatch) -> None:
    observed: dict[str, str] = {}

    def fake_run_command(self, **kwargs):  # type: ignore[no-untyped-def]
        snapshot_path = Path(kwargs["snapshot_path"])
        observed["snapshot_path"] = snapshot_path.as_posix()
        assert (snapshot_path / "app.txt").read_text(encoding="utf-8") == "hello"
        work_dir = Path(kwargs.get("work_dir") or (snapshot_path.parent / "workdir-test"))
        work_dir.mkdir(parents=True, exist_ok=True)
        return CommandExecutionResult(
            exit_code=0,
            stdout="command ok",
            stderr="",
            work_dir=work_dir.as_posix(),
            docker_command=["docker", "run", "fake"],
        )

    monkeypatch.setattr(DockerSandboxExecutor, "run_command", fake_run_command)

    with TestClient(app) as client:
        headers = _auth_headers(client)
        group_id, workspace_id = _create_project_group(client, headers)
        root = get_project_code_root(group_id)
        (root / "app.txt").write_text("hello", encoding="utf-8")

        response = client.post(
            "/api/v1/executions",
            headers=headers,
            json={
                "workspace_id": workspace_id,
                "command": "cat app.txt",
                "cwd": ".",
                "network_enabled": False,
                "env": {"APP_ENV": "test"},
            },
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["status"] == "succeeded"
        assert data["result"]["exit_code"] == 0
        assert data["stdout"] == "command ok"
        assert observed["snapshot_path"].endswith(data["result"]["snapshot_id"])


def test_deployment_endpoint_supports_retry(monkeypatch) -> None:
    run_calls = {"deploy": 0}

    def fake_run_command(self, **kwargs):  # type: ignore[no-untyped-def]
        work_dir = Path(kwargs.get("work_dir") or (Path(kwargs["snapshot_path"]).parent / "deploy-workdir"))
        work_dir.mkdir(parents=True, exist_ok=True)
        return CommandExecutionResult(
            exit_code=0,
            stdout=f"ran {kwargs['command']}",
            stderr="",
            work_dir=work_dir.as_posix(),
            docker_command=["docker", "run", "fake"],
        )

    def fake_deploy(self, **kwargs):  # type: ignore[no-untyped-def]
        run_calls["deploy"] += 1
        if run_calls["deploy"] == 1:
            raise RuntimeError(
                json.dumps(
                    {
                        "message": "docker run failed with code 1",
                        "rollback_image_ref": "old:image",
                        "rollback_status": "succeeded",
                        "logs": [{"step": "docker_run", "exit_code": 1}],
                    },
                    ensure_ascii=False,
                )
            )
        return {
            "logs": [{"step": "docker_run", "exit_code": 0}],
            "deployed_container_id": "container-123",
            "rollback_image_ref": "old:image",
            "rollback_status": "not_needed",
        }

    monkeypatch.setattr(DockerSandboxExecutor, "run_command", fake_run_command)
    monkeypatch.setattr(DockerDeploymentRunner, "run", fake_deploy)

    with TestClient(app) as client:
        headers = _auth_headers(client)
        group_id, workspace_id = _create_project_group(client, headers)
        root = get_project_code_root(group_id)
        (root / "Dockerfile").write_text("FROM nginx:alpine\n", encoding="utf-8")

        create_response = client.post(
            "/api/v1/deployments",
            headers=headers,
            json={
                "workspace_id": workspace_id,
                "image_ref": "agenthub/test:latest",
                "container_name": "agenthub-test",
                "install_command": "npm install",
                "test_command": "npm test",
                "build_command": "npm run build",
                "ports": [{"host_port": 8080, "container_port": 80}],
            },
        )
        assert create_response.status_code == 200
        failed_job = create_response.json()["data"]
        assert failed_job["status"] == "failed"
        assert failed_job["rollback_status"] == "succeeded"

        get_response = client.get(
            f"/api/v1/deployments/{failed_job['id']}",
            headers=headers,
        )
        assert get_response.status_code == 200
        assert get_response.json()["data"]["status"] == "failed"

        retry_response = client.post(
            f"/api/v1/deployments/{failed_job['id']}/retry",
            headers=headers,
        )
        assert retry_response.status_code == 200
        retried = retry_response.json()["data"]
        assert retried["status"] == "succeeded"
        assert retried["deployed_container_id"] == "container-123"


def test_project_deploy_run_defaults_and_reuses_run_port(monkeypatch) -> None:
    def fake_run_command(self, **kwargs):  # type: ignore[no-untyped-def]
        work_dir = Path(kwargs.get("work_dir") or (Path(kwargs["snapshot_path"]).parent / "deploy-run-defaults"))
        work_dir.mkdir(parents=True, exist_ok=True)
        return CommandExecutionResult(
            exit_code=0,
            stdout=f"ran {kwargs['command']}",
            stderr="",
            work_dir=work_dir.as_posix(),
            docker_command=["docker", "run", "fake"],
        )

    def fake_deploy(self, **kwargs):  # type: ignore[no-untyped-def]
        return {
            "logs": [{"step": "docker_run", "exit_code": 0}],
            "deployed_container_id": "container-defaults",
            "rollback_image_ref": None,
            "rollback_status": None,
        }

    monkeypatch.setattr(DockerSandboxExecutor, "run_command", fake_run_command)
    monkeypatch.setattr(DockerDeploymentRunner, "run", fake_deploy)

    with TestClient(app) as client:
        headers = _auth_headers(client)
        group_id, _workspace_id = _create_project_group(client, headers)
        root = get_project_code_root(group_id)
        (root / "Dockerfile").write_text("FROM nginx:alpine\n", encoding="utf-8")
        db = SessionLocal()
        try:
            existing_count = (
                db.query(DeploymentJob)
                .filter(DeploymentJob.project_id == int(group_id))
                .count()
            )
        finally:
            db.close()

        first = execute_builtin_tool(
            agent_id=1,
            tool_code="project_deploy_run",
            args={"ports": [{"container_port": 80}]},
            runtime_context={"group_type": "project", "group_id": group_id, "run_id": 101, "node_id": 11},
        )
        second = execute_builtin_tool(
            agent_id=1,
            tool_code="project_deploy_run",
            args={"ports": [{"container_port": 80}]},
            runtime_context={"group_type": "project", "group_id": group_id, "run_id": 101, "node_id": 11},
        )
        third = execute_builtin_tool(
            agent_id=1,
            tool_code="project_deploy_run",
            args={"ports": [{"container_port": 80}]},
            runtime_context={"group_type": "project", "group_id": group_id, "run_id": 102, "node_id": 12},
        )

        assert first["status"] == "succeeded"
        assert second["status"] == "succeeded"
        assert third["status"] == "succeeded"
        assert first["image_ref"] == "agenthub/deploy-project-run-101:latest"
        assert first["container_name"] == "agenthub-deploy-project-run-101"
        assert first["url"] is not None

        db = SessionLocal()
        try:
            rows = (
                db.query(DeploymentJob)
                .filter(DeploymentJob.project_id == int(group_id))
                .order_by(DeploymentJob.id.asc())
                .all()
            )
            rows = rows[existing_count:]
            assert len(rows) == 3
            first_spec = rows[0].spec_json
            second_spec = rows[1].spec_json
            third_spec = rows[2].spec_json
            first_context = rows[0].context_json
            third_context = rows[2].context_json
        finally:
            db.close()

        first_ports = json.loads(first_spec)["ports"]
        second_ports = json.loads(second_spec)["ports"]
        third_ports = json.loads(third_spec)["ports"]
        assert first_ports[0]["host_port"] == second_ports[0]["host_port"]
        assert first_ports[0]["host_port"] != third_ports[0]["host_port"]
        assert json.loads(first_context)["run_id"] == 101
        assert json.loads(first_context)["node_id"] == 11
        assert json.loads(third_context)["run_id"] == 102
        assert json.loads(third_context)["node_id"] == 12
