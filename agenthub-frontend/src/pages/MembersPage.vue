<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Search } from '@element-plus/icons-vue'

import AppRail from '@/components/chat/AppRail.vue'
import {
  createAgentInstance,
  createUser,
  getMe,
  listAgentInstances,
  listGroups,
  listUsers,
  type AgentInstance,
  type Group,
  type User,
} from '@/services/agenthubService'

type ContactCategory = {
  key: 'directory' | 'users' | 'agents'
  label: string
  count: number
}

type ContactDetailField = {
  label: string
  value: string
}

type Contact = {
  id: string
  kind: 'user' | 'agent'
  display_name: string
  subtitle: string
  email?: string | null
  username?: string | null
  role?: string | null
  status?: string | null
  agent_instance_id?: string | null
  group_id?: string | null
}

const router = useRouter()
const loading = ref(false)
const userDialogVisible = ref(false)
const agentDialogVisible = ref(false)

const searchKeyword = ref('')
const activeCategory = ref<ContactCategory['key']>('directory')
const selectedContactId = ref('')

const groups = ref<Group[]>([])
const users = ref<User[]>([])
const agentInstances = ref<AgentInstance[]>([])

const userContactForm = reactive({
  email: '',
  username: '',
  password: '',
  display_name: '',
  role: 'member',
  status: 'active',
})

const agentContactForm = reactive({
  group_id: '',
  display_name: '',
  profile_id: '',
  title: '',
})

const groupNameMap = computed(() => {
  const map = new Map<string, string>()
  for (const group of groups.value) map.set(group.id, group.name)
  return map
})

const contacts = computed<Contact[]>(() => {
  const userContacts: Contact[] = users.value.map((user) => ({
    id: user.id,
    kind: 'user',
    display_name: user.display_name ?? user.username,
    subtitle: user.email,
    email: user.email,
    username: user.username,
    role: user.role,
    status: user.status,
  }))

  const agentContacts: Contact[] = agentInstances.value.map((instance) => ({
    id: instance.id,
    kind: 'agent',
    display_name: instance.display_name,
    subtitle: groupNameMap.value.get(instance.group_id) ?? `群组#${instance.group_id}`,
    agent_instance_id: instance.id,
    group_id: instance.group_id,
    status: instance.status,
  }))

  return [...userContacts, ...agentContacts]
})

const contactCategories = computed<ContactCategory[]>(() => {
  const userCount = users.value.length
  const agentCount = agentInstances.value.length
  return [
    { key: 'directory', label: '通讯录管理', count: userCount + agentCount },
    { key: 'users', label: '企业联系人', count: userCount },
    { key: 'agents', label: 'AI 助手', count: agentCount },
  ]
})

const filteredContacts = computed(() => {
  const keyword = searchKeyword.value.trim().toLowerCase()
  return contacts.value.filter((item) => {
    if (activeCategory.value === 'users' && item.kind !== 'user') return false
    if (activeCategory.value === 'agents' && item.kind !== 'agent') return false
    if (!keyword) return true
    const haystack = [
      item.display_name,
      item.subtitle ?? '',
      item.email ?? '',
      item.username ?? '',
      item.role ?? '',
      item.agent_instance_id ?? '',
      item.group_id ?? '',
      item.group_id ? groupNameMap.value.get(item.group_id) ?? '' : '',
    ]
      .join(' ')
      .toLowerCase()
    return haystack.includes(keyword)
  })
})

const groupedContacts = computed(() => {
  const bucket = new Map<string, Contact[]>()
  for (const contact of filteredContacts.value) {
    const firstChar = contact.display_name.trim().charAt(0).toUpperCase() || '#'
    const groupKey = /[A-Z]/.test(firstChar) ? firstChar : '#'
    const rows = bucket.get(groupKey) ?? []
    rows.push(contact)
    bucket.set(groupKey, rows)
  }
  return [...bucket.entries()]
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([letter, rows]) => ({
      letter,
      rows: [...rows].sort((left, right) => left.display_name.localeCompare(right.display_name)),
    }))
})

