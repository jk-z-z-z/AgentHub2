from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from app.models.group import Group
from app.services.deployment_runtime_service import create_and_run_deployment_job
from app.services.preview_runtime_service import create_and_run_preview_job
from app.services.project_code_service import get_project_code_root, write_project_code_file
from app.services.workspace_runtime_service import ensure_workspace_for_project_id


HELLO_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Hello 页面</title>
  <style>
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      display: grid;
      place-items: center;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: linear-gradient(135deg, #f5f7fb 0%, #e6eefc 100%);
      color: #152033;
    }
    .card {
      width: min(560px, calc(100vw - 48px));
      padding: 40px 32px;
      border-radius: 24px;
      background: rgba(255, 255, 255, 0.92);
      border: 1px solid rgba(21, 32, 51, 0.08);
      box-shadow: 0 24px 64px rgba(36, 60, 102, 0.14);
      text-align: center;
    }
    h1 {
      margin: 0;
      font-size: clamp(40px, 8vw, 64px);
      line-height: 1.05;
    }
    p {
      margin: 16px 0 0;
      font-size: 18px;
      color: rgba(21, 32, 51, 0.72);
    }
  </style>
</head>
<body>
  <main class="card">
    <h1>Hello</h1>
    <p>页面已经创建完成，可以直接预览。</p>
  </main>
</body>
</html>
"""


GENERIC_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>项目页面</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f4f7fb;
      --panel: rgba(255, 255, 255, 0.94);
      --line: rgba(15, 23, 42, 0.08);
      --text: #152033;
      --muted: rgba(21, 32, 51, 0.68);
      --accent: #2563eb;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      display: grid;
      place-items: center;
      padding: 32px;
      background:
        radial-gradient(circle at top right, rgba(37, 99, 235, 0.14), transparent 28%),
        radial-gradient(circle at bottom left, rgba(14, 165, 233, 0.12), transparent 24%),
        var(--bg);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: var(--text);
    }
    .panel {
      width: min(760px, 100%);
      padding: 36px;
      border-radius: 24px;
      background: var(--panel);
      border: 1px solid var(--line);
      box-shadow: 0 24px 80px rgba(15, 23, 42, 0.12);
    }
    .eyebrow {
      font-size: 13px;
      font-weight: 700;
      color: var(--accent);
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }
    h1 {
      margin: 14px 0 0;
      font-size: clamp(34px, 6vw, 54px);
      line-height: 1.08;
    }
    p {
      margin: 16px 0 0;
      font-size: 18px;
      line-height: 1.7;
      color: var(--muted);
    }
  </style>
</head>
<body>
  <section class="panel">
    <div class="eyebrow">AgentHub Preview</div>
    <h1>页面已创建</h1>
    <p>这是管家根据对话直接生成的静态页面。你可以继续在群聊里提出修改要求，然后刷新预览查看最新效果。</p>
  </section>
</body>
</html>
"""


@dataclass
class ProjectConversationResult:
    handled: bool
    content: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    applied_files: list[str] = field(default_factory=list)


def _normalize_text(text: str) -> str:
    return str(text or "").strip().lower()


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", _normalize_text(text))
    return slug.strip("-")[:48] or "project"


def _looks_like_page_request(text: str) -> bool:
    keywords = ["纯 html", "html", "静态页", "静态页面", "index.html", "landing", "hello", "打印", "显示", "展示", "改成", "改为", "文字改成", "标题改成"]
    return any(keyword in text for keyword in keywords)


def _looks_like_complex_feature_request(text: str) -> bool:
    keywords = [
        "登录流程",
        "登录界面",
        "登录页面",
        "登录页",
        "注册流程",
        "注册界面",
        "注册页面",
        "注册页",
        "认证",
        "接口",
        "后端",
        "前端",
        "数据库",
        "jwt",
        "pinia",
        "router",
        "路由守卫",
        "go",
        "gin",
        "vue",
        "react",
        "功能",
        "流程",
        "联调",
    ]
    return any(keyword in text for keyword in keywords)


