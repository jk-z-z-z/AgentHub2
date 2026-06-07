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
        @open-code-diff="openCodeDiffPanel"
      />

      <MessageComposer
        :draft="draft"
        :can-mention-agents="canMentionAgents"
        :can-send="canSend"
        :selected-mentions="selectedMentions"
        :mention-suggest-open="mentionSuggestOpen"
        :filtered-agent-members="filteredAgentMembers"
        :mention-names="mentionNames"
        @update:draft="draft = $event"
        @keydown="onDraftKeydown"
        @open-mention="openMention"
        @send="send"
        @remove-mention="removeMention"
        @pick-mention="pickMention"
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
        @close="projectFilesOpen = false"
        @refresh="reloadProjectFiles"
        @open-file="openProjectFile"
        @toggle-dir="toggleProjectDir"
      />

      <MessageDeploymentPanel
        v-else-if="deployOpen"
        :active-group="activeGroup"
        :messages="messages"
        :project-files-entries="projectFilesEntries"
        :preview-job="activePreviewJob"
        :preview-pending="previewPending"
        :deployment-job="activeDeploymentJob"
        :deploy-pending="deployPending"
        @close="deployOpen = false"
        @close-preview="closePreview"
        @deploy="deployProject"
        @retry-deploy="retryDeployment"
      />

      <MessageCodeDiffPanel
        v-else-if="codeDiffOpen"
        :active-group="activeGroup"
        :loading="codeDiffLoading"
        :diff="activeCodeDiff"
        :error="codeDiffError"
        @close="closeCodeDiffPanel"
      />

      <MessageManagePanel
        v-else-if="manageOpen"
        :active-group="activeGroup"
        :members="members"
        :users="users"
        :agents="agents"
        :manage-err="manageErr"
        :adding="adding"
        :memory-cfg-loading="memoryCfgLoading"
        :memory-cfg-saving="memoryCfgSaving"
        :memory-compressing="memoryCompressing"
        :memory-cfg="memoryCfg"
        :memory-status="memoryStatus"
        :assistant-cfg-loading="assistantCfgLoading"
        :assistant-cfg-saving="assistantCfgSaving"
        :assistant-cfg="assistantCfg"
        v-model:add-kind="addKind"
        v-model:add-user-id="addUserId"
        v-model:add-agent-id="addAgentId"
        v-model:assistant-enabled="assistantCfgEnabled"
        @close="manageOpen = false"
        @delete-group="deleteActiveGroup"
        @remove-member="removeMember"
        @add-member="addMember"
        @save-memory-config="saveMemoryConfig"
        @run-memory-compress="runMemoryCompressNow"
        @refresh-memory-status="loadMemoryStatus"
        @save-assistant-config="saveAssistantConfig"
      />

      <TaskPlannerPanel
        v-else
        :active-group="activeGroup"
        :members="members"
        :runs="taskRuns"
        :active-run-id="activeRunId"
        :active-run="activeTaskRun"
        :graph="taskGraph"
        :nodes="taskNodes"
        :node-stats="taskNodeStats"
        :runs-loading="taskRunsLoading"
        :nodes-loading="taskNodesLoading"
        :manage-err="manageErr"
        @close="taskOpen = false"
        @refresh-runs="loadTaskRuns"
        @select-run="selectTaskRun"
        @create-run="taskCreateOpen = true"
        @refresh-run-details="loadTaskRunDetails"
        @claim-node="claimNode"
        @complete-node="completeNode"
        @review-node="reviewNode"
      />
    </aside>
  </div>

  <el-dialog v-model="mentionOpen" title="选择要@的智能体" width="420px">
    <el-table
      :data="agentMembers"
      class="mentionList"
      height="320"
      empty-text="该会话没有智能体成员"
      :row-class-name="mentionRowClassName"
      @row-click="handleMentionRowClick"
    >
      <el-table-column label="" width="58">
        <template #default>
          <div class="mAvatar">
            <el-icon>
              <Monitor />
            </el-icon>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="智能体" min-width="180">
        <template #default="{ row }">
          <div class="mName">{{ row.display_name }}</div>
        </template>
      </el-table-column>
      <el-table-column label="" width="48" align="right">
        <template #default="{ row }">
          <el-icon v-if="selectedMentions.has(row.id)">
            <Select />
          </el-icon>
        </template>
      </el-table-column>
    </el-table>
    <template #footer>
      <el-button @click="mentionOpen = false">关闭</el-button>
      <el-button type="primary" @click="mentionOpen = false">确定</el-button>
    </template>
  </el-dialog>

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
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { Monitor, Operation, FolderOpened, Select, Setting, UploadFilled } from '@element-plus/icons-vue'
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
import { apiDeleteWorkspacePreview, apiGetWorkspacePreview, type PreviewJob } from '../api/previews'
import MessageConversationList from '../components/messages/MessageConversationList.vue'
import MessageComposer from '../components/messages/MessageComposer.vue'
import MessageDeploymentPanel from '../components/messages/MessageDeploymentPanel.vue'
import MessageCodeDiffPanel from '../components/messages/MessageCodeDiffPanel.vue'
import GroupCreateDialog from '../components/messages/GroupCreateDialog.vue'
import MessageFilePanel from '../components/messages/MessageFilePanel.vue'
import MessageManagePanel from '../components/messages/MessageManagePanel.vue'
import TaskRunCreateDialog from '../components/messages/TaskRunCreateDialog.vue'
import TaskPlannerPanel from '../components/messages/TaskPlannerPanel.vue'
import MessageThread from '../components/messages/MessageThread.vue'
import { ElMessage, ElMessageBox } from 'element-plus'

