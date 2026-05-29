import { httpDelete, httpGet, httpPost, httpPut } from '@/api/http'
import type { components } from '@/api/generated/schema'

const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? 'http://127.0.0.1:8000/api/v1'
const WS_BASE = (import.meta.env.VITE_WS_BASE as string | undefined) ?? 'ws://127.0.0.1:8000'

type ApiGroup = components['schemas']['GroupOut']
type ApiUser = components['schemas']['UserOut']
type ApiMember = components['schemas']['MemberOut']
type ApiMessage = components['schemas']['MessageOut']
type ApiAgentProfile = components['schemas']['AgentProfileOut']
type ApiAgentInstance = components['schemas']['AgentInstanceOut']
type ApiTool = components['schemas']['ToolOut']
type ApiMcp = components['schemas']['MCPOut']
type ApiSkill = components['schemas']['SkillOut']
type ApiAcpProvider = components['schemas']['ACPProviderOut']
type ApiGroupCreateRequest = components['schemas']['GroupCreateRequest']
type ApiUserMemberCreateRequest = components['schemas']['UserMemberCreateRequest']
type ApiAgentMemberCreateRequest = components['schemas']['AgentMemberCreateRequest']
type ApiAgentProfileCreateRequest = components['schemas']['AgentProfileCreateRequest']
type ApiAgentInstanceCreateRequest = components['schemas']['AgentInstanceCreateRequest']

export type LoginPayload = {
  email: string
  password: string
}

export type User = {
  id: string
  email: string
  username: string
  display_name?: string | null
  role: string
  status: string
  bio?: string | null
}

export type Group = {
  id: string
  name: string
  description?: string | null
}

export type Member = {
  id: string
  group_id: string
  kind: 'user' | 'agent' | string
  display_name: string
  user_ref?: string | null
  agent_instance_id?: string | null
  title?: string | null
  created_at?: string
  updated_at?: string
}

export type Message = {
  id: string
  group_id: string
  sender_member_id: string
  message_type: string
  content: string
  reply_to_message_id?: string | null
  metadata_json: string
  created_at: string
  updated_at: string
}

export type AgentProfile = {
  id: string
  name: string
  role: string
  description?: string | null
  system_prompt: string
  default_model_json: string
  planning_mode?: string | null
  is_active: number
  created_at?: string
  updated_at?: string
}

export type AgentInstance = {
  id: string
  group_id: string
  profile_id: string
  display_name: string
  description?: string | null
  base_url?: string | null
  api_key_ref?: string | null
  config_json: string
  status: string
  created_at?: string
  updated_at?: string
}

export type ToolResource = {
  id: string
  name: string
  code: string
  description?: string | null
  source_type: string
  schema_json: string
  is_active: number
}

export type McpResource = {
  id: string
  name: string
  server_code: string
  description?: string | null
  connection_json: string
  capability_json: string
  is_active: number
}

export type SkillResource = {
  id: string
  name: string
  code: string
  description?: string | null
  content: string
  version: string
  is_active: number
}

export type AcpProviderResource = {
  id: string
  name: string
  provider_type: string
  transport_type: string
  endpoint?: string | null
  capability_json: string
  auth_config_json: string
  is_active: number
}

export type LoginResult = {
  access_token: string
  user: User
}

function toId(value: string | number | null | undefined): string {
  return value == null ? '' : String(value)
}

function normalizeUser(value: ApiUser): User {
  return { ...value, id: toId(value.id) }
}

function normalizeGroup(value: ApiGroup): Group {
  return { ...value, id: toId(value.id) }
}

function normalizeMember(value: ApiMember): Member {
  return {
    ...value,
    id: toId(value.id),
    group_id: toId(value.group_id),
    user_ref: value.user_ref ?? null,
    agent_instance_id: value.agent_instance_id == null ? null : toId(value.agent_instance_id),
    created_at: value.created_at,
    updated_at: value.updated_at,
  }
}

function normalizeMessage(value: ApiMessage): Message {
  return {
    ...value,
    id: toId(value.id),
    group_id: toId(value.group_id),
    sender_member_id: toId(value.sender_member_id),
    reply_to_message_id: value.reply_to_message_id == null ? null : toId(value.reply_to_message_id),
  }
}

