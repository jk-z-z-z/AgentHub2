from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx


@dataclass
class Ctx:
    base_url: str
    client: httpx.Client


def _url(ctx: Ctx, path: str) -> str:
    return f"{ctx.base_url}{path}"


def _unwrap(resp: httpx.Response) -> dict | list:
    resp.raise_for_status()
    body = resp.json()
    return body["data"]


def _get(ctx: Ctx, path: str, params: dict | None = None) -> dict | list:
    return _unwrap(ctx.client.get(_url(ctx, path), params=params))


def _post(ctx: Ctx, path: str, payload: dict) -> dict:
    return _unwrap(ctx.client.post(_url(ctx, path), json=payload))


def _put(ctx: Ctx, path: str, payload: dict) -> dict:
    return _unwrap(ctx.client.put(_url(ctx, path), json=payload))


def ensure_admin_user(ctx: Ctx) -> dict:
    users = _get(ctx, "/users")
    for user in users:
        if user.get("email") == "admin@example.com":
            return user
    return _post(
        ctx,
        "/users",
        {
            "email": "admin@example.com",
            "username": "admin",
            "display_name": "管理员",
            "password": "admin123456",
            "role": "admin",
            "status": "active",
            "bio": "seed default admin",
        },
    )


def login_default_admin(ctx: Ctx) -> dict:
    try:
        data = _post(
            ctx,
            "/auth/login",
            {
                "email": "admin@example.com",
                "password": "admin123456",
            },
        )
    except httpx.HTTPStatusError as e:
        if e.response.status_code != 401:
            raise
        ensure_admin_user(ctx)
        data = _post(
            ctx,
            "/auth/login",
            {
                "email": "admin@example.com",
                "password": "admin123456",
            },
        )
    token = data["access_token"]
    ctx.client.headers.update({"Authorization": f"Bearer {token}"})
    return data


def ensure_user(ctx: Ctx, *, email: str, username: str, display_name: str) -> dict:
    users = _get(ctx, "/users")
    for user in users:
        if user.get("email") == email:
            return user
    return _post(
        ctx,
        "/users",
        {
            "email": email,
            "username": username,
            "display_name": display_name,
            "password": "demo123456",
            "role": "user",
            "status": "active",
            "bio": "seed demo user",
        },
    )


def ensure_agent_profile(ctx: Ctx, *, name: str, role: str, soul_md: str) -> dict:
    return ensure_agent_profile_with_payload(
        ctx,
        {
            "name": name,
            "role": role,
            "description": "seeded template profile",
            "soul_md": soul_md,
            "profile_md": "# 工作方式\n- 回答简洁\n- 优先给可执行方案\n- 保持最小改动\n",
            "bootstrap_md": "",
            "tools_json": json.dumps({"preferred": ["file_list", "file_read", "file_write"]}, ensure_ascii=False),
            "skills_json": json.dumps({"notes": ["优先使用技能和工具完成任务"]}, ensure_ascii=False),
            "enabled_files_json": json.dumps(
                {
                    "SOUL.md": True,
                    "PROFILE.md": True,
                    "BOOTSTRAP.md": False,
                    "tools.json": True,
                    "skills.json": True,
                },
                ensure_ascii=False,
            ),
            "model_name": "qwen3.6-plus",
            "temperature": 0.7,
            "top_p": 1.0,
            "max_output_tokens": None,
            "is_active": 1,
        },
    )


def ensure_agent_profile_with_payload(ctx: Ctx, payload: dict) -> dict:
    profiles = _get(ctx, "/agent-profiles")
    for profile in profiles:
        if profile.get("name") == payload.get("name"):
            return profile
    normalized = {
        "name": payload["name"],
        "role": payload["role"],
        "description": payload.get("description"),
        "soul_md": payload.get("soul_md") or "# 身份\n你是一个可靠的智能体。\n",
        "profile_md": payload.get("profile_md") or "",
        "bootstrap_md": payload.get("bootstrap_md") or "",
        "tools_json": payload.get("tools_json") or "{}",
        "skills_json": payload.get("skills_json") or "{}",
        "enabled_files_json": payload.get("enabled_files_json") or "{}",
        "model_name": payload.get("model_name") or "qwen3.6-plus",
        "temperature": payload.get("temperature", 0.7),
        "top_p": payload.get("top_p", 1.0),
        "max_output_tokens": payload.get("max_output_tokens"),
        "is_active": payload.get("is_active", 1),
    }
    return _post(ctx, "/agent-profiles", normalized)