const selectedContact = computed(() => {
  return filteredContacts.value.find((item) => item.id === selectedContactId.value) ?? filteredContacts.value[0] ?? null
})

const availableGroups = computed(() => groups.value)

const detailFields = computed<ContactDetailField[]>(() => {
  const contact = selectedContact.value
  if (!contact) return []
  if (contact.kind === 'user') {
    return [
      { label: '联系人类型', value: '企业成员' },
      { label: '显示名称', value: contact.display_name },
      { label: '邮箱', value: contact.email || '—' },
      { label: '用户名', value: contact.username || '—' },
      { label: '角色', value: contact.role || '—' },
      { label: '状态', value: contact.status || '—' },
    ]
  }
  return [
    { label: '联系人类型', value: 'AI 助手' },
    { label: '显示名称', value: contact.display_name },
    { label: '所属群组', value: contact.group_id ? groupNameMap.value.get(contact.group_id) ?? contact.group_id : '—' },
    { label: '实例状态', value: contact.status || '—' },
    { label: 'Agent 实例', value: contact.agent_instance_id || '—' },
  ]
})

function contactAvatarText(contact: Contact) {
  return contact.display_name.slice(0, 2).toUpperCase()
}

function resetUserContactForm() {
  userContactForm.email = ''
  userContactForm.username = ''
  userContactForm.password = ''
  userContactForm.display_name = ''
  userContactForm.role = 'member'
  userContactForm.status = 'active'
}

function resetAgentContactForm() {
  agentContactForm.group_id = groups.value[0]?.id ?? ''
  agentContactForm.display_name = ''
  agentContactForm.profile_id = ''
  agentContactForm.title = ''
}

function selectContact(contactId: string) {
  selectedContactId.value = contactId
}

async function logout() {
  localStorage.removeItem('token')
  await router.replace({ name: 'login' })
}

