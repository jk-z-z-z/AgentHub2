import { httpGet, httpPost, httpPut, type ApiResult } from './http'
import type {
  AgentRun,
  AgentRunEvent,
  GroupAssistantConfig,
  GroupTaskEvent,
  GroupTaskGraph,
  GroupTaskNodeDraft,
  GroupTaskNodeIn,
  Id,
  Message,
  GroupTaskNode,
} from './models'

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

export async function apiGetAgentRun(runId: string): Promise<ApiResult<AgentRun>> {
  return httpGet<AgentRun>(`/api/v1/agent-runs/${runId}`)
}

export async function apiListAgentRunEvents(runId: string): Promise<ApiResult<AgentRunEvent[]>> {
  return httpGet<AgentRunEvent[]>(`/api/v1/agent-runs/${runId}/events`)
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

export function parseGroupTaskNodeDraftLine(line: string): GroupTaskNodeDraft {
  const parts = line.split('|').map((item) => item.trim())
  return {
    title: parts[0] || '节点1',
    role_required: parts[1] || null,
    detail: parts[2] || '',
    deps: parts[3]
      ? parts[3]
          .split(',')
          .map((item) => item.trim())
          .filter(Boolean)
      : [],
  }
}

export async function apiCreateGroupTaskNodesFromText(body: {
  group_id: Id
  node_text: string
}): Promise<ApiResult<GroupTaskNode[]>> {
  const lines = body.node_text
    .split('\n')
    .map((item) => item.trim())
    .filter(Boolean)
  const drafts = (lines.length > 0 ? lines : ['需求澄清与初始计划 | manager']).map(parseGroupTaskNodeDraftLine)
  const nodes: GroupTaskNodeIn[] = drafts.map((item, index) => ({
    node_key: `n${index + 1}`,
    title: item.title,
    detail: item.detail || '',
    role_required: item.role_required || null,
    deps: item.deps || [],
  }))
  return httpPost<GroupTaskNode[], { nodes: GroupTaskNodeIn[] }>(`/api/v1/group-tasks/groups/${body.group_id}/nodes`, { nodes })
}

export async function apiListGroupTaskNodes(groupId: string): Promise<ApiResult<GroupTaskNode[]>> {
  return httpGet<GroupTaskNode[]>(`/api/v1/group-tasks/groups/${groupId}/nodes`)
}

export async function apiListGroupTaskEvents(groupId: string): Promise<ApiResult<GroupTaskEvent[]>> {
  return httpGet<GroupTaskEvent[]>(`/api/v1/group-tasks/groups/${groupId}/events`)
}

export async function apiGetGroupTaskGraph(groupId: string): Promise<ApiResult<GroupTaskGraph>> {
  return httpGet<GroupTaskGraph>(`/api/v1/group-tasks/groups/${groupId}/graph`)
}

export async function apiClaimGroupTaskNode(nodeId: string, memberId: string): Promise<ApiResult<GroupTaskNode>> {
  return httpPost<GroupTaskNode, { member_id: Id }>(`/api/v1/group-tasks/nodes/${nodeId}/claim`, { member_id: memberId })
}

export async function apiCompleteGroupTaskNode(
  nodeId: string,
  memberId: string,
  outputSummary: string,
): Promise<ApiResult<GroupTaskNode>> {
  return httpPost<GroupTaskNode, { member_id: Id; output_summary: string }>(`/api/v1/group-tasks/nodes/${nodeId}/complete`, {
    member_id: memberId,
    output_summary: outputSummary,
  })
}

export type {
  AgentRun,
  AgentRunEvent,
  Group,
  GroupAssistantConfig,
  GroupTaskEvent,
  GroupTaskGraph,
  GroupTaskNode,
  GroupTaskNodeDraft,
  GroupTaskNodeIn,
  Member,
  Message,
  MemoryCompressRunResult,
  MemoryCompressorConfig,
  MemoryCompressorStatus,
  ProjectCodeEntry,
} from './models'
