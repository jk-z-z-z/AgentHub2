from __future__ import annotations

import json
import shutil
import socket
import subprocess
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.common.file_utils import normalize_rel_dir, safe_resolve_under_root
from app.core.config import settings
from app.db.session import SessionLocal
from app.models.deployment_job import DeploymentJob
from app.models.sandbox_run import SandboxRun
from app.models.workspace import Workspace
from app.services.execution_runtime_service import (
    DockerSandboxExecutor,
    Executor,
    _safe_dump,
    _safe_load_dict,
    _truncate,
)
from app.services.workspace_runtime_service import (
    assert_workspace_access,
    build_execution_context,
    create_workspace_snapshot_record,
    get_workspace_by_id,
)


def _infer_container_port_from_dockerfile(work_root: Path, dockerfile_path: str) -> int:
    try:
        dockerfile = safe_resolve_under_root(work_root.resolve(), dockerfile_path)
        if not dockerfile.exists() or not dockerfile.is_file():
            return 80
        for raw_line in dockerfile.read_text(encoding="utf-8").splitlines():
            line = raw_line.split("#", 1)[0].strip()
            if not line or not line.upper().startswith("EXPOSE "):
                continue
            for token in line[7:].split():
                port_text = token.split("/", 1)[0].strip()
                if port_text.isdigit():
                    port = int(port_text)
                    if 1 <= port <= 65535:
                        return port
    except Exception:
        return 80
    return 80


