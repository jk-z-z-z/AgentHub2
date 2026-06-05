import { httpDelete, httpGet, httpPost, httpPut, type ApiResult } from './http'
import type {
  Group,
  GroupCreateAgentInput,
  GroupCreateAgentSelection,
  GroupCreateRequest,
  GroupCreateSelection,
  GroupCreateUserInput,
  MemoryCompressRunResult,
  MemoryCompressorConfig,
  MemoryCompressorStatus,
  Member,
  UserMemberCreateRequest,
  AgentMemberCreateRequest,
} from './models'

export async function apiListGroups(): Promise<ApiResult<Group[]>> {
  return httpGet<Group[]>('/api/v1/groups')
}

export async function apiDeleteGroup(groupId: string): Promise<ApiResult<boolean>> {
  return httpDelete<boolean>(`/api/v1/groups/${groupId}`)
}

export async function apiCreateGroup(body: GroupCreateRequest): Promise<ApiResult<Group>> {
  return httpPost<Group, GroupCreateRequest>('/api/v1/groups', body)
}

export async function apiCreateGroupFromSelection(body: {
  name: string
  description: string | null
  type: 'project' | 'personal' | 'bootstrap'
  users: GroupCreateSelection[]
  agents: GroupCreateAgentSelection[]
}): Promise<ApiResult<Group>> {
  return apiCreateGroup({
    name: body.name,
    description: body.description,
    type: body.type,
    users: body.users.map<GroupCreateUserInput>((item) => ({
      user_id: item.user_id,
      display_name: item.user_label,
      title: null,
    })),
    agents: body.agents.map<GroupCreateAgentInput>((item) => ({
      agent_id: item.agent_id,
      display_name: item.agent_label,
      title: null,
    })),
  })
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
  return httpPost<Member, UserMemberCreateRequest>('/api/v1/members/users', { title: null, ...body })
}

export async function apiAddAgentMember(body: {
  group_id: string
  display_name: string
  agent_instance_id: string
  title?: string | null
}): Promise<ApiResult<Member>> {
  return httpPost<Member, AgentMemberCreateRequest>('/api/v1/members/agents', { title: null, ...body })
}

export async function apiDeleteMember(memberId: string): Promise<ApiResult<boolean>> {
  return httpDelete<boolean>(`/api/v1/members/${memberId}`)
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
  return httpPut<MemoryCompressorConfig, MemoryCompressorConfig>(
    `/api/v1/groups/${groupId}/memory/compressor-config`,
    body,
  )
}

export async function apiRunGroupMemoryCompress(groupId: string): Promise<ApiResult<MemoryCompressRunResult>> {
  return httpPost<MemoryCompressRunResult, Record<string, never>>(`/api/v1/groups/${groupId}/memory/compress`, {})
}

export type {
  Agent,
  Group,
  GroupAssistantConfig,
  GroupCreateAgentInput,
  GroupCreateRequest,
  GroupCreateUserInput,
  GroupTaskNode,
  MemoryCompressorConfig,
  MemoryCompressorStatus,
  Member,
  Message,
  ProjectCodeEntry,
  User,
} from './models'
