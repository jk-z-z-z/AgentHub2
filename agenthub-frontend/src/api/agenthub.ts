import { httpDelete, httpGet, httpPost, httpPut, type ApiResult } from './http'

type Id = string | number

export type Group = {
  id: string
  name: string
  description: string | null
  type: 'project' | 'personal'
  created_at: string
  updated_at: string
}

export type Member = {
  id: string
  group_id: string
  kind: 'user' | 'agent' | 'system'
  display_name: string
  user_ref: string | null
  agent_instance_id: string | null
  title: string | null
  created_at: string
  updated_at: string
}

export type Message = {
  id: string
  group_id: string
  sender_member_id: string
  message_type: string
  content: string
  metadata_json: string
  created_at: string
  updated_at: string
}

export type Agent = {
  id: string
  creator_user_id: string
  display_name: string
  description: string | null
  base_url: string | null
  api_key_ref: string | null
  status: string
  created_at: string
  updated_at: string
}

export type AgentProfile = {
  id: string
  creator_user_id: string
  name: string
  role: string
  description: string | null
  soul_md: string
  agents_md: string
  profile_md: string
  bootstrap_md: string
  memory_md: string
  heartbeat_md: string
  enabled_files_json: string
  model_name: string
  temperature: number
  top_p: number
  max_output_tokens: number | null
  reasoning_effort: string | null
  planning_mode: string | null
  is_active: number
  created_at: string
  updated_at: string
}

export type User = {
  id: string
  email: string
  username: string
  display_name: string | null
  role: string
  status: string
  bio: string | null
  created_at: string
  updated_at: string
}

type UserSelfUpdate = {
  display_name: string | null
  bio: string | null
}

export async function apiListGroups(): Promise<ApiResult<Group[]>> {
  return httpGet<Group[]>('/api/v1/groups')
}

export async function apiDeleteGroup(groupId: string): Promise<ApiResult<boolean>> {
  return httpDelete<boolean>(`/api/v1/groups/${groupId}`)
}

export type MemoryCompressorStatus = {
  project_id: number
  last_message_id: number
  pending_message_count: number
  pending_tokens: number
  trigger_tokens: number
  keep_recent_messages: number
  will_trigger: boolean
  state_file: string
  memory_file: string
}

export type MemoryCompressorConfig = {
  enabled: boolean
  trigger_tokens: number
  keep_recent_messages: number
  min_interval_seconds: number
}

type MemoryCompressRunResult = {
  compressed: boolean
  reason?: string | null
  compressed_count?: number | null
  last_message_id?: number | null
}

export type GroupAssistantConfig = {
  group_id: string
  manager_member_id: string | null
  enabled: number
  creator_user_id: string
}

type GroupTaskNodeIn = {
  node_key: string
  title: string
  detail?: string
  role_required?: string | null
  deps?: string[]
}

export type GroupTaskRun = {
  id: string
  group_id: string
  creator_member_id: string
  trigger_message_id: string | null
  title: string
  goal_text: string
  status: string
  dag_json: string
  runtime_dir: string
  created_at: string
  updated_at: string
}

export type GroupTaskNode = {
  id: string
  run_id: string
  node_key: string
  title: string
  detail: string
  role_required: string | null
  deps: string[]
  status: string
  assignee_kind: string
  assignee_member_id: string | null
  output_summary: string
  manager_review_status: string
  created_at: string
  updated_at: string
}

export type GroupTaskEvent = {
  id: string
  run_id: string
  node_id: string | null
  event_type: string
  payload_json: string
  created_at: string
  updated_at: string
}

export async function apiGetGroupAssistantConfig(groupId: string): Promise<ApiResult<GroupAssistantConfig>> {
  return httpGet<GroupAssistantConfig>(`/api/v1/group-tasks/groups/${groupId}/assistant`)
}

export async function apiUpdateGroupAssistantConfig(
  groupId: string,
  body: { enabled: number },
): Promise<ApiResult<GroupAssistantConfig>> {
  return httpPut<GroupAssistantConfig, typeof body>(`/api/v1/group-tasks/groups/${groupId}/assistant`, body)
}

export async function apiCreateGroupTaskRun(body: {
  group_id: Id
  creator_member_id: Id
  title: string
  goal_text: string
  nodes: GroupTaskNodeIn[]
  trigger_message_id?: Id | null
}): Promise<ApiResult<GroupTaskRun>> {
  return httpPost<GroupTaskRun, typeof body>('/api/v1/group-tasks/runs', body)
}