def ensure_agent(ctx: Ctx, *, display_name: str, profile_id: int) -> dict:
    agents = _get(ctx, "/agents")
    for agent in agents:
        if agent.get("display_name") == display_name:
            return agent
    return _post(
        ctx,
        "/agents",
        {
            "display_name": display_name,
            "description": "seeded demo agent",
            "base_url": None,
            "api_key_ref": None,
            "engine_type": "internal_llm",
            "engine_config_json": "{}",
            "status": "active",
            "template_profile_id": profile_id,
            "soul_md": None,
        },
    )


def ensure_group(
    ctx: Ctx,
    *,
    name: str,
    group_type: str,
    users: list[dict],
    agents: list[dict],
    description: str | None = None,
) -> dict:
    groups = _get(ctx, "/groups")
    for group in groups:
        if group.get("name") == name:
            return group
    return _post(
        ctx,
        "/groups",
        {
            "name": name,
            "description": description,
            "type": group_type,
            "users": users,
            "agents": agents,
        },
    )


def list_members(ctx: Ctx, group_id: str | int) -> list[dict]:
    return _get(ctx, "/members", params={"group_id": str(group_id)})


def find_member(members: list[dict], *, kind: str, ref: str) -> dict | None:
    for member in members:
        if member.get("kind") != kind:
            continue
        if kind == "user" and str(member.get("user_ref")) == str(ref):
            return member
        if kind == "agent" and str(member.get("agent_instance_id")) == str(ref):
            return member
    return None


def ensure_personal_agent_chat(ctx: Ctx, *, admin_user: dict, agent: dict) -> tuple[dict, dict]:
    group_name = f"Demo-私聊-{admin_user['username']}-to-{agent['display_name']}"
    group = ensure_group(
        ctx,
        name=group_name,
        group_type="personal",
        users=[],
        agents=[{"agent_id": int(agent["id"]), "display_name": agent["display_name"], "title": "AI"}],
        description="个人会话：自动触发 agent 回复",
    )
    members = list_members(ctx, group["id"])
    admin_member = find_member(members, kind="user", ref=str(admin_user["id"]))
    agent_member = find_member(members, kind="agent", ref=str(agent["id"]))
    if not admin_member or not agent_member:
        raise RuntimeError("Failed to resolve personal chat members")
    return group, admin_member


def ensure_project_group(ctx: Ctx, *, dev_user: dict, agent: dict) -> tuple[dict, dict, dict]:
    group_name = "Demo-项目群聊-AI协作"
    group = ensure_group(
        ctx,
        name=group_name,
        group_type="project",
        users=[{"user_id": int(dev_user["id"]), "display_name": dev_user["display_name"] or dev_user["username"], "title": "开发"}],
        agents=[{"agent_id": int(agent["id"]), "display_name": agent["display_name"], "title": "助手"}],
        description="项目群聊：@agent 才触发",
    )
    members = list_members(ctx, group["id"])
    admin_member = None
    dev_member = None
    agent_member = None
    for member in members:
        if member.get("kind") == "user" and str(member.get("user_ref")) == str(dev_user["id"]):
            dev_member = member
        elif member.get("kind") == "agent" and str(member.get("agent_instance_id")) == str(agent["id"]):
            agent_member = member
        elif member.get("kind") == "user":
            # creator auto member (admin)
            admin_member = member
    if not admin_member:
        # fallback by finding current admin via username/email not available in member; pick first user
        user_members = [m for m in members if m.get("kind") == "user"]
        admin_member = user_members[0] if user_members else None
    if not admin_member or not dev_member or not agent_member:
        raise RuntimeError("Failed to resolve project group members")
    return group, admin_member, agent_member


def ensure_message(
    ctx: Ctx,
    *,
    group_id: int | str,
    sender_member_id: int | str,
    content: str,
    message_type: str = "text",
    metadata_json: str = "{}",
) -> dict:
    existing = _get(ctx, "/messages", params={"group_id": str(group_id), "limit": 100})
    for message in existing:
        if (
            str(message.get("sender_member_id")) == str(sender_member_id)
            and message.get("message_type") == message_type
            and message.get("content") == content
        ):
            return message
    return _post(
        ctx,
        "/messages",
        {
            "group_id": str(group_id),
            "sender_member_id": str(sender_member_id),
            "message_type": message_type,
            "content": content,
            "metadata_json": metadata_json,
        },
    )


def ensure_group_assistant_enabled(ctx: Ctx, *, group_id: int | str, enabled: bool = True) -> dict:
    current = _get(ctx, f"/group-tasks/groups/{group_id}/assistant")
    if bool(int(current.get("enabled", 0))) == bool(enabled):
        return current
    return _put(ctx, f"/group-tasks/groups/{group_id}/assistant", {"enabled": 1 if enabled else 0})