function normalizeAgentProfile(value: ApiAgentProfile): AgentProfile {
  return {
    ...value,
    id: toId(value.id),
    created_at: value.created_at,
    updated_at: value.updated_at,
  }
}

function normalizeAgentInstance(value: ApiAgentInstance): AgentInstance {
  return {
    ...value,
    id: toId(value.id),
    group_id: toId(value.group_id),
    profile_id: toId(value.profile_id),
    created_at: value.created_at,
    updated_at: value.updated_at,
  }
}

function normalizeTool(value: ApiTool): ToolResource {
  return {
    ...value,
    id: toId(value.id),
    schema_json: value.schema_json,
  }
}

function normalizeMcp(value: ApiMcp): McpResource {
  return { ...value, id: toId(value.id) }
}

function normalizeSkill(value: ApiSkill): SkillResource {
  return { ...value, id: toId(value.id) }
}

function normalizeAcpProvider(value: ApiAcpProvider): AcpProviderResource {
  return { ...value, id: toId(value.id) }
}

export async function login(payload: LoginPayload): Promise<LoginResult> {
  const { data } = await httpPost<components['schemas']['LoginOut'], LoginPayload>(`${API_BASE}/auth/login`, payload)
  return {
    access_token: data.access_token,
    user: normalizeUser(data.user),
  }
}

export async function getMe(): Promise<User> {
  const { data } = await httpGet<ApiUser>(`${API_BASE}/auth/me`)
  return normalizeUser(data)
}

export async function listUsers(query?: { q?: string }): Promise<User[]> {
  const { data } = await httpGet<ApiUser[]>(`${API_BASE}/users`, { q: query?.q })
  return data.map(normalizeUser)
}

export async function createUser(payload: {
  email: string
  username: string
  password: string
  display_name?: string | null
  role?: string
  status?: string
  bio?: string | null
}): Promise<User> {
  const { data } = await httpPost<ApiUser, typeof payload>(`${API_BASE}/users`, payload)
  return normalizeUser(data)
}

export async function listGroups(): Promise<Group[]> {
  const { data } = await httpGet<ApiGroup[]>(`${API_BASE}/groups`)
  return data.map(normalizeGroup)
}

export async function createGroup(payload: ApiGroupCreateRequest): Promise<Group> {
  const { data } = await httpPost<ApiGroup, ApiGroupCreateRequest>(`${API_BASE}/groups`, payload)
  return normalizeGroup(data)
}

export async function listMembers(groupId?: string): Promise<Member[]> {
  const { data } = await httpGet<ApiMember[]>(`${API_BASE}/members`, { group_id: groupId })
  return data.map(normalizeMember)
}

export async function createUserMember(payload: ApiUserMemberCreateRequest): Promise<Member> {
  const { data } = await httpPost<ApiMember, ApiUserMemberCreateRequest>(`${API_BASE}/members/users`, payload)
  return normalizeMember(data)
}

export async function createAgentMember(payload: ApiAgentMemberCreateRequest): Promise<Member> {
  const { data } = await httpPost<ApiMember, ApiAgentMemberCreateRequest>(`${API_BASE}/members/agents`, payload)
  return normalizeMember(data)
}

export async function updateMember(payload: {
  member_id: string
  display_name: string
  title?: string | null
}): Promise<Member> {
  const { data } = await httpPut<ApiMember, { display_name: string; title?: string | null }>(
    `${API_BASE}/members/${payload.member_id}`,
    {
      display_name: payload.display_name,
      title: payload.title ?? null,
    },
  )
  return normalizeMember(data)
}

export async function deleteMember(memberId: string): Promise<boolean> {
  const { data } = await httpDelete<boolean>(`${API_BASE}/members/${memberId}`)
  return data
}

export async function listMessagesByGroup(groupId: string, limit = 200): Promise<Message[]> {
  const { data } = await httpGet<ApiMessage[]>(`${API_BASE}/messages`, { group_id: groupId, limit })
  return data.map(normalizeMessage).sort((a, b) => Number(a.id) - Number(b.id))
}

