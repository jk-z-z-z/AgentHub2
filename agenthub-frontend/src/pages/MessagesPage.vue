<template>
  <div
    ref="shellRef"
    class="shell"
    :class="{ withSidePane: hasSidePane, isResizingSidePane: sidePaneDragging }"
    :style="shellStyle"
  >
    <MessageConversationList
      v-model:search="groupSearch"
      :groups="filteredGroups"
      :active-group-id="activeGroupId"
      :last-preview-map="lastPreviewMap"
      :last-time-map="lastTimeMap"
      :loading="loadingGroups"
      @select="selectGroup"
      @create="createOpen = true"
    />

    <section class="chatPane">
      <div class="chatHeader">
        <div class="chatHeading">
          <div class="chatTitle">{{ activeGroup?.name || '选择一个会话' }}</div>
          <div v-if="activeGroup" class="chatMeta">
            <span>{{ members.length }} 位成员</span>
            <span>{{ agentMembers.length }} 个智能体</span>
          </div>
        </div>
        <div class="chatActions">
          <el-tooltip v-if="supportsProjectWorkspace(activeGroup)" content="查看代码" placement="bottom">
            <el-button class="iconBtn iconBtnLarge" text :icon="FolderOpened" @click="openProjectCode" aria-label="查看代码" />
          </el-tooltip>
          <el-tooltip v-if="supportsProjectWorkspace(activeGroup)" content="部署" placement="bottom">
            <el-button class="iconBtn iconBtnLarge" text :icon="UploadFilled" @click="openDeployPanel" aria-label="部署" />
          </el-tooltip>
          <el-tooltip v-if="supportsProjectWorkspace(activeGroup)" content="任务规划" placement="bottom">
            <el-button class="iconBtn iconBtnLarge" text :icon="Operation" @click="openTaskPlanner" aria-label="任务规划" />
          </el-tooltip>
          <el-tooltip content="聊天管理" placement="bottom">
            <el-button class="iconBtn" :disabled="!activeGroup" text :icon="Setting" @click="openManage" aria-label="聊天管理" />
          </el-tooltip>
        </div>
      </div>

      <MessageThread
        :loading="loadingGroups"
        :active-group="activeGroup"
        :messages="messages"
        :members="members"
        :current-user-id="currentUserId"
        :scroll-to-message-id="pendingScrollToMessageId"
        @open-code-diff="openCodeDiffPanel"
        @open-message-events="openMessageEventsPanel"
        @reply-message="setReplyTarget"
        @locate-message="locateMessage"
        @scroll-target-handled="handleScrollTargetHandled"
      />

      <MessageComposer
        ref="composerRef"
        :draft="draft"
        :can-mention-agents="canMentionAgents"
        :can-send="canSend"
        :selected-mentions="selectedMentions"
        :mention-suggest-open="mentionSuggestOpen"
        :filtered-agent-members="filteredAgentMembers"
        :mention-names="mentionNames"
        :reply-preview="replyPreview"
        @update:draft="updateDraft"
        @keydown="onDraftKeydown"
        @open-mention="openMention"
        @send="send"
        @remove-mention="removeMention"
        @pick-mention="pickMention"
        @clear-reply="clearReplyTarget"
      />
    </section>

    <aside v-if="hasSidePane" class="sidePane">
      <div
        class="sidePaneResize"
        :class="{ dragging: sidePaneDragging }"
        role="separator"
        aria-label="调整右侧侧边栏宽度"
        aria-orientation="vertical"
        @pointerdown="startSidePaneResize"
      />
      <MessageFilePanel
        v-if="projectFilesOpen"
        :active-group="activeGroup"
        :loading="projectFilesLoading"
        :roots="projectFilesEntries"
        :active-path="projectActiveFilePath"
        :open-dirs="projectOpenDirs"
        :show-hidden-files="showHiddenFiles"
        @close="projectFilesOpen = false"
        @refresh="reloadProjectFiles"
        @open-file="openProjectFile"
        @toggle-dir="toggleProjectDir"
        @update:show-hidden-files="showHiddenFiles = $event"
      />

      <MessageDeploymentPanel
        v-else-if="deployOpen"
        :active-group="activeGroup"
        :preview-job="activePreviewJob"
        :preview-pending="previewPending"
        :deployment-job="activeDeploymentJob"
        :deploy-pending="deployPending"
        @close="deployOpen = false"
        @close-preview="closePreview"
        @open-preview="openPreview"
        @deploy="deployProject"
        @retry-deploy="retryDeployment"
      />

      <MessageManagePanel
        v-else-if="manageOpen"
        :active-group="activeGroup"
        :members="members"
        :manage-err="manageErr"
        :memory-cfg-loading="memoryCfgLoading"
        :memory-cfg-saving="memoryCfgSaving"
        :memory-compressing="memoryCompressing"
        :memory-cfg="memoryCfg"
        :memory-status="memoryStatus"
        :assistant-cfg-loading="assistantCfgLoading"
        :assistant-cfg-saving="assistantCfgSaving"
        :assistant-cfg="assistantCfg"
        v-model:assistant-enabled="assistantCfgEnabled"
        @close="manageOpen = false"
        @delete-group="deleteActiveGroup"
        @remove-member="removeMember"
        @open-add-member="openAddMember"
        @save-memory-config="saveMemoryConfig"
        @run-memory-compress="runMemoryCompressNow"
        @refresh-memory-status="loadMemoryStatus"
        @save-assistant-config="saveAssistantConfig"
      />

      <TaskPlannerPanel
        v-else
        :active-group="activeGroup"
        :members="members"
        :current-user-id="currentUserId"
        :runs="taskRuns"
        :active-run-id="activeRunId"
        :active-run="activeTaskRun"
        :graph="taskGraph"
        :nodes="taskNodes"
        :node-stats="taskNodeStats"
        :runs-loading="taskRunsLoading"
        :nodes-loading="taskNodesLoading"
        :manage-err="manageErr"
        :detail-open="taskDetailOpen"
        @close="closeTaskPlanner"
        @refresh-runs="loadTaskRuns"
        @open-run="openTaskRunDetail"
        @create-run="taskCreateOpen = true"
        @refresh-run-details="loadTaskRunDetails"
        @claim-node="claimNode"
        @complete-node="completeNode"
        @review-node="reviewNode"
        @close-detail="closeTaskRunDetail"
      />
    </aside>
  </div>

  <GroupCreateDialog
    v-model:open="createOpen"
    v-model:create-type="createType"
    v-model:create-name="createName"
    :users="users"
    :agents="agents"
    :picked-user-ids="pickedUserIds"
    :picked-agent-ids="pickedAgentIds"
    :create-err="createErr"
    :creating="creating"
    @toggle-user="togglePickUser"
    @toggle-agent="togglePickAgent"
    @create="createGroup"
  />

  <GroupCreateDialog
    v-model:open="addMemberOpen"
    v-model:create-type="addMemberType"
    v-model:create-name="addMemberName"
    mode="add-member"
    :users="addableUsers"
    :agents="addableAgents"
    :picked-user-ids="pickedUserIds"
    :picked-agent-ids="pickedAgentIds"
    :create-err="addMemberErr"
    :creating="adding"
    @toggle-user="togglePickUser"
    @toggle-agent="togglePickAgent"
    @create="addMembers"
  />

  <MessageCodeDiffPanel
    v-model:open="codeDiffOpen"
    :active-group="activeGroup"
    :loading="codeDiffLoading"
    :diff="activeCodeDiff"
    :error="codeDiffError"
    @close="closeCodeDiffPanel"
  />

  <MessageEventPanel
    v-model:open="messageEventOpen"
    :active-group="activeGroup"
    :message="activeMessageEventMessage"
    :events="activeMessageEvents"
    :loading="messageEventLoading"
    :error="messageEventError"
    @close="closeMessageEventsPanel"
  />

  <TaskRunCreateDialog
    v-model:open="taskCreateOpen"
    v-model:title="taskCreateTitle"
    v-model:goal="taskCreateGoal"
    v-model:node-text="taskCreateNodeText"
    :create-err="manageErr"
    @create="createTaskRunNow"
  />
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { Operation, FolderOpened, Setting, UploadFilled } from '@element-plus/icons-vue'
import {
  type Group,
  type GroupTaskGraph,
  type GroupTaskNode,
  type MemoryCompressorConfig,
  type MemoryCompressorStatus,
  type Member,
  type Message,
  apiCreateMessage,
  apiGetMessageCodeDiff,
  apiGetGroupTaskGraph,
  apiListMessages,
  apiListMessageEvents,
  apiGetGroupAssistantConfig,
  apiUpdateGroupAssistantConfig,
  apiCreateGroupTaskRunFromText,
  apiListGroupTaskRuns,
  apiListGroupTaskNodes,
  apiClaimGroupTaskNode,
  apiCompleteGroupTaskNode,
  apiReviewGroupTaskNode,
  type GroupAssistantConfig,
  type MessageCodeDiffResponse,
  type MessageEvent,
  type GroupTaskRun,
} from '../api/messages'
import {
  type Agent,
  apiAddAgentMember,
  apiAddUserMember,
  apiCreateGroupFromSelection,
  apiDeleteGroup,
  apiDeleteMember,
  apiGetGroupMemoryCompressorConfig,
  apiGetGroupMemoryCompressorStatus,
  apiListGroups,
  apiListMembers,
  apiRunGroupMemoryCompress,
  apiUpdateGroupMemoryCompressorConfig,
} from '../api/groups'
import { apiListAgents } from '../api/agents'
import { apiGetCurrentUser, apiListUsers, type User } from '../api/users'
import { apiListProjectCode, type ProjectCodeEntry } from '../api/project-code'
import { apiCreateDeployment, apiGetDeployment, apiRetryDeployment, type DeploymentJob, type DeploymentRequest } from '../api/deployments'
import { apiCreatePreview, apiDeleteWorkspacePreview, apiGetWorkspacePreview, type PreviewJob } from '../api/previews'
import MessageConversationList from '../components/messages/MessageConversationList.vue'
import MessageComposer from '../components/messages/MessageComposer.vue'
import MessageDeploymentPanel from '../components/messages/MessageDeploymentPanel.vue'
import MessageCodeDiffPanel from '../components/messages/MessageCodeDiffPanel.vue'
import MessageEventPanel from '../components/messages/MessageEventPanel.vue'
import GroupCreateDialog from '../components/messages/GroupCreateDialog.vue'
import MessageFilePanel from '../components/messages/MessageFilePanel.vue'
import MessageManagePanel from '../components/messages/MessageManagePanel.vue'
import TaskRunCreateDialog from '../components/messages/TaskRunCreateDialog.vue'
import TaskPlannerPanel from '../components/messages/TaskPlannerPanel.vue'
import MessageThread from '../components/messages/MessageThread.vue'
import { ElMessage, ElMessageBox } from 'element-plus'