const route = useRoute()
const shellRef = ref<HTMLElement | null>(null)
const draft = ref('')
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

const mentionOpen = ref(false)
const selectedMentions = ref<Set<string>>(new Set())

const createOpen = ref(false)
const createType = ref<'project' | 'personal'>('project')
const createName = ref('')
const creating = ref(false)
const createErr = ref('')
const users = ref<User[]>([])
const agents = ref<Agent[]>([])
const pickedUserIds = ref<Set<string>>(new Set())
const pickedAgentIds = ref<Set<string>>(new Set())
const currentUserId = ref('')

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
const addKind = ref<'user' | 'agent'>('user')
const addUserId = ref<string>('')
const addAgentId = ref<string>('')
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
const projectFilesLoading = ref(false)
const projectFilesEntries = ref<ProjectCodeEntry[]>([])
const projectOpenDirs = ref<Record<string, boolean>>({})
const projectActiveFilePath = ref('')
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
const hasSidePane = computed(() => manageOpen.value || taskOpen.value || projectFilesOpen.value || deployOpen.value || codeDiffOpen.value)
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
  closeCodeDiffPanel()
  const [mRes, msgRes] = await Promise.all([apiListMembers(id), apiListMessages(id, undefined, 50)])
  if (seq !== loadSeq || String(activeGroupId.value) !== String(id)) return
  members.value = mRes.data
  messages.value = msgRes.data.map((item) => normalizeMessage(item))
  selectedMentions.value = new Set()
  mentionSuggestOpen.value = false
  mentionQuery.value = ''
  updatePreview(id)
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
  const userMember = members.value.find((m) => m.kind === 'user')
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
    mentionIds.size > 0
      ? JSON.stringify({
          mentions: Array.from(mentionIds).map((id) => ({ kind: 'agent', member_id: id })),
        })
      : '{}'

  draft.value = ''
  const res = await apiCreateMessage({
    group_id: activeGroup.value.id,
    sender_member_id: userMember.id,
    message_type: 'text',
    content: text,
    metadata_json: meta,
  })
  // Optimistic append: even if WS is disconnected, show the sent message immediately.
  const created = normalizeMessage(res.data)
  upsertMessage(created)
  updatePreview(activeGroup.value.id)
  selectedMentions.value = new Set()
}

function removeMention(memberId: string) {
  const next = new Set(selectedMentions.value)
  next.delete(memberId)
  selectedMentions.value = next
}

