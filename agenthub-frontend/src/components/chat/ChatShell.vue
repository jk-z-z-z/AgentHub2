<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import {
  listAgentInstances,
  buildGroupWebSocketUrl,
  createGroup,
  createUserMember,
  getMe,
  listGroups,
  listMembers,
  listMessagesByGroup,
  sendMessage,
  type Group,
  type AgentInstance,
  type Member,
  type Message,
  type User,
} from '@/services/agenthubService'
import AppRail from './AppRail.vue'
import ChatPanel from './ChatPanel.vue'
import ConversationList from './ConversationList.vue'
import RightPanel from './RightPanel.vue'

type Conversation = {
  id: string
  title: string
  badge?: string
  lastPreview: string
  lastTime: string
  unread?: number
  avatarText: string
}

type ChatMessage = {
  id: string
  author: string
  senderKind: 'user' | 'agent' | 'unknown'
  content: string
  ts: string
  side: 'left' | 'right'
}

const loading = ref(false)
const router = useRouter()
const me = ref<User | null>(null)
const groups = ref<Group[]>([])
const members = ref<Member[]>([])
const agentInstances = ref<AgentInstance[]>([])
const rawMessages = ref<Message[]>([])
const activeConversationId = ref('')
const rightPanelOpen = ref(true)
const createGroupDialogVisible = ref(false)
const createGroupName = ref('')
const createGroupDescription = ref('')
let ws: WebSocket | null = null

const conversations = computed<Conversation[]>(() =>
  groups.value.map((group) => {
    const last = [...rawMessages.value].filter((message) => message.group_id === group.id).at(-1)
    return {
      id: String(group.id),
      title: group.name,
      badge: '群聊',
      lastPreview: last?.content ?? '',
      lastTime: last?.created_at ?? '',
      unread: 0,
      avatarText: group.name.slice(0, 2),
    }
  }),
)

const activeConversation = computed(
  () => conversations.value.find((conversation) => conversation.id === activeConversationId.value) ?? null,
)

const currentGroupId = computed(() => {
  return activeConversationId.value || null
})

const memberNameMap = computed(() => {
  const map = new Map<string, string>()
  for (const member of members.value) map.set(member.id, member.display_name)
  return map
})

const memberKindMap = computed(() => {
  const map = new Map<string, 'user' | 'agent' | 'unknown'>()
  for (const member of members.value) {
    map.set(member.id, member.kind === 'agent' ? 'agent' : member.kind === 'user' ? 'user' : 'unknown')
  }
  return map
})

const currentUserMember = computed(() => {
  const currentUser = me.value
  if (!currentUser) return null
  return (
    members.value.find((member) => member.kind === 'user' && member.user_ref === String(currentUser.id)) ??
    members.value.find((member) => member.kind === 'user') ??
    null
  )
})

const messages = computed<ChatMessage[]>(() =>
  rawMessages.value.map((message) => ({
    id: String(message.id),
    author: memberNameMap.value.get(message.sender_member_id) ?? `成员#${message.sender_member_id}`,
    senderKind: memberKindMap.value.get(message.sender_member_id) ?? 'unknown',
    content: message.content,
    ts: message.created_at,
    side: currentUserMember.value && currentUserMember.value.id === message.sender_member_id ? 'right' : 'left',
  })),
)

const panelMembers = computed(() =>
  members.value.map((member) => ({
    id: member.id,
    displayName: member.display_name,
    kind: member.kind,
    title: member.title,
  })),
)

function handleSelectConversation(conversationId: string) {
  activeConversationId.value = conversationId
}

async function logout() {
  if (ws) {
    ws.close()
    ws = null
  }
  localStorage.removeItem('token')
  await router.replace({ name: 'login' })
}

async function loadGroups() {
  const rows = await listGroups()
  groups.value = rows
  if (!activeConversationId.value && rows[0]) {
    activeConversationId.value = String(rows[0].id)
  }
}

async function refreshMembers() {
  if (!currentGroupId.value) return
  members.value = await listMembers(currentGroupId.value)
}

