from __future__ import annotations

import json


def default_acp_provider_specs() -> list[dict]:
    return [
        {
            "name": "Codex (ACP)",
            "provider_type": "codex",
            "transport_type": "stdio",
            "endpoint": None,
            "capability_json": json.dumps({"supports_terminal": True, "supports_fs": True}, ensure_ascii=False),
            "auth_config_json": json.dumps({}, ensure_ascii=False),
            "is_active": 0,
        },
        {
            "name": "Claude Code (ACP)",
            "provider_type": "claude_code",
            "transport_type": "stdio",
            "endpoint": None,
            "capability_json": json.dumps({"supports_terminal": True, "supports_fs": True}, ensure_ascii=False),
            "auth_config_json": json.dumps({}, ensure_ascii=False),
            "is_active": 0,
        },
    ]

