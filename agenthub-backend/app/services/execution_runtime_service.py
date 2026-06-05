from __future__ import annotations

import json
import shlex
import shutil
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.common.file_utils import normalize_rel_dir
from app.core.config import settings
from app.db.session import SessionLocal
from app.models.execution_job import ExecutionJob
from app.models.sandbox_run import SandboxRun
from app.models.workspace import Workspace
from app.services.storage_paths import sandbox_run_dir
from app.services.workspace_runtime_service import (
    assert_workspace_access,
    build_execution_context,
    create_workspace_snapshot_record,
    get_workspace_by_id,
)


def _safe_load_dict(raw: str) -> dict[str, Any]:
    try:
        data = json.loads(raw or "{}")
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _safe_dump(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False)


def _truncate(text: str) -> str:
    limit = max(1000, int(settings.command_output_limit_chars))
    return str(text or "")[-limit:]


@dataclass
class CommandExecutionResult:
    exit_code: int
    stdout: str
    stderr: str
    work_dir: str
    docker_command: list[str]


class Executor(ABC):
    @abstractmethod
    def run_command(
        self,
        *,
        snapshot_path: str,
        sandbox_id: str,
        command: str,
        cwd: str,
        sandbox_image: str,
        network_enabled: bool,
        env: dict[str, str],
        timeout_seconds: int,
        work_dir: str | None = None,
    ) -> CommandExecutionResult:
        raise NotImplementedError


class DockerSandboxExecutor(Executor):
    def _ensure_docker(self) -> None:
        if shutil.which("docker"):
            return
        raise RuntimeError("docker CLI is required for sandbox execution")

    def _build_shell_script(self, *, command: str, cwd: str, copy_source: bool) -> str:
        rel_cwd = normalize_rel_dir(cwd, allow_root=True)
        parts: list[str] = []
        if copy_source:
            parts.append("cp -a /workspace/input/. /workspace/run/")
        parts.append("cd /workspace/run")
        if rel_cwd != ".":
            parts.append(f"cd {shlex.quote(rel_cwd)}")
        parts.append(command)
        return " && ".join(parts)

    def build_docker_command(
        self,
        *,
        snapshot_path: str,
        work_dir: str,
        sandbox_image: str,
        command: str,
        cwd: str,
        network_enabled: bool,
        env: dict[str, str],
        copy_source: bool,
    ) -> list[str]:
        cmd = [
            "docker",
            "run",
            "--rm",
            "--init",
            "--cpus",
            str(settings.docker_sandbox_cpu_limit),
            "--memory",
            str(settings.docker_sandbox_memory_limit),
            "-v",
            f"{snapshot_path}:/workspace/input:ro",
            "-v",
            f"{work_dir}:/workspace/run",
            "-w",
            "/workspace/run",
        ]
        if not network_enabled:
            cmd.extend(["--network", "none"])
        for key, value in sorted((env or {}).items()):
            cmd.extend(["-e", f"{key}={value}"])
        cmd.extend(
            [
                str(sandbox_image),
                "sh",
                "-lc",
                self._build_shell_script(command=command, cwd=cwd, copy_source=copy_source),
            ]
        )
        return cmd

    def run_command(
        self,
        *,
        snapshot_path: str,
        sandbox_id: str,
        command: str,
        cwd: str,
        sandbox_image: str,
        network_enabled: bool,
        env: dict[str, str],
        timeout_seconds: int,
        work_dir: str | None = None,
    ) -> CommandExecutionResult:
        self._ensure_docker()
        target_dir = Path(work_dir or (sandbox_run_dir(sandbox_id) / "workdir").as_posix()).resolve()
        target_dir.mkdir(parents=True, exist_ok=True)
        copy_source = not any(target_dir.iterdir())
        docker_command = self.build_docker_command(
            snapshot_path=snapshot_path,
            work_dir=target_dir.as_posix(),
            sandbox_image=sandbox_image,
            command=command,
            cwd=cwd,
            network_enabled=network_enabled,
            env=env,
            copy_source=copy_source,
        )
        proc = subprocess.run(
            docker_command,
            capture_output=True,
            text=True,
            timeout=max(10, int(timeout_seconds)),
        )
        return CommandExecutionResult(
            exit_code=int(proc.returncode),
            stdout=_truncate(proc.stdout),
            stderr=_truncate(proc.stderr),
            work_dir=target_dir.as_posix(),
            docker_command=docker_command,
        )


def _workspace_for_job_access(db: Session, *, workspace_id: int, user_id: int) -> Workspace:
    return assert_workspace_access(db, workspace_id=int(workspace_id), user_id=int(user_id))


def _execution_job_to_payload(row: ExecutionJob) -> dict[str, Any]:
    return {
        "id": int(row.id),
        "workspace_id": int(row.workspace_id),
        "project_id": int(row.project_id),
        "sandbox_run_id": int(row.sandbox_run_id) if row.sandbox_run_id else None,
        "status": str(row.status),
        "job_type": str(row.job_type),
        "command": str(row.command),
        "cwd": str(row.cwd),
        "sandbox_image": str(row.sandbox_image),
        "network_enabled": bool(row.network_enabled),
        "attempt_count": int(row.attempt_count or 0),
        "stdout": str(row.stdout or ""),
        "stderr": str(row.stderr or ""),
        "error_message": row.error_message,
        "spec": _safe_load_dict(row.spec_json),
        "context": _safe_load_dict(row.context_json),
        "result": _safe_load_dict(row.result_json),
        "created_at": row.created_at,
        "updated_at": row.updated_at,
        "started_at": row.started_at,
        "finished_at": row.finished_at,
    }