export async function apiListGroupTaskRuns(groupId: string): Promise<ApiResult<GroupTaskRun[]>> {
  return httpGet<GroupTaskRun[]>(`/api/v1/group-tasks/groups/${groupId}/runs`)
}

export async function apiListGroupTaskNodes(runId: string): Promise<ApiResult<GroupTaskNode[]>> {
  return httpGet<GroupTaskNode[]>(`/api/v1/group-tasks/runs/${runId}/nodes`)
}

export async function apiListGroupTaskEvents(runId: string): Promise<ApiResult<GroupTaskEvent[]>> {
  return httpGet<GroupTaskEvent[]>(`/api/v1/group-tasks/runs/${runId}/events`)
}

export async function apiUpdateGroupTaskDag(runId: string, nodes: GroupTaskNodeIn[]): Promise<ApiResult<GroupTaskRun>> {
  return httpPut<GroupTaskRun, { nodes: GroupTaskNodeIn[] }>(`/api/v1/group-tasks/runs/${runId}/dag`, { nodes })
}

export async function apiClaimGroupTaskNode(nodeId: string, memberId: string): Promise<ApiResult<GroupTaskNode>> {
  return httpPost<GroupTaskNode, { member_id: Id }>(`/api/v1/group-tasks/nodes/${nodeId}/claim`, { member_id: memberId })
}

export async function apiCompleteGroupTaskNode(nodeId: string, outputSummary: string): Promise<ApiResult<GroupTaskNode>> {
  return httpPost<GroupTaskNode, { output_summary: string }>(`/api/v1/group-tasks/nodes/${nodeId}/complete`, {
    output_summary: outputSummary,
  })
}

export async function apiReviewGroupTaskNode(
  nodeId: string,
  body: { manager_review_status: 'approved' | 'rework'; note?: string },
): Promise<ApiResult<GroupTaskNode>> {
  return httpPost<GroupTaskNode, { manager_review_status: 'approved' | 'rework'; note: string }>(
    `/api/v1/group-tasks/nodes/${nodeId}/review`,
    { manager_review_status: body.manager_review_status, note: body.note || '' },
  )
}

export async function apiBlockGroupTaskRoleBranch(runId: string, roleRequired: string, reason: string): Promise<ApiResult<number>> {
  return httpPost<number, { reason: string }>(
    `/api/v1/group-tasks/runs/${runId}/branches/${encodeURIComponent(roleRequired)}/block`,
    { reason },
  )
}

export async function apiUnblockGroupTaskRoleBranch(runId: string, roleRequired: string, reason: string): Promise<ApiResult<number>> {
  return httpPost<number, { reason: string }>(
    `/api/v1/group-tasks/runs/${runId}/branches/${encodeURIComponent(roleRequired)}/unblock`,
    { reason },
  )
}

export async function apiGetGroupMemoryCompressorStatus(groupId: string): Promise<ApiResult<MemoryCompressorStatus>> {
  return httpGet<MemoryCompressorStatus>(`/api/v1/groups/${groupId}/memory/compressor-status`)
}

export async function apiGetGroupMemoryCompressorConfig(groupId: string): Promise<ApiResult<MemoryCompressorConfig>> {
  return httpGet<MemoryCompressorConfig>(`/api/v1/groups/${groupId}/memory/compressor-config`)
}

export async function apiUpdateGroupMemoryCompressorConfig(
  groupId: string,
  body: MemoryCompressorConfig,
): Promise<ApiResult<MemoryCompressorConfig>> {
  return httpPut<MemoryCompressorConfig, MemoryCompressorConfig>(`/api/v1/groups/${groupId}/memory/compressor-config`, body)
}

export async function apiRunGroupMemoryCompress(groupId: string): Promise<ApiResult<MemoryCompressRunResult>> {
  return httpPost<MemoryCompressRunResult, Record<string, never>>(`/api/v1/groups/${groupId}/memory/compress`, {})
}

export async function apiListMembers(groupId: string): Promise<ApiResult<Member[]>> {
  return httpGet<Member[]>('/api/v1/members', { group_id: groupId })
}

export async function apiAddUserMember(body: {
  group_id: string
  display_name: string
  user_ref: string
  title?: string | null
}): Promise<ApiResult<Member>> {
  return httpPost<Member, typeof body>('/api/v1/members/users', { title: null, ...body })
}

export async function apiAddAgentMember(body: {
  group_id: string
  display_name: string
  agent_instance_id: string
  title?: string | null
}): Promise<ApiResult<Member>> {
  return httpPost<Member, typeof body>('/api/v1/members/agents', { title: null, ...body })
}

