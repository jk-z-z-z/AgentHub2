import { httpDelete, httpGet, httpPost, httpPut, type ApiResult } from './http'
import type {
  Agent,
  AgentCreateBody,
  AgentInstanceCreateRequest,
  AgentProfile,
  AgentProfileCreateBody,
  AgentProfileCreateRequest,
  AgentSkillConfig,
  AgentSkillConfigUpdateRequest,
  AgentToolToggles,
  AgentToolTogglesUpdateRequest,
  FsEntry,
  Id,
  MCP,
  MCPCreateBody,
  MCPCreateRequest,
  SkillPoolItem,
  TextFile,
  TextFileWriteRequest,
  Tool,
  WorkspaceFileContent,
  WorkspaceFileToggles,
} from './models'

export async function apiListAgents(): Promise<ApiResult<Agent[]>> {
  return httpGet<Agent[]>('/api/v1/agents')
}

export async function apiCreateAgent(body: AgentCreateBody): Promise<ApiResult<Agent>> {
  const payload: AgentInstanceCreateRequest = {
    display_name: body.display_name,
    description: body.description ?? null,
    base_url: body.base_url ?? null,
    api_key_ref: body.api_key_ref ?? null,
    engine_type: body.engine_type ?? 'internal_llm',
    engine_config_json: body.engine_config_json ?? '{}',
    status: body.status ?? 'active',
    template_profile_id: body.template_profile_id ?? null,
    soul_md: body.soul_md ?? null,
  }
  return httpPost<Agent, AgentInstanceCreateRequest>('/api/v1/agents', payload)
}

export async function apiGetAgentBootstrapGroup(agentId: string): Promise<ApiResult<Agent | null>> {
  return httpGet<Agent | null>(`/api/v1/agents/${agentId}/bootstrap-group`)
}

export async function apiStartAgentBootstrap(agentId: string): Promise<ApiResult<boolean>> {
  return httpPost<boolean, Record<string, never>>(`/api/v1/agents/${agentId}/bootstrap/start`, {})
}

export async function apiListAgentFs(agentId: string): Promise<ApiResult<FsEntry[]>> {
  return httpGet<FsEntry[]>(`/api/v1/agents/${agentId}/fs`)
}

export async function apiReadAgentFsFile(agentId: string, path: string): Promise<ApiResult<TextFile>> {
  return httpGet<TextFile>(`/api/v1/agents/${agentId}/fs/${path}`)
}

export async function apiWriteAgentFsFile(agentId: string, path: string, content: string): Promise<ApiResult<TextFile>> {
  return httpPut<TextFile, TextFileWriteRequest>(`/api/v1/agents/${agentId}/fs/${path}`, { content })
}

export async function apiDeleteAgentFsFile(agentId: string, path: string): Promise<ApiResult<boolean>> {
  return httpDelete<boolean>(`/api/v1/agents/${agentId}/fs/${path}`)
}

export async function apiListAgentProfiles(): Promise<ApiResult<AgentProfile[]>> {
  return httpGet<AgentProfile[]>('/api/v1/agent-profiles')
}

export async function apiListAgentProfileFiles(profileId: Id): Promise<ApiResult<string[]>> {
  return httpGet<string[]>(`/api/v1/agent-profiles/${profileId}/files`)
}

export async function apiGetAgentProfileFileToggles(profileId: Id): Promise<ApiResult<WorkspaceFileToggles>> {
  return httpGet<WorkspaceFileToggles>(`/api/v1/agent-profiles/${profileId}/file-toggles`)
}

export async function apiUpdateAgentProfileFileToggles(
  profileId: Id,
  toggles: Record<string, boolean>,
): Promise<ApiResult<WorkspaceFileToggles>> {
  return httpPut<WorkspaceFileToggles, Record<string, boolean>>(
    `/api/v1/agent-profiles/${profileId}/file-toggles`,
    toggles,
  )
}

export async function apiCreateAgentProfile(body: AgentProfileCreateBody): Promise<ApiResult<AgentProfile>> {
  const payload: AgentProfileCreateRequest = {
    name: body.name,
    role: body.role,
    description: body.description ?? null,
    soul_md: body.soul_md,
    profile_md: body.profile_md ?? '',
    bootstrap_md: body.bootstrap_md ?? '',
    tools_json: body.tools_json ?? '',
    skills_json: body.skills_json ?? '',
    enabled_files_json: body.enabled_files_json ?? '{}',
    model_name: body.model_name ?? 'gpt-4.1-mini',
    temperature: body.temperature ?? 0.7,
    top_p: body.top_p ?? 1.0,
    max_output_tokens: body.max_output_tokens ?? null,
    is_active: body.is_active ?? 1,
  }
  return httpPost<AgentProfile, AgentProfileCreateRequest>('/api/v1/agent-profiles', payload)
}

