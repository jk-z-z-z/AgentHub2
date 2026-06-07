import { httpGet, httpPost, httpPut, type ApiResult } from './http'
import type {
  AgentRun,
  AgentRunEvent,
  GroupAssistantConfig,
  GroupTaskEvent,
  GroupTaskGraph,
  GroupTaskNodeDraft,
  GroupTaskNodeIn,
  GroupTaskRun,
  Id,
  Message,
  MessageCodeDiffResponse,
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

export async function apiGetMessageCodeDiff(messageId: string | number): Promise<ApiResult<MessageCodeDiffResponse>> {
  return httpGet<MessageCodeDiffResponse>(`/api/v1/messages/${messageId}/code-diff`)
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

export async function apiCreateGroupTaskRunFromText(body: {
  group_id: Id
  creator_member_id: Id
  title: string
  goal_text: string
  node_text: string
  trigger_message_id?: Id | null
}): Promise<ApiResult<GroupTaskRun>> {
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
  return apiCreateGroupTaskRun({
    group_id: body.group_id,
    creator_member_id: body.creator_member_id,
    title: body.title,
    goal_text: body.goal_text,
    nodes,
    trigger_message_id: body.trigger_message_id,
  })
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

export async function apiGetGroupTaskGraph(runId: string): Promise<ApiResult<GroupTaskGraph>> {
  return httpGet<GroupTaskGraph>(`/api/v1/group-tasks/runs/${runId}/graph`)
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
  GroupTaskRun,
  MessageCodeDiffFile,
  MessageCodeDiffResponse,
  MessageCodeDiffSummary,
  Member,
  Message,
  MemoryCompressRunResult,
  MemoryCompressorConfig,
  MemoryCompressorStatus,
  ProjectCodeEntry,
} from './models'