const route = useRoute()
const shellRef = ref<HTMLElement | null>(null)
const composerRef = ref<{ focusEditor?: () => Promise<void> | void } | null>(null)
const draft = ref('')
const replyToMessageId = ref('')
const pendingScrollToMessageId = ref('')
const groups = ref<Group[]>([])
const loadingGroups = ref(false)
const activeGroupId = ref<string>('')
const members = ref<Member[]>([])
const messages = ref<Message[]>([])
const ws = ref<WebSocket | null>(null)
let loadSeq = 0
let wsSeq = 0
let wsReconnectTimer: number | null = null
let wsReconnectAttempts = 0
let locatingMessageRequestId = 0

const lastPreviewMap = ref<Record<string, string>>({})
const lastTimeMap = ref<Record<string, string>>({})
const groupSearch = ref('')

const activeGroup = computed(() => groups.value.find((g) => g.id === activeGroupId.value) || null)
const mentionNames = computed<Record<string, string>>(() => {
  const out: Record<string, string> = {}
  for (const member of agentMembers.value) {
    out[String(member.id)] = member.display_name || String(member.id)
  }
  return out
})
const filteredGroups = computed(() => {
  const query = groupSearch.value.trim().toLowerCase()
  if (!query) return groups.value
  return groups.value.filter((group) => {
    const name = (group.name || '').toLowerCase()
    const type = (group.type || '').toLowerCase()
    const preview = (lastPreviewMap.value[group.id] || '').toLowerCase()
    return name.includes(query) || type.includes(query) || preview.includes(query)
  })
})

function supportsProjectWorkspace(group: Group | null | undefined) {
  if (!group) return false
  return String(group.type || '') === 'project' || Number(group.workspace_id || 0) > 0
}

const canSend = computed(() => Boolean(activeGroup.value) && Boolean(draft.value.trim()))
const replyPreview = computed(() => {
  const targetId = String(replyToMessageId.value || '').trim()
  if (!targetId) return null
  const target = messages.value.find((item) => String(item.id) === targetId)
  if (!target) return null
  const sender = members.value.find((item) => String(item.id) === String(target.sender_member_id))
  const content = String(target.content || '').replace(/\s+/g, ' ').trim()
  return {
    senderName: sender?.display_name || String(target.sender_member_id),
    content: content.length > 96 ? `${content.slice(0, 96)}...` : content || '空消息',
  }
})
const canMentionAgents = computed(() => supportsProjectWorkspace(activeGroup.value))
const MANAGER_NAME = '管家'
const agentMembers = computed(() =>
  members.value
    .filter((m) => m.kind === 'agent' || (m.kind === 'system' && m.display_name === MANAGER_NAME))
    .sort((a, b) => {
      const aManager = a.kind === 'system' && a.display_name === MANAGER_NAME
      const bManager = b.kind === 'system' && b.display_name === MANAGER_NAME
      if (aManager && !bManager) return -1
      if (!aManager && bManager) return 1
      return (a.display_name || '').localeCompare(b.display_name || '', 'zh-Hans-CN')
    }),
)
const mentionSuggestOpen = ref(false)
const mentionQuery = ref('')
const filteredAgentMembers = computed(() => {
  const q = mentionQuery.value.trim().toLowerCase()
  if (!q) return agentMembers.value
  return agentMembers.value.filter((m) => (m.display_name || '').toLowerCase().includes(q))
})

const selectedMentions = ref<Set<string>>(new Set())

const createOpen = ref(false)
const createType = ref<'project' | 'personal'>('project')
const createName = ref('')
const creating = ref(false)
const createErr = ref('')
const addMemberOpen = ref(false)
const addMemberType = ref<'project' | 'personal'>('project')
const addMemberName = ref('')
const addMemberErr = ref('')
const users = ref<User[]>([])
const agents = ref<Agent[]>([])
const pickedUserIds = ref<Set<string>>(new Set())
const pickedAgentIds = ref<Set<string>>(new Set())
const currentUserId = ref('')
const currentUserMember = computed(
  () =>
    members.value.find(
      (member) => member.kind === 'user' && String(member.user_ref || '') === String(currentUserId.value || ''),
    ) || null,
)
const addableUsers = computed(() => {
  const memberUserRefs = new Set(
    members.value
      .map((member) => String(member.user_ref || ''))
      .filter((id) => Boolean(id)),
  )
  return users.value.filter((user) => !memberUserRefs.has(String(user.id)))
})
const addableAgents = computed(() => {
  const memberAgentIds = new Set(
    members.value
      .map((member) => String(member.agent_instance_id || ''))
      .filter((id) => Boolean(id)),
  )
  return agents.value.filter((agent) => !memberAgentIds.has(String(agent.id)))
})