export async function apiGetAgentProfileFile(profileId: Id, filename: string): Promise<ApiResult<WorkspaceFileContent>> {
  return httpGet<WorkspaceFileContent>(`/api/v1/agent-profiles/${profileId}/files/${filename}`)
}

export async function apiUpdateAgentProfileFile(
  profileId: Id,
  filename: string,
  content: string,
): Promise<ApiResult<WorkspaceFileContent>> {
  return httpPut<WorkspaceFileContent, { content: string }>(`/api/v1/agent-profiles/${profileId}/files/${filename}`, {
    content,
  })
}

export async function apiListTools(): Promise<ApiResult<Tool[]>> {
  return httpGet<Tool[]>('/api/v1/tools')
}

export async function apiListMcps(): Promise<ApiResult<MCP[]>> {
  return httpGet<MCP[]>('/api/v1/mcps')
}

export async function apiCreateMcp(body: MCPCreateBody): Promise<ApiResult<MCP>> {
  const payload: MCPCreateRequest = {
    name: body.name,
    server_code: body.server_code,
    description: body.description ?? null,
    connection_json: body.connection_json ?? '{}',
    capability_json: body.capability_json ?? '{}',
    is_active: body.is_active ?? 1,
  }
  return httpPost<MCP, MCPCreateRequest>('/api/v1/mcps', payload)
}

export async function apiUpdateMcp(mcpId: Id, body: MCPCreateBody): Promise<ApiResult<MCP>> {
  const payload: MCPCreateRequest = {
    name: body.name,
    server_code: body.server_code,
    description: body.description ?? null,
    connection_json: body.connection_json ?? '{}',
    capability_json: body.capability_json ?? '{}',
    is_active: body.is_active ?? 1,
  }
  return httpPut<MCP, MCPCreateRequest>(`/api/v1/mcps/${mcpId}`, payload)
}

export async function apiDeleteMcp(mcpId: Id): Promise<ApiResult<boolean>> {
  return httpDelete<boolean>(`/api/v1/mcps/${mcpId}`)
}

export async function apiGetAgentToolToggles(agentId: string): Promise<ApiResult<AgentToolToggles>> {
  return httpGet<AgentToolToggles>(`/api/v1/agents/${agentId}/tools/toggles`)
}

export async function apiUpdateAgentToolToggles(
  agentId: string,
  enabled: Record<string, boolean>,
): Promise<ApiResult<AgentToolToggles>> {
  return httpPut<AgentToolToggles, AgentToolTogglesUpdateRequest>(`/api/v1/agents/${agentId}/tools/toggles`, { enabled })
}

export async function apiListAgentSkillPool(): Promise<ApiResult<SkillPoolItem[]>> {
  return httpGet<SkillPoolItem[]>('/api/v1/agents/skill-pool')
}

export async function apiGetAgentSkillConfig(agentId: string): Promise<ApiResult<AgentSkillConfig>> {
  return httpGet<AgentSkillConfig>(`/api/v1/agents/${agentId}/skills/config`)
}

export async function apiUpdateAgentSkillConfig(
  agentId: string,
  body: AgentSkillConfigUpdateRequest,
): Promise<ApiResult<AgentSkillConfig>> {
  return httpPut<AgentSkillConfig, AgentSkillConfigUpdateRequest>(`/api/v1/agents/${agentId}/skills/config`, body)
}

export type {
  Agent,
  AgentCreateBody,
  AgentInstanceCreateRequest,
  AgentProfile,
  AgentProfileCreateBody,
  AgentProfileCreateRequest,
  AgentSkillConfig,
  AgentSkillConfigUpdateRequest,
  AgentToolToggles,
  AgentToolTogglesUpdateRequest,
  FsEntry,
  MCP,
  MCPCreateBody,
  SkillPoolItem,
  TextFile,
  TextFileWriteRequest,
  Tool,
  WorkspaceFileContent,
  WorkspaceFileToggles,
} from './models'