async function bootstrap() {
  loading.value = true
  try {
    await getMe()
    const [groupRows, userRows, instanceRows] = await Promise.all([listGroups(), listUsers(), listAgentInstances()])
    groups.value = groupRows
    users.value = userRows
    agentInstances.value = instanceRows
    resetUserContactForm()
    resetAgentContactForm()
    if (userRows[0]) {
      selectedContactId.value = userRows[0].id
    } else if (instanceRows[0]) {
      selectedContactId.value = instanceRows[0].id
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

async function submitUserContact() {
  if (!userContactForm.email.trim() || !userContactForm.username.trim() || !userContactForm.password.trim()) {
    ElMessage.warning('请补全联系人信息')
    return
  }
  loading.value = true
  try {
    const created = await createUser({
      email: userContactForm.email.trim(),
      username: userContactForm.username.trim(),
      password: userContactForm.password.trim(),
      display_name: userContactForm.display_name.trim() || null,
      role: userContactForm.role,
      status: userContactForm.status,
    })
    users.value = [...users.value, created]
    selectedContactId.value = created.id
    userDialogVisible.value = false
    resetUserContactForm()
    ElMessage.success('联系人已创建')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : String(error))
  } finally {
    loading.value = false
  }
}

async function submitAgentContact() {
  if (!agentContactForm.group_id || !agentContactForm.display_name.trim() || !agentContactForm.profile_id) {
    ElMessage.warning('请补全 AI 联系人信息')
    return
  }
  loading.value = true
  try {
    const created = await createAgentInstance({
      group_id: Number(agentContactForm.group_id),
      display_name: agentContactForm.display_name.trim(),
      profile_id: Number(agentContactForm.profile_id),
      description: agentContactForm.title.trim() || null,
      base_url: null,
      api_key_ref: null,
      config_json: '{}',
      status: 'active',
    })
    agentInstances.value = [...agentInstances.value, created]
    selectedContactId.value = created.id
    agentDialogVisible.value = false
    resetAgentContactForm()
    ElMessage.success('AI 联系人已创建')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : String(error))
  } finally {
    loading.value = false
  }
}

watch(filteredContacts, (rows) => {
  if (!rows.length) {
    selectedContactId.value = ''
    return
  }
  const exists = rows.some((item) => item.id === selectedContactId.value)
  if (!exists) {
    selectedContactId.value = rows[0]?.id ?? ''
  }
})

watch(userDialogVisible, (visible) => {
  if (visible) resetUserContactForm()
})

watch(agentDialogVisible, (visible) => {
  if (visible) resetAgentContactForm()
})

onMounted(() => {
  void bootstrap()
})
</script>

<template>
  <div v-loading="loading" class="contacts-shell">
    <AppRail @logout="logout" />

    <aside class="contacts-sidebar">
      <div class="search-box">
        <el-input v-model="searchKeyword" placeholder="搜索" clearable>
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
      </div>

      <button
        v-for="category in contactCategories"
        :key="category.key"
        class="category-item"
        :class="{ active: activeCategory === category.key }"
        @click="activeCategory = category.key"
      >
        <span>{{ category.label }}</span>
        <span class="category-count">{{ category.count }}</span>
      </button>

      <div class="quick-actions">
        <el-button type="primary" plain @click="userDialogVisible = true">新增联系人</el-button>
        <el-button type="success" plain @click="agentDialogVisible = true">新增 AI</el-button>
      </div>
    </aside>

    <section class="contacts-list-panel">
      <div class="panel-title">联系人</div>

      <div v-if="!groupedContacts.length" class="empty-state">
        <el-empty description="没有匹配的联系人" :image-size="84" />
      </div>

      <div v-else class="contact-groups">
        <div v-for="group in groupedContacts" :key="group.letter" class="contact-group">
          <div class="group-letter">{{ group.letter }}</div>

          <button
            v-for="contact in group.rows"
            :key="contact.id"
            class="contact-item"
            :class="{ active: selectedContact?.id === contact.id }"
            @click="selectContact(contact.id)"
          >
            <div class="contact-avatar" :class="contact.kind === 'agent' ? 'agent' : 'user'">
              {{ contactAvatarText(contact) }}
            </div>
            <div class="contact-meta">
              <div class="contact-name">{{ contact.display_name }}</div>
              <div class="contact-subtitle">
                {{ contact.subtitle || (contact.kind === 'agent' ? 'AI 助手' : '企业联系人') }}
              </div>
            </div>
          </button>
        </div>
      </div>
    </section>

    <main class="contact-detail-panel">
      <template v-if="selectedContact">
        <section class="profile-card">
          <div class="profile-left">
            <div class="profile-avatar" :class="selectedContact.kind === 'agent' ? 'agent' : 'user'">
              {{ contactAvatarText(selectedContact) }}
            </div>
            <div class="profile-main">
              <div class="profile-name-row">
                <div class="profile-name">{{ selectedContact.display_name }}</div>
                <el-tag :type="selectedContact.kind === 'agent' ? 'success' : 'info'" effect="plain">
                  {{ selectedContact.kind === 'agent' ? 'AI 助手' : '企业成员' }}
                </el-tag>
              </div>
              <div class="profile-subline">昵称：{{ selectedContact.display_name }}</div>
              <div class="profile-subline">
                {{ selectedContact.kind === 'agent' ? 'Agent 实例' : '邮箱' }}：
                {{ selectedContact.kind === 'agent' ? selectedContact.agent_instance_id || '未设置' : selectedContact.email || '未设置' }}
              </div>
            </div>
          </div>
        </section>

        <section class="detail-section">
          <div class="detail-title">联系人资料</div>
          <div class="detail-grid">
            <div v-for="field in detailFields" :key="field.label" class="detail-row">
              <div class="detail-label">{{ field.label }}</div>
              <div class="detail-value">{{ field.value }}</div>
            </div>
          </div>
        </section>

        <section class="detail-section">
          <div class="detail-title">协作信息</div>
          <div class="detail-grid">
            <div class="detail-row">
              <div class="detail-label">协作定位</div>
              <div class="detail-value">
                {{ selectedContact.kind === 'agent' ? '可以通过聊天直接委派任务的 AI 助手' : '可以参与群聊协作和任务确认的企业成员' }}
              </div>
            </div>
            <div v-if="selectedContact.kind === 'agent'" class="detail-row">
              <div class="detail-label">所属群组</div>
              <div class="detail-value">
                {{ selectedContact.group_id ? groupNameMap.get(selectedContact.group_id) || selectedContact.group_id : '—' }}
              </div>
            </div>
            <div v-if="selectedContact.kind === 'agent'" class="detail-row">
              <div class="detail-label">实例状态</div>
              <div class="detail-value">{{ selectedContact.status || '未知' }}</div>
            </div>
          </div>
        </section>

        <section class="bottom-actions">
          <button class="detail-action primary">发消息</button>
          <button class="detail-action">查看群聊</button>
          <button class="detail-action" :class="{ success: selectedContact.kind === 'agent' }">
            {{ selectedContact.kind === 'agent' ? '分配任务' : '发起协作' }}
          </button>
        </section>
      </template>

      <div v-else class="empty-state detail-empty">
        <el-empty description="请选择一个联系人查看资料" :image-size="96" />
      </div>
    </main>

    <el-dialog v-model="userDialogVisible" title="新增企业联系人" width="460px">
      <el-form label-width="88px">
        <el-form-item label="邮箱">
          <el-input v-model="userContactForm.email" placeholder="例如：alice@example.com" />
        </el-form-item>
        <el-form-item label="用户名">
          <el-input v-model="userContactForm.username" placeholder="例如：alice" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="userContactForm.password" type="password" show-password placeholder="临时密码" />
        </el-form-item>
        <el-form-item label="显示名">
          <el-input v-model="userContactForm.display_name" placeholder="例如：产品经理小林（可选）" />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="userContactForm.role" placeholder="选择角色" style="width: 100%">
            <el-option label="member" value="member" />
            <el-option label="admin" value="admin" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="userContactForm.status" placeholder="选择状态" style="width: 100%">
            <el-option label="active" value="active" />
            <el-option label="disabled" value="disabled" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="userDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitUserContact">创建</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="agentDialogVisible" title="新增 AI 联系人" width="460px">
      <el-form label-width="88px">
        <el-form-item label="所属群组">
          <el-select v-model="agentContactForm.group_id" placeholder="选择群组" style="width: 100%">
            <el-option v-for="group in availableGroups" :key="group.id" :label="group.name" :value="group.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="显示名">
          <el-input v-model="agentContactForm.display_name" placeholder="例如：后端 Agent" />
        </el-form-item>
        <el-form-item label="Profile ID">
          <el-input v-model="agentContactForm.profile_id" placeholder="填写 agent profile id" />
        </el-form-item>
        <el-form-item label="角色标题">
          <el-input v-model="agentContactForm.title" placeholder="例如：服务管家 Agent" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="agentDialogVisible = false">取消</el-button>
        <el-button type="success" @click="submitAgentContact">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.contacts-shell {
  min-height: 100vh;
  display: grid;
  grid-template-columns: 84px 280px 360px 1fr;
  background: #f5f5f5;
}

.contacts-sidebar {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 22px 18px;
  background: #ededed;
  border-right: 1px solid rgba(15, 23, 42, 0.06);
}

.search-box :deep(.el-input__wrapper) {
  border-radius: 14px;
  box-shadow: none;
  background: rgba(255, 255, 255, 0.92);
}

.category-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border: 0;
  border-radius: 16px;
  background: transparent;
  color: #1f2329;
  font-size: 16px;
  text-align: left;
}

