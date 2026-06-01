from __future__ import annotations

import os


def get_codex_acp_command() -> list[str]:
    raw = os.getenv("AGENTHUB_ACP_CODEX_COMMAND", "npx -y @zed-industries/codex-acp")
    return raw.split()


def get_claude_code_acp_command() -> list[str]:
    raw = os.getenv("AGENTHUB_ACP_CLAUDE_COMMAND", "python -m claude_code_acp")
    return raw.split()


def command_for_provider(provider_type: str) -> list[str]:
    t = str(provider_type or "").strip().lower()
    if t in {"codex", "codex_cli", "codex-acp"}:
        return get_codex_acp_command()
    if t in {"claude_code", "claude", "claude-acp", "claude-code-acp"}:
        return get_claude_code_acp_command()
    raise ValueError(f"Unknown provider_type: {provider_type}")