def is_project_feature_delivery_request(text: str) -> bool:
    normalized = _normalize_text(text)
    if not normalized:
        return False
    return _looks_like_complex_feature_request(normalized) and not _looks_like_page_request(normalized)


def _wants_preview(text: str) -> bool:
    if any(keyword in text for keyword in ["不预览", "只改页面", "只写文件", "只修改页面"]):
        return False
    return any(keyword in text for keyword in ["预览", "页面", "html", "效果", "做个"])


def _wants_deploy(text: str) -> bool:
    return any(keyword in text for keyword in ["部署", "上线", "发布"])


def _pick_target_path(text: str) -> str:
    match = re.search(r"([a-zA-Z0-9_./-]+\.(?:html|css|js|json|md|txt|vue))", text)
    if match:
        return match.group(1).lstrip("/")
    return "index.html"


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


def _clean_display_text(text: str) -> str:
    cleaned = str(text or "").strip()
    cleaned = cleaned.strip("`'\"“”‘’「」『』《》【】[]()（）,，.。!！?？:：;；")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _extract_display_text(text: str) -> str | None:
    raw = str(text or "").strip()
    patterns = [
        r"(?:打印|显示|展示|写上|写成|改成|改为|内容改成|文字改成|标题改成)\s*[\"“'`]?(.+?)[\"”'`]?(?:\s*的?\s*(?:页面|网页|html)\b|[，。,！!？?\n]|$)",
        r"(?:做一个|做个)\s*(?:打印|显示|展示)\s*[\"“'`]?(.+?)[\"”'`]?(?:\s*的?\s*(?:页面|网页|html)\b|[，。,！!？?\n]|$)",
        r"(?:做一个|做个)\s*[\"“'`]?(.+?)[\"”'`]?(?:\s*的?\s*(?:页面|网页|html)\b|[，。,！!？?\n]|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, raw, flags=re.IGNORECASE)
        if not match:
            continue
        candidate = _clean_display_text(match.group(1))
        if candidate:
            return candidate
    return None


def _build_text_only_html(display_text: str) -> str:
    safe_text = html.escape(display_text)
    safe_title = html.escape(f"{display_text} 页面")
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{safe_title}</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f3f6fb;
      --card: rgba(255, 255, 255, 0.94);
      --text: #162033;
      --line: rgba(22, 32, 51, 0.08);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      display: grid;
      place-items: center;
      padding: 24px;
      background:
        radial-gradient(circle at top right, rgba(37, 99, 235, 0.14), transparent 28%),
        radial-gradient(circle at bottom left, rgba(14, 165, 233, 0.1), transparent 24%),
        var(--bg);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: var(--text);
    }}
    main {{
      width: min(720px, 100%);
      padding: 56px 36px;
      border-radius: 28px;
      border: 1px solid var(--line);
      background: var(--card);
      box-shadow: 0 24px 80px rgba(15, 23, 42, 0.14);
      text-align: center;
    }}
    h1 {{
      margin: 0;
      font-size: clamp(42px, 10vw, 88px);
      line-height: 1.02;
      letter-spacing: -0.04em;
      word-break: break-word;
    }}
  </style>
</head>
<body>
  <main>
    <h1>{safe_text}</h1>
  </main>