def get_execution_job(db: Session, *, job_id: int, user_id: int) -> ExecutionJob:
    row = db.query(ExecutionJob).filter(ExecutionJob.id == int(job_id)).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution job not found")
    _workspace_for_job_access(db, workspace_id=int(row.workspace_id), user_id=int(user_id))
    return row


def create_execution_job(
    db: Session,
    *,
    workspace_id: int,
    user_id: int,
    command: str,
    cwd: str = ".",
    sandbox_image: str | None = None,
    network_enabled: bool = False,
    env: dict[str, str] | None = None,
) -> ExecutionJob:
    workspace = _workspace_for_job_access(db, workspace_id=int(workspace_id), user_id=int(user_id))
    row = ExecutionJob(
        creator_user_id=int(workspace.creator_user_id),
        tenant_id=str(workspace.tenant_id),
        project_id=int(workspace.project_id),
        workspace_id=int(workspace.id),
        requested_by_user_id=int(user_id),
        command=str(command),
        cwd=normalize_rel_dir(cwd, allow_root=True),
        sandbox_image=str(sandbox_image or settings.docker_sandbox_default_image),
        network_enabled=1 if network_enabled else 0,
        spec_json=_safe_dump({"env": env or {}}),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def run_execution_job(
    db: Session,
    *,
    job_id: int,
    executor: Executor | None = None,
) -> ExecutionJob:
    row = db.query(ExecutionJob).filter(ExecutionJob.id == int(job_id)).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution job not found")
    workspace = get_workspace_by_id(db, workspace_id=int(row.workspace_id))
    if not workspace:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")

    runner = executor or DockerSandboxExecutor()
    snapshot = create_workspace_snapshot_record(db, workspace=workspace, label=f"execution-{row.id}")
    row.status = "running"
    row.attempt_count = int(row.attempt_count or 0) + 1
    row.started_at = datetime.now(timezone.utc)
    sandbox_id = f"sandbox-exec-{row.id}-a{row.attempt_count}"
    row.context_json = _safe_dump(
        build_execution_context(workspace=workspace, user_id=int(row.requested_by_user_id), sandbox_id=sandbox_id)
    )
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
        network_enabled=int(row.network_enabled or 0),
        command=str(row.command),
        started_at=row.started_at,
    )
    db.add(sandbox)
    db.add(row)
    db.commit()
    db.refresh(sandbox)
    row.sandbox_run_id = int(sandbox.id)
    db.add(row)
    db.commit()

    spec = _safe_load_dict(row.spec_json)
    try:
        result = runner.run_command(
            snapshot_path=snapshot.snapshot_path,
            sandbox_id=sandbox_id,
            command=str(row.command),
            cwd=str(row.cwd or "."),
            sandbox_image=str(row.sandbox_image),
            network_enabled=bool(row.network_enabled),
            env={str(k): str(v) for k, v in (spec.get("env") or {}).items()},
            timeout_seconds=int(settings.execution_command_timeout_seconds),
        )
        row.stdout = result.stdout
        row.stderr = result.stderr
        row.result_json = _safe_dump(
            {
                "exit_code": int(result.exit_code),
                "docker_command": result.docker_command,
                "snapshot_id": snapshot.snapshot_id,
                "snapshot_digest": snapshot.digest,
                "work_dir": result.work_dir,
            }
        )
        row.status = "succeeded" if int(result.exit_code) == 0 else "failed"
        sandbox.status = row.status
        sandbox.stdout = result.stdout
        sandbox.stderr = result.stderr
        sandbox.working_dir = result.work_dir
        sandbox.result_json = row.result_json
        if int(result.exit_code) != 0:
            row.error_message = f"Command exited with code {result.exit_code}"
            sandbox.error_message = row.error_message
    except Exception as exc:
        row.status = "failed"
        row.error_message = str(exc)
        row.stderr = _truncate(f"{row.stderr}\n{exc}".strip())
        row.result_json = _safe_dump(
            {"snapshot_id": snapshot.snapshot_id, "snapshot_digest": snapshot.digest}
        )
        sandbox.status = "failed"
        sandbox.error_message = str(exc)
    finished_at = datetime.now(timezone.utc)
    row.finished_at = finished_at
    sandbox.finished_at = finished_at
    db.add(row)
    db.add(sandbox)
    db.commit()
    db.refresh(row)
    return row


def create_and_run_execution_job(
    *,
    workspace_id: int,
    user_id: int,
    command: str,
    cwd: str = ".",
    sandbox_image: str | None = None,
    network_enabled: bool = False,
    env: dict[str, str] | None = None,
    executor: Executor | None = None,
) -> dict[str, Any]:
    db = SessionLocal()
    try:
        row = create_execution_job(
            db,
            workspace_id=int(workspace_id),
            user_id=int(user_id),
            command=command,
            cwd=cwd,
            sandbox_image=sandbox_image,
            network_enabled=network_enabled,
            env=env,
        )
        row = run_execution_job(db, job_id=int(row.id), executor=executor)
        return _execution_job_to_payload(row)
    finally:
        db.close()


def execution_job_payload_for_user(db: Session, *, job_id: int, user_id: int) -> dict[str, Any]:
    row = get_execution_job(db, job_id=int(job_id), user_id=int(user_id))
    return _execution_job_to_payload(row)
