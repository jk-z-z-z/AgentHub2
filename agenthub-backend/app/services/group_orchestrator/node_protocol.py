from __future__ import annotations

import json
from dataclasses import dataclass


RECEIPT_TAG_OPEN = "<agenthub_node_receipt>"
RECEIPT_TAG_CLOSE = "</agenthub_node_receipt>"


@dataclass
class NodeResult:
    node_id: int | None
    node_key: str | None
    status: str
    summary: str
    deliverables: list[dict]
    evidence: list[dict]
    confidence: float | None
    issues: list[str]
    suggested_ops: list[dict]
    invalidates_node_id: int | None = None
    supersedes_node_id: int | None = None


def _extract_json_object(text: str) -> dict | None:
    raw = str(text or "").strip()
    if not raw:
        return None
    if RECEIPT_TAG_OPEN in raw and RECEIPT_TAG_CLOSE in raw:
        start = raw.find(RECEIPT_TAG_OPEN) + len(RECEIPT_TAG_OPEN)
        end = raw.rfind(RECEIPT_TAG_CLOSE)
        if end > start:
            raw = raw[start:end].strip()
    if "```" in raw:
        for block in raw.split("```"):
            b = block.strip()
            if b.startswith("json"):
                b = b[4:].strip()
            if b.startswith("{") and b.endswith("}"):
                try:
                    obj = json.loads(b)
                    if isinstance(obj, dict):
                        return obj
                except Exception:
                    pass
    if raw.startswith("{") and raw.endswith("}"):
        try:
            obj = json.loads(raw)
            return obj if isinstance(obj, dict) else None
        except Exception:
            return None
    start = raw.find("{")
    end = raw.rfind("}")
    if start >= 0 and end > start:
        try:
            obj = json.loads(raw[start : end + 1])
            return obj if isinstance(obj, dict) else None
        except Exception:
            return None
    return None


def parse_node_result(text: str) -> NodeResult:
    obj = _extract_json_object(text) or {}
    status = str(obj.get("status") or "succeeded").strip()
    summary = str(obj.get("summary") or "").strip()
    node_id = obj.get("node_id")
    try:
        node_id = int(node_id) if node_id is not None else None
    except Exception:
        node_id = None
    node_key = str(obj.get("node_key") or "").strip() or None
    deliverables = obj.get("deliverables") if isinstance(obj.get("deliverables"), list) else []
    evidence = obj.get("evidence") if isinstance(obj.get("evidence"), list) else []
    issues = obj.get("issues") if isinstance(obj.get("issues"), list) else []
    suggested_ops = obj.get("suggested_ops") if isinstance(obj.get("suggested_ops"), list) else []
    confidence = obj.get("confidence")
    try:
        confidence = float(confidence) if confidence is not None else None
    except Exception:
        confidence = None
    invalidates = obj.get("invalidates_node_id")
    supersedes = obj.get("supersedes_node_id")
    try:
        invalidates = int(invalidates) if invalidates is not None else None
    except Exception:
        invalidates = None
    try:
        supersedes = int(supersedes) if supersedes is not None else None
    except Exception:
        supersedes = None
    return NodeResult(
        node_id=node_id,
        node_key=node_key,
        status=status,
        summary=summary,
        deliverables=list(deliverables),
        evidence=list(evidence),
        confidence=confidence,
        issues=[str(x) for x in issues if str(x).strip()],
        suggested_ops=list(suggested_ops),
        invalidates_node_id=invalidates,
        supersedes_node_id=supersedes,
    )


def format_receipt_message(*, human_text: str, payload: dict) -> str:
    return (
        f"{human_text}\n\n"
        f"{RECEIPT_TAG_OPEN}{json.dumps(payload, ensure_ascii=False)}{RECEIPT_TAG_CLOSE}"
    )