async function handleCreateGroup() {
  const currentUser = me.value
  if (!currentUser) return
  const groupName = createGroupName.value.trim()
  if (!groupName) {
    ElMessage.warning('请输入群聊名称')
    return
  }
  loading.value = true
  try {
    const createdGroup = await createGroup({
      name: groupName,
      description: createGroupDescription.value.trim() || null,
    })
    await createUserMember({
      group_id: createdGroup.id,
      display_name: currentUser.display_name || currentUser.username,
      user_ref: currentUser.id,
      title: currentUser.role,
    })
    groups.value = [createdGroup, ...groups.value]
    activeConversationId.value = createdGroup.id
    createGroupDialogVisible.value = false
    createGroupName.value = ''
    createGroupDescription.value = ''
    await loadGroupContext(createdGroup.id)
    ElMessage.success('群聊已创建')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : String(error))
  } finally {
    loading.value = false
  }
}

function connectWs(groupId: string) {
  if (ws) {
    ws.close()
    ws = null
  }
  ws = new WebSocket(buildGroupWebSocketUrl(groupId))
  ws.onmessage = (event) => {
    const payload = JSON.parse(event.data)
    if (payload.event === 'message.created' && payload.data?.group_id === groupId) {
      const exists = rawMessages.value.some((message) => message.id === payload.data.id)
      if (!exists) {
        rawMessages.value.push(payload.data as Message)
      }
    }
  }
}

async function loadGroupContext(groupId: string) {
  const [memberRows, messageRows] = await Promise.all([
    listMembers(groupId),
    listMessagesByGroup(groupId, 200),
  ])
  members.value = memberRows
  rawMessages.value = messageRows
  connectWs(groupId)
}

async function bootstrap() {
  loading.value = true
  try {
    me.value = await getMe()
    const [, instanceRows] = await Promise.all([loadGroups(), listAgentInstances()])
    agentInstances.value = instanceRows
    if (currentGroupId.value) {
      await loadGroupContext(currentGroupId.value)
    }
  } catch (error) {
    const text = error instanceof Error ? error.message : String(error)
    if (text.includes('401')) {
      await logout()
      return
    }
    ElMessage.error(text)
  } finally {
    loading.value = false
  }
}

async function handleSendMessage(text: string) {
  if (!currentGroupId.value || !currentUserMember.value) return
  try {
    const created = await sendMessage({
      group_id: currentGroupId.value,
      sender_member_id: currentUserMember.value.id,
      content: text,
    })
    rawMessages.value = [...rawMessages.value, created]
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : String(error))
  }
}

watch(currentGroupId, async (groupId) => {
  if (!groupId) return
  loading.value = true
  try {
    await loadGroupContext(groupId)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : String(error))
  } finally {
    loading.value = false
  }
})

onMounted(() => {
  void bootstrap()
})

onBeforeUnmount(() => {
  if (ws) {
    ws.close()
    ws = null
  }
})
</script>

<template>
  <div v-loading="loading" class="shell">
    <AppRail @logout="logout" />
    <ConversationList
      :conversations="conversations"
      :active-id="activeConversationId"
      @select="handleSelectConversation"
      @create-group="createGroupDialogVisible = true"
    />
    <ChatPanel
      :title="activeConversation?.title ?? '未选择会话'"
      :badge="activeConversation?.badge"
      :messages="messages"
      :right-panel-open="rightPanelOpen"
      @toggle-right-panel="rightPanelOpen = !rightPanelOpen"
      @send="handleSendMessage"
    />
    <RightPanel
      :open="rightPanelOpen"
      :group-id="currentGroupId"
      :conversation-title="activeConversation?.title"
      :conversation-badge="activeConversation?.badge"
      :members="panelMembers"
      :agent-instances="agentInstances"
      @members-updated="refreshMembers"
    />

    <el-dialog v-model="createGroupDialogVisible" title="新建群聊" width="460px">
      <el-form label-width="84px">
        <el-form-item label="群聊名称">
          <el-input v-model="createGroupName" placeholder="例如：AgentHub 产品群" />
        </el-form-item>
        <el-form-item label="群聊描述">
          <el-input v-model="createGroupDescription" type="textarea" :rows="3" placeholder="补充群聊用途" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createGroupDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleCreateGroup">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.shell {
  height: 100vh;
  display: grid;
  grid-template-columns: 84px 360px 1fr 340px;
  background: radial-gradient(1200px 800px at 20% 10%, #f3f7ff 0%, #f6f7fb 35%, #f2f4f8 100%);
  color: #1f2329;
}

@media (max-width: 1080px) {
  .shell {
    grid-template-columns: 72px 1fr;
  }
}
</style>