export async function apiDeleteMember(memberId: string): Promise<ApiResult<boolean>> {
  return httpDelete<boolean>(`/api/v1/members/${memberId}`)
}

export async function apiListMessages(groupId: string, cursor?: string, limit: number = 50): Promise<ApiResult<Message[]>> {
  return httpGet<Message[]>('/api/v1/messages', { group_id: groupId, cursor, limit })
}

export async function apiCreateMessage(body: {
  group_id: string
  sender_member_id: string
  message_type: string
  content: string
  metadata_json: string
}): Promise<ApiResult<Message>> {
  return httpPost<Message, typeof body>('/api/v1/messages', body)
}

export async function apiListAgents(): Promise<ApiResult<Agent[]>> {
  return httpGet<Agent[]>('/api/v1/agents')
}

export async function apiCreateGroup(body: {
  name: string
  description: string | null
  type: 'project' | 'personal'
  users: Array<{ user_id: Id; display_name: string; title?: string | null }>
  agents: Array<{ agent_id: Id; display_name: string; title?: string | null }>
}): Promise<ApiResult<Group>> {
  return httpPost<Group, typeof body>('/api/v1/groups', body)
}

export async function apiCreateAgent(body: {
  display_name: string
  description: string | null
  base_url?: string | null
  api_key_ref?: string | null
  status?: string
  template_profile_id?: Id | null
  soul_md?: string | null
}): Promise<ApiResult<Agent>> {
  return httpPost<Agent, typeof body>('/api/v1/agents', {
    base_url: null,
    api_key_ref: null,
    status: 'active',
    template_profile_id: null,
    soul_md: null,
    ...body,
  })
}

export type FsEntry = {
  path: string
  is_dir: boolean
  size: number
}

export type ProjectCodeEntry = FsEntry

export async function apiListAgentFs(agentId: string): Promise<ApiResult<FsEntry[]>> {
  return httpGet<FsEntry[]>(`/api/v1/agents/${agentId}/fs`)
}

export async function apiReadAgentFsFile(agentId: string, path: string): Promise<ApiResult<{ path: string; content: string }>> {
  return httpGet<{ path: string; content: string }>(`/api/v1/agents/${agentId}/fs/${path}`)
}

export async function apiWriteAgentFsFile(agentId: string, path: string, content: string): Promise<ApiResult<{ path: string; content: string }>> {
  return httpPut<{ path: string; content: string }, { content: string }>(`/api/v1/agents/${agentId}/fs/${path}`, { content })
}

export async function apiDeleteAgentFsFile(agentId: string, path: string): Promise<ApiResult<boolean>> {
  return httpDelete<boolean>(`/api/v1/agents/${agentId}/fs/${path}`)
}

export async function apiListProjectCode(groupId: string): Promise<ApiResult<ProjectCodeEntry[]>> {
  return httpGet<ProjectCodeEntry[]>(`/api/v1/project-code/${groupId}`)
}

export async function apiReadProjectCodeFile(groupId: string, path: string): Promise<ApiResult<{ path: string; content: string }>> {
  return httpGet<{ path: string; content: string }>(`/api/v1/project-code/${groupId}/${path}`)
}

export async function apiListAgentProfiles(): Promise<ApiResult<AgentProfile[]>> {
  return httpGet<AgentProfile[]>('/api/v1/agent-profiles')
}

export async function apiCreateAgentProfile(body: {
  name: string
  role: string
  description?: string | null
  soul_md: string
  agents_md?: string
  profile_md?: string
  bootstrap_md?: string
  memory_md?: string
  heartbeat_md?: string
  enabled_files_json?: string
  model_name?: string
  temperature?: number
  top_p?: number
  max_output_tokens?: number | null
  reasoning_effort?: string | null
  planning_mode?: string | null
  is_active?: number
}): Promise<ApiResult<AgentProfile>> {
  return httpPost<AgentProfile, typeof body>('/api/v1/agent-profiles', {
    agents_md: '',
    profile_md: '',
    bootstrap_md: '',
    memory_md: '',
    heartbeat_md: '',
    enabled_files_json: '{}',
    model_name: 'gpt-4.1-mini',
    temperature: 0.7,
    top_p: 1.0,
    max_output_tokens: null,
    reasoning_effort: null,
    planning_mode: null,
    is_active: 1,
    ...body,
  })
}

export async function apiGetAgentProfileFile(profileId: string, filename: string): Promise<ApiResult<{ name: string; content: string }>> {
  return httpGet<{ name: string; content: string }>(`/api/v1/agent-profiles/${profileId}/files/${filename}`)
}

