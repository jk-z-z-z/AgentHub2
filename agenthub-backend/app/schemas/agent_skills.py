from app.schemas.common import ORMBaseModel


class SkillPoolItemOut(ORMBaseModel):
    code: str
    name: str
    description: str
    dir: str


class AgentSkillConfigOut(ORMBaseModel):
    enable_agent_local_skills: bool
    pool_skill_codes: list[str]


class AgentSkillConfigUpdateRequest(ORMBaseModel):
    enable_agent_local_skills: bool = True
    pool_skill_codes: list[str] = []

