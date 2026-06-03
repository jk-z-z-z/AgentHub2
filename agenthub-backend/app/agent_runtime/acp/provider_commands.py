from __future__ import annotations

from app.core.config import settings


def get_codex_acp_command() -> list[str]:
    raw = settings.acp_codex_command
    return raw.split()


def get_claude_code_acp_command() -> list[str]:
    raw = settings.acp_claude_command
    return raw.split()


def command_for_provider(provider_type: str) -> list[str]:
    t = str(provider_type or "").strip().lower()
    if t in {"codex", "codex_cli", "codex-acp"}:
        return get_codex_acp_command()
    if t in {"claude_code", "claude", "claude-acp", "claude-code-acp"}:
        return get_claude_code_acp_command()
    raise ValueError(f"Unknown provider_type: {provider_type}")
