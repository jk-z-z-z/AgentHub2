from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from app.agent_runtime import invoke_agent
from app.agent_runtime.tool._executor import execute_builtin_tool
from app.models.agent_instance import AgentInstance
from app.models.group import Group
from app.services.agent_instance_service import create_agent_instance


DELIVERY_AGENT_DESCRIPTION = "__system_project_feature_delivery__"
DELIVERY_AGENT_NAME = "项目交付助手"


@dataclass
class DeliveryExecutionResult:
    text: str
    applied_files: list[dict[str, str]] = field(default_factory=list)
    validation_result: dict[str, Any] = field(default_factory=dict)
    preview_result: dict[str, Any] | None = None
    deploy_result: dict[str, Any] | None = None
    delivery_result: dict[str, Any] = field(default_factory=dict)
    code_diff: dict[str, Any] | None = None

    @property
    def metadata(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "applied_files": self.applied_files,
            "validation_result": self.validation_result,
            "delivery_result": self.delivery_result,
        }
        if self.code_diff:
            payload["code_diff"] = self.code_diff
        if self.preview_result:
            payload["preview_result"] = self.preview_result
        if self.deploy_result:
            payload["deploy_result"] = self.deploy_result
        return payload


def _ensure_delivery_agent(db: Session, *, user_id: int) -> AgentInstance:
    existing = (
        db.query(AgentInstance)
        .filter(
            AgentInstance.creator_user_id == int(user_id),
            AgentInstance.description == DELIVERY_AGENT_DESCRIPTION,
        )
        .order_by(AgentInstance.id.asc())
        .first()
    )
    if existing:
        return existing
    return create_agent_instance(
        db,
        {
            "display_name": DELIVERY_AGENT_NAME,
            "description": DELIVERY_AGENT_DESCRIPTION,
            "base_url": None,
            "api_key_ref": None,
            "engine_type": "agentscope_react",
            "engine_config_json": "{}",
            "status": "active",
            "soul_md": "",
        },
        creator_user_id=int(user_id),
    )


def _normalize_text(text: str) -> str:
    return str(text or "").strip().lower()


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", _normalize_text(text))
    return slug.strip("-")[:48] or "project"


def _wants_deploy(text: str) -> bool:
    return any(keyword in text for keyword in ["部署", "上线", "发布", "deploy"])


def _extract_requested_port(text: str) -> int | None:
    raw = str(text or "")
    match = re.search(r"(?:端口|部署到|预览到|运行到)\s*(\d{2,5})", raw, flags=re.IGNORECASE)
    if not match and any(keyword in raw.lower() for keyword in ["部署", "预览", "运行"]):
        match = re.search(r"到\s*(\d{2,5})", raw, flags=re.IGNORECASE)
    if not match:
        return None
    try:
        value = int(match.group(1))
    except (TypeError, ValueError):
        return None
    if 1 <= value <= 65535:
        return value
    return None


def _wants_plan_file(text: str) -> bool:
    normalized = str(text or "").strip().lower()
    if not normalized:
        return False
    return any(keyword in normalized for keyword in ["计划", "plan", "方案"])


def _suggest_plan_file_path(text: str) -> str:
    raw = str(text or "")
    if "docs/" in raw.lower():
        return "docs/implementation-plan.md"
    return "plan.md"


