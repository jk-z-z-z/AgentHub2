from fastapi import HTTPException

from app.common.file_utils import normalize_rel_dir
from app.services.execution_runtime_service import DockerSandboxExecutor


def test_normalize_rel_dir_blocks_parent_escape() -> None:
    try:
        normalize_rel_dir("../etc", allow_root=True)
    except HTTPException as exc:
        assert exc.status_code == 400
    else:
        raise AssertionError("expected HTTPException")


def test_docker_command_builder_uses_isolation_flags() -> None:
    executor = DockerSandboxExecutor()
    cmd = executor.build_docker_command(
        snapshot_path="/tmp/snapshot",
        work_dir="/tmp/workdir",
        sandbox_image="node:20-bookworm",
        command="npm test",
        cwd="apps/web",
        network_enabled=False,
        env={"NODE_ENV": "test"},
        copy_source=True,
    )
    assert cmd[:3] == ["docker", "run", "--rm"]
    assert "--network" in cmd
    assert "none" in cmd
    assert "node:20-bookworm" in cmd
    assert any(part == "/tmp/snapshot:/workspace/input:ro" for part in cmd)
