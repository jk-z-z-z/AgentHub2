import type { components } from './generated/schema'

export type Schema = components['schemas']
export type Id = string | number

export type Group = Schema['GroupOut']
export type Member = Schema['MemberOut']
export type Message = Schema['MessageOut'] & {
  reply_to_message_id?: string | null
}
export type MessageEvent = Schema['MessageEventOut']
export type Agent = Schema['AgentInstanceOut']
export type AgentProfile = Schema['AgentProfileOut']
export type User = Schema['UserOut']
export type GroupCreateRequest = Schema['GroupCreateRequest']
export type GroupCreateUserInput = Schema['GroupMemberUserIn']
export type GroupCreateAgentInput = Schema['GroupMemberAgentIn']
export type GroupCreateSelection = {
  user_id: string
  user_label: string
}
export type GroupCreateAgentSelection = {
  agent_id: string
  agent_label: string
}
export type UserMemberCreateRequest = Schema['UserMemberCreateRequest']
export type AgentMemberCreateRequest = Schema['AgentMemberCreateRequest']
export type MessageCreateRequest = Schema['MessageCreateRequest'] & {
  reply_to_message_id?: string | null
}
export type GroupTaskNodeIn = Schema['GroupTaskNodeIn']
export type GroupTaskNode = Schema['GroupTaskNodeOut'] & {
  run_id: string
  manager_review_status: string
}
export type FsEntry = Schema['FsEntryOut']
export type ProjectCodeEntry = FsEntry
export type Tool = Schema['ToolOut']
export type MCP = Schema['MCPOut']
export type SkillPoolItem = Schema['SkillPoolItemOut']
export type AgentSkillConfig = Schema['AgentSkillConfigOut']
export type AgentToolToggles = Schema['AgentToolTogglesOut']
export type AgentToolTogglesUpdateRequest = Schema['AgentToolTogglesUpdateRequest']
export type AgentMcpToggles = {
  enabled: Record<string, boolean>
}
export type AgentMcpTogglesUpdateRequest = {
  enabled: Record<string, boolean>
}
export type UserCreateRequest = Schema['UserCreateRequest']
export type UserSelfUpdate = Schema['UserSelfUpdateRequest']
export type UserProfileMd = Schema['UserProfileMdOut']
export type UserProfileMdOut = Schema['UserProfileMdOut']
export type WorkspaceFileContent = Schema['WorkspaceFileContentOut']
export type WorkspaceFileToggles = Schema['WorkspaceFileTogglesOut']
export type WorkspaceFileWriteRequest = Schema['WorkspaceFileWriteRequest']
export type TextFileWriteRequest = Schema['TextFileWriteRequest']
export type AgentProfileCreateRequest = Schema['AgentProfileCreateRequest']
export type AgentInstanceCreateRequest = Schema['AgentInstanceCreateRequest']
export type MCPCreateRequest = Schema['MCPCreateRequest']
export type AgentCreateBody = Pick<AgentInstanceCreateRequest, 'display_name'> &
  Partial<Omit<AgentInstanceCreateRequest, 'display_name'>>
export type AgentSkillConfigUpdateRequest = Schema['AgentSkillConfigUpdateRequest']
export type ProjectMemoryCompressorConfigUpdateRequest = Schema['ProjectMemoryCompressorConfigUpdateRequest']
export type TextFile = Schema['TextFileOut']
export type ProjectMemoryCompressorStatus = Schema['ProjectMemoryCompressorStatusOut']
export type ProjectMemoryCompressorConfig = Schema['ProjectMemoryCompressorConfigOut']
export type MemoryCompressorStatus = ProjectMemoryCompressorStatus
export type MemoryCompressorConfig = ProjectMemoryCompressorConfig
export type AgentProfileCreateBody = Pick<AgentProfileCreateRequest, 'name' | 'role' | 'soul_md'> &
  Partial<Omit<AgentProfileCreateRequest, 'name' | 'role' | 'soul_md'>>
export type MCPCreateBody = Pick<Schema['MCPCreateRequest'], 'name' | 'server_code'> &
  Partial<Omit<Schema['MCPCreateRequest'], 'name' | 'server_code'>>
export type MemoryCompressRunResult = {
  compressed: boolean
  reason?: string | null
  compressed_count?: number | null
  last_message_id?: number | null
}

export type GroupTaskGraph = Schema['GroupTaskGraphOut']

export type GroupTaskNodeDraft = {
  title: string
  role_required?: string | null
  detail?: string
  deps?: string[]
}

export type GroupAssistantConfig = {
  enabled: number
  manager_member_id?: string | number | null
  group_id?: string | number | null
  created_at?: string | null
  updated_at?: string | null
}

export type AgentRun = {
  id: string | number
  group_id?: string | number | null
  title?: string | null
  goal_text?: string | null
  status?: string | null
  trigger_message_id?: string | number | null
  created_at?: string
  updated_at?: string
}

export type AgentRunEvent = {
  id: string | number
  run_id: string | number
  seq?: number
  event_type?: string | null
  category?: string | null
  status?: string | null
  payload_json?: string | null
  created_at?: string
  updated_at?: string
}

export type GroupTaskEvent = {
  id: string | number
  run_id: string | number
  seq?: number
  event_type?: string | null
  category?: string | null
  status?: string | null
  payload_json?: string | null
  created_at?: string
  updated_at?: string
}

export type GroupTaskRun = {
  id: string | number
  group_id?: string | number | null
  creator_member_id?: string | number | null
  title: string
  goal_text: string
  status: string
  trigger_message_id?: string | number | null
  created_at: string
  updated_at?: string
}

export type MessageCodeDiffSummary = {
  message_id: number | string
  workspace_id?: number | null
  group_id?: number | null
  before_commit?: string | null
  after_commit?: string | null
  changed_file_count: number
  insertions: number
  deletions: number
  has_code_changes: boolean
  repo_initialized: boolean
  diff_preview_available: boolean
}

export type MessageCodeDiffFile = {
  path: string
  change_type: 'added' | 'modified' | 'deleted' | 'renamed' | 'binary'
  old_path?: string | null
  additions: number
  deletions: number
  patch?: string | null
  patch_truncated: boolean
}

export type MessageCodeDiffResponse = {
  status: 'ready' | 'no_changes' | 'unavailable' | 'failed'
  summary?: MessageCodeDiffSummary | null
  files: MessageCodeDiffFile[]
  error?: string | null
}
