<template>
  <div class="shell" :class="{ withSidePane: manageOpen || taskOpen || projectFilesOpen }">
    <MessageConversationList
      :groups="groups"
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
          <el-tooltip v-if="activeGroup?.type === 'project'" content="查看代码" placement="bottom">
            <el-button class="iconBtn iconBtnLarge" text :icon="FolderOpened" @click="openProjectCode" aria-label="查看代码" />
          </el-tooltip>
          <el-tooltip v-if="activeGroup?.type === 'project'" content="任务规划" placement="bottom">
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

    <aside v-if="manageOpen || taskOpen || projectFilesOpen" class="sidePane">
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
        :nodes="taskNodes"
        :node-stats="taskNodeStats"
        :nodes-loading="taskNodesLoading"
        :manage-err="manageErr"
        @close="taskOpen = false"
        @refresh-nodes="loadTaskNodes"
        @create-nodes="taskCreateOpen = true"
        @claim-node="claimNode"
        @complete-node="completeNode"
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

  <TaskNodeCreateDialog
    v-model:open="taskCreateOpen"
    v-model:node-text="taskCreateNodeText"
    :create-err="manageErr"
    @create="createTaskNodesNow"
  />
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { Monitor, Operation, FolderOpened, Select, Setting } from '@element-plus/icons-vue'
import {
  type Group,
  type GroupTaskNode,
  type MemoryCompressorConfig,
  type MemoryCompressorStatus,
  type Member,
  type Message,
  apiCreateMessage,
  apiListMessages,
  apiGetGroupAssistantConfig,
  apiUpdateGroupAssistantConfig,
  apiCreateGroupTaskNodesFromText,
  apiListGroupTaskNodes,
  apiClaimGroupTaskNode,
  apiCompleteGroupTaskNode,
  type GroupAssistantConfig,
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
import { apiListUsers, type User } from '../api/users'
import { apiListProjectCode, type ProjectCodeEntry } from '../api/project-code'
import MessageConversationList from '../components/messages/MessageConversationList.vue'
import MessageComposer from '../components/messages/MessageComposer.vue'
import GroupCreateDialog from '../components/messages/GroupCreateDialog.vue'
import MessageFilePanel from '../components/messages/MessageFilePanel.vue'
import MessageManagePanel from '../components/messages/MessageManagePanel.vue'
import TaskNodeCreateDialog from '../components/messages/TaskNodeCreateDialog.vue'
import TaskPlannerPanel from '../components/messages/TaskPlannerPanel.vue'
import MessageThread from '../components/messages/MessageThread.vue'
import { ElMessage, ElMessageBox } from 'element-plus'

const route = useRoute()
const draft = ref('')
const groups = ref<Group[]>([])
const loadingGroups = ref(false)
const activeGroupId = ref<string>('')
const members = ref<Member[]>([])
const messages = ref<Message[]>([])
const ws = ref<WebSocket | null>(null)
let loadSeq = 0
let wsSeq = 0

const lastPreviewMap = ref<Record<string, string>>({})
const lastTimeMap = ref<Record<string, string>>({})
const activeGroup = computed(() => groups.value.find((g) => g.id === activeGroupId.value) || null)
const mentionNames = computed<Record<string, string>>(() => {
  const out: Record<string, string> = {}
  for (const member of agentMembers.value) {
    out[String(member.id)] = member.display_name || String(member.id)
  }
  return out
})
const canSend = computed(() => Boolean(activeGroup.value) && Boolean(draft.value.trim()))
const canMentionAgents = computed(() => activeGroup.value?.type === 'project')
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

const manageOpen = ref(false)
const taskOpen = ref(false)
const projectFilesOpen = ref(false)
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
const taskNodesLoading = ref(false)
const taskNodes = ref<GroupTaskNode[]>([])
const taskCreateOpen = ref(false)
const taskCreateNodeText = ref('需求澄清与初始计划 | manager')
const projectFilesLoading = ref(false)
const projectFilesEntries = ref<ProjectCodeEntry[]>([])
const projectOpenDirs = ref<Record<string, boolean>>({})
const projectActiveFilePath = ref('')

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

function connectWs(groupId: string) {
  const seq = ++wsSeq
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
    // Best-effort auto-reconnect
    setTimeout(() => {
      if (String(activeGroupId.value) === String(groupId)) connectWs(groupId)
    }, 800)
  }
  socket.onmessage = (evt) => {
    if (seq !== wsSeq || ws.value !== socket) return
    try {
      const payload = JSON.parse(evt.data)
      if (payload.event === 'message.created') {
        const msg = normalizeMessage(payload.data)
        if (
          String(msg.group_id) === String(groupId) &&
          String(activeGroupId.value) === String(groupId)
        ) {
          if (!messages.value.some((m) => String(m.id) === String(msg.id))) {
            messages.value = [...messages.value, msg]
          }
          updatePreview(groupId)
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
  if (!messages.value.some((m) => String(m.id) === String(created.id))) {
    messages.value = [...messages.value, created]
    updatePreview(activeGroup.value.id)
  }
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

function openManage() {
  manageErr.value = ''
  addUserId.value = ''
  addAgentId.value = ''
  taskOpen.value = false
  projectFilesOpen.value = false
  manageOpen.value = true
  if (activeGroup.value?.type === 'project') {
    void loadMemoryConfig()
    void loadMemoryStatus()
    void loadAssistantConfig()
    void loadTaskNodes()
  }
}

function openTaskPlanner() {
  if (!activeGroup.value || activeGroup.value.type !== 'project') return
  manageOpen.value = false
  projectFilesOpen.value = false
  taskOpen.value = true
  void loadTaskNodes()
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

async function loadTaskNodes() {
  if (!activeGroup.value || activeGroup.value.type !== 'project') return
  manageErr.value = ''
  taskNodesLoading.value = true
  try {
    const nodesRes = await apiListGroupTaskNodes(activeGroup.value.id)
    taskNodes.value = nodesRes.data
  } catch (error) {
    taskNodes.value = []
    manageErr.value = error instanceof Error ? error.message : String(error)
  } finally {
    taskNodesLoading.value = false
  }
}

async function createTaskNodesNow() {
  if (!activeGroup.value || activeGroup.value.type !== 'project') return
  const nodeText = taskCreateNodeText.value.trim()
  if (!nodeText) {
    manageErr.value = '请输入任务节点'
    return
  }
  manageErr.value = ''
  try {
    await apiCreateGroupTaskNodesFromText({
      group_id: activeGroup.value.id,
      node_text: nodeText,
    })
    taskCreateOpen.value = false
    taskCreateNodeText.value = '需求澄清与初始计划 | manager'
    await loadTaskNodes()
    ElMessage.success('任务节点已创建')
  } catch (e) {
    manageErr.value = e instanceof Error ? e.message : String(e)
  }
}

async function claimNode(node: GroupTaskNode) {
  const me = members.value.find((m) => m.kind === 'user')
  if (!me) return
  try {
    await apiClaimGroupTaskNode(String(node.id), String(me.id))
    await loadTaskNodes()
  } catch (e) {
    manageErr.value = e instanceof Error ? e.message : String(e)
  }
}

async function completeNode(node: GroupTaskNode) {
  const me = members.value.find((m) => m.kind === 'user')
  if (!me) return
  const summary = window.prompt('请输入节点完成总结') || ''
  if (!summary.trim()) return
  try {
    await apiCompleteGroupTaskNode(String(node.id), String(me.id), summary.trim())
    await loadTaskNodes()
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
  if (!activeGroup.value || activeGroup.value.type !== 'project') return
  taskOpen.value = false
  manageOpen.value = false
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
  const [u, a] = await Promise.all([apiListUsers(), apiListAgents()])
  users.value = u.data
  agents.value = a.data
})

onBeforeUnmount(() => {
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
  const pickedUsers = Array.from(pickedUserIds.value)
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
  height: 100%;
  display: grid;
  grid-template-columns: 360px minmax(0, 1fr);
  gap: 18px;
  align-items: stretch;
}

.shell.withSidePane {
  grid-template-columns: 340px minmax(0, 1fr) 430px;
}

.chatPane {
  background: var(--ah-surface);
  backdrop-filter: blur(10px);
  border: 1px solid var(--ah-border);
  border-radius: 26px;
  overflow: hidden;
  min-width: 0;
  display: flex;
  flex-direction: column;
  box-shadow: var(--ah-shadow-md);
}

.sidePane {
  min-width: 0;
  height: 100%;
}
.chatHeader {
  min-height: 74px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 24px;
  border-bottom: 1px solid var(--ah-border-soft);
}
.chatHeading {
  display: grid;
  gap: 6px;
  min-width: 0;
}
.chatTitle {
  font-size: 18px;
  font-weight: 900;
  color: var(--ah-text-primary);
}
.chatMeta {
  display: flex;
  align-items: center;
  gap: 14px;
  font-size: 12px;
  color: var(--ah-text-tertiary);
}
.chatActions {
  display: flex;
  gap: 10px;
  align-items: center;
}
.iconBtn {
  width: 40px;
  height: 40px;
  border-radius: 14px;
  font-size: 16px;
  padding: 0;
  background: var(--ah-surface-soft);
  color: var(--ah-text-secondary);
}
.iconBtnLarge {
  font-size: 17px;
}
.iconBtn:hover {
  background: var(--ah-conv-item-hover-bg, var(--ah-hover-strong));
}
.iconBtn:disabled {
  opacity: 0.45;
}

.mentionList {
  width: 100%;
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
  background: var(--ah-surface-soft);
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