export async function apiUpdateAgentProfileFile(profileId: string, filename: string, content: string): Promise<ApiResult<{ name: string; content: string }>> {
  return httpPut<{ name: string; content: string }, { content: string }>(`/api/v1/agent-profiles/${profileId}/files/${filename}`, { content })
}

export type Tool = {
  id: string
  name: string
  code: string
  description: string | null
  source_type: string
  schema_json: string
  is_active: number
  created_at: string
  updated_at: string
}

export type MCP = {
  id: string
  name: string
  server_code: string
  description: string | null
  connection_json: string
  capability_json: string
  is_active: number
  created_at: string
  updated_at: string
}

export async function apiListTools(): Promise<ApiResult<Tool[]>> {
  return httpGet<Tool[]>('/api/v1/tools')
}

export async function apiListMcps(): Promise<ApiResult<MCP[]>> {
  return httpGet<MCP[]>('/api/v1/mcps')
}

export async function apiCreateMcp(body: {
  name: string
  server_code: string
  description?: string | null
  connection_json?: string
  capability_json?: string
  is_active?: number
}): Promise<ApiResult<MCP>> {
  return httpPost<MCP, typeof body>('/api/v1/mcps', {
    description: null,
    connection_json: '{}',
    capability_json: '{}',
    is_active: 1,
    ...body,
  })
}

export async function apiUpdateMcp(mcpId: Id, body: {
  name: string
  server_code: string
  description?: string | null
  connection_json?: string
  capability_json?: string
  is_active?: number
}): Promise<ApiResult<MCP>> {
  return httpPut<MCP, typeof body>(`/api/v1/mcps/${mcpId}`, {
    description: null,
    connection_json: '{}',
    capability_json: '{}',
    is_active: 1,
    ...body,
  })
}

export async function apiDeleteMcp(mcpId: Id): Promise<ApiResult<boolean>> {
  return httpDelete<boolean>(`/api/v1/mcps/${mcpId}`)
}

export async function apiGetAgentToolToggles(agentId: string): Promise<ApiResult<{ enabled: Record<string, boolean> }>> {
  return httpGet<{ enabled: Record<string, boolean> }>(`/api/v1/agents/${agentId}/tools/toggles`)
}

export async function apiUpdateAgentToolToggles(
  agentId: string,
  enabled: Record<string, boolean>,
): Promise<ApiResult<{ enabled: Record<string, boolean> }>> {
  return httpPut<{ enabled: Record<string, boolean> }, { enabled: Record<string, boolean> }>(
    `/api/v1/agents/${agentId}/tools/toggles`,
    { enabled },
  )
}

export type SkillPoolItem = {
  code: string
  name: string
  description: string
  dir: string
}

type AgentSkillConfig = {
  enable_agent_local_skills: boolean
  pool_skill_codes: string[]
}

export async function apiListAgentSkillPool(): Promise<ApiResult<SkillPoolItem[]>> {
  return httpGet<SkillPoolItem[]>('/api/v1/agents/skill-pool')
}

export async function apiGetAgentSkillConfig(agentId: string): Promise<ApiResult<AgentSkillConfig>> {
  return httpGet<AgentSkillConfig>(`/api/v1/agents/${agentId}/skills/config`)
}

export async function apiUpdateAgentSkillConfig(
  agentId: string,
  body: AgentSkillConfig,
): Promise<ApiResult<AgentSkillConfig>> {
  return httpPut<AgentSkillConfig, AgentSkillConfig>(`/api/v1/agents/${agentId}/skills/config`, body)
}

export async function apiListUsers(q?: string): Promise<ApiResult<User[]>> {
  return httpGet<User[]>('/api/v1/users', { q })
}

export async function apiCreateUser(body: {
  email: string
  username: string
  display_name: string | null
  password: string
  role: string
  status: string
  bio: string
}): Promise<ApiResult<User>> {
  return httpPost<User, typeof body>('/api/v1/users', body)
}

export async function apiGetCurrentUser(): Promise<ApiResult<User>> {
  return httpGet<User>('/api/v1/users/me')
}

export async function apiUpdateCurrentUser(body: UserSelfUpdate): Promise<ApiResult<User>> {
  return httpPut<User, UserSelfUpdate>('/api/v1/users/me', body)
}

export async function apiGetCurrentUserProfileMd(): Promise<ApiResult<{ content: string }>> {
  return httpGet<{ content: string }>('/api/v1/users/me/profile-md')
}

export async function apiUpdateCurrentUserProfileMd(content: string): Promise<ApiResult<{ content: string }>> {
  return httpPut<{ content: string }, { content: string }>('/api/v1/users/me/profile-md', { content })
}
