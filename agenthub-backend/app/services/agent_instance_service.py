import json

from sqlalchemy.orm import Session

from app.models.agent_instance import AgentInstance
from app.models.agent_profile import AgentProfile
from app.models.group import Group
from app.models.member import Member
from app.services.group_service import create_group
from app.services.member_service import create_agent_member, create_user_member
from app.services.agent_profile_files import PROFILE_FILE_MAP, get_profile_enabled_files, get_profile_file_content
from app.services.storage_init_service import ensure_agent_space
from app.services.storage_paths import agent_dir


def list_agent_instances(db: Session, creator_user_id: int) -> list[AgentInstance]:
    return (
        db.query(AgentInstance)
        .filter(AgentInstance.creator_user_id == creator_user_id)
        .order_by(AgentInstance.id.asc())
        .all()
    )


def get_bootstrap_group_for_agent(db: Session, *, agent_instance_id: int, creator_user_id: int) -> Group | None:
    """
    Find an existing bootstrap group for (creator_user_id, agent_instance_id).
    Bootstrap groups are lightweight groups used for instance onboarding.
    """
    # Find bootstrap groups that contain both:
    # - an agent member referencing agent_instance_id
    # - a user member referencing creator_user_id
    group_ids = (
        db.query(Member.group_id)
        .filter(Member.kind == "agent", Member.agent_instance_id == int(agent_instance_id))
        .subquery()
    )
    g = (
        db.query(Group)
        .filter(Group.id.in_(group_ids), Group.type == "bootstrap")
        .order_by(Group.id.desc())
        .first()
    )
    if not g:
        return None
    u = (
        db.query(Member)
        .filter(Member.group_id == int(g.id), Member.kind == "user", Member.user_ref == str(creator_user_id))
        .first()
    )
    return g if u else None


def get_or_create_bootstrap_group(db: Session, *, agent_instance: AgentInstance, creator_user_id: int) -> Group:
    existing = get_bootstrap_group_for_agent(db, agent_instance_id=int(agent_instance.id), creator_user_id=int(creator_user_id))
    if existing:
        return existing
    g = create_group(
        db,
        name=f"bootstrap · {agent_instance.display_name}",
        description=f"bootstrap for agent_instance_id={int(agent_instance.id)}",
        creator_user_id=int(creator_user_id),
        group_type="bootstrap",
    )
    creator_display = f"user:{creator_user_id}"
    create_user_member(db, str(g.id), creator_display, str(creator_user_id), "bootstrap_owner")
    create_agent_member(db, str(g.id), agent_instance.display_name, str(agent_instance.id), "bootstrap_agent")
    return g


def create_agent_instance(db: Session, payload: dict, creator_user_id: int) -> AgentInstance:
    template_profile_id = payload.pop("template_profile_id", None)
    soul_md = payload.pop("soul_md", None)
    template_profile_id_int: int | None = None
    if template_profile_id not in (None, ""):
        try:
            template_profile_id_int = int(template_profile_id)
        except (TypeError, ValueError):
            template_profile_id_int = None
    template_soul = None
    profile = None
    if template_profile_id_int is not None and soul_md is None:
        profile = db.query(AgentProfile).filter(AgentProfile.id == template_profile_id_int).first()
        if profile:
            template_soul = profile.soul_md

    instance = AgentInstance(**payload)
    instance.creator_user_id = creator_user_id
    db.add(instance)
    db.flush()

    ensure_agent_space(
        int(instance.id),
        soul_md=soul_md if soul_md is not None else template_soul,
        profile_md=(profile.profile_md if profile else None),
    )

    if template_profile_id_int is not None and profile:
        root = agent_dir(int(instance.id))
        enabled = get_profile_enabled_files(profile)
        # Copy enabled profile files into the agent workspace root.
        # Note: agent workspace uses SOUL.md + PROFILE.md as core; other files are still useful
        # for future context assembly but are stored alongside for now.
        for filename in PROFILE_FILE_MAP.keys():
            # If enabled_files_json provided, respect it; otherwise default to copy all.
            # Missing keys should default to "enabled" to avoid silently skipping newly-added template files.
            if enabled and filename in enabled and not bool(enabled.get(filename, True)):
                continue
            content = get_profile_file_content(profile, filename)
            (root / filename).write_text(content or "", encoding="utf-8")

        # Also store a snapshot of toggles for reference (detached from template afterward).
        if enabled:
            (root / "profile.enabled_files.json").write_text(
                json.dumps(enabled, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

        # If template provides BOOTSTRAP.md, create a bootstrap group for onboarding.
        if str(profile.bootstrap_md or "").strip():
            try:
                _ = get_or_create_bootstrap_group(db, agent_instance=instance, creator_user_id=int(creator_user_id))
            except Exception:
                # Best-effort; instance creation should still succeed.
                pass
    db.commit()
    db.refresh(instance)
    return instance