def _normalize_ports_for_workspace(
    *,
    workspace: Workspace,
    dockerfile_path: str,
    ports: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    work_root = Path(str(workspace.source_path or ".")).resolve()
    inferred_container_port = _infer_container_port_from_dockerfile(work_root, dockerfile_path)
    normalized: list[dict[str, Any]] = []
    for item in ports or []:
        if not isinstance(item, dict):
            continue
        try:
            host_port = int(item.get("host_port"))
        except Exception:
            continue
        raw_container_port = item.get("container_port")
        try:
            container_port = int(raw_container_port)
        except Exception:
            container_port = inferred_container_port
        if container_port == 80 and inferred_container_port != 80:
            container_port = inferred_container_port
        normalized.append(
            {
                "host_port": host_port,
                "container_port": container_port,
                "protocol": str(item.get("protocol") or "tcp"),
            }
        )
    return normalized


class DeploymentRunner(ABC):
    @abstractmethod
    def run(
        self,
        *,
        job: DeploymentJob,
        workspace: Workspace,
        sandbox_run: SandboxRun | None,
        work_dir: str,
        spec: dict[str, Any],
    ) -> dict[str, Any]:
        raise NotImplementedError


def _serialize_ports(ports: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for item in ports or []:
        try:
            out.append(
                {
                    "host_port": int(item["host_port"]),
                    "container_port": int(item["container_port"]),
                    "protocol": str(item.get("protocol") or "tcp"),
                }
            )
        except Exception:
            continue
    return out


def _context_int(context: dict[str, Any] | None, key: str) -> int | None:
    if not isinstance(context, dict):
        return None
    value = context.get(key)
    try:
        return int(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _port_is_available(host_port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("127.0.0.1", int(host_port)))
        except OSError:
            return False
    return True


def _previous_run_host_port(
    db: Session,
    *,
    workspace_id: int,
    run_id: int,
    container_name: str,
) -> int | None:
    rows = (
        db.query(DeploymentJob)
        .filter(
            DeploymentJob.workspace_id == int(workspace_id),
            DeploymentJob.status == "succeeded",
        )
        .order_by(DeploymentJob.id.desc())
        .all()
    )
    for row in rows:
        context_payload = _safe_load_dict(row.context_json)
        if _context_int(context_payload, "run_id") != int(run_id):
            continue
        spec_payload = _safe_load_dict(row.spec_json)
        ports = _serialize_ports(spec_payload.get("ports") or [])
        if not ports:
            continue
        host_port = int(ports[0]["host_port"])
        if _port_is_available(host_port) or str(row.container_name or "") == str(container_name or ""):
            return host_port
    return None


def _allocate_run_host_port(
    db: Session,
    *,
    workspace_id: int,
    run_id: int,
    container_name: str,
) -> int:
    previous_host_port = _previous_run_host_port(
        db,
        workspace_id=int(workspace_id),
        run_id=int(run_id),
        container_name=str(container_name or ""),
    )
    if previous_host_port is not None:
        return int(previous_host_port)
    candidate = max(1, 20000 + (int(run_id) % 20000))
    while candidate <= 65535:
        if _port_is_available(candidate):
            return candidate
        candidate += 1
    raise RuntimeError("No available host port for deployment")


def _normalize_deployment_ports(
    db: Session,
    *,
    workspace_id: int,
    container_name: str,
    ports: list[dict[str, Any]] | None,
    context: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    run_id = _context_int(context, "run_id")
    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(ports or []):
        if not isinstance(item, dict):
            continue
        try:
            container_port = int(item["container_port"])
        except Exception:
            continue
        protocol = str(item.get("protocol") or "tcp")
        host_port_raw = item.get("host_port")
        try:
            host_port = int(host_port_raw) if host_port_raw not in (None, "") else None
        except (TypeError, ValueError):
            host_port = None
        if index == 0 and host_port is None and run_id is not None:
            host_port = _allocate_run_host_port(
                db,
                workspace_id=int(workspace_id),
                run_id=int(run_id),
                container_name=str(container_name or ""),
            )
        payload = {
            "container_port": int(container_port),
            "protocol": protocol,
        }
        if host_port is not None:
            payload["host_port"] = int(host_port)
        normalized.append(payload)
    return normalized


class DockerDeploymentRunner(DeploymentRunner):
    def _ensure_docker(self) -> None:
        if shutil.which("docker"):
            return
        raise RuntimeError("docker CLI is required for deployment")

    def _run_host_command(self, command: list[str], *, timeout_seconds: int) -> subprocess.CompletedProcess[str]:
        self._ensure_docker()
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=max(10, int(timeout_seconds)),
        )

    def _inspect_existing_image(self, container_name: str) -> str | None:
        proc = self._run_host_command(
            ["docker", "inspect", container_name, "--format", "{{.Config.Image}}"],
            timeout_seconds=int(settings.deployment_command_timeout_seconds),
        )
        if proc.returncode != 0:
            return None
        image = str(proc.stdout or "").strip()
        return image or None

    def _remove_existing_container(self, container_name: str) -> subprocess.CompletedProcess[str]:
        return self._run_host_command(
            ["docker", "rm", "-f", container_name],
            timeout_seconds=int(settings.deployment_command_timeout_seconds),
        )

    def _build_image(
        self,
        *,
        image_ref: str,
        work_dir: str,
        dockerfile_path: str,
        build_context_path: str,
    ) -> tuple[subprocess.CompletedProcess[str], list[str]]:
        work_root = Path(work_dir).resolve()
        dockerfile = safe_resolve_under_root(work_root, dockerfile_path)
        context_dir_rel = normalize_rel_dir(build_context_path, allow_root=True)
        context_dir = work_root if context_dir_rel == "." else safe_resolve_under_root(work_root, context_dir_rel)
        command = [
            "docker",
            "build",
            "-t",
            image_ref,
            "-f",
            dockerfile.as_posix(),
            context_dir.as_posix(),
        ]
        return self._run_host_command(
            command,
            timeout_seconds=int(settings.deployment_command_timeout_seconds),
        ), command

    def _run_container(
        self,
        *,
        image_ref: str,
        container_name: str,
        ports: list[dict[str, Any]],
        env: dict[str, str],
        container_command: str | None,
    ) -> tuple[subprocess.CompletedProcess[str], list[str]]:
        command = ["docker", "run", "-d", "--name", container_name]
        for port in _serialize_ports(ports):
            command.extend(
                [
                    "-p",
                    f"{port['host_port']}:{port['container_port']}/{port['protocol']}",
                ]
            )
        for key, value in sorted((env or {}).items()):
            command.extend(["-e", f"{key}={value}"])
        command.append(image_ref)
        if str(container_command or "").strip():
            command.extend(["sh", "-lc", str(container_command).strip()])
        return self._run_host_command(
            command,
            timeout_seconds=int(settings.deployment_command_timeout_seconds),
        ), command

    def run(
        self,
        *,
        job: DeploymentJob,
        workspace: Workspace,
        sandbox_run: SandboxRun | None,
        work_dir: str,
        spec: dict[str, Any],
    ) -> dict[str, Any]:
        _ = workspace
        _ = sandbox_run
        logs: list[dict[str, Any]] = []
        previous_image = self._inspect_existing_image(str(job.container_name))

        build_proc, build_cmd = self._build_image(
            image_ref=str(job.image_ref),
            work_dir=str(work_dir),
            dockerfile_path=str(job.dockerfile_path),
            build_context_path=str(job.build_context_path),
        )
        logs.append(
            {
                "step": "docker_build",
                "command": build_cmd,
                "exit_code": int(build_proc.returncode),
                "stdout": _truncate(build_proc.stdout),
                "stderr": _truncate(build_proc.stderr),
            }
        )
        if build_proc.returncode != 0:
            raise RuntimeError(
                json.dumps(
                    {
                        "message": f"docker build failed with code {build_proc.returncode}",
                        "rollback_image_ref": previous_image,
                        "rollback_status": None,
                        "logs": logs,
                    },
                    ensure_ascii=False,
                )
            )

        if previous_image:
            rm_proc = self._remove_existing_container(str(job.container_name))
            logs.append(
                {
                    "step": "remove_previous_container",
                    "command": ["docker", "rm", "-f", str(job.container_name)],
                    "exit_code": int(rm_proc.returncode),
                    "stdout": _truncate(rm_proc.stdout),
                    "stderr": _truncate(rm_proc.stderr),
                }
            )

        run_proc, run_cmd = self._run_container(
            image_ref=str(job.image_ref),
            container_name=str(job.container_name),
            ports=_serialize_ports(spec.get("ports") or []),
            env={str(k): str(v) for k, v in (spec.get("env") or {}).items()},
            container_command=str(spec.get("container_command") or "").strip() or None,
        )
        logs.append(
            {
                "step": "docker_run",
                "command": run_cmd,
                "exit_code": int(run_proc.returncode),
                "stdout": _truncate(run_proc.stdout),
                "stderr": _truncate(run_proc.stderr),
            }
        )
        if run_proc.returncode != 0:
            rollback_status = None
            if previous_image:
                rollback_proc, rollback_cmd = self._run_container(
                    image_ref=str(previous_image),
                    container_name=str(job.container_name),
                    ports=_serialize_ports(spec.get("ports") or []),
                    env={str(k): str(v) for k, v in (spec.get("env") or {}).items()},
                    container_command=str(spec.get("container_command") or "").strip() or None,
                )
                logs.append(
                    {
                        "step": "rollback",
                        "command": rollback_cmd,
                        "exit_code": int(rollback_proc.returncode),
                        "stdout": _truncate(rollback_proc.stdout),
                        "stderr": _truncate(rollback_proc.stderr),
                    }
                )
                rollback_status = "succeeded" if rollback_proc.returncode == 0 else "failed"
            raise RuntimeError(
                json.dumps(
                    {
                        "message": f"docker run failed with code {run_proc.returncode}",
                        "rollback_image_ref": previous_image,
                        "rollback_status": rollback_status,
                        "logs": logs,
                    },
                    ensure_ascii=False,
                )
            )

        return {
            "logs": logs,
            "deployed_container_id": str(run_proc.stdout or "").strip() or None,
            "rollback_image_ref": previous_image,
            "rollback_status": "not_needed" if previous_image else None,
        }


def _deployment_job_to_payload(row: DeploymentJob) -> dict[str, Any]:
    return {
        "id": int(row.id),
        "workspace_id": int(row.workspace_id),
        "project_id": int(row.project_id),
        "sandbox_run_id": int(row.sandbox_run_id) if row.sandbox_run_id else None,
        "status": str(row.status),
        "target_type": str(row.target_type),
        "image_ref": str(row.image_ref),
        "container_name": str(row.container_name),
        "sandbox_image": str(row.sandbox_image),
        "dockerfile_path": str(row.dockerfile_path),
        "build_context_path": str(row.build_context_path),
        "deployed_container_id": row.deployed_container_id,
        "rollback_image_ref": row.rollback_image_ref,
        "rollback_status": row.rollback_status,
        "attempt_count": int(row.attempt_count or 0),
        "logs_text": str(row.logs_text or ""),
        "error_message": row.error_message,
        "spec": _safe_load_dict(row.spec_json),
        "context": _safe_load_dict(row.context_json),
        "result": _safe_load_dict(row.result_json),
        "created_at": row.created_at,
        "updated_at": row.updated_at,
        "started_at": row.started_at,
        "finished_at": row.finished_at,
    }


def get_deployment_job(db: Session, *, deployment_id: int, user_id: int) -> DeploymentJob:
    row = db.query(DeploymentJob).filter(DeploymentJob.id == int(deployment_id)).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deployment job not found")
    assert_workspace_access(db, workspace_id=int(row.workspace_id), user_id=int(user_id))
    return row


def create_deployment_job(
    db: Session,
    *,
    workspace_id: int,
    user_id: int,
    image_ref: str,
    container_name: str,
    sandbox_image: str | None = None,
    dockerfile_path: str = "Dockerfile",
    build_context_path: str = ".",
    install_command: str | None = None,
    test_command: str | None = None,
    build_command: str | None = None,
    env: dict[str, str] | None = None,
    ports: list[dict[str, Any]] | None = None,
    container_command: str | None = None,
    runtime_context: dict[str, Any] | None = None,
) -> DeploymentJob:
    workspace = assert_workspace_access(db, workspace_id=int(workspace_id), user_id=int(user_id))
    normalized_context = {
        key: int(value)
        for key, value in {
            "run_id": _context_int(runtime_context, "run_id"),
            "node_id": _context_int(runtime_context, "node_id"),
        }.items()
        if value is not None
    }
    normalized_ports = _normalize_deployment_ports(
        db,
        workspace_id=int(workspace.id),
        container_name=str(container_name or ""),
        ports=ports,
        context=normalized_context,
    )
    normalized_ports = _normalize_ports_for_workspace(
        workspace=workspace,
        dockerfile_path=str(dockerfile_path or "Dockerfile"),
        ports=normalized_ports,
    )
    row = DeploymentJob(
        creator_user_id=int(workspace.creator_user_id),
        tenant_id=str(workspace.tenant_id),
        project_id=int(workspace.project_id),
        workspace_id=int(workspace.id),
        requested_by_user_id=int(user_id),
        image_ref=str(image_ref),
        container_name=str(container_name),
        sandbox_image=str(sandbox_image or settings.docker_sandbox_default_image),
        dockerfile_path=str(dockerfile_path or "Dockerfile"),
        build_context_path=str(build_context_path or "."),
        spec_json=_safe_dump(
            {
                "install_command": str(install_command or "").strip() or None,
                "test_command": str(test_command or "").strip() or None,
                "build_command": str(build_command or "").strip() or None,
                "env": env or {},
                "ports": normalized_ports,
                "container_command": str(container_command or "").strip() or None,
            }
        ),
        context_json=_safe_dump(normalized_context),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _append_logs(row: DeploymentJob, message: str) -> None:
    row.logs_text = "\n".join([part for part in [str(row.logs_text or "").strip(), message.strip()] if part]).strip()


def run_deployment_job(
    db: Session,
    *,
    deployment_id: int,
    executor: Executor | None = None,
    runner: DeploymentRunner | None = None,
) -> DeploymentJob:
    row = db.query(DeploymentJob).filter(DeploymentJob.id == int(deployment_id)).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deployment job not found")
    workspace = get_workspace_by_id(db, workspace_id=int(row.workspace_id))
    if not workspace:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")

    row.status = "running"
    row.attempt_count = int(row.attempt_count or 0) + 1
    row.started_at = datetime.now(timezone.utc)
    sandbox_id = f"sandbox-deploy-{row.id}-a{row.attempt_count}"
    existing_context = _safe_load_dict(row.context_json)
    merged_context = build_execution_context(workspace=workspace, user_id=int(row.requested_by_user_id), sandbox_id=sandbox_id)
    merged_context.update(existing_context)
    row.context_json = _safe_dump(merged_context)
    db.add(row)
    db.commit()

    spec = _safe_load_dict(row.spec_json)
    snapshot = create_workspace_snapshot_record(db, workspace=workspace, label=f"deployment-{row.id}")
    sandbox = SandboxRun(
        creator_user_id=int(workspace.creator_user_id),
        tenant_id=str(workspace.tenant_id),
        project_id=int(workspace.project_id),
        workspace_id=int(workspace.id),
        requested_by_user_id=int(row.requested_by_user_id),
        sandbox_id=sandbox_id,
        backend_type="docker",
        sandbox_image=str(row.sandbox_image),
        status="running",
        snapshot_id=snapshot.snapshot_id,
        snapshot_path=snapshot.snapshot_path,
        network_enabled=1 if spec.get("install_command") else 0,
        command="pipeline",
        started_at=row.started_at,
    )
    db.add(sandbox)
    db.commit()
    db.refresh(sandbox)
    row.sandbox_run_id = int(sandbox.id)
    db.add(row)
    db.commit()

    exec_runner = executor or DockerSandboxExecutor()
    deploy_runner = runner or DockerDeploymentRunner()
    work_dir: str | None = None
    logs: list[dict[str, Any]] = []
    try:
        for step_name in ["install_command", "test_command", "build_command"]:
            command = str(spec.get(step_name) or "").strip()
            if not command:
                continue
            result = exec_runner.run_command(
                snapshot_path=snapshot.snapshot_path,
                sandbox_id=sandbox_id,
                command=command,
                cwd=".",
                sandbox_image=str(row.sandbox_image),
                network_enabled=step_name == "install_command",
                env={str(k): str(v) for k, v in (spec.get("env") or {}).items()},
                timeout_seconds=int(settings.execution_command_timeout_seconds),
                work_dir=work_dir,
            )
            work_dir = result.work_dir
            logs.append(
                {
                    "step": step_name,
                    "command": command,
                    "exit_code": int(result.exit_code),
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "docker_command": result.docker_command,
                }
            )
            sandbox.stdout = _truncate(f"{sandbox.stdout}\n[{step_name}]\n{result.stdout}".strip())
            sandbox.stderr = _truncate(f"{sandbox.stderr}\n[{step_name}]\n{result.stderr}".strip())
            sandbox.working_dir = result.work_dir
            if result.exit_code != 0:
                raise RuntimeError(f"{step_name} failed with code {result.exit_code}")

        final_work_dir = work_dir or snapshot.snapshot_path
        deploy_result = deploy_runner.run(
            job=row,
            workspace=workspace,
            sandbox_run=sandbox,
            work_dir=final_work_dir,
            spec=spec,
        )
        row.status = "succeeded"
        row.deployed_container_id = deploy_result.get("deployed_container_id")
        row.rollback_image_ref = deploy_result.get("rollback_image_ref")
        row.rollback_status = deploy_result.get("rollback_status")
        row.result_json = _safe_dump(
            {
                "snapshot_id": snapshot.snapshot_id,
                "snapshot_digest": snapshot.digest,
                "work_dir": final_work_dir,
                "pipeline_logs": logs,
                "deploy_logs": deploy_result.get("logs") or [],
            }
        )
        _append_logs(row, json.dumps(deploy_result.get("logs") or [], ensure_ascii=False, indent=2))
        sandbox.status = "succeeded"
        sandbox.result_json = row.result_json
    except Exception as exc:
        row.status = "failed"
        row.error_message = str(exc)
        payload = {}
        try:
            payload = json.loads(str(exc))
            if isinstance(payload, dict):
                row.rollback_image_ref = payload.get("rollback_image_ref") or row.rollback_image_ref
                row.rollback_status = payload.get("rollback_status") or row.rollback_status
                _append_logs(row, json.dumps(payload.get("logs") or [], ensure_ascii=False, indent=2))
        except Exception:
            pass
        row.result_json = _safe_dump(
            {
                "snapshot_id": snapshot.snapshot_id,
                "snapshot_digest": snapshot.digest,
                "pipeline_logs": logs,
                "error_payload": payload if isinstance(payload, dict) else {},
            }
        )
        sandbox.status = "failed"
        sandbox.error_message = str(exc)
        sandbox.result_json = row.result_json
    finished_at = datetime.now(timezone.utc)
    row.finished_at = finished_at
    sandbox.finished_at = finished_at
    db.add(row)
    db.add(sandbox)
    db.commit()
    db.refresh(row)
    return row


def retry_deployment_job(
    db: Session,
    *,
    deployment_id: int,
    user_id: int,
    executor: Executor | None = None,
    runner: DeploymentRunner | None = None,
) -> DeploymentJob:
    row = get_deployment_job(db, deployment_id=int(deployment_id), user_id=int(user_id))
    row.status = "pending"
    row.error_message = None
    row.logs_text = ""
    row.deployed_container_id = None
    db.add(row)
    db.commit()
    return run_deployment_job(
        db,
        deployment_id=int(row.id),
        executor=executor,
        runner=runner,
    )


def create_and_run_deployment_job(
    *,
    workspace_id: int,
    user_id: int,
    image_ref: str,
    container_name: str,
    sandbox_image: str | None = None,
    dockerfile_path: str = "Dockerfile",
    build_context_path: str = ".",
    install_command: str | None = None,
    test_command: str | None = None,
    build_command: str | None = None,
    env: dict[str, str] | None = None,
    ports: list[dict[str, Any]] | None = None,
    container_command: str | None = None,
    runtime_context: dict[str, Any] | None = None,
    executor: Executor | None = None,
    runner: DeploymentRunner | None = None,
) -> dict[str, Any]:
    db = SessionLocal()
    try:
        row = create_deployment_job(
            db,
            workspace_id=int(workspace_id),
            user_id=int(user_id),
            image_ref=image_ref,
            container_name=container_name,
            sandbox_image=sandbox_image,
            dockerfile_path=dockerfile_path,
            build_context_path=build_context_path,
            install_command=install_command,
            test_command=test_command,
            build_command=build_command,
            env=env,
            ports=ports,
            container_command=container_command,
            runtime_context=runtime_context,
        )
        row = run_deployment_job(db, deployment_id=int(row.id), executor=executor, runner=runner)
        return _deployment_job_to_payload(row)
    finally:
        db.close()


def deployment_job_payload_for_user(db: Session, *, deployment_id: int, user_id: int) -> dict[str, Any]:
    row = get_deployment_job(db, deployment_id=int(deployment_id), user_id=int(user_id))
    return _deployment_job_to_payload(row)
