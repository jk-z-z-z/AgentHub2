from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def safe_load_json_dict(path: Path, *, default: dict | None = None) -> dict:
    fallback = default or {}
    if not path.exists():
        return fallback
    try:
        raw = json.loads(path.read_text(encoding="utf-8") or "{}")
        return raw if isinstance(raw, dict) else fallback
    except Exception:
        return fallback


def safe_dump_json(path: Path, payload: Any, *, indent: int = 2) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=indent), encoding="utf-8")