const manageOpen = ref(false)
const taskOpen = ref(false)
const projectFilesOpen = ref(false)
const deployOpen = ref(false)
const codeDiffOpen = ref(false)
const LEFT_PANE_WIDTH = 340
const SIDE_PANE_COMPACT_MIN_WIDTH = 260
const SIDE_PANE_MIN_WIDTH = 400
const SIDE_PANE_DEFAULT_WIDTH = 540
const SIDE_PANE_MAX_WIDTH = 760
const SIDE_PANE_MIN_CHAT_WIDTH = 320
const SHELL_COLUMN_GAP = 24
const SIDE_PANE_WIDTH_STORAGE_KEY = 'agenthub.messages.sidePaneWidth'
const sidePaneWidth = ref(SIDE_PANE_DEFAULT_WIDTH)
const sidePaneDragging = ref(false)
const manageErr = ref('')
const adding = ref(false)
const memoryCfgLoading = ref(false)
const memoryCfgSaving = ref(false)
const memoryCompressing = ref(false)
const memoryCfg = ref<MemoryCompressorConfig>({
  enabled: true,
  trigger_tokens: 3500,
  keep_recent_messages: 12,
  min_interval_seconds: 60,
})
const memoryStatus = ref<MemoryCompressorStatus | null>(null)
const assistantCfgLoading = ref(false)
const assistantCfgSaving = ref(false)
const assistantCfg = ref<GroupAssistantConfig | null>(null)
const assistantCfgEnabled = computed({
  get: () => (assistantCfg.value?.enabled ?? 0) === 1,
  set: (value: boolean) => {
    if (!assistantCfg.value) return
    assistantCfg.value.enabled = value ? 1 : 0
  },
})
const taskRunsLoading = ref(false)
const taskRuns = ref<GroupTaskRun[]>([])
const activeRunId = ref('')
const taskDetailOpen = ref(false)
const activeTaskRun = computed(
  () => taskRuns.value.find((run) => String(run.id) === String(activeRunId.value)) || null,
)
const taskNodesLoading = ref(false)
const taskNodes = ref<GroupTaskNode[]>([])
const taskGraph = ref<GroupTaskGraph | null>(null)
const taskCreateOpen = ref(false)
const taskCreateTitle = ref('')
const taskCreateGoal = ref('')
const taskCreateNodeText = ref('需求澄清与初始计划 | manager')
const messageEventOpen = ref(false)
const messageEventLoading = ref(false)
const messageEventError = ref('')
const activeMessageEventMessageId = ref('')
const activeMessageEvents = ref<MessageEvent[]>([])
const messageEventCache = ref<Record<string, MessageEvent[]>>({})
const activeMessageEventMessage = computed(
  () => messages.value.find((message) => String(message.id) === String(activeMessageEventMessageId.value)) || null,
)
type DeployDraft = {
  imageRef: string
  containerName: string
  dockerfilePath: string
  buildContextPath: string
  hostPort: number
  containerPort: number
  installCommand: string
  testCommand: string
  buildCommand: string
  containerCommand: string
  envText: string
}
const deployDraft = reactive<DeployDraft>({
  imageRef: '',
  containerName: '',
  dockerfilePath: 'Dockerfile',
  buildContextPath: '.',
  hostPort: 18080,
  containerPort: 80,
  installCommand: '',
  testCommand: '',
  buildCommand: '',
  containerCommand: '',
  envText: '',
})
const projectFilesLoading = ref(false)
const projectFilesEntries = ref<ProjectCodeEntry[]>([])
const projectOpenDirs = ref<Record<string, boolean>>({})
const projectActiveFilePath = ref('')
const showHiddenFiles = ref(false)
const previewJobs = ref<Record<string, PreviewJob | null>>({})
const previewPending = ref(false)
const deploymentJobs = ref<Record<string, DeploymentJob | null>>({})
const deployPending = ref(false)
const codeDiffLoading = ref(false)
const activeCodeDiff = ref<MessageCodeDiffResponse | null>(null)
const codeDiffError = ref('')
const activeCodeDiffMessageId = ref('')

const taskNodeStats = computed(() => {
  const counts = { total: taskNodes.value.length, pending: 0, running: 0, completed: 0, blocked: 0 }
  for (const node of taskNodes.value) {
    if (node.status === 'pending') counts.pending += 1
    else if (node.status === 'running') counts.running += 1
    else if (node.status === 'completed') counts.completed += 1
    else if (node.status === 'blocked') counts.blocked += 1
  }
  return counts
})
const hasSidePane = computed(() => manageOpen.value || taskOpen.value || projectFilesOpen.value || deployOpen.value)
const activeDeploymentJob = computed(() => {
  if (!activeGroupId.value) return null
  return deploymentJobs.value[activeGroupId.value] || null
})
const activePreviewJob = computed(() => {
  if (!activeGroupId.value) return null
  return previewJobs.value[activeGroupId.value] || null
})
const shellStyle = computed(() => ({
  '--side-pane-width': `${sidePaneWidth.value}px`,
}))

function slugify(text: string) {
  return (
    text
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-+|-+$/g, '')
      .slice(0, 48) || 'project'
  )
}

function deployEnvTextToRecord() {
  const env: Record<string, string> = {}
  for (const rawLine of deployDraft.envText.split('\n')) {
    const line = rawLine.trim()
    if (!line) continue
    const divider = line.indexOf('=')
    if (divider <= 0) continue
    const key = line.slice(0, divider).trim()
    const value = line.slice(divider + 1).trim()
    if (!key) continue
    env[key] = value
  }
  return env
}

function resetDeployDraftFromContext() {
  const group = activeGroup.value
  if (!group) return
  const job = activeDeploymentJob.value
  const slug = slugify(group.name || 'project')
  const hostPort = job?.spec?.ports && Array.isArray(job.spec.ports) && job.spec.ports[0] && typeof job.spec.ports[0] === 'object'
    ? Number((job.spec.ports[0] as { host_port?: unknown }).host_port)
    : buildDefaultDeployPort(group)
  const containerPort = job?.spec?.ports && Array.isArray(job.spec.ports) && job.spec.ports[0] && typeof job.spec.ports[0] === 'object'
    ? Number((job.spec.ports[0] as { container_port?: unknown }).container_port)
    : 80
  deployDraft.imageRef = job?.image_ref || `agenthub/${slug}:latest`
  deployDraft.containerName = job?.container_name || `agenthub-${slug}`
  deployDraft.dockerfilePath = job?.dockerfile_path || 'Dockerfile'
  deployDraft.buildContextPath = job?.build_context_path || '.'
  deployDraft.hostPort = Number.isFinite(hostPort) && hostPort > 0 ? hostPort : buildDefaultDeployPort(group)
  deployDraft.containerPort = Number.isFinite(containerPort) && containerPort > 0 ? containerPort : 80
  deployDraft.installCommand = String(job?.spec?.install_command || '').trim()
  deployDraft.testCommand = String(job?.spec?.test_command || '').trim()
  deployDraft.buildCommand = String(job?.spec?.build_command || '').trim()
  deployDraft.containerCommand = String(job?.spec?.container_command || '').trim()
  const env = job?.spec?.env
  if (env && typeof env === 'object' && !Array.isArray(env)) {
    deployDraft.envText = Object.entries(env as Record<string, unknown>)
      .map(([key, value]) => `${key}=${String(value ?? '')}`)
      .join('\n')
  } else {
    deployDraft.envText = ''
  }
}

function buildDefaultDeployPort(group: Group | null) {
  const workspaceId = Number(group?.workspace_id || 0)
  return workspaceId > 0 ? Math.min(65535, 18000 + workspaceId) : 18080
}

watch(
  () => createType.value,
  (t) => {
    createErr.value = ''
    // personal 只允许选 1 个 第二成员，这里直接清空已选用户，避免误选造成 400
    if (t === 'personal') {
      pickedUserIds.value = new Set()
    }
  },
)

function normalizeMessage(raw: Message ): Message {
  return {
    ...raw,
    id: String(raw.id ?? ''),
    group_id: String(raw.group_id ?? ''),
    sender_member_id: String(raw.sender_member_id ?? ''),
    message_type: String(raw.message_type ?? 'text'),
    content: String(raw.content ?? ''),
    reply_to_message_id: raw.reply_to_message_id == null ? null : String(raw.reply_to_message_id),
    metadata_json: String(raw.metadata_json ?? '{}'),
    created_at: String(raw.created_at ?? ''),
    updated_at: String(raw.updated_at ?? ''),
  }
}

function messageMeta(raw: Message): Record<string, unknown> {
  try {
    return JSON.parse(String(raw.metadata_json || '{}')) as Record<string, unknown>
  } catch {
    return {}
  }
}

function deployIdFromMessages() {
  for (let index = messages.value.length - 1; index >= 0; index -= 1) {
    const meta = messageMeta(messages.value[index]!)
    const deploy = meta.deploy_result
    if (!deploy || typeof deploy !== 'object' || Array.isArray(deploy)) continue
    const deploymentId = Number((deploy as { deployment_id?: unknown }).deployment_id)
    if (Number.isFinite(deploymentId) && deploymentId > 0) return deploymentId
  }
  return null
}