def _build_delivery_system_prompt(
    *,
    input_text: str,
    wants_deploy: bool,
    requested_port: int | None,
) -> str:
    port_line = (
        f"- 用户指定了端口 `{requested_port}`，所有预览或部署必须使用这个端口；如果端口冲突，直接失败说明。\n"
        if requested_port is not None
        else ""
    )
    plan_line = ""
    if _wants_plan_file(input_text):
        plan_line = (
            f"- 用户要求计划文件时，必须使用 `project_code_write` 把计划真实写入项目共享代码，例如 `{_suggest_plan_file_path(input_text)}`；"
            "不能只在回复里描述计划，也不能只用命令验证一个还没写出的文件。\n"
            "- `/workspace/run/` 是沙箱快照目录，不是交付目录；不要把这里的临时文件当成项目产物，也不要把这里的路径当作最终交付路径。\n"
            "- 如果用户同时要求“计划 + 实现 + 预览/部署”，计划文件只是附加产物，不能代替真实代码修改。\n"
        )
    final_action = "使用 `project_deploy_run` 给出可访问部署地址" if wants_deploy else "使用 `project_preview_run` 给出可访问预览地址"
    return (
        "你是项目交付 agent，目标是把用户要的功能真实写进当前项目共享代码，并只基于真实工具结果交付。\n\n"
        "强制要求：\n"
        "- 先用项目工具查看当前代码结构，再决定改哪些文件。\n"
        "- 需要落盘时，必须使用 `project_code_write`，不能只回复代码片段或教程。\n"
        "- 复杂功能不能退化成占位页，也不能把未落盘的内容说成已完成。\n"
        "- 如果做不到，就明确失败，不要伪造成功。\n"
        "- 如果修改了真实应用代码，优先用 `project_command_run` 做最小验证；不要启动常驻 dev server。\n"
        f"{plan_line}"
        f"{port_line}"
        f"- 本次请求结束前必须 {final_action}。\n"
        "- 最终回复只要简短说明你做了什么，不要输出大段教程。\n"
    )


def _trim_detail(text: str, *, limit: int = 240) -> str:
    value = str(text or "").strip()
    if len(value) <= limit:
        return value
    return value[: max(0, limit - 3)].rstrip() + "..."


def _dedupe_applied_files(items: list[dict[str, str]]) -> list[dict[str, str]]:
    ordered: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in items:
        path = str(item.get("path") or "").strip()
        if not path or path in seen:
            continue
        seen.add(path)
        ordered.append({"path": path, "action": str(item.get("action") or "overwrite")})
    return ordered


def _pick_preview_result(tool_calls: list[dict[str, Any]]) -> dict[str, Any] | None:
    for item in reversed(tool_calls):
        if item.get("tool_code") != "project_preview_run" or not item.get("ok"):
            continue
        result = item.get("result") or {}
        if not isinstance(result, dict):
            continue
        return {
            "url": result.get("url"),
            "workspace_id": int(result["workspace_id"]),
            "preview_id": int(result["preview_id"]),
        }
    return None


def _pick_deploy_result(tool_calls: list[dict[str, Any]]) -> dict[str, Any] | None:
    for item in reversed(tool_calls):
        if item.get("tool_code") != "project_deploy_run" or not item.get("ok"):
            continue
        result = item.get("result") or {}
        args = item.get("args") or {}
        if not isinstance(result, dict):
            continue
        url = result.get("url")
        if not url and isinstance(args, dict):
            ports = args.get("ports")
            if isinstance(ports, list) and ports and isinstance(ports[0], dict):
                try:
                    host_port = int(ports[0].get("host_port"))
                except (TypeError, ValueError):
                    host_port = None
                url = f"http://127.0.0.1:{host_port}" if host_port else None
        return {
            "deployment_id": int(result["deployment_job_id"]),
            "url": url,
            "status": str(result.get("status") or ""),
        }
    return None


def _build_validation_result(
    *,
    tool_calls: list[dict[str, Any]],
    preview_result: dict[str, Any] | None,
    deploy_result: dict[str, Any] | None,
    error_message: str | None,
) -> dict[str, Any]:
    for item in reversed(tool_calls):
        if item.get("tool_code") != "project_command_run" or not item.get("ok"):
            continue
        result = item.get("result") or {}
        if not isinstance(result, dict):
            continue
        ok = bool(result.get("ok"))
        details = f"{result.get('command') or 'project command'} -> exit_code={result.get('exit_code')}"
        stderr = _trim_detail(str(result.get("stderr") or ""))
        if not ok and stderr:
            details = f"{details}; {stderr}"
        return {
            "kind": "command",
            "ok": ok,
            "details": details,
        }
    if deploy_result:
        status = str(deploy_result.get("status") or "")
        return {
            "kind": "deploy",
            "ok": status == "succeeded",
            "details": str(deploy_result.get("url") or error_message or f"部署状态：{status or 'unknown'}"),
        }
    if preview_result:
        return {
            "kind": "preview",
            "ok": bool(preview_result.get("url")),
            "details": str(preview_result.get("url") or error_message or "预览未返回地址"),
        }
    return {
        "kind": "none",
        "ok": False,
        "details": str(error_message or "未检测到验证步骤"),
    }


