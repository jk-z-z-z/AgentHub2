from __future__ import annotations

from app.services.group_ai_reply.agents.assistant_agent import AssistantRoleAgent
from app.services.group_ai_reply.agents.manager_agent import ManagerRoleAgent
from app.services.group_ai_reply.memory.personal import PersonalMemoryStrategy
from app.services.group_ai_reply.memory.project import ProjectMemoryStrategy


class AgentFactory:
    def build_personal_assistant(self) -> AssistantRoleAgent:
        return AssistantRoleAgent(PersonalMemoryStrategy())

    def build_project_assistant(self) -> AssistantRoleAgent:
        return AssistantRoleAgent(ProjectMemoryStrategy())

    def build_project_manager(self) -> ManagerRoleAgent:
        return ManagerRoleAgent(ProjectMemoryStrategy())