async function loadGroups() {
  loadingGroups.value = true
  try {
    const res = await apiListGroups()
    groups.value = res.data
    const qid = String(route.query.groupId || '').trim()
    const preferred = qid ? groups.value.find((g) => String(g.id) === qid) : null
    if (!activeGroupId.value) {
      if (preferred) await selectGroup(preferred.id)
      else if (groups.value.length > 0 && groups.value[0]) await selectGroup(groups.value[0].id)
    }
  } finally {
    loadingGroups.value = false
  }
}

async function selectGroup(id: string) {
  const seq = ++loadSeq
  activeGroupId.value = id
  manageOpen.value = false
  closeTaskPlanner()
  projectFilesOpen.value = false
  deployOpen.value = false
  addMemberOpen.value = false
  closeCodeDiffPanel()
  closeMessageEventsPanel()
  projectActiveFilePath.value = ''
  projectOpenDirs.value = {}
  const [mRes, msgRes] = await Promise.all([apiListMembers(id), apiListMessages(id, undefined, 50)])
  if (seq !== loadSeq || String(activeGroupId.value) !== String(id)) return
  members.value = mRes.data
  messages.value = msgRes.data.map((item) => normalizeMessage(item))
  replyToMessageId.value = ''
  pendingScrollToMessageId.value = ''
  selectedMentions.value = new Set()
  mentionSuggestOpen.value = false
  mentionQuery.value = ''
  updatePreview(id)
  if (supportsProjectWorkspace(activeGroup.value)) {
    resetDeployDraftFromContext()
  }
  connectWs(id)
}

function updatePreview(groupId: string) {
  const last = messages.value.at(-1)
  if (!last) return
  lastPreviewMap.value[groupId] = last.content
  lastTimeMap.value[groupId] = new Date(last.created_at).toLocaleDateString()
}

function upsertMessage(nextMessage: Message) {
  const nextId = String(nextMessage.id)
  const index = messages.value.findIndex((item) => String(item.id) === nextId)
  if (index < 0) {
    messages.value = [...messages.value, nextMessage]
    return
  }
  const next = messages.value.slice()
  next[index] = {
    ...next[index],
    ...nextMessage,
  }
  messages.value = next
}

function connectWs(groupId: string) {
  const seq = ++wsSeq
  if (wsReconnectTimer != null) {
    window.clearTimeout(wsReconnectTimer)
    wsReconnectTimer = null
  }
  if (ws.value) {
    try {
      ws.value.close()
    } catch {}
    ws.value = null
  }
  const token = localStorage.getItem('token')
  if (!token) return
  const url = `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws/groups/${groupId}?token=${encodeURIComponent(token)}`
  const socket = new WebSocket(url)
  const pingTimer = window.setInterval(() => {
    try {
      if (socket.readyState === WebSocket.OPEN) socket.send('ping')
    } catch {}
  }, 15000)
  socket.onopen = () => {
    if (seq !== wsSeq || ws.value !== socket) return
    wsReconnectAttempts = 0
    // Keep the connection alive by sending a tiny ping periodically.
    // Server's ws endpoint currently blocks on receive_text().
    try {
      socket.send('ping')
    } catch {}
  }
  socket.onerror = () => {
    // ignore; UI will still work via refresh/load
  }
  socket.onclose = () => {
    if (seq !== wsSeq || ws.value !== socket) return
    try {
      window.clearInterval(pingTimer)
    } catch {}
    ws.value = null
    wsReconnectAttempts += 1
    if (wsReconnectAttempts >= 5) {
      ElMessage.warning('聊天实时连接已断开，请刷新页面或重新登录后重试')
      return
    }
    const delay = Math.min(800 * 2 ** (wsReconnectAttempts - 1), 5000)
    wsReconnectTimer = window.setTimeout(() => {
      wsReconnectTimer = null
      if (String(activeGroupId.value) === String(groupId)) connectWs(groupId)
    }, delay)
  }
  socket.onmessage = (evt) => {
    if (seq !== wsSeq || ws.value !== socket) return
    try {
      const payload = JSON.parse(evt.data)
      if (payload.event === 'message.created' || payload.event === 'message.updated') {
        const msg = normalizeMessage(payload.data)
        if (
          String(msg.group_id) === String(groupId) &&
          String(activeGroupId.value) === String(groupId)
        ) {
          upsertMessage(msg)
          updatePreview(groupId)
          const meta = messageMeta(msg)
          if (meta.preview_result) {
            void loadCurrentPreview()
          }
          if (meta.deploy_result) {
            void loadCurrentDeployment()
          }
        }
      } else if (payload.event === 'reply.failed') {
        const data = (payload.data || {})
        if (
          String(data.group_id || '') === String(groupId) &&
          String(activeGroupId.value) === String(groupId)
        ) {
          const errText = String(data.error || 'unknown error')
          ElMessage.error(`AI回复失败：${errText}`)
          const systemMsg = normalizeMessage({
            id: `local-reply-failed-${Date.now()}`,
            group_id: groupId,
            sender_member_id: 'system',
            message_type: 'system',
            content: `系统提示：AI 回复失败（${errText}）`,
            metadata_json: '{}',
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          })
          messages.value = [...messages.value, systemMsg]
          updatePreview(groupId)
        }
      }
    } catch {
      // ignore
    }
  }
  ws.value = socket
}

async function send() {
  if (!activeGroup.value) return
  const userMember = currentUserMember.value
  if (!userMember) return
  const text = draft.value.trim()
  if (!text) return

  const mentionIds = new Set<string>(selectedMentions.value)
  for (const m of agentMembers.value) {
    const name = (m.display_name || '').trim()
    if (!name) continue
    if (text.includes(`@${name}`)) mentionIds.add(String(m.id))
  }
  const meta =
    JSON.stringify(
      {
        ...(mentionIds.size > 0
          ? { mentions: Array.from(mentionIds).map((id) => ({ kind: 'agent', member_id: id })) }
          : {}),
        ...(replyToMessageId.value ? { reply_to: String(replyToMessageId.value) } : {}),
      },
      undefined,
      0,
    )

  draft.value = ''
  const res = await apiCreateMessage({
    group_id: activeGroup.value.id,
    sender_member_id: userMember.id,
    message_type: 'text',
    content: text,
    metadata_json: meta,
    reply_to_message_id: replyToMessageId.value || null,
  })
  // Optimistic append: even if WS is disconnected, show the sent message immediately.
  const created = normalizeMessage(res.data)
  upsertMessage(created)
  updatePreview(activeGroup.value.id)
  selectedMentions.value = new Set()
  replyToMessageId.value = ''
}

function setReplyTarget(messageId: string) {
  replyToMessageId.value = String(messageId || '').trim()
  void nextTick(() => composerRef.value?.focusEditor?.())
}

function clearReplyTarget() {
  replyToMessageId.value = ''
}

function handleScrollTargetHandled(messageId: string) {
  if (String(pendingScrollToMessageId.value) === String(messageId)) {
    pendingScrollToMessageId.value = ''
  }
}

async function locateMessage(messageId: string) {
  const targetId = String(messageId || '').trim()
  const groupId = String(activeGroupId.value || '').trim()
  if (!targetId || !groupId) return
  if (messages.value.some((item) => String(item.id) === targetId)) {
    pendingScrollToMessageId.value = targetId
    return
  }

  const requestId = ++locatingMessageRequestId
  let cursor = String(messages.value[0]?.id || '').trim()
  let found = false

  for (let pass = 0; pass < 20; pass += 1) {
    if (!cursor) break
    const res = await apiListMessages(groupId, cursor, 50)
    if (requestId !== locatingMessageRequestId || String(activeGroupId.value || '') !== groupId) return
    const older = res.data.map((item) => normalizeMessage(item))
    if (older.length === 0) break

    const existingIds = new Set(messages.value.map((item) => String(item.id)))
    const prepend = older.filter((item) => !existingIds.has(String(item.id)))
    if (prepend.length > 0) {
      messages.value = [...prepend, ...messages.value]
    }
    if (messages.value.some((item) => String(item.id) === targetId)) {
      found = true
      break
    }
    const nextCursor = String(older[0]?.id || '').trim()
    if (!nextCursor || nextCursor === cursor) break
    cursor = nextCursor
  }

  if (!found) {
    ElMessage.info('未找到要定位的原消息，可能已超出当前可加载范围')
    return
  }
  pendingScrollToMessageId.value = targetId
}