def _build_delivery_result(
    *,
    wants_deploy: bool,
    applied_files: list[dict[str, str]],
    validation_result: dict[str, Any],
    preview_result: dict[str, Any] | None,
    deploy_result: dict[str, Any] | None,
    error_message: str | None,
) -> dict[str, Any]:
    status = "failed"
    if applied_files:
        if wants_deploy:
            if deploy_result and str(deploy_result.get("status") or "") == "succeeded":
                status = "succeeded" if bool(validation_result.get("ok")) else "partial"
            else:
                status = "partial"
        elif preview_result and preview_result.get("url"):
            status = "succeeded" if bool(validation_result.get("ok")) else "partial"
        else:
            status = "partial"
    summary = error_message or "代码尚未落盘"
    if status == "succeeded":
        summary = f"已写入 {len(applied_files)} 个文件，并生成可访问{'部署' if wants_deploy else '预览'}结果"
    elif status == "partial":
        summary = error_message or "已写入部分文件，但还没有形成完整可访问交付结果"
    return {
        "mode": "project_feature_delivery",
        "status": status,
        "changed_file_count": len(applied_files),
        "validated": bool(validation_result.get("ok")),
        "summary": summary,
    }


def _build_reply_text(
    *,
    applied_files: list[dict[str, str]],
    validation_result: dict[str, Any],
    preview_result: dict[str, Any] | None,
    deploy_result: dict[str, Any] | None,
    delivery_result: dict[str, Any],
    error_message: str | None,
) -> str:
    lines: list[str] = []
    if applied_files:
        lines.append("已写入文件：")
        lines.extend([f"- {item['path']}" for item in applied_files])
    else:
        lines.append("代码尚未落盘。")
    kind = str(validation_result.get("kind") or "none")
    ok = bool(validation_result.get("ok"))
    details = str(validation_result.get("details") or "").strip()
    if kind != "none" or details:
        lines.append(f"验证结果：{'通过' if ok else '失败'}{f'（{details}）' if details else ''}")
    if preview_result and preview_result.get("url"):
        lines.append(f"本地预览地址：{preview_result['url']}")
    if deploy_result:
        deploy_status = str(deploy_result.get("status") or "unknown")
        deploy_url = str(deploy_result.get("url") or "").strip()
        if deploy_url:
            lines.append(f"部署结果：{deploy_status}，地址：{deploy_url}")
        else:
            lines.append(f"部署结果：{deploy_status}")
    if error_message:
        lines.append(f"失败原因：{error_message}")
    if str(delivery_result.get("status") or "") != "succeeded":
        lines.append(f"交付状态：{delivery_result.get('summary')}")
    return "\n".join(lines).strip()


