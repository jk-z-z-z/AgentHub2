from __future__ import annotations

import argparse
from dataclasses import dataclass

import httpx


@dataclass
class Ctx:
    base_url: str
    client: httpx.Client


def _get_all(ctx: Ctx, path: str) -> list[dict]:
    resp = ctx.client.get(f"{ctx.base_url}{path}")
    resp.raise_for_status()
    return resp.json()["data"]


def _post(ctx: Ctx, path: str, payload: dict) -> dict:
    resp = ctx.client.post(f"{ctx.base_url}{path}", json=payload)
    resp.raise_for_status()
    return resp.json()["data"]


def login_default_admin(ctx: Ctx) -> dict:
    return _post(
        ctx,
        "/auth/login",
        {
            "email": "admin@example.com",
            "password": "admin123456",
        },
    )


def ensure_group(ctx: Ctx, name: str) -> dict:
    groups = _get_all(ctx, "/groups")
    for g in groups:
        if g["name"] == name:
            return g
    return _post(ctx, "/groups", {"name": name, "description": "Seeded demo group"})


def ensure_agent_profile(ctx: Ctx, name: str, role: str, system_prompt: str) -> dict:
    profiles = _get_all(ctx, "/agent-profiles")
    for p in profiles:
        if p["name"] == name:
            return p
    return _post(
        ctx,
        "/agent-profiles",
        {
            "name": name,
            "role": role,
            "description": "Seeded demo profile",
            "system_prompt": system_prompt,
            "default_model_json": "{}",
            "planning_mode": None,
            "is_active": 1,
        },
    )


def ensure_agent_instance(ctx: Ctx, group_id: int, profile_id: int, display_name: str) -> dict:
    instances = _get_all(ctx, "/agent-instances")
    for it in instances:
        if it["group_id"] == group_id and it["display_name"] == display_name:
            return it
    return _post(
        ctx,
        "/agent-instances",
        {
            "group_id": group_id,
            "profile_id": profile_id,
            "display_name": display_name,
            "description": "Seeded demo instance",
            "base_url": None,
            "api_key_ref": None,
            "config_json": "{}",
            "status": "active",
        },
    )


def ensure_user_member(ctx: Ctx, group_id: int, display_name: str, user_ref: str) -> dict:
    members = _get_all(ctx, f"/members?group_id={group_id}")
    for m in members:
        if m["kind"] == "user" and m["display_name"] == display_name:
            return m
    return _post(
        ctx,
        "/members/users",
        {
            "group_id": group_id,
            "display_name": display_name,
            "user_ref": user_ref,
            "title": "Backend Engineer",
        },
    )


def ensure_message(ctx: Ctx, group_id: int, sender_member_id: int, content: str) -> dict:
    existing = _get_all(ctx, f"/messages?group_id={group_id}&limit=100")
    for msg in existing:
        if msg["sender_member_id"] == sender_member_id and msg["content"] == content:
            return msg
    return _post(
        ctx,
        "/messages",
        {
            "group_id": group_id,
            "sender_member_id": sender_member_id,
            "message_type": "text",
            "content": content,
            "reply_to_message_id": None,
            "metadata_json": "{}",
        },
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000/api/v1")
    args = parser.parse_args()

    with httpx.Client(timeout=10.0) as client:
        ctx = Ctx(base_url=args.base_url.rstrip("/"), client=client)

        login_result = login_default_admin(ctx)
        admin_user = login_result["user"]

        group = ensure_group(ctx, "AgentHub Demo")
        profile = ensure_agent_profile(
            ctx,
            name="后端开发工程师",
            role="backend-engineer",
            system_prompt="你是一个后端开发工程师，回答要简洁、可执行、可落地。",
        )
        _ = ensure_agent_instance(ctx, group_id=group["id"], profile_id=profile["id"], display_name="后端 Agent")
        user = ensure_user_member(
            ctx,
            group_id=group["id"],
            display_name=admin_user["display_name"] or admin_user["username"],
            user_ref=str(admin_user["id"]),
        )

        ensure_message(ctx, group_id=group["id"], sender_member_id=user["id"], content="大家好，我来测试一下消息落库。")
        ensure_message(ctx, group_id=group["id"], sender_member_id=user["id"], content="下一步我们把前端接到后端真实数据。")


if __name__ == "__main__":
    main()