function removeMention(memberId: string) {
  const next = new Set(selectedMentions.value)
  next.delete(memberId)
  selectedMentions.value = next
}

function openMention() {
  if (!canMentionAgents.value) return
  const hasActiveMention = /(?:^|\s)@([^\s@]*)$/.test(draft.value)
  const nextValue = hasActiveMention
    ? draft.value
    : `${draft.value}${draft.value && !/\s$/.test(draft.value) ? ' ' : ''}@`
  updateDraft(nextValue)
  void nextTick(() => composerRef.value?.focusEditor?.())
}

function syncMentionSuggest(value: string) {
  if (!canMentionAgents.value) {
    mentionSuggestOpen.value = false
    mentionQuery.value = ''
    return
  }
  const match = value.match(/(?:^|\s)@([^\s@]*)$/)
  if (!match) {
    mentionSuggestOpen.value = false
    mentionQuery.value = ''
    return
  }
  mentionSuggestOpen.value = true
  mentionQuery.value = (match[1] || '').trim()
}

function updateDraft(value: string) {
  draft.value = value
  syncMentionSuggest(value)
}

function onDraftKeydown(event: KeyboardEvent) {
  if (event.key !== 'Enter' || event.shiftKey || event.isComposing) return
  event.preventDefault()
  void send()
}

function pickMention(memberId: string) {
  const m = agentMembers.value.find((x) => x.id === memberId)
  if (!m) return
  const next = new Set(selectedMentions.value)
  next.add(memberId)
  selectedMentions.value = next

  // Replace the last "@xxx" token with "@DisplayName "
  const parts = draft.value.split(/\s/)
  if (parts.length > 0) {
    const last = parts.at(-1) || ''
    if (last.startsWith('@')) {
      parts[parts.length - 1] = `@${m.display_name}`
      draft.value = parts.join(' ') + ' '
    }
  }
  mentionSuggestOpen.value = false
  mentionQuery.value = ''
  void nextTick(() => composerRef.value?.focusEditor?.())
}

function getSidePaneBounds() {
  const shellWidth = shellRef.value?.clientWidth || window.innerWidth
  const layoutMax =
    shellWidth - LEFT_PANE_WIDTH - SIDE_PANE_MIN_CHAT_WIDTH - SHELL_COLUMN_GAP
  const max = Math.min(
    SIDE_PANE_MAX_WIDTH,
    Math.max(SIDE_PANE_COMPACT_MIN_WIDTH, layoutMax),
  )
  return {
    min: Math.min(SIDE_PANE_MIN_WIDTH, max),
    max,
  }
}

function clampSidePaneWidth(width: number) {
  const bounds = getSidePaneBounds()
  return Math.min(Math.max(width, bounds.min), bounds.max)
}

function syncSidePaneWidth(width: number) {
  sidePaneWidth.value = clampSidePaneWidth(width)
  try {
    localStorage.setItem(SIDE_PANE_WIDTH_STORAGE_KEY, String(sidePaneWidth.value))
  } catch {}
}

function updateSidePaneWidthFromClientX(clientX: number) {
  const shellRect = shellRef.value?.getBoundingClientRect()
  if (!shellRect) return
  syncSidePaneWidth(shellRect.right - clientX)
}

function onSidePaneResize(event: PointerEvent) {
  if (!sidePaneDragging.value) return
  updateSidePaneWidthFromClientX(event.clientX)
}

function stopSidePaneResize() {
  if (!sidePaneDragging.value) return
  sidePaneDragging.value = false
  document.body.style.cursor = ''
  document.body.style.userSelect = ''
  window.removeEventListener('pointermove', onSidePaneResize)
  window.removeEventListener('pointerup', stopSidePaneResize)
  window.removeEventListener('pointercancel', stopSidePaneResize)
}

function startSidePaneResize(event: PointerEvent) {
  if (!hasSidePane.value) return
  sidePaneDragging.value = true
  document.body.style.cursor = 'col-resize'
  document.body.style.userSelect = 'none'
  updateSidePaneWidthFromClientX(event.clientX)
  window.addEventListener('pointermove', onSidePaneResize)
  window.addEventListener('pointerup', stopSidePaneResize)
  window.addEventListener('pointercancel', stopSidePaneResize)
}

function handleWindowResize() {
  syncSidePaneWidth(sidePaneWidth.value)
}

function openManage() {
  manageErr.value = ''
  closeTaskPlanner()
  projectFilesOpen.value = false
  deployOpen.value = false
  codeDiffOpen.value = false
  closeMessageEventsPanel()
  addMemberOpen.value = false
  manageOpen.value = true
  if (supportsProjectWorkspace(activeGroup.value)) {
    void loadMemoryConfig()
    void loadMemoryStatus()
    void loadAssistantConfig()
    void loadTaskRuns()
  }
}

function closeTaskRunDetail() {
  taskDetailOpen.value = false
}

function closeTaskPlanner() {
  taskOpen.value = false
  taskDetailOpen.value = false
}

function openTaskPlanner() {
  if (!supportsProjectWorkspace(activeGroup.value)) return
  manageOpen.value = false
  projectFilesOpen.value = false
  deployOpen.value = false
  codeDiffOpen.value = false
  closeMessageEventsPanel()
  taskOpen.value = true
  taskDetailOpen.value = false
  void loadTaskRuns()
}

async function openDeployPanel() {
  if (!supportsProjectWorkspace(activeGroup.value)) return
  closeTaskPlanner()
  manageOpen.value = false
  projectFilesOpen.value = false
  codeDiffOpen.value = false
  closeMessageEventsPanel()
  deployOpen.value = true
  await Promise.all([reloadProjectFiles(), loadCurrentPreview(), loadCurrentDeployment()])
}

function closeCodeDiffPanel() {
  codeDiffOpen.value = false
  codeDiffLoading.value = false
  activeCodeDiff.value = null
  codeDiffError.value = ''
  activeCodeDiffMessageId.value = ''
}

function closeMessageEventsPanel() {
  messageEventOpen.value = false
  messageEventLoading.value = false
  messageEventError.value = ''
  activeMessageEventMessageId.value = ''
  activeMessageEvents.value = []
}

async function openCodeDiffPanel(messageId: string) {
  if (!supportsProjectWorkspace(activeGroup.value)) return
  closeTaskPlanner()
  manageOpen.value = false
  projectFilesOpen.value = false
  deployOpen.value = false
  closeMessageEventsPanel()
  codeDiffOpen.value = true
  codeDiffLoading.value = true
  activeCodeDiff.value = null
  codeDiffError.value = ''
  activeCodeDiffMessageId.value = String(messageId)
  try {
    const res = await apiGetMessageCodeDiff(messageId)
    if (String(activeCodeDiffMessageId.value) !== String(messageId)) return
    activeCodeDiff.value = res.data
  } catch (error) {
    if (String(activeCodeDiffMessageId.value) !== String(messageId)) return
    codeDiffError.value = error instanceof Error ? error.message : String(error)
  } finally {
    if (String(activeCodeDiffMessageId.value) === String(messageId)) {
      codeDiffLoading.value = false
    }
  }
}

async function openMessageEventsPanel(messageId: string) {
  if (!messageId) return
  closeCodeDiffPanel()
  messageEventOpen.value = true
  activeMessageEventMessageId.value = String(messageId)
  const cached = messageEventCache.value[String(messageId)]
  if (cached) {
    activeMessageEvents.value = cached
    messageEventLoading.value = false
    messageEventError.value = ''
    return
  }
  messageEventLoading.value = true
  messageEventError.value = ''
  activeMessageEvents.value = []
  try {
    const res = await apiListMessageEvents(messageId)
    if (String(activeMessageEventMessageId.value) !== String(messageId)) return
    activeMessageEvents.value = res.data
    messageEventCache.value = {
      ...messageEventCache.value,
      [String(messageId)]: res.data,
    }
  } catch (error) {
    if (String(activeMessageEventMessageId.value) !== String(messageId)) return
    messageEventError.value = error instanceof Error ? error.message : String(error)
  } finally {
    if (String(activeMessageEventMessageId.value) === String(messageId)) {
      messageEventLoading.value = false
    }
  }
}