export async function sendMessage(payload: {
  group_id: string
  sender_member_id: string
  content: string
  message_type?: string
  reply_to_message_id?: string | null
  metadata_json?: string
}): Promise<Message> {
  const { data } = await httpPost<ApiMessage, object>(`${API_BASE}/messages`, {
    group_id: payload.group_id,
    sender_member_id: payload.sender_member_id,
    message_type: payload.message_type ?? 'text',
    content: payload.content,
    reply_to_message_id: payload.reply_to_message_id ?? null,
    metadata_json: payload.metadata_json ?? '{}',
  })
  return normalizeMessage(data)
}

export async function listAgentProfiles(): Promise<AgentProfile[]> {
  const { data } = await httpGet<ApiAgentProfile[]>(`${API_BASE}/agent-profiles`)
  return data.map(normalizeAgentProfile)
}

export async function createAgentProfile(payload: ApiAgentProfileCreateRequest): Promise<AgentProfile> {
  const { data } = await httpPost<ApiAgentProfile, ApiAgentProfileCreateRequest>(`${API_BASE}/agent-profiles`, payload)
  return normalizeAgentProfile(data)
}

export async function listAgentInstances(): Promise<AgentInstance[]> {
  const { data } = await httpGet<ApiAgentInstance[]>(`${API_BASE}/agent-instances`)
  return data.map(normalizeAgentInstance)
}

export async function createAgentInstance(payload: ApiAgentInstanceCreateRequest): Promise<AgentInstance> {
  const { data } = await httpPost<ApiAgentInstance, ApiAgentInstanceCreateRequest>(`${API_BASE}/agent-instances`, payload)
  return normalizeAgentInstance(data)
}

export async function listTools(): Promise<ToolResource[]> {
  const { data } = await httpGet<ApiTool[]>(`${API_BASE}/tools`)
  return data.map(normalizeTool)
}

export async function listMcps(): Promise<McpResource[]> {
  const { data } = await httpGet<ApiMcp[]>(`${API_BASE}/mcps`)
  return data.map(normalizeMcp)
}

export async function listSkills(): Promise<SkillResource[]> {
  const { data } = await httpGet<ApiSkill[]>(`${API_BASE}/skills`)
  return data.map(normalizeSkill)
}

export async function listAcpProviders(): Promise<AcpProviderResource[]> {
  const { data } = await httpGet<ApiAcpProvider[]>(`${API_BASE}/acp-providers`)
  return data.map(normalizeAcpProvider)
}

export async function bindProfileTools(profileId: string, toolIds: string[]): Promise<ToolResource[]> {
  const { data } = await httpPut<ApiTool[], number[]>(`${API_BASE}/agent-profiles/${profileId}/tools`, toolIds.map(Number))
  return data.map(normalizeTool)
}

export async function bindProfileMcps(profileId: string, mcpIds: string[]): Promise<McpResource[]> {
  const { data } = await httpPut<ApiMcp[], number[]>(`${API_BASE}/agent-profiles/${profileId}/mcps`, mcpIds.map(Number))
  return data.map(normalizeMcp)
}

export async function bindProfileSkills(profileId: string, skillIds: string[]): Promise<SkillResource[]> {
  const { data } = await httpPut<ApiSkill[], number[]>(`${API_BASE}/agent-profiles/${profileId}/skills`, skillIds.map(Number))
  return data.map(normalizeSkill)
}

export async function bindProfileAcpProviders(profileId: string, providerIds: string[]): Promise<AcpProviderResource[]> {
  const { data } = await httpPut<ApiAcpProvider[], number[]>(
    `${API_BASE}/agent-profiles/${profileId}/acp-providers`,
    providerIds.map(Number),
  )
  return data.map(normalizeAcpProvider)
}

export function buildGroupWebSocketUrl(groupId: string): string {
  const token = localStorage.getItem('token') || ''
  return `${WS_BASE}/ws/groups/${groupId}?token=${encodeURIComponent(token)}`
}