async def execute_project_feature_delivery(
    db: Session,
    *,
    group: Group,
    user_id: int,
    input_text: str,
    short_term_memory: list[dict[str, Any]],
    trace_message_id: int | None = None,
) -> DeliveryExecutionResult:
    text = str(input_text or "").strip()
    wants_deploy = _wants_deploy(text.lower())
    requested_port = _extract_requested_port(text)
    agent = _ensure_delivery_agent(db, user_id=int(user_id))
    runtime_context = {
        "group_type": "project",
        "group_id": int(group.id),
        "project_id": int(group.id),
        "user_id": int(user_id),
        "input_text": text,
    }
    tool_calls: list[dict[str, Any]] = []
    error_message: str | None = None
    slug = _slugify(str(group.name or "project"))

    def tracked_tool_executor(tool_code: str, args: dict[str, Any]) -> dict[str, Any]:
        payload = dict(args or {})
        if tool_code == "project_preview_run":
            payload.setdefault("source_path", ".")
            if requested_port is not None and payload.get("host_port") in (None, ""):
                payload["host_port"] = int(requested_port)
        if tool_code == "project_deploy_run":
            payload.setdefault("image_ref", f"agenthub/{slug}:latest")
            payload.setdefault("container_name", f"agenthub-{slug}")
            payload.setdefault("dockerfile_path", "Dockerfile")
            payload.setdefault("build_context_path", ".")
            ports = payload.get("ports")
            if not isinstance(ports, list):
                ports = []
            normalized_ports = [dict(item) for item in ports if isinstance(item, dict)]
            if requested_port is not None:
                if normalized_ports:
                    normalized_ports[0]["host_port"] = int(requested_port)
                    if normalized_ports[0].get("container_port") in (None, "", 0):
                        normalized_ports[0]["container_port"] = 80
                    normalized_ports[0]["protocol"] = str(normalized_ports[0].get("protocol") or "tcp")
                else:
                    normalized_ports = [{"host_port": int(requested_port), "container_port": 80, "protocol": "tcp"}]
            if normalized_ports:
                payload["ports"] = normalized_ports
        try:
            result = execute_builtin_tool(
                agent_id=int(agent.id),
                tool_code=str(tool_code),
                args=payload,
                runtime_context=runtime_context,
            )
            tool_calls.append({"tool_code": str(tool_code), "args": payload, "result": result, "ok": True})
            return result
        except Exception as exc:
            tool_calls.append({"tool_code": str(tool_code), "args": payload, "error": str(exc), "ok": False})
            raise

    try:
        await invoke_agent(
            db,
            agent_id=int(agent.id),
            short_term_memory=short_term_memory,
            extra_context=runtime_context,
            system_prompt=_build_delivery_system_prompt(
                input_text=text,
                wants_deploy=wants_deploy,
                requested_port=requested_port,
            ),
            trace_message_id=trace_message_id,
            tool_executor=tracked_tool_executor,
        )
    except Exception as exc:
        error_message = str(exc)

    provisional_applied_files = _dedupe_applied_files(
        [
            {
                "path": str((item.get("result") or {}).get("path") or ""),
                "action": "overwrite",
            }
            for item in tool_calls
            if item.get("tool_code") == "project_code_write" and item.get("ok")
        ]
    )
    if provisional_applied_files and not wants_deploy and _pick_preview_result(tool_calls) is None:
        try:
            tracked_tool_executor("project_preview_run", {})
        except Exception as exc:
            if not error_message:
                error_message = str(exc)

    applied_files = _dedupe_applied_files(
        [
            {
                "path": str((item.get("result") or {}).get("path") or ""),
                "action": "overwrite",
            }
            for item in tool_calls
            if item.get("tool_code") == "project_code_write" and item.get("ok")
        ]
    )
    preview_result = _pick_preview_result(tool_calls)
    deploy_result = _pick_deploy_result(tool_calls)
    validation_result = _build_validation_result(
        tool_calls=tool_calls,
        preview_result=preview_result,
        deploy_result=deploy_result,
        error_message=error_message,
    )
    delivery_result = _build_delivery_result(
        wants_deploy=wants_deploy,
        applied_files=applied_files,
        validation_result=validation_result,
        preview_result=preview_result,
        deploy_result=deploy_result,
        error_message=error_message,
    )
    text_out = _build_reply_text(
        applied_files=applied_files,
        validation_result=validation_result,
        preview_result=preview_result,
        deploy_result=deploy_result,
        delivery_result=delivery_result,
        error_message=error_message,
    )
    return DeliveryExecutionResult(
        text=text_out,
        applied_files=applied_files,
        validation_result=validation_result,
        preview_result=preview_result,
        deploy_result=deploy_result,
        delivery_result=delivery_result,
    )
