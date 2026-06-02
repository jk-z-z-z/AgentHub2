from __future__ import annotations

import json
from dataclasses import dataclass

from app.services._zero_deps_ai_helpers import simple_internal_llm_chat as internal_llm_chat


@dataclass(frozen=True)
class ManagerDecision:
    action: str  # CHAT | ASK_CLARIFY | DRAFT_PLAN | APPLY_PLAN
    reason: str
    reply_text: str
    questions: list[str]
    plan: dict
    tool_calls: list[dict]
    skills: list[str]


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


def _normalize_questions(value) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for x in value:
        s = str(x or "").strip()
        if not s:
            continue
        out.append(s)
    return out[:6]


def _normalize_plan(value) -> dict:
    return value if isinstance(value, dict) else {}


def _normalize_reply_text(value) -> str:
    return str(value or "").strip()


def _normalize_tool_calls(value) -> list[dict]:
    if not isinstance(value, list):
        return []
    out: list[dict] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        tool_code = str(item.get("tool_code") or "").strip()
        args = item.get("args")
        if not tool_code:
            continue
        if args is None:
            args = {}
        if not isinstance(args, dict):
            continue
        out.append({"tool_code": tool_code, "args": args})
        if len(out) >= 6:
            break
    return out


def _normalize_skills(value) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value:
        s = str(item or "").strip().upper()
        if not s:
            continue
        out.append(s)
        if len(out) >= 6:
            break
    allowed = {"DOC_UPDATE"}
    return [x for x in out if x in allowed]


async def compose_reply_after_tool_calls(
    *,
    user_text: str,
    previous_reply_text: str,
    tool_results: list[dict],
) -> str:
    """
    Ask LLM to produce final user-facing reply based on tool call results.
    This keeps user-visible text AI-authored while avoiding 'fake success' when tools fail.
    """
    prompt = (
        "你是群聊项目的管家（Master）。你刚刚请求并执行了一些工具调用。\n"
        "请基于工具调用结果，输出给用户的最终回复文本（自然语言）。\n"
        "- 如果某个工具失败，明确说明失败原因，并给出下一步建议。\n"
        "- 如果工具成功写入/更新了MD文档，说明更新了哪些文件、做了什么修改。\n"
        "- 不要输出JSON，不要markdown代码块。\n\n"
        f"用户消息：{user_text}\n\n"
        f"你原本准备回复：{previous_reply_text}\n\n"
        f"工具调用结果（JSON数组）：{json.dumps(tool_results, ensure_ascii=False)[:6000]}\n"
    )
    reply = await internal_llm_chat(prompt, system_prompt="只输出用户可读的纯文本回复。")
    return str(reply or "").strip()


async def decide_manager_action(
    *,
    user_text: str,
    pending_clarify: dict | None,
    pending_plan: dict | None,
    memory_preview: str,
    docs_preview: str,
    short_term_preview: str,
) -> ManagerDecision:
    prompt = (
        "你是群聊项目的管家（Master）。你需要决定下一步动作：\n"
        "- CHAT：正常聊天答疑，不生成DAG、不要求确认、不落库执行。\n"
        "- ASK_CLARIFY：需要先提出澄清问题（最多6个）。\n"
        "- DRAFT_PLAN：基于已有信息生成DAG规划草案（plan JSON）。\n"
        "- APPLY_PLAN：用户已经同意/要求落库执行当前草案，下一步应落库并开始分配执行。\n"
        "\n"
        "你还可以选择运行技能（skills），让模型在后续步骤里自行判断是否需要更新项目文档：\n"
        "- DOC_UPDATE：用于把项目规范、接口契约、关键决策等沉淀到 README/MEMORY/knowledge/*.md（由模型自行把握写入粒度）。\n"
        "说明：优先使用 skills，而不是在这里直接输出大量 tool_calls。\n"
        "你必须只输出一个JSON对象，不要markdown。\n"
        "schema:\n"
        '{\n'
        '  "action": "CHAT|ASK_CLARIFY|DRAFT_PLAN|APPLY_PLAN",\n'
        '  "reason": "string",\n'
        '  "reply_text": "string",\n'
        '  "skills": ["DOC_UPDATE"],\n'
        '  "tool_calls": [{"tool_code":"manager.project_md","args":{"op":"read","path":"README.md"}}],\n'
        '  "questions": ["..."],\n'
        '  "plan": {"plan_title":"...","goal":"...","nodes":[{"node_key":"N1","title":"...","detail":"...","role_required":null,"deps":[]}]} \n'
        "}\n"
        "规则：\n"
        "1) 如果 pending_plan 存在且用户明确表示“确认/同意/落库/执行/开始”，优先输出 APPLY_PLAN。\n"
        "2) 如果 pending_clarify 存在且用户正在逐条回答问题（有 1)2) 或明显回答结构），输出 DRAFT_PLAN。\n"
        "3) 如果用户明确要求“出DAG/规划图”，但缺少关键约束，输出 ASK_CLARIFY。\n"
        "4) 规划必须贴合具体领域，禁止空泛模板拆分。\n\n"
        "澄清问题要求（非常重要）：\n"
        "- 只问业务/产品/数据/流程相关问题（例如角色、课表来源、匿名规则、问卷题型、统计报表）。\n"
        "- 禁止询问运维部署/数据库实例/表名/Cron/密钥/超时重试/日志中心等工程运行细节，除非用户明确提出部署或定时需求。\n"
        "- reply_text 必须是面向用户的自然语言回复（可以包含问题列表或DAG JSON），不要让程序再拼接模板。\n\n"
        "额外规则（文档沉淀）：\n"
        "- 当用户明确要求“写README/写文档/沉淀接口/输出规范/记录决策”等，建议设置 skills=[\"DOC_UPDATE\"]。\n"
        "- 当用户只是正常聊天答疑，不要写文档。\n\n"
        f"用户消息：{user_text}\n\n"
        f"pending_clarify：{json.dumps(pending_clarify or {}, ensure_ascii=False)}\n\n"
        f"pending_plan_exists：{bool(pending_plan)}\n\n"
        f"长期记忆摘要：{memory_preview[:2000]}\n\n"
        f"项目文档摘要：{docs_preview[:2000]}\n\n"
        f"短期对话摘要：{short_term_preview[:1500]}\n"
    )
    reply = await internal_llm_chat(prompt, system_prompt="只输出严格JSON对象。")
    obj = _extract_json_object(reply) or {}
    action = str(obj.get("action") or "CHAT").strip().upper()
    if action not in {"CHAT", "ASK_CLARIFY", "DRAFT_PLAN", "APPLY_PLAN"}:
        action = "CHAT"
    return ManagerDecision(
        action=action,
        reason=str(obj.get("reason") or "").strip(),
        reply_text=_normalize_reply_text(obj.get("reply_text")),
        tool_calls=_normalize_tool_calls(obj.get("tool_calls")),
        skills=_normalize_skills(obj.get("skills")),
        questions=_normalize_questions(obj.get("questions")),
        plan=_normalize_plan(obj.get("plan")),
    )