.category-item.active,
.category-item:hover {
  background: rgba(255, 255, 255, 0.88);
}

.category-count {
  color: rgba(31, 35, 41, 0.4);
  font-size: 14px;
}

.quick-actions {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 8px;
}

.contacts-list-panel {
  background: #f3f3f3;
  border-right: 1px solid rgba(15, 23, 42, 0.06);
  overflow: auto;
}

.panel-title {
  padding: 22px 24px 10px;
  font-size: 14px;
  color: rgba(31, 35, 41, 0.52);
}

.contact-groups {
  padding-bottom: 32px;
}

.contact-group {
  display: flex;
  flex-direction: column;
}

.group-letter {
  padding: 12px 24px 8px;
  font-size: 14px;
  color: rgba(31, 35, 41, 0.52);
}

.contact-item {
  display: flex;
  align-items: center;
  gap: 14px;
  width: 100%;
  padding: 14px 24px;
  border: 0;
  background: transparent;
  text-align: left;
}

.contact-item.active {
  background: #dfe0e3;
}

.contact-avatar,
.profile-avatar {
  display: grid;
  place-items: center;
  border-radius: 18px;
  color: #fff;
  font-weight: 700;
  background: linear-gradient(135deg, #6b7280 0%, #9ca3af 100%);
}

.contact-avatar {
  width: 46px;
  height: 46px;
  font-size: 16px;
}

.profile-avatar {
  width: 116px;
  height: 116px;
  font-size: 34px;
  border-radius: 24px;
}

.contact-avatar.agent,
.profile-avatar.agent {
  background: linear-gradient(135deg, #26c281 0%, #47d69a 100%);
}

.contact-avatar.user,
.profile-avatar.user {
  background: linear-gradient(135deg, #6b86ff 0%, #8ca2ff 100%);
}

.contact-meta {
  min-width: 0;
}

.contact-name {
  font-size: 16px;
  color: #1f2329;
}

.contact-subtitle {
  margin-top: 4px;
  font-size: 12px;
  color: rgba(31, 35, 41, 0.5);
}

.contact-detail-panel {
  padding: 40px 54px;
  background: #f7f7f7;
  overflow: auto;
}

.profile-card {
  padding-bottom: 34px;
  border-bottom: 1px solid rgba(15, 23, 42, 0.08);
}

.profile-left {
  display: flex;
  align-items: center;
  gap: 26px;
}

.profile-main {
  min-width: 0;
}

.profile-name-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.profile-name {
  font-size: 24px;
  font-weight: 700;
  color: #1f2329;
}

.profile-subline {
  margin-top: 10px;
  font-size: 14px;
  color: rgba(31, 35, 41, 0.56);
}

.detail-section {
  padding: 34px 0;
  border-bottom: 1px solid rgba(15, 23, 42, 0.08);
}

.detail-title {
  margin-bottom: 22px;
  font-size: 18px;
  font-weight: 600;
  color: rgba(31, 35, 41, 0.76);
}

.detail-grid {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.detail-row {
  display: grid;
  grid-template-columns: 140px 1fr;
  gap: 16px;
  align-items: start;
}

.detail-label {
  color: rgba(31, 35, 41, 0.48);
  font-size: 15px;
}

.detail-value {
  color: #1f2329;
  font-size: 15px;
  line-height: 1.7;
}

.bottom-actions {
  display: flex;
  gap: 18px;
  padding: 36px 0 8px;
}

.detail-action {
  min-width: 116px;
  height: 46px;
  border-radius: 16px;
  border: 1px solid rgba(59, 92, 178, 0.16);
  background: #fff;
  color: #3157a5;
  font-size: 16px;
}

.detail-action.primary {
  background: #3157a5;
  color: #fff;
  border-color: #3157a5;
}

.detail-action.success {
  color: #159561;
  border-color: rgba(21, 149, 97, 0.18);
}

.empty-state,
.detail-empty {
  display: grid;
  place-items: center;
  min-height: 240px;
}

@media (max-width: 1440px) {
  .contacts-shell {
    grid-template-columns: 84px 240px 320px 1fr;
  }
}
</style>