async function loadAssistantConfig() {
  if (!activeGroup.value || activeGroup.value.type !== 'project') return
  assistantCfgLoading.value = true
  try {
    const res = await apiGetGroupAssistantConfig(activeGroup.value.id)
    assistantCfg.value = res.data
  } catch (error) {
    assistantCfg.value = null
    manageErr.value = error instanceof Error ? error.message : String(error)
  } finally {
    assistantCfgLoading.value = false
  }
}

async function saveAssistantConfig() {
  if (!activeGroup.value || activeGroup.value.type !== 'project') return
  assistantCfgSaving.value = true
  manageErr.value = ''
  try {
    const res = await apiUpdateGroupAssistantConfig(activeGroup.value.id, {
      enabled: assistantCfg.value?.enabled ? 1 : 0,
    })
    assistantCfg.value = res.data
    ElMessage.success('管家配置已保存')
  } catch (e) {
    manageErr.value = e instanceof Error ? e.message : String(e)
  } finally {
    assistantCfgSaving.value = false
  }
}

async function loadTaskRuns() {
  if (!activeGroup.value || activeGroup.value.type !== 'project') return
  taskRunsLoading.value = true
  try {
    const res = await apiListGroupTaskRuns(activeGroup.value.id)
    taskRuns.value = res.data
    if (
      activeRunId.value &&
      !taskRuns.value.some((r) => String(r.id) === String(activeRunId.value))
    ) {
      activeRunId.value = ''
    }
    if (!activeRunId.value && taskRuns.value[0]) {
      activeRunId.value = String(taskRuns.value[0].id)
    }
    if (activeRunId.value) {
      await loadTaskRunDetails(activeRunId.value)
    } else {
      taskNodes.value = []
      taskGraph.value = null
    }
  } catch (error) {
    taskRuns.value = []
    taskNodes.value = []
    taskGraph.value = null
    manageErr.value = error instanceof Error ? error.message : String(error)
  } finally {
    taskRunsLoading.value = false
  }
}

async function loadTaskRunDetails(runId: string) {
  if (!runId) return
  taskNodesLoading.value = true
  try {
    const [nodesRes, graphRes] = await Promise.all([apiListGroupTaskNodes(runId), apiGetGroupTaskGraph(runId)])
    taskNodes.value = nodesRes.data
    taskGraph.value = graphRes.data
  } catch (error) {
    taskNodes.value = []
    taskGraph.value = null
    manageErr.value = error instanceof Error ? error.message : String(error)
  } finally {
    taskNodesLoading.value = false
  }
}

async function openTaskRunDetail(runId: string) {
  if (!runId) return
  activeRunId.value = String(runId)
  taskNodes.value = []
  taskGraph.value = null
  taskDetailOpen.value = true
  await loadTaskRunDetails(activeRunId.value)
}

async function selectTaskRun(runId: string) {
  await openTaskRunDetail(runId)
}

async function createTaskRunNow() {
  if (!activeGroup.value) return
  const me = currentUserMember.value
  if (!me) {
    manageErr.value = '当前会话缺少用户成员'
    return
  }
  const title = taskCreateTitle.value.trim()
  const goal = taskCreateGoal.value.trim()
  if (!title || !goal) {
    manageErr.value = '请输入任务标题与目标'
    return
  }
  try {
    const res = await apiCreateGroupTaskRunFromText({
      group_id: activeGroup.value.id,
      creator_member_id: me.id,
      title,
      goal_text: goal,
      node_text: taskCreateNodeText.value,
    })
    taskCreateOpen.value = false
    taskCreateTitle.value = ''
    taskCreateGoal.value = ''
    taskCreateNodeText.value = '需求澄清与初始计划 | manager'
    await loadTaskRuns()
    if (res.data?.id) {
      activeRunId.value = String(res.data.id)
      await loadTaskRunDetails(activeRunId.value)
    } else if (activeRunId.value) {
      await loadTaskRunDetails(activeRunId.value)
    }
    ElMessage.success('任务运行已创建')
  } catch (e) {
    manageErr.value = e instanceof Error ? e.message : String(e)
  }
}

async function claimNode(node: GroupTaskNode) {
  const me = currentUserMember.value
  if (!me) return
  try {
    await apiClaimGroupTaskNode(String(node.id), String(me.id))
    await loadTaskRunDetails(String(node.run_id))
  } catch (e) {
    manageErr.value = e instanceof Error ? e.message : String(e)
  }
}

async function completeNode(node: GroupTaskNode) {
  const summary = window.prompt('请输入节点完成总结（会用于管家复核）') || ''
  if (!summary.trim()) return
  try {
    await apiCompleteGroupTaskNode(String(node.id), summary.trim())
    await loadTaskRunDetails(String(node.run_id))
  } catch (e) {
    manageErr.value = e instanceof Error ? e.message : String(e)
  }
}

async function reviewNode(node: GroupTaskNode, status: 'approved' | 'rework') {
  const note = status === 'rework' ? window.prompt('请输入返工说明') || '' : ''
  try {
    await apiReviewGroupTaskNode(String(node.id), { manager_review_status: status, note })
    await loadTaskRunDetails(String(node.run_id))
  } catch (e) {
    manageErr.value = e instanceof Error ? e.message : String(e)
  }
}

async function loadMemoryConfig() {
  if (!activeGroup.value || activeGroup.value.type !== 'project') return
  memoryCfgLoading.value = true
  try {
    const res = await apiGetGroupMemoryCompressorConfig(activeGroup.value.id)
    memoryCfg.value = res.data
  } catch (e) {
    manageErr.value = e instanceof Error ? e.message : String(e)
  } finally {
    memoryCfgLoading.value = false
  }
}

async function loadMemoryStatus() {
  if (!activeGroup.value || activeGroup.value.type !== 'project') return
  try {
    const res = await apiGetGroupMemoryCompressorStatus(activeGroup.value.id)
    memoryStatus.value = res.data
  } catch (e) {
    manageErr.value = e instanceof Error ? e.message : String(e)
  }
}

async function saveMemoryConfig() {
  if (!activeGroup.value || activeGroup.value.type !== 'project') return
  manageErr.value = ''
  memoryCfgSaving.value = true
  try {
    const res = await apiUpdateGroupMemoryCompressorConfig(activeGroup.value.id, {
      enabled: Boolean(memoryCfg.value.enabled),
      trigger_tokens: Number(memoryCfg.value.trigger_tokens || 0),
      keep_recent_messages: Number(memoryCfg.value.keep_recent_messages || 0),
      min_interval_seconds: Number(memoryCfg.value.min_interval_seconds || 0),
    })
    memoryCfg.value = res.data
    await loadMemoryStatus()
    ElMessage.success('长期记忆自动提炼配置已保存')
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e)
    manageErr.value = msg
    ElMessage.error(msg)
  } finally {
    memoryCfgSaving.value = false
  }
}

async function runMemoryCompressNow() {
  if (!activeGroup.value || activeGroup.value.type !== 'project') return
  manageErr.value = ''
  memoryCompressing.value = true
  try {
    const res = await apiRunGroupMemoryCompress(activeGroup.value.id)
    if (res.data.compressed) {
      ElMessage.success(`提炼完成，压缩 ${res.data.compressed_count || 0} 条消息`)
    } else {
      ElMessage.info(`本次未触发提炼：${res.data.reason || 'no-op'}`)
    }
    await loadMemoryStatus()
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e)
    manageErr.value = msg
    ElMessage.error(msg)
  } finally {
    memoryCompressing.value = false
  }
}

async function openProjectCode() {
  if (!supportsProjectWorkspace(activeGroup.value)) return
  closeTaskPlanner()
  manageOpen.value = false
  deployOpen.value = false
  codeDiffOpen.value = false
  closeMessageEventsPanel()
  projectFilesOpen.value = true
  await reloadProjectFiles()
  if (projectActiveFilePath.value) {
    await openProjectFile(projectActiveFilePath.value)
  }
}

