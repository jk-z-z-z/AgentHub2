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

from app.common.file_utils import normalize_rel_dir
from app.core.config import settings
from app.db.session import SessionLocal
from app.models.preview_job import PreviewJob
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


def _append_logs(row: PreviewJob, message: str) -> None:
    row.logs_text = "\n".join([part for part in [str(row.logs_text or "").strip(), message.strip()] if part]).strip()


def _preview_job_to_payload(row: PreviewJob) -> dict[str, Any]:
    return {
        "id": int(row.id),
        "workspace_id": int(row.workspace_id),
        "project_id": int(row.project_id),
        "sandbox_run_id": int(row.sandbox_run_id) if row.sandbox_run_id else None,
        "status": str(row.status),
        "container_name": str(row.container_name),
        "container_id": row.container_id,
        "sandbox_image": str(row.sandbox_image),
        "source_path": str(row.source_path),
        "host_port": int(row.host_port),
        "preview_root_path": row.preview_root_path,
        "url": row.url,
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


def _port_is_available(host_port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("127.0.0.1", int(host_port)))
        except OSError:
            return False
    return True


def _pick_host_port(workspace_id: int, preferred: int | None = None) -> int:
    start = int(preferred or (19000 + int(workspace_id)))
    candidate = max(1, start)
    while candidate <= 65535:
        if _port_is_available(candidate):
            return candidate
        candidate += 1
    raise RuntimeError("No available host port for preview")


def _resolve_preview_root(work_dir: str, source_path: str) -> Path:
    root = Path(str(work_dir)).resolve()
    source_rel = normalize_rel_dir(source_path, allow_root=True)
    source_root = root if source_rel == "." else (root / source_rel).resolve()
    if not source_root.exists() or not source_root.is_dir():
        raise RuntimeError(f"Preview source path not found: {source_rel}")
    direct_index = source_root / "index.html"
    dist_index = source_root / "dist" / "index.html"
    if direct_index.exists() and direct_index.is_file():
        return source_root
    if dist_index.exists() and dist_index.is_file():
        return (source_root / "dist").resolve()
    raise RuntimeError("缺少可预览入口文件：需要 index.html 或 dist/index.html")


class PreviewRunner(ABC):
    @abstractmethod
    def run(
        self,
        *,
        job: PreviewJob,
        workspace: Workspace,
        sandbox_run: SandboxRun | None,
        preview_root: str,
        spec: dict[str, Any],
    ) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def stop(self, *, job: PreviewJob) -> dict[str, Any]:
        raise NotImplementedError


class DockerPreviewRunner(PreviewRunner):
    def _ensure_docker(self) -> None:
        if shutil.which("docker"):
            return
        raise RuntimeError("docker CLI is required for preview")

    def _run_host_command(self, command: list[str], *, timeout_seconds: int) -> subprocess.CompletedProcess[str]:
        self._ensure_docker()
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=max(10, int(timeout_seconds)),
        )

    def _remove_existing_container(self, container_name: str) -> subprocess.CompletedProcess[str]:
        return self._run_host_command(
            ["docker", "rm", "-f", container_name],
            timeout_seconds=int(settings.deployment_command_timeout_seconds),
        )

    def run(
        self,
        *,
        job: PreviewJob,
        workspace: Workspace,
        sandbox_run: SandboxRun | None,
        preview_root: str,
        spec: dict[str, Any],
    ) -> dict[str, Any]:
        _ = workspace
        _ = sandbox_run
        _ = spec
        logs: list[dict[str, Any]] = []
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
        run_cmd = [
            "docker",
            "run",
            "-d",
            "--name",
            str(job.container_name),
            "-p",
            f"{int(job.host_port)}:80/tcp",
            "-v",
            f"{Path(preview_root).resolve().as_posix()}:/usr/share/nginx/html:ro",
            "nginx:alpine",
        ]
        run_proc = self._run_host_command(
            run_cmd,
            timeout_seconds=int(settings.deployment_command_timeout_seconds),
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
            raise RuntimeError(
                json.dumps(
                    {
                        "message": f"docker run failed with code {run_proc.returncode}",
                        "logs": logs,
                    },
                    ensure_ascii=False,
                )
            )
        return {
            "logs": logs,
            "container_id": str(run_proc.stdout or "").strip() or None,
            "url": f"http://127.0.0.1:{int(job.host_port)}",
        }

    def stop(self, *, job: PreviewJob) -> dict[str, Any]:
        rm_proc = self._remove_existing_container(str(job.container_name))
        logs = [
            {
                "step": "docker_rm",
                "command": ["docker", "rm", "-f", str(job.container_name)],
                "exit_code": int(rm_proc.returncode),
                "stdout": _truncate(rm_proc.stdout),
                "stderr": _truncate(rm_proc.stderr),
            }
        ]
        if rm_proc.returncode != 0 and "No such container" not in str(rm_proc.stderr or ""):
            raise RuntimeError(
                json.dumps(
                    {
                        "message": f"docker rm failed with code {rm_proc.returncode}",
                        "logs": logs,
                    },
                    ensure_ascii=False,
                )
            )
        return {"logs": logs}


def get_preview_job(db: Session, *, workspace_id: int, user_id: int) -> PreviewJob:
    assert_workspace_access(db, workspace_id=int(workspace_id), user_id=int(user_id))
    row = db.query(PreviewJob).filter(PreviewJob.workspace_id == int(workspace_id)).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Preview job not found")
    return row


def create_or_update_preview_job(
    db: Session,
    *,
    workspace_id: int,
    user_id: int,
    source_path: str = ".",
    sandbox_image: str | None = None,
    install_command: str | None = None,
    build_command: str | None = None,
    env: dict[str, str] | None = None,
    host_port: int | None = None,
) -> PreviewJob:
    workspace = assert_workspace_access(db, workspace_id=int(workspace_id), user_id=int(user_id))
    row = db.query(PreviewJob).filter(PreviewJob.workspace_id == int(workspace.id)).first()
    resolved_port = int(host_port) if host_port else None
    if row is None:
        row = PreviewJob(
            creator_user_id=int(workspace.creator_user_id),
            tenant_id=str(workspace.tenant_id),
            project_id=int(workspace.project_id),
            workspace_id=int(workspace.id),
            requested_by_user_id=int(user_id),
            container_name=f"agenthub-preview-{int(workspace.id)}",
            sandbox_image=str(sandbox_image or settings.docker_sandbox_default_image),
            source_path=normalize_rel_dir(source_path, allow_root=True),
            host_port=_pick_host_port(int(workspace.id), preferred=resolved_port),
            spec_json=_safe_dump({}),
        )
        db.add(row)
        db.commit()
        db.refresh(row)

    row.requested_by_user_id = int(user_id)
    row.sandbox_image = str(sandbox_image or row.sandbox_image or settings.docker_sandbox_default_image)
    row.source_path = normalize_rel_dir(source_path, allow_root=True)
    if resolved_port:
        row.host_port = int(resolved_port)
    elif not int(row.host_port or 0):
        row.host_port = _pick_host_port(int(workspace.id))
    row.spec_json = _safe_dump(
        {
            "install_command": str(install_command or "").strip() or None,
            "build_command": str(build_command or "").strip() or None,
            "env": env or {},
            "host_port": int(row.host_port),
        }
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def run_preview_job(
    db: Session,
    *,
    workspace_id: int,
    executor: Executor | None = None,
    runner: PreviewRunner | None = None,
) -> PreviewJob:
    row = db.query(PreviewJob).filter(PreviewJob.workspace_id == int(workspace_id)).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Preview job not found")
    workspace = get_workspace_by_id(db, workspace_id=int(row.workspace_id))
    if not workspace:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")

    row.status = "running"
    row.error_message = None
    row.logs_text = ""
    row.attempt_count = int(row.attempt_count or 0) + 1
    row.started_at = datetime.now(timezone.utc)
    row.finished_at = None
    sandbox_id = f"sandbox-preview-{row.id}-a{row.attempt_count}"
    row.context_json = _safe_dump(
        build_execution_context(workspace=workspace, user_id=int(row.requested_by_user_id), sandbox_id=sandbox_id)
    )
    db.add(row)
    db.commit()

    spec = _safe_load_dict(row.spec_json)
    snapshot = create_workspace_snapshot_record(db, workspace=workspace, label=f"preview-{row.id}")
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
        command="preview",
        started_at=row.started_at,
    )
    db.add(sandbox)
    db.commit()
    db.refresh(sandbox)
    row.sandbox_run_id = int(sandbox.id)
    db.add(row)
    db.commit()

    exec_runner = executor or DockerSandboxExecutor()
    preview_runner = runner or DockerPreviewRunner()
    work_dir: str | None = None
    logs: list[dict[str, Any]] = []
    try:
        for step_name in ["install_command", "build_command"]:
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
        preview_root = _resolve_preview_root(final_work_dir, str(row.source_path or "."))
        preview_result = preview_runner.run(
            job=row,
            workspace=workspace,
            sandbox_run=sandbox,
            preview_root=preview_root.as_posix(),
            spec=spec,
        )
        row.status = "active"
        row.preview_root_path = preview_root.as_posix()
        row.container_id = preview_result.get("container_id")
        row.url = preview_result.get("url")
        row.result_json = _safe_dump(
            {
                "snapshot_id": snapshot.snapshot_id,
                "snapshot_digest": snapshot.digest,
                "work_dir": final_work_dir,
                "preview_root_path": preview_root.as_posix(),
                "pipeline_logs": logs,
                "preview_logs": preview_result.get("logs") or [],
            }
        )
        _append_logs(row, json.dumps(preview_result.get("logs") or [], ensure_ascii=False, indent=2))
        sandbox.status = "succeeded"
        sandbox.result_json = row.result_json
    except Exception as exc:
        row.status = "failed"
        row.error_message = str(exc)
        payload = {}
        try:
            payload = json.loads(str(exc))
            if isinstance(payload, dict):
                _append_logs(row, json.dumps(payload.get("logs") or [], ensure_ascii=False, indent=2))
        except Exception:
            payload = {}
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


def close_preview_job(
    db: Session,
    *,
    workspace_id: int,
    user_id: int,
    runner: PreviewRunner | None = None,
) -> PreviewJob:
    row = get_preview_job(db, workspace_id=int(workspace_id), user_id=int(user_id))
    preview_runner = runner or DockerPreviewRunner()
    try:
        stop_result = preview_runner.stop(job=row)
        _append_logs(row, json.dumps(stop_result.get("logs") or [], ensure_ascii=False, indent=2))
    except Exception as exc:
        row.error_message = str(exc)
        raise
    row.status = "stopped"
    row.container_id = None
    row.url = None
    row.finished_at = datetime.now(timezone.utc)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def preview_job_payload_for_user(db: Session, *, workspace_id: int, user_id: int) -> dict[str, Any]:
    row = get_preview_job(db, workspace_id=int(workspace_id), user_id=int(user_id))
    return _preview_job_to_payload(row)


def create_and_run_preview_job(
    *,
    workspace_id: int,
    user_id: int,
    source_path: str = ".",
    sandbox_image: str | None = None,
    install_command: str | None = None,
    build_command: str | None = None,
    env: dict[str, str] | None = None,
    host_port: int | None = None,
    executor: Executor | None = None,
    runner: PreviewRunner | None = None,
) -> dict[str, Any]:
    db = SessionLocal()
    try:
        create_or_update_preview_job(
            db,
            workspace_id=int(workspace_id),
            user_id=int(user_id),
            source_path=source_path,
            sandbox_image=sandbox_image,
            install_command=install_command,
            build_command=build_command,
            env=env,
            host_port=host_port,
        )
        row = run_preview_job(db, workspace_id=int(workspace_id), executor=executor, runner=runner)
        return _preview_job_to_payload(row)
    finally:
        db.close()
