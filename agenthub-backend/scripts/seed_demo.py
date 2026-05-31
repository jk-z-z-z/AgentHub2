from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

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
    profiles = _get(ctx, "/agent-profiles")
    for profile in profiles:
        if profile.get("name") == name:
            return profile
    return _post(
        ctx,
        "/agent-profiles",
        {
            "name": name,
            "role": role,
            "description": "seeded template profile",
            "soul_md": soul_md,
            "agents_md": "# Agent AGENTS\n- 回答简洁\n- 优先给可执行方案",
            "profile_md": "",
            "bootstrap_md": "",
            "memory_md": "",
            "heartbeat_md": "",
            "enabled_files_json": "{}",
            "model_name": "qwen3.6-plus",
            "temperature": 0.7,
            "top_p": 1.0,
            "max_output_tokens": None,
            "reasoning_effort": None,
            "planning_mode": None,
            "is_active": 1,
        },
    )


def ensure_agent_profile_with_payload(ctx: Ctx, payload: dict) -> dict:
    profiles = _get(ctx, "/agent-profiles")
    for profile in profiles:
        if profile.get("name") == payload.get("name"):
            return profile
    return _post(ctx, "/agent-profiles", payload)


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


def seed_messages(ctx: Ctx, *, personal_group: dict, personal_sender: dict, project_group: dict, project_sender: dict, project_agent_member: dict) -> None:
    ensure_message(
        ctx,
        group_id=personal_group["id"],
        sender_member_id=personal_sender["id"],
        message_type="seed_text",
        content="你好，我是项目助手，有问题可以直接 @ 我。",
        metadata_json="{}",
    )
    ensure_message(
        ctx,
        group_id=project_group["id"],
        sender_member_id=project_sender["id"],
        message_type="seed_text",
        content="@助手 帮我列一下今天要做的后端任务（seed示例，未触发模型调用）",
        metadata_json="{}",
    )
    ensure_message(
        ctx,
        group_id=project_group["id"],
        sender_member_id=project_sender["id"],
        content="这条消息不@agent，只做群聊消息展示。",
        metadata_json="{}",
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
        ensure_agent_profile_with_payload(
            ctx,
            {
                "name": "前端工程助手模版",
                "role": "frontend-engineer",
                "description": "面向 Vue3 + TypeScript + Element Plus 的前端工程助手",
                "soul_md": "# 身份\n你是一个经验扎实的前端工程师，擅长在现有 Vue 项目中做最小可控改动。\n\n# 工作原则\n- 先读代码，再下结论\n- 优先做小步修改，避免无关重构\n- 能验证就验证，至少运行 type-check 或 build\n- 输出要说明改了哪些文件、为什么这么改\n",
                "agents_md": "# 通用执行规则\n- 优先使用项目代码读取工具理解上下文\n- 先在 runtime_workspace 起草，再写入 project_code\n- 修改前确认当前页面路由、API、组件边界\n- 使用 Element Plus 时保持现有设计语言一致\n- 完成后执行 `project_command_run` 做最小验证\n",
                "profile_md": "# 前端助手档案\n- 技术栈：Vue3 / TypeScript / Element Plus\n- 风格：结构清晰、命名语义化、最小修改优先\n",
                "bootstrap_md": "# 首次接手项目时\n1. 读取目录结构\n2. 读取目标页面、相关 API、路由\n3. 输出最小改动计划\n4. 在 workspace 中落稿\n5. 写入正式代码并验证\n",
                "memory_md": "# 长期偏好\n- 不要盲目重构\n- 优先保留现有代码风格\n- 先保证可运行，再考虑抽象\n",
                "heartbeat_md": "",
                "enabled_files_json": json.dumps(
                    {
                        "SOUL.md": True,
                        "AGENTS.md": True,
                        "PROFILE.md": True,
                        "BOOTSTRAP.md": True,
                        "MEMORY.md": True,
                        "HEARTBEAT.md": False,
                    },
                    ensure_ascii=False,
                ),
                "model_name": "qwen3.6-plus",
                "temperature": 0.3,
                "top_p": 1.0,
                "max_output_tokens": None,
                "is_active": 1,
            },
        )
        agent = ensure_agent(
            ctx,
            display_name="后端助手-Alpha",
            profile_id=int(profile["id"]),
        )

        ensure_agent_tools_and_skills(ctx, agent_id=int(agent["id"]), pool_skill_codes=pool_codes)
        write_agent_workspace_files(ctx, agent_id=int(agent["id"]))

        personal_group, personal_admin_member = ensure_personal_agent_chat(ctx, admin_user=admin_user, agent=agent)
        project_group, project_dev_member, project_agent_member = ensure_project_group(ctx, dev_user=dev_user, agent=agent)

        seed_messages(
            ctx,
            personal_group=personal_group,
            personal_sender=personal_admin_member,
            project_group=project_group,
            project_sender=project_dev_member,
            project_agent_member=project_agent_member,
        )

        print("✅ Seed completed.")
        print(f"- admin login: admin@example.com / admin123456")
        print(f"- demo user: dev1@example.com / demo123456")
        print(f"- agent: {agent['display_name']} (id={agent['id']})")
        print(f"- personal group: {personal_group['name']} (id={personal_group['id']})")
        print(f"- project group: {project_group['name']} (id={project_group['id']})")
        print(f"- skill pool dir: {Path(args.skill_pool_dir).expanduser().resolve().as_posix()}")
        print(f"- skill codes: {', '.join(pool_codes)}")


if __name__ == "__main__":
    main()