async function reloadProjectFiles() {
  if (!activeGroup.value || activeGroup.value.type !== 'project') return
  projectFilesLoading.value = true
  try {
    const res = await apiListProjectCode(activeGroup.value.id)
    projectFilesEntries.value = res.data
    if (
      projectActiveFilePath.value &&
      !projectFilesEntries.value.some((item) => item.path === projectActiveFilePath.value)
    ) {
      projectActiveFilePath.value = ''
    }
    if (projectActiveFilePath.value) {
      await openProjectFile(projectActiveFilePath.value)
    }
  } catch (e) {
    projectFilesEntries.value = []
    manageErr.value = e instanceof Error ? e.message : String(e)
  } finally {
    projectFilesLoading.value = false
  }
}

function toggleProjectDir(path: string) {
  projectOpenDirs.value = { ...projectOpenDirs.value, [path]: !projectOpenDirs.value[path] }
}

function openProjectFile(path: string) {
  const group = activeGroup.value
  if (!group || group.type !== 'project') return
  projectActiveFilePath.value = path
}

function setDeploymentJob(groupId: string, job: DeploymentJob | null) {
  deploymentJobs.value = {
    ...deploymentJobs.value,
    [groupId]: job,
  }
}

function setPreviewJob(groupId: string, job: PreviewJob | null) {
  previewJobs.value = {
    ...previewJobs.value,
    [groupId]: job,
  }
}

async function loadCurrentPreview() {
  const group = activeGroup.value
  const workspaceId = Number(group?.workspace_id || 0)
  if (!group || !workspaceId) return
  try {
    const res = await apiGetWorkspacePreview(workspaceId)
    setPreviewJob(activeGroupId.value, res.data)
  } catch {
    setPreviewJob(activeGroupId.value, null)
  }
}

async function loadCurrentDeployment() {
  if (!activeGroupId.value) return
  const deploymentId = deployIdFromMessages()
  if (!deploymentId) {
    setDeploymentJob(activeGroupId.value, null)
    return
  }
  try {
    const res = await apiGetDeployment(deploymentId)
    setDeploymentJob(activeGroupId.value, res.data)
  } catch {
    // keep current state if fetch fails
  }
}

function buildDeploymentRequest(): DeploymentRequest | null {
  const group = activeGroup.value
  if (!group) return null
  const imageRef = deployDraft.imageRef.trim()
  const containerName = deployDraft.containerName.trim()
  if (!imageRef || !containerName) return null
  return {
    workspace_id: Number(group.workspace_id),
    image_ref: imageRef,
    container_name: containerName,
    dockerfile_path: deployDraft.dockerfilePath.trim() || 'Dockerfile',
    build_context_path: deployDraft.buildContextPath.trim() || '.',
    install_command: deployDraft.installCommand.trim() || null,
    test_command: deployDraft.testCommand.trim() || null,
    build_command: deployDraft.buildCommand.trim() || null,
    container_command: deployDraft.containerCommand.trim() || null,
    env: deployEnvTextToRecord(),
    ports: [
      {
        host_port: Number(deployDraft.hostPort),
        container_port: Number(deployDraft.containerPort),
        protocol: 'tcp',
      },
    ],
  }
}

async function deployProject() {
  const payload = buildDeploymentRequest()
  if (!activeGroupId.value || !payload) {
    manageErr.value = '请先在编辑器页补全镜像名和容器名'
    ElMessage.error(manageErr.value)
    return
  }
  deployPending.value = true
  manageErr.value = ''
  try {
    const res = await apiCreateDeployment(payload)
    setDeploymentJob(activeGroupId.value, res.data)
    if (res.data.status === 'succeeded') {
      ElMessage.success('部署完成，可直接打开效果')
      return
    }
    ElMessage.error(res.data.error_message || '部署失败，请查看日志')
  } catch (error) {
    const msg = error instanceof Error ? error.message : String(error)
    manageErr.value = msg
    ElMessage.error(msg)
  } finally {
    deployPending.value = false
  }
}

async function retryDeployment(deploymentId: number) {
  if (!activeGroupId.value) return
  deployPending.value = true
  manageErr.value = ''
  try {
    const res = await apiRetryDeployment(deploymentId)
    setDeploymentJob(activeGroupId.value, res.data)
    if (res.data.status === 'succeeded') {
      ElMessage.success('重新部署完成')
      return
    }
    ElMessage.error(res.data.error_message || '重新部署失败，请查看日志')
  } catch (error) {
    const msg = error instanceof Error ? error.message : String(error)
    manageErr.value = msg
    ElMessage.error(msg)
  } finally {
    deployPending.value = false
  }
}

async function closePreview() {
  const group = activeGroup.value
  const workspaceId = Number(group?.workspace_id || 0)
  if (!group || !workspaceId || !activeGroupId.value) return
  previewPending.value = true
  manageErr.value = ''
  try {
    const res = await apiDeleteWorkspacePreview(workspaceId)
    setPreviewJob(activeGroupId.value, res.data)
    ElMessage.success('预览已关闭')
  } catch (error) {
    const msg = error instanceof Error ? error.message : String(error)
    manageErr.value = msg
    ElMessage.error(msg)
  } finally {
    previewPending.value = false
  }
}

async function openPreview() {
  const group = activeGroup.value
  const workspaceId = Number(group?.workspace_id || 0)
  if (!group || !workspaceId || !activeGroupId.value) return
  previewPending.value = true
  manageErr.value = ''
  try {
    const preview = activePreviewJob.value
    const deployment = activeDeploymentJob.value
    const previewSpec = preview?.spec || {}
    const deploymentSpec = deployment?.spec || {}
    const envSource = previewSpec.env || deploymentSpec.env
    const env =
      envSource && typeof envSource === 'object' && !Array.isArray(envSource)
        ? Object.fromEntries(
            Object.entries(envSource as Record<string, unknown>).map(([key, value]) => [key, String(value ?? '')]),
          )
        : {}
    const res = await apiCreatePreview({
      workspace_id: workspaceId,
      source_path: preview?.source_path || '.',
      sandbox_image: preview?.sandbox_image || deployment?.sandbox_image || null,
      install_command: String(previewSpec.install_command || deploymentSpec.install_command || '').trim() || null,
      build_command: String(previewSpec.build_command || deploymentSpec.build_command || '').trim() || null,
      env,
      host_port: preview?.host_port || null,
    })
    setPreviewJob(activeGroupId.value, res.data)
    ElMessage.success('预览已重新打开')
  } catch (error) {
    const msg = error instanceof Error ? error.message : String(error)
    manageErr.value = msg
    ElMessage.error(msg)
  } finally {
    previewPending.value = false
  }
}

function openAddMember() {
  if (!supportsProjectWorkspace(activeGroup.value)) return
  addMemberErr.value = ''
  pickedUserIds.value = new Set()
  pickedAgentIds.value = new Set()
  addMemberType.value = 'project'
  addMemberName.value = ''
  addMemberOpen.value = true
}

async function addMembers() {
  if (!activeGroup.value) return
  if (activeGroup.value.type !== 'project') return
  const userIds = Array.from(pickedUserIds.value)
  const agentIds = Array.from(pickedAgentIds.value)
  if (userIds.length === 0 && agentIds.length === 0) {
    addMemberErr.value = '请选择至少 1 个成员'
    return
  }

  addMemberErr.value = ''
  adding.value = true
  try {
    await Promise.all([
      ...userIds.map(async (id) => {
        const u = users.value.find((x) => String(x.id) === String(id))
        const label = u?.display_name || u?.username || u?.email || id
        await apiAddUserMember({
          group_id: activeGroup.value!.id,
          user_ref: String(id),
          display_name: label,
          title: null,
        })
      }),
      ...agentIds.map(async (id) => {
        const a = agents.value.find((x) => String(x.id) === String(id))
        const label = a?.display_name || `Agent#${id}`
        await apiAddAgentMember({
          group_id: activeGroup.value!.id,
          agent_instance_id: String(id),
          display_name: label,
          title: null,
        })
      }),
    ])
    const mRes = await apiListMembers(activeGroup.value.id)
    members.value = mRes.data
    addMemberOpen.value = false
    pickedUserIds.value = new Set()
    pickedAgentIds.value = new Set()
  } catch (e) {
    addMemberErr.value = e instanceof Error ? e.message : String(e)
  } finally {
    adding.value = false
  }
}

