from __future__ import annotations

import json
from dataclasses import dataclass

from app.services._zero_deps_ai_helpers import simple_internal_llm_chat as internal_llm_chat


@dataclass(frozen=True)
class DocUpdateSkillResult:
    reply_text: str
    tool_calls: list[dict]


def _extract_json_object(text: str) -> dict | None:
    raw = str(text or "").strip()
    if not raw:
        return None
    if "```" in raw:
        for b in raw.split("```"):
            c = b.strip()
            if c.startswith("json"):
                c = c[4:].strip()
            if c.startswith("{") and c.endswith("}"):
                try:
                    obj = json.loads(c)
                    return obj if isinstance(obj, dict) else None
                except Exception:
                    pass
    if raw.startswith("{") and raw.endswith("}"):
        try:
            obj = json.loads(raw)
            return obj if isinstance(obj, dict) else None
        except Exception:
            return None
    s = raw.find("{")
    e = raw.rfind("}")
    if s >= 0 and e > s:
        try:
            obj = json.loads(raw[s : e + 1])
            return obj if isinstance(obj, dict) else None
        except Exception:
            return None
    return None


def _normalize_tool_calls(value) -> list[dict]:
    if not isinstance(value, list):
        return []
    out: list[dict] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        tool_code = str(item.get("tool_code") or "").strip()
        args = item.get("args")
        if tool_code != "manager.project_md":
            continue
        if args is None:
            args = {}
        if not isinstance(args, dict):
            continue
        op = str(args.get("op") or "").strip()
        path = str(args.get("path") or "").strip()
        if op not in {"read", "write", "list"}:
            continue
        if not path:
            continue
        out.append({"tool_code": tool_code, "args": args})
        if len(out) >= 6:
            break
    return out


async def run_doc_update_skill(
    *,
    user_text: str,
    memory_preview: str,
    docs_preview: str,
    short_term_preview: str,
) -> DocUpdateSkillResult:
    """
    LLM skill that decides *whether* and *how much* to write into project docs.
    It may:
    - read existing docs (README/MEMORY/knowledge/*.md)
    - write/append structured content (API contracts, conventions, decisions, etc.)
    """
    prompt = (
        "你是群聊项目的管家（Master），你正在执行技能 DOC_UPDATE，用于将项目关键内容沉淀为MD文档。\n"
        "你必须自行把握写入粒度：\n"
        "- 只把稳定、可复用、对协作有价值的信息写进文档（例如：项目目标/范围、角色与权限、核心数据模型、接口契约、工作流约定、关键决策记录）。\n"
        "- 不要把临时聊天闲聊、未确认的假设、或过长的过程性内容塞进文档。\n"
        "- 如果当前信息不足以落文档，选择不写，并提示用户需要补充什么。\n"
        "\n"
        "可用工具（只能用这一种）：\n"
        "- manager.project_md: op=read|write|list\n"
        "  - path: README.md | MEMORY.md | knowledge/**.md | runs/**.md\n"
        "  - write 需要 content，mode 可选 overwrite|append\n"
        "\n"
        "只输出一个JSON对象，不要markdown。\n"
        "schema:\n"
        "{\n"
        '  "reply_text": "给用户看的回复（说明写了哪些文档，或为什么不写/需要补充什么）",\n'
        '  "tool_calls": [{"tool_code":"manager.project_md","args":{"op":"read","path":"README.md"}}]\n'
        "}\n\n"
        f"用户消息：{user_text}\n\n"
        f"长期记忆摘要：{memory_preview[:2000]}\n\n"
        f"项目文档摘要：{docs_preview[:2000]}\n\n"
        f"短期对话摘要：{short_term_preview[:1500]}\n"
    )
    reply = await internal_llm_chat(prompt, system_prompt="只输出严格JSON对象。")
    obj = _extract_json_object(reply) or {}
    reply_text = str(obj.get("reply_text") or "").strip()
    tool_calls = _normalize_tool_calls(obj.get("tool_calls"))
    return DocUpdateSkillResult(reply_text=reply_text, tool_calls=tool_calls)

