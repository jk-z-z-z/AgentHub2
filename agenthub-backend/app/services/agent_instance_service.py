import json

from sqlalchemy.orm import Session

from app.models.agent_instance import AgentInstance
from app.models.agent_profile import AgentProfile
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
        agents_md=(profile.agents_md if profile else None),
    )

    if template_profile_id_int is not None and profile:
        root = agent_dir(int(instance.id))
        enabled = get_profile_enabled_files(profile)
        # Copy enabled profile files into the agent workspace root.
        # Note: agent workspace uses SOUL.md + AGENTS.md as core; other files are still useful
        # for future context assembly but are stored alongside for now.
        for filename in PROFILE_FILE_MAP.keys():
            # If enabled_files_json provided, respect it; otherwise default to copy all.
            if enabled and not bool(enabled.get(filename, False)):
                continue
            content = get_profile_file_content(profile, filename)
            (root / filename).write_text(content or "", encoding="utf-8")

        # Also store a snapshot of toggles for reference (detached from template afterward).
        if enabled:
            (root / "profile.enabled_files.json").write_text(
                json.dumps(enabled, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
    db.commit()
    db.refresh(instance)
    return instance
