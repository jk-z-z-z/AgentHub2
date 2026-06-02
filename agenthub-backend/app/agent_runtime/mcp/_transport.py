from __future__ import annotations

import asyncio
import json
import subprocess
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import AsyncGenerator, Any


@dataclass
class ACPRunnerConfig:
    provider_type: str
    command: str
    cwd: str = "."


class ACPTransport:
    def __init__(self, config: ACPRunnerConfig):
        self._config = config
        self._process: subprocess.Popen[bytes] | None = None
        self._lock = asyncio.Lock()

    async def ensure_started(self) -> None:
        async with self._lock:
            if self._process is not None and self._process.poll() is None:
                return
            self._process = subprocess.Popen(
                self._config.command,
                cwd=self._config.cwd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

    async def send_request(self, payload: dict[str, Any]) -> dict[str, Any]:
        await self.ensure_started()
        if self._process is None or self._process.stdin is None or self._process.stdout is None:
            raise RuntimeError("ACP transport process not started")
        request_bytes = (json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8")
        self._process.stdin.write(request_bytes)
        self._process.stdin.flush()
        loop = asyncio.get_running_loop()
        line_bytes = await loop.run_in_executor(None, self._process.stdout.readline)
        if not line_bytes:
            raise RuntimeError("ACP transport got empty response")
        return json.loads(line_bytes.decode("utf-8"))

    async def close(self) -> None:
        async with self._lock:
            if self._process is not None:
                self._process.terminate()
                try:
                    await asyncio.wait_for(asyncio.to_thread(self._process.wait), timeout=5.0)
                except asyncio.TimeoutError:
                    self._process.kill()
                self._process = None


@asynccontextmanager
async def managed_acp_transport(config: ACPRunnerConfig) -> AsyncGenerator[ACPTransport, None]:
    transport = ACPTransport(config)
    try:
        await transport.ensure_started()
        yield transport
    finally:
        await transport.close()
