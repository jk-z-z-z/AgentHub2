from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

import acp
from acp.client.connection import ClientSideConnection
from acp.schema import (
    AgentMessageChunk,
    AgentThoughtChunk,
    PermissionOption,
    RequestPermissionResponse,
    TextContentBlock,
    ToolCallUpdate,
    UserMessageChunk,
)


@dataclass
class ACPUpdateChunk:
    kind: str
    text: str
    raw_type: str


class ACPClientCallbacks:
    def __init__(self) -> None:
        self.updates: list[ACPUpdateChunk] = []

    async def session_update(self, session_id: str, update: Any, **kwargs: Any) -> None:
        raw_type = type(update).__name__
        if isinstance(update, (AgentMessageChunk, UserMessageChunk, AgentThoughtChunk)):
            content = getattr(update, "content", None)
            if getattr(content, "type", None) == "text":
                self.updates.append(ACPUpdateChunk(kind=raw_type, text=str(content.text), raw_type=raw_type))
            else:
                self.updates.append(
                    ACPUpdateChunk(kind=raw_type, text=f"[{getattr(content, 'type', 'content')}]", raw_type=raw_type)
                )
            return
        title = getattr(update, "title", None)
        self.updates.append(ACPUpdateChunk(kind=raw_type, text=str(title or ""), raw_type=raw_type))

    async def request_permission(
        self,
        options: list[PermissionOption],
        session_id: str,
        tool_call: ToolCallUpdate,
        **kwargs: Any,
    ) -> RequestPermissionResponse:
        reject = next((o for o in options if str(o.kind).startswith("reject")), None)
        option_id = reject.option_id if reject else (options[-1].option_id if options else "reject")
        return RequestPermissionResponse(option_id=option_id)

    async def write_text_file(self, content: str, path: str, session_id: str, **kwargs: Any):
        from acp.schema import WriteTextFileResponse

        return WriteTextFileResponse(ok=False)

    async def read_text_file(self, path: str, session_id: str, limit: int | None = None, line: int | None = None, **kwargs: Any):
        from acp.schema import ReadTextFileResponse

        return ReadTextFileResponse(content="")

    async def create_terminal(self, command: str, session_id: str, args=None, cwd=None, env=None, output_byte_limit=None, **kwargs: Any):
        from acp.schema import CreateTerminalResponse

        return CreateTerminalResponse(terminal_id="unsupported")

    async def terminal_output(self, session_id: str, terminal_id: str, **kwargs: Any):
        from acp.schema import TerminalOutputResponse

        return TerminalOutputResponse(chunks=[])

    async def release_terminal(self, session_id: str, terminal_id: str, **kwargs: Any):
        from acp.schema import ReleaseTerminalResponse

        return ReleaseTerminalResponse(ok=True)

    async def wait_for_terminal_exit(self, session_id: str, terminal_id: str, **kwargs: Any):
        from acp.schema import WaitForTerminalExitResponse

        return WaitForTerminalExitResponse(exit_code=0)

    async def kill_terminal(self, session_id: str, terminal_id: str, **kwargs: Any):
        from acp.schema import KillTerminalResponse

        return KillTerminalResponse(ok=True)


class ACPStdioAgentClient:
    def __init__(self, *, command: list[str], cwd: str) -> None:
        self.command = list(command)
        self.cwd = str(cwd)
        self._proc: asyncio.subprocess.Process | None = None
        self._conn: ClientSideConnection | None = None
        self._cb = ACPClientCallbacks()
        self._session_id: str | None = None

    @property
    def updates(self) -> list[ACPUpdateChunk]:
        return self._cb.updates

    async def start(self) -> None:
        if self._proc:
            return
        self._proc = await asyncio.create_subprocess_exec(
            *self.command,
            cwd=self.cwd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        assert self._proc.stdin and self._proc.stdout
        self._conn = ClientSideConnection(self._cb, self._proc.stdin, self._proc.stdout, receive_timeout=60.0)
        await self._conn.initialize(protocol_version=acp.PROTOCOL_VERSION)
        sess = await self._conn.new_session(cwd=self.cwd)
        self._session_id = str(sess.session_id)

    async def prompt_text(self, text: str) -> None:
        if not self._conn or not self._session_id:
            raise RuntimeError("ACP client not started")
        await self._conn.prompt([TextContentBlock(text=text, type="text")], session_id=self._session_id)

    def collect_text_output(self) -> str:
        parts: list[str] = []
        for u in self._cb.updates:
            if u.raw_type == "AgentMessageChunk" and u.text:
                parts.append(u.text)
        return "\n".join([p for p in parts if p.strip()]).strip()

    async def close(self) -> None:
        if self._conn and self._session_id:
            try:
                await self._conn.close_session(session_id=self._session_id)
            except Exception:
                pass
        if self._proc:
            try:
                self._proc.terminate()
            except Exception:
                pass
        self._proc = None
        self._conn = None
        self._session_id = None