def ensure_group_task_run(
    ctx: Ctx,
    *,
    group_id: int | str,
    creator_member_id: int | str,
    title: str,
    goal_text: str,
    nodes: list[dict[str, Any]],
    trigger_message_id: int | str | None = None,
) -> dict:
    runs = _get(ctx, f"/group-tasks/groups/{group_id}/runs")
    for run in runs:
        if str(run.get("title")) == title:
            return run
    payload: dict[str, Any] = {
        "group_id": str(group_id),
        "creator_member_id": str(creator_member_id),
        "title": title,
        "goal_text": goal_text,
        "nodes": nodes,
    }
    if trigger_message_id not in (None, ""):
        payload["trigger_message_id"] = str(trigger_message_id)
    return _post(ctx, "/group-tasks/runs", payload)


def write_project_code_file(ctx: Ctx, *, group_id: int | str, path: str, content: str) -> dict:
    return _put(ctx, f"/project-code/{group_id}/{path}", {"content": content})


def seed_project_code(ctx: Ctx, *, project_group: dict) -> None:
    group_id = project_group["id"]
    files = {
        "README.md": "# Demo Project\n\n这是为当前 AgentHub 项目群聊准备的演示代码。\n\n- 包含最小前端入口\n- 可用于代码面板/部署面板/任务规划联动展示\n",
        "package.json": json.dumps(
            {
                "name": "agenthub-demo-project",
                "private": True,
                "version": "0.1.0",
                "scripts": {
                    "dev": "vite",
                    "build": "vite build",
                },
                "dependencies": {
                    "vue": "^3.5.0",
                },
                "devDependencies": {
                    "vite": "^5.4.0",
                },
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        "src/main.ts": "const app = document.querySelector('#app')\nif (app) {\n  app.innerHTML = `<main><h1>AgentHub Demo Project</h1><p>Seeded project workspace is ready.</p></main>`\n}\n",
        "index.html": "<!doctype html>\n<html lang=\"zh-CN\">\n  <head>\n    <meta charset=\"UTF-8\" />\n    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />\n    <title>AgentHub Demo</title>\n  </head>\n  <body>\n    <div id=\"app\"></div>\n    <script type=\"module\" src=\"/src/main.ts\"></script>\n  </body>\n</html>\n",
        "Dockerfile": "FROM node:20-alpine\nWORKDIR /app\nCOPY package.json ./\nRUN npm install\nCOPY . .\nEXPOSE 4173\nCMD [\"npm\", \"run\", \"dev\", \"--\", \"--host\", \"0.0.0.0\", \"--port\", \"4173\"]\n",
    }
    for path, content in files.items():
        write_project_code_file(ctx, group_id=group_id, path=path, content=content)


def ensure_agent_tools_and_skills(ctx: Ctx, *, agent_id: int, pool_skill_codes: list[str]) -> None:
    tools_res = _get(ctx, "/tools")
    enabled = {}
    for tool in tools_res:
        code = str(tool.get("code"))
        is_active = int(tool.get("is_active", 0)) == 1
        enabled[code] = bool(is_active and code in {"file_list", "file_read", "file_write"})
    _put(ctx, f"/agents/{agent_id}/tools/toggles", {"enabled": enabled})

    _put(
        ctx,
        f"/agents/{agent_id}/skills/config",
        {
            "enable_agent_local_skills": True,
            "pool_skill_codes": pool_skill_codes,
        },
    )


def write_agent_workspace_files(ctx: Ctx, *, agent_id: int) -> None:
    _put(
        ctx,
        f"/agents/{agent_id}/fs/skills/local-notes.md",
        {"content": "# Local Skill Notes\n\n- 这个文件用于前端体验本地 skills 目录。\n"},
    )
    _put(
        ctx,
        f"/agents/{agent_id}/fs/knowledge/faq.md",
        {"content": "# FAQ\n\n- Q: 这个 agent 有什么能力？\n- A: 文件工具 + Skill 加载 + 群聊/私聊触发。\n"},
    )
    _put(
        ctx,
        f"/agents/{agent_id}/fs/mcps/demo.json",
        {"content": json.dumps({"name": "demo-mcp", "enabled": False}, ensure_ascii=False, indent=2)},
    )


def seed_messages(ctx: Ctx, *, personal_group: dict, personal_sender: dict, project_group: dict, project_sender: dict) -> None:
    ensure_message(
        ctx,
        group_id=personal_group["id"],
        sender_member_id=personal_sender["id"],
        message_type="seed_text",
        content="你好，我是项目助手，有问题可以直接 @ 我。",
        metadata_json="{}",
    )
    mention_message = ensure_message(
        ctx,
        group_id=project_group["id"],
        sender_member_id=project_sender["id"],
        message_type="text",
        content="@助手 帮我列一下今天要做的后端任务。",
        metadata_json=json.dumps({"seed_demo": True}, ensure_ascii=False),
    )
    ensure_message(
        ctx,
        group_id=project_group["id"],
        sender_member_id=project_sender["id"],
        message_type="text",
        content="这条消息不 @ agent，只做群聊消息展示。",
        metadata_json="{}",
    )
    ensure_group_assistant_enabled(ctx, group_id=project_group["id"], enabled=True)
    ensure_group_task_run(
        ctx,
        group_id=project_group["id"],
        creator_member_id=project_sender["id"],
        title="Demo 项目交付任务",
        goal_text="围绕当前演示项目，补齐首页、检查构建命令，并准备部署前检查项。",
        trigger_message_id=mention_message["id"],
        nodes=[
            {
                "node_key": "inspect-current-project",
                "title": "检查当前项目结构",
                "detail": "读取 README、package.json 与 src 目录，确认当前项目入口与脚本。",
                "role_required": "analyst",
                "deps": [],
            },
            {
                "node_key": "refine-homepage-copy",
                "title": "完善首页展示文案",
                "detail": "调整首页标题与说明文案，确保符合演示项目语义。",
                "role_required": "frontend-engineer",
                "deps": ["inspect-current-project"],
            },
            {
                "node_key": "prepare-deployment-checklist",
                "title": "准备部署检查项",
                "detail": "补一份最小部署检查单，确认端口、安装命令和构建命令。",
                "role_required": "backend-engineer",
                "deps": ["inspect-current-project"],
            },
        ],
    )


def get_bootstrap_group(ctx: Ctx, *, agent_id: int | str) -> dict | None:
    return _get(ctx, f"/agents/{agent_id}/bootstrap-group")


def seed_bootstrap_messages(ctx: Ctx, *, bootstrap_group: dict, admin_user: dict, bootstrap_agent: dict) -> None:
    members = list_members(ctx, bootstrap_group["id"])
    admin_member = find_member(members, kind="user", ref=str(admin_user["id"]))
    agent_member = find_member(members, kind="agent", ref=str(bootstrap_agent["id"]))
    if not admin_member or not agent_member:
        raise RuntimeError("Failed to resolve bootstrap members")
    ensure_message(
        ctx,
        group_id=bootstrap_group["id"],
        sender_member_id=admin_member["id"],
        message_type="seed_text",
        content="我想先完成这个智能体的 bootstrap 配置，确认它的工作方式和交付节奏。",
        metadata_json=json.dumps({"seed_demo": True, "group_type": "bootstrap"}, ensure_ascii=False),
    )


def ensure_demo_skill_pool(skill_pool_dir: Path) -> list[str]:
    skill_pool_dir.mkdir(parents=True, exist_ok=True)
    created_codes: list[str] = []
    samples = [
        (
            "code-review-mini",
            "---\nname: 代码审查助手\ndescription: 给出简洁可执行的代码审查建议\n---\n# 使用方式\n1. 先理解需求\n2. 输出风险点\n3. 给出最小改动建议\n",
        ),
        (
            "api-design-mini",
            "---\nname: API 设计助手\ndescription: 面向REST接口给出字段和错误码建议\n---\n# 使用方式\n- 明确资源边界\n- 给出请求/响应示例\n- 检查幂等性与错误码\n",
        ),
        (
            "vue-feature-delivery",
            "---\nname: Vue 功能交付助手\ndescription: 面向 Vue3 + TypeScript + Element Plus 页面开发，强调先读代码、最小改动、完成后自检。\n---\n# 工作方式\n1. 先使用项目代码读取工具理解现有结构。\n2. 优先在 runtime_workspace 起草，再写入 project_code。\n3. 保持组件职责清晰，避免大面积重构。\n4. 完成后执行 type-check 或 build 做最小验证。\n\n# 输出偏好\n- 先列修改文件\n- 再给关键实现说明\n- 标明验证结果\n",
        ),
        (
            "frontend-spec-reader",
            "---\nname: 前端规范阅读助手\ndescription: 在改代码前，先梳理页面结构、接口契约、状态流和视觉约束。\n---\n# 使用方式\n- 先读目录和关键页面文件\n- 识别路由、API 调用、组件边界\n- 总结最小修改方案后再动手\n",
        ),
    ]
    for code, content in samples:
        root = skill_pool_dir / code
        root.mkdir(parents=True, exist_ok=True)
        (root / "SKILL.md").write_text(content, encoding="utf-8")
        created_codes.append(code)
    return created_codes


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed demo data for fast frontend体验")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000/api/v1")
    parser.add_argument("--skill-pool-dir", default="./skill-pool")
    parser.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args()

    pool_codes = ensure_demo_skill_pool(Path(args.skill_pool_dir).expanduser().resolve())

    with httpx.Client(timeout=args.timeout) as client:
        ctx = Ctx(base_url=args.base_url.rstrip("/"), client=client)

        login_result = login_default_admin(ctx)
        admin_user = login_result["user"]
        dev_user = ensure_user(
            ctx,
            email="dev1@example.com",
            username="dev1",
            display_name="开发同学A",
        )

        profile = ensure_agent_profile(
            ctx,
            name="后端开发工程师模版",
            role="backend-engineer",
            soul_md="你是一个严谨的后端工程师助手，回答简洁、可执行、优先给最小改动方案。",
        )
        agent = ensure_agent(
            ctx,
            display_name="后端助手-Alpha",
            profile_id=int(profile["id"]),
        )
        frontend_profile = ensure_agent_profile_with_payload(
            ctx,
            {
                "name": "前端工程助手模版",
                "role": "frontend-engineer",
                "description": "面向 Vue3 + TypeScript + Element Plus 的前端工程助手",
                "soul_md": "# 身份\n你是一个经验扎实的前端工程师，擅长在现有 Vue 项目中做最小可控改动。\n",
                "profile_md": "# 工作方式\n- 先读目录和接口\n- 保持最小修改\n- 完成后至少做一次 type-check 或 build\n",
                "bootstrap_md": "# Bootstrap\n1. 先确认项目结构\n2. 再确认关键页面和 API\n3. 形成最小改动计划\n",
                "enabled_files_json": json.dumps(
                    {
                        "SOUL.md": True,
                        "PROFILE.md": True,
                        "BOOTSTRAP.md": True,
                        "tools.json": True,
                        "skills.json": True,
                    },
                    ensure_ascii=False,
                ),
                "tools_json": json.dumps({"preferred": ["file_list", "file_read", "file_write"]}, ensure_ascii=False),
                "skills_json": json.dumps({"preferred_pool": ["vue-feature-delivery", "frontend-spec-reader"]}, ensure_ascii=False),
                "model_name": "qwen3.6-plus",
                "temperature": 0.3,
                "top_p": 1.0,
                "max_output_tokens": None,
                "is_active": 1,
            },
        )
        frontend_agent = ensure_agent(
            ctx,
            display_name="前端助手-Beta",
            profile_id=int(frontend_profile["id"]),
        )

        ensure_agent_tools_and_skills(ctx, agent_id=int(agent["id"]), pool_skill_codes=pool_codes)
        ensure_agent_tools_and_skills(ctx, agent_id=int(frontend_agent["id"]), pool_skill_codes=pool_codes)
        write_agent_workspace_files(ctx, agent_id=int(agent["id"]))
        write_agent_workspace_files(ctx, agent_id=int(frontend_agent["id"]))

        personal_group, personal_admin_member = ensure_personal_agent_chat(ctx, admin_user=admin_user, agent=agent)
        project_group, project_dev_member, project_agent_member = ensure_project_group(ctx, dev_user=dev_user, agent=agent)
        seed_project_code(ctx, project_group=project_group)

        seed_messages(
            ctx,
            personal_group=personal_group,
            personal_sender=personal_admin_member,
            project_group=project_group,
            project_sender=project_dev_member,
        )
        bootstrap_group = get_bootstrap_group(ctx, agent_id=int(frontend_agent["id"]))
        if bootstrap_group:
            seed_bootstrap_messages(ctx, bootstrap_group=bootstrap_group, admin_user=admin_user, bootstrap_agent=frontend_agent)

        print("✅ Seed completed.")
        print(f"- admin login: admin@example.com / admin123456")
        print(f"- demo user: dev1@example.com / demo123456")
        print(f"- agent: {agent['display_name']} (id={agent['id']})")
        print(f"- bootstrap agent: {frontend_agent['display_name']} (id={frontend_agent['id']})")
        print(f"- personal group: {personal_group['name']} (id={personal_group['id']})")
        print(f"- project group: {project_group['name']} (id={project_group['id']})")
        if bootstrap_group:
            print(f"- bootstrap group: {bootstrap_group['name']} (id={bootstrap_group['id']})")
        print(f"- skill pool dir: {Path(args.skill_pool_dir).expanduser().resolve().as_posix()}")
        print(f"- skill codes: {', '.join(pool_codes)}")


if __name__ == "__main__":
    main()