</body>
</html>
"""


def _build_html_content(text: str) -> str:
    display_text = _extract_display_text(text)
    if display_text:
        return _build_text_only_html(display_text)
    if "hello" in text:
        return HELLO_HTML
    return GENERIC_HTML


def _build_static_dockerfile(root) -> tuple[str, str]:
    dist_index = root / "dist" / "index.html"
    if dist_index.exists():
        return "Dockerfile", "FROM nginx:alpine\nCOPY dist/ /usr/share/nginx/html/\n"
    index_path = root / "index.html"
    if index_path.exists():
        return "Dockerfile", "FROM nginx:alpine\nCOPY index.html /usr/share/nginx/html/index.html\n"
    return "Dockerfile", "FROM nginx:alpine\nCOPY . /usr/share/nginx/html/\n"


def _has_static_page_entry(root) -> bool:
    return bool((root / "index.html").exists() or (root / "dist" / "index.html").exists())


def _should_refresh_static_dockerfile(*, dockerfile_path: str, content: str, looks_like_page: bool) -> bool:
    if not looks_like_page:
        return False
    normalized = "\n".join(line.strip() for line in str(content or "").splitlines() if line.strip())
    lowered = normalized.lower()
    if not normalized:
        return True
    if lowered in {"from nginx:alpine", "from nginx"}:
        return True
    if dockerfile_path == "Dockerfile" and "copy index.html /usr/share/nginx/html/index.html" in lowered:
        return False
    if dockerfile_path == "Dockerfile" and "copy dist/ /usr/share/nginx/html/" in lowered:
        return False
    return False


def _default_deploy_port(workspace_id: int) -> int:
    return min(65535, 18000 + int(workspace_id))


def _build_reply_text(
    *,
    changed_files: list[str],
    preview_url: str | None,
    deploy_url: str | None,
    deploy_status: str | None,
    error_message: str | None = None,
) -> str:
    lines: list[str] = []
    if changed_files:
        lines.append("已创建或修改文件：")
        lines.extend([f"- {path}" for path in changed_files])
    elif preview_url and not deploy_status:
        lines.append("未检测到代码写入，本次仅返回现有项目预览地址。")
    if preview_url:
        lines.append(f"本地预览地址：{preview_url}")
    if deploy_status:
        if deploy_url:
            lines.append(f"部署结果：{deploy_status}，地址：{deploy_url}")
        else:
            lines.append(f"部署结果：{deploy_status}")
    if error_message:
        lines.append(f"失败原因：{error_message}")
    return "\n".join(lines).strip()


def _build_complex_request_limit_text() -> str:
    return (
        "我这条对话内直连能力目前只支持简单静态页面的创建、预览和部署，"
        "还不能把“登录流程”这类真实前后端功能自动实现后再直接部署出来。"
        "\n\n"
        "这次我没有继续覆盖成占位页面，也没有把未实现的功能当成已完成。"
        "\n"
        "如果你要的是纯 HTML 登录页，我可以直接生成并预览；"
        "如果你要的是真实登录功能，需要先把对应前后端代码实际写出来，再部署。"
    )


def handle_project_conversation(
    db: Session,
    *,
    group: Group,
    user_id: int,
    input_text: str,
) -> ProjectConversationResult:
    text = str(input_text or "").strip()
    normalized = _normalize_text(text)
    if not normalized:
        return ProjectConversationResult(handled=False)

    wants_deploy = _wants_deploy(normalized)
    looks_like_page = _looks_like_page_request(normalized)
    wants_preview = _wants_preview(normalized)
    complex_feature_request = _looks_like_complex_feature_request(normalized)

    if complex_feature_request and not looks_like_page:
        return ProjectConversationResult(handled=False)

    if not wants_deploy and not looks_like_page and not wants_preview:
        return ProjectConversationResult(handled=False)

    workspace = ensure_workspace_for_project_id(db, project_id=int(group.id))
    changed_files: list[str] = []
    preview_result: dict[str, Any] | None = None
    deploy_result: dict[str, Any] | None = None
    error_message: str | None = None
    requested_port = _extract_requested_port(text)

    try:
        if looks_like_page:
            target_path = _pick_target_path(text)
            write_project_code_file(int(group.id), target_path, _build_html_content(text))
            changed_files.append(target_path)

        if wants_preview and not wants_deploy:
            preview_payload = create_and_run_preview_job(
                workspace_id=int(workspace.id),
                user_id=int(user_id),
                source_path=".",
                host_port=requested_port,
            )
            preview_result = {
                "url": preview_payload.get("url"),
                "workspace_id": int(preview_payload["workspace_id"]),
                "preview_id": int(preview_payload["id"]),
            }
            if str(preview_payload.get("status") or "") == "failed":
                error_message = str(preview_payload.get("error_message") or "预览失败")

        if wants_deploy:
            project_root = get_project_code_root(int(group.id))
            if not looks_like_page and not _has_static_page_entry(project_root):
                return ProjectConversationResult(
                    handled=True,
                    content=_build_complex_request_limit_text(),
                    metadata={},
                    applied_files=[],
                )
            dockerfile_path = project_root / "Dockerfile"
            dockerfile_content = dockerfile_path.read_text(encoding="utf-8") if dockerfile_path.exists() else ""
            if (not dockerfile_path.exists()) or _should_refresh_static_dockerfile(
                dockerfile_path="Dockerfile",
                content=dockerfile_content,
                looks_like_page=looks_like_page,
            ):
                rel_path, dockerfile_content = _build_static_dockerfile(project_root)
                write_project_code_file(int(group.id), rel_path, dockerfile_content)
                changed_files.append(rel_path)
            deploy_payload = create_and_run_deployment_job(
                workspace_id=int(workspace.id),
                user_id=int(user_id),
                image_ref=f"agenthub/{_slugify(str(group.name or 'project'))}:latest",
                container_name=f"agenthub-{_slugify(str(group.name or 'project'))}",
                dockerfile_path="Dockerfile",
                build_context_path=".",
                ports=[{"host_port": requested_port or _default_deploy_port(int(workspace.id)), "container_port": 80, "protocol": "tcp"}],
            )
            deploy_ports = (deploy_payload.get("spec") or {}).get("ports") or []
            deploy_port = None
            if deploy_ports and isinstance(deploy_ports[0], dict):
                try:
                    deploy_port = int(deploy_ports[0].get("host_port"))
                except (TypeError, ValueError):
                    deploy_port = None
            deploy_result = {
                "deployment_id": int(deploy_payload["id"]),
                "url": f"http://127.0.0.1:{deploy_port}" if deploy_port else None,
                "status": str(deploy_payload["status"]),
            }
            if str(deploy_payload.get("status") or "") == "failed":
                error_message = str(deploy_payload.get("error_message") or "部署失败")
    except Exception as exc:
        error_message = str(exc)

    reply_text = _build_reply_text(
        changed_files=changed_files,
        preview_url=preview_result.get("url") if preview_result else None,
        deploy_url=deploy_result.get("url") if deploy_result else None,
        deploy_status=deploy_result.get("status") if deploy_result else None,
        error_message=error_message,
    )
    metadata: dict[str, Any] = {}
    metadata["applied_files"] = [{"path": path, "action": "overwrite"} for path in changed_files]
    if preview_result:
        metadata["preview_result"] = preview_result
    if deploy_result:
        metadata["deploy_result"] = deploy_result
    validation_kind = "none"
    validation_ok = False
    validation_details = "未执行验证"
    if deploy_result:
        validation_kind = "deploy"
        validation_ok = str(deploy_result.get("status") or "") == "succeeded"
        validation_details = str(deploy_result.get("url") or error_message or "部署未返回访问地址")
    elif preview_result:
        validation_kind = "preview"
        validation_ok = bool(preview_result.get("url"))
        validation_details = str(preview_result.get("url") or error_message or "预览未返回访问地址")
    elif changed_files and not error_message:
        validation_details = "本次仅写入文件，未启动预览或部署"
    elif error_message:
        validation_details = error_message
    delivery_status = "failed"
    if changed_files and not error_message:
        if wants_deploy:
            delivery_status = "succeeded" if validation_ok else "partial"
        elif wants_preview:
            delivery_status = "succeeded" if validation_ok else "partial"
        else:
            delivery_status = "succeeded"
    elif changed_files:
        delivery_status = "partial"
    summary = error_message or ("已写入静态页面并生成可访问结果" if validation_ok else validation_details)
    if not changed_files and preview_result and not deploy_result and not error_message:
        summary = "未检测到文件写入，本次仅返回现有项目预览地址"
    metadata["validation_result"] = {
        "kind": validation_kind,
        "ok": validation_ok,
        "details": validation_details,
    }
    metadata["delivery_result"] = {
        "mode": "static_page_shortcut",
        "status": delivery_status,
        "changed_file_count": len(changed_files),
        "validated": validation_ok,
        "summary": summary,
    }
    return ProjectConversationResult(
        handled=True,
        content=reply_text or "已执行完成。",
        metadata=metadata,
        applied_files=list(changed_files),
    )