function openMention() {
  mentionOpen.value = true
}

function toggleMention(memberId: string) {
  const next = new Set(selectedMentions.value)
  if (next.has(memberId)) next.delete(memberId)
  else next.add(memberId)
  selectedMentions.value = next
}

function handleMentionRowClick(row: Member) {
  toggleMention(row.id)
}

function mentionRowClassName({ row }: { row: Member }) {
  return selectedMentions.value.has(row.id) ? 'active' : ''
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
  addUserId.value = ''
  addAgentId.value = ''
  taskOpen.value = false
  projectFilesOpen.value = false
  deployOpen.value = false
  codeDiffOpen.value = false
  manageOpen.value = true
  if (supportsProjectWorkspace(activeGroup.value)) {
    void loadMemoryConfig()
    void loadMemoryStatus()
    void loadAssistantConfig()
    void loadTaskRuns()
  }
}

function openTaskPlanner() {
  if (!supportsProjectWorkspace(activeGroup.value)) return
  manageOpen.value = false
  projectFilesOpen.value = false
  deployOpen.value = false
  codeDiffOpen.value = false
  taskOpen.value = true
  void loadTaskRuns()
}

async function openDeployPanel() {
  if (!supportsProjectWorkspace(activeGroup.value)) return
  taskOpen.value = false
  manageOpen.value = false
  projectFilesOpen.value = false
  codeDiffOpen.value = false
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

async function openCodeDiffPanel(messageId: string) {
  if (!supportsProjectWorkspace(activeGroup.value)) return
  taskOpen.value = false
  manageOpen.value = false
  projectFilesOpen.value = false
  deployOpen.value = false
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

async function selectTaskRun(runId: string) {
  activeRunId.value = String(runId)
  await loadTaskRunDetails(activeRunId.value)
}

async function createTaskRunNow() {
  if (!activeGroup.value) return
  const me = members.value.find((m) => m.kind === 'user')
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
  const me = members.value.find((m) => m.kind === 'user')
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
  taskOpen.value = false
  manageOpen.value = false
  deployOpen.value = false
  codeDiffOpen.value = false
  projectFilesOpen.value = true
  await reloadProjectFiles()
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

async function deployProject(payload: DeploymentRequest) {
  if (!activeGroupId.value) return
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

async function addMember() {
  if (!activeGroup.value) return
  if (activeGroup.value.type !== 'project') return
  manageErr.value = ''
  adding.value = true
  try {
    if (addKind.value === 'user') {
      const id = addUserId.value
      if (!id) {
        manageErr.value = '请选择用户'
        return
      }
      const u = users.value.find((x) => String(x.id) === String(id))
      const label = u?.display_name || u?.username || u?.email || id
      await apiAddUserMember({
        group_id: activeGroup.value.id,
        user_ref: String(id),
        display_name: label,
        title: null,
      })
    } else {
      const id = addAgentId.value
      if (!id) {
        manageErr.value = '请选择智能体'
        return
      }
      const a = agents.value.find((x) => String(x.id) === String(id))
      const label = a?.display_name || `Agent#${id}`
      await apiAddAgentMember({
        group_id: activeGroup.value.id,
        agent_instance_id: String(id),
        display_name: label,
        title: null,
      })
    }
    const mRes = await apiListMembers(activeGroup.value.id)
    members.value = mRes.data
    addUserId.value = ''
    addAgentId.value = ''
  } catch (e) {
    manageErr.value = e instanceof Error ? e.message : String(e)
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
  background: rgba(255, 255, 255, 0.84);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(31, 35, 41, 0.08);
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
  background: rgba(79, 140, 255, 0.72);
  box-shadow: 0 0 0 4px rgba(79, 140, 255, 0.16);
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
  height: 58px;
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
  background: rgba(79, 140, 255, 0.14);
  font-size: 16px;
}
.mName {
  font-weight: 800;
}
.mCheck {
  color: #2f6bff;
  display: flex;
  justify-content: center;
  font-size: 16px;
}

</style>