async function removeMember(m: Member) {
  if (!activeGroup.value) return
  if (activeGroup.value.type !== 'project') return
  manageErr.value = ''
  try {
    await apiDeleteMember(m.id)
    const mRes = await apiListMembers(activeGroup.value.id)
    members.value = mRes.data
  } catch (e) {
    manageErr.value = e instanceof Error ? e.message : String(e)
  }
}

async function deleteActiveGroup() {
  if (!activeGroup.value) return
  const g = activeGroup.value
  try {
    await ElMessageBox.confirm(
      `确认删除会话「${g.name}」？该操作会删除成员与消息记录。`,
      '删除会话',
      {
        type: 'warning',
        confirmButtonText: '删除',
        cancelButtonText: '取消',
      },
    )
  } catch {
    return
  }
  manageErr.value = ''
  try {
    await apiDeleteGroup(g.id)
    ElMessage.success('已删除会话')
    manageOpen.value = false
    activeGroupId.value = ''
    members.value = []
    messages.value = []
    await loadGroups()
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e)
    manageErr.value = msg
    ElMessage.error(msg)
  }
}

onMounted(loadGroups)

onMounted(async () => {
  try {
    const saved = Number(localStorage.getItem(SIDE_PANE_WIDTH_STORAGE_KEY) || '')
    if (Number.isFinite(saved) && saved > 0) {
      sidePaneWidth.value = clampSidePaneWidth(saved)
    } else {
      sidePaneWidth.value = clampSidePaneWidth(SIDE_PANE_DEFAULT_WIDTH)
    }
  } catch {
    sidePaneWidth.value = clampSidePaneWidth(SIDE_PANE_DEFAULT_WIDTH)
  }
  window.addEventListener('resize', handleWindowResize)
  const [u, a, me] = await Promise.all([apiListUsers(), apiListAgents(), apiGetCurrentUser()])
  currentUserId.value = String(me.data.id || '')
  users.value = u.data.filter((item) => String(item.id) !== currentUserId.value)
  agents.value = a.data
})

onBeforeUnmount(() => {
  stopSidePaneResize()
  window.removeEventListener('resize', handleWindowResize)
  try {
    ws.value?.close()
  } catch {}
})

function togglePickUser(u: User) {
  const id = String(u.id)
  const next = new Set(pickedUserIds.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  pickedUserIds.value = next
}

function togglePickAgent(a: Agent) {
  const id = String(a.id)
  const next = new Set(pickedAgentIds.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  pickedAgentIds.value = next
}

async function createGroup() {
  createErr.value = ''
  const pickedUsers = Array.from(pickedUserIds.value).filter((id) => String(id) !== currentUserId.value)
  const pickedAgents = Array.from(pickedAgentIds.value)

  if (createType.value === 'personal') {
    // 按产品约束：personal 只选 1 个智能体（创建者自动加入）
    if (pickedUsers.length !== 0 || pickedAgents.length !== 1) {
      createErr.value = '单聊只能选择 1 个智能体（不需要选择用户）'
      return
    }
  }

  let name = createName.value.trim()
  if (!name) {
    if (createType.value === 'personal' && pickedAgents.length === 1) {
      const a = agents.value.find((x) => String(x.id) === pickedAgents[0])
      const label = a?.display_name || `Agent#${pickedAgents[0]}`
      name = `与${label}的单聊`
    } else {
      createErr.value = '请输入会话名称'
      return
    }
  }

  creating.value = true
  try {
    await apiCreateGroupFromSelection({
      name,
      description: null,
      type: createType.value,
      users: pickedUsers.map((id) => {
        const u = users.value.find((x) => String(x.id) === id)
        const label = u?.display_name || u?.username || u?.email || id
        return { user_id: String(id), user_label: label }
      }),
      agents: pickedAgents.map((id) => {
        const a = agents.value.find((x) => String(x.id) === id)
        const label = a?.display_name || `Agent#${id}`
        return { agent_id: String(id), agent_label: label }
      }),
    })
    createOpen.value = false
    createName.value = ''
    pickedUserIds.value = new Set()
    pickedAgentIds.value = new Set()
    await loadGroups()
  } catch (e) {
    createErr.value = e instanceof Error ? e.message : String(e)
  } finally {
    creating.value = false
  }
}
</script>

<style scoped>
.shell {
  height: calc(100vh - 36px);
  display: grid;
  grid-template-columns: 340px minmax(0, 1fr);
  gap: 12px;
  align-items: stretch;
  min-width: 0;
  min-height: 0;
}

.shell.withSidePane {
  grid-template-columns: 340px minmax(0, 1fr) var(--side-pane-width);
}

.shell > * {
  min-width: 0;
  min-height: 0;
}

.chatPane {
  background: var(--ah-panel-bg);
  backdrop-filter: blur(10px);
  border: 1px solid var(--ah-panel-border, var(--ah-border));
  border-radius: 18px;
  overflow: hidden;
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.sidePane {
  min-width: 0;
  min-height: 0;
  height: 100%;
  position: relative;
  overflow: hidden;
  display: flex;
}

.sidePane > * {
  flex: 1;
  min-width: 0;
  min-height: 0;
}
.sidePaneResize {
  position: absolute;
  top: 0;
  bottom: 0;
  left: -18px;
  width: 24px;
  cursor: col-resize;
  z-index: 3;
  touch-action: none;
}
.sidePaneResize::before {
  content: '';
  position: absolute;
  top: 18px;
  bottom: 18px;
  left: 50%;
  width: 4px;
  transform: translateX(-50%);
  border-radius: 999px;
  background: rgba(31, 35, 41, 0.1);
  transition: background 0.18s ease, box-shadow 0.18s ease;
}
.sidePaneResize:hover::before,
.sidePaneResize.dragging::before,
.shell.isResizingSidePane .sidePaneResize::before {
  background: var(--ah-primary);
  box-shadow: 0 0 0 4px color-mix(in srgb, var(--ah-primary) 24%, transparent);
}
.searchInput :deep() {
  height: 38px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.92);
  box-shadow: none;
}
.searchInput :deep() {
  color: rgba(31, 35, 41, 0.42);
}

.taskStat span {
  display: block;
  font-size: 12px;
  color: rgba(31, 35, 41, 0.58);
}
.taskStat strong {
  display: block;
  margin-top: 4px;
  font-size: 18px;
}

.fileTreeWrap :deep() {
  margin-bottom: 4px;
}

.mName {
  font-weight: 900;
}

.chatHeader {
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 18px;
  border-bottom: 1px solid rgba(31, 35, 41, 0.06);
  gap: 12px;
  flex: 0 0 auto;
}
.chatHeading {
  display: grid;
  gap: 4px;
  min-width: 0;
}
.chatTitle {
  font-size: 16px;
  font-weight: 900;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.chatMeta {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: rgba(31, 35, 41, 0.56);
}
.chatActions {
  display: flex;
  gap: 8px;
  align-items: center;
  flex: 0 0 auto;
}
.iconBtn {
  width: 34px;
  height: 34px;
  padding: 0;
  border-radius: 10px;
  background: rgba(31, 35, 41, 0.06);
  font-size: 16px;
}
.iconBtnLarge {
  font-size: 17px;
}
.iconBtn:hover,
.iconBtn:focus-visible {
  background: rgba(31, 35, 41, 0.1);
}
.iconBtn:disabled {
  opacity: 0.45;
}

.mentionList :deep(.el-table__row) {
  cursor: pointer;
}
.mentionList :deep(.el-table__row.active) {
  background: var(--ah-list-active-bg);
}
.mAvatar {
  width: 36px;
  height: 36px;
  border-radius: 12px;
  display: grid;
  place-items: center;
  background: var(--ah-primary-soft);
  font-size: 16px;
}
.mName {
  font-weight: 800;
}
.mCheck {
  color: var(--ah-primary-strong);
  display: flex;
  justify-content: center;
  font-size: 16px;
}

</style>
