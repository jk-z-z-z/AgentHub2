<template>
  <div class="contactsPage">
    <section class="contactsListPanel">
      <div class="panelHeader">
        <div>
          <div class="eyebrow">Contacts</div>
          <div class="panelTitle">通讯录</div>
          <div class="panelSub">搜索联系人并快速进入会话。</div>
        </div>
        <div class="countPill">{{ visibleUsers.length }}</div>
      </div>

      <el-input v-model="searchKeyword" class="searchBar" placeholder="搜索联系人" clearable>
        <template #prefix>
          <el-icon class="searchIcon">
            <Search />
          </el-icon>
        </template>
      </el-input>

      <div class="sectionTitle">
        <span>联系人</span>
        <span v-if="loading" class="sectionHint">加载中…</span>
        <span v-else class="sectionHint">{{ visibleUsers.length }} 人</span>
      </div>

      <div v-if="loading" class="stateBlock">
        <el-skeleton :rows="7" animated />
      </div>
      <div v-else-if="listError" class="stateBlock stateError">
        <div class="stateTitle">联系人加载失败</div>
        <div class="stateText">{{ listError }}</div>
        <el-button class="stateAction" type="primary" plain @click="loadContacts">重试</el-button>
      </div>
      <div v-else-if="visibleUsers.length === 0" class="stateBlock">
        <el-empty description="没有匹配的联系人" />
      </div>
      <div v-else class="contactList">
        <button
          v-for="user in visibleUsers"
          :key="user.id"
          class="contactRow"
          :class="{ active: selectedUserId === user.id, self: user.id === currentUserId }"
          @click="selectUser(user.id)"
        >
          <div class="avatar">{{ avatarText(user) }}</div>
          <div class="contactMeta">
            <div class="contactTop">
              <div class="contactName">{{ displayName(user) }}</div>
              <span v-if="user.id === currentUserId" class="tag">我</span>
            </div>
            <div class="contactBottom">
              <span class="contactLine">{{ user.username }}</span>
              <span class="dot">·</span>
              <span class="contactLine">{{ user.role }}</span>
            </div>
          </div>
        </button>
      </div>
    </section>

    <section class="detailPanel">
      <template v-if="selectedUser">
        <div class="detailCard">
          <div class="detailHero">
            <div class="detailAvatar">{{ avatarText(selectedUser) }}</div>
            <div class="detailHeroMeta">
              <div class="detailNameRow">
                <div class="detailName">{{ displayName(selectedUser) }}</div>
                <span v-if="selectedUser.id === currentUserId" class="heroTag">当前账号</span>
              </div>
              <div class="detailUser">{{ selectedUser.username }}</div>
              <div class="detailEmail">{{ selectedUser.email }}</div>
            </div>
            <button
              class="detailArrowBtn"
              type="button"
              aria-label="进入详细信息"
              @click="scrollToDetails"
            >
              <el-icon>
                <ArrowRight />
              </el-icon>
            </button>
          </div>

          <div class="detailSection">
            <div class="detailSectionTitle">基础信息</div>
            <div class="detailGrid">
              <div class="kv">
                <div class="k">用户名</div>
                <div class="v">{{ selectedUser.username }}</div>
              </div>
              <div class="kv">
                <div class="k">邮箱</div>
                <div class="v">{{ selectedUser.email }}</div>
              </div>
              <div class="kv">
                <div class="k">角色</div>
                <div class="v">{{ selectedUser.role }}</div>
              </div>
              <div class="kv">
                <div class="k">状态</div>
                <div class="v">{{ selectedUser.status }}</div>
              </div>
            </div>
          </div>

          <div class="detailSection">
            <div class="detailSectionTitle">个人简介</div>
            <div class="bioBox">
              <template v-if="selectedUser.bio">
                {{ selectedUser.bio }}
              </template>
              <template v-else>暂无简介。</template>
            </div>
          </div>

          <div class="detailSection detailFooter">
            <div class="detailTip">
              立刻联系会创建一个新的单聊会话，并跳转到消息页。
            </div>
            <el-button
              type="primary"
              class="contactBtn"
              :loading="contacting"
              :disabled="selectedUser.id === currentUserId"
              @click="contactNow"
            >
              立刻联系
            </el-button>
          </div>
        </div>
      </template>
      <div v-else class="emptyPanel">
        <el-empty description="选择一个联系人查看详情" />
      </div>
    </section>
  </div>

  <el-drawer v-model="detailOpen" title="联系人详细信息" direction="rtl" size="380px" :destroy-on-close="true">
    <template v-if="selectedUser">
      <div class="drawerHero">
        <div class="drawerAvatar">{{ avatarText(selectedUser) }}</div>
        <div class="drawerMeta">
          <div class="drawerName">{{ displayName(selectedUser) }}</div>
          <div class="drawerSub">{{ selectedUser.username }}</div>
        </div>
      </div>

      <div class="drawerSection">
        <div class="drawerTitle">基础字段</div>
        <div class="drawerRows">
          <div class="drawerRow"><span>用户名</span><span>{{ selectedUser.username }}</span></div>
          <div class="drawerRow"><span>邮箱</span><span>{{ selectedUser.email }}</span></div>
          <div class="drawerRow"><span>角色</span><span>{{ selectedUser.role }}</span></div>
          <div class="drawerRow"><span>状态</span><span>{{ selectedUser.status }}</span></div>
        </div>
      </div>

      <div class="drawerSection">
        <div class="drawerTitle">个人简介</div>
        <div class="drawerBio">{{ selectedUser.bio || '暂无简介。' }}</div>
      </div>

      <div class="drawerSection">
        <div class="drawerTitle">时间信息</div>
        <div class="drawerRows">
          <div class="drawerRow"><span>创建时间</span><span>{{ formatDate(selectedUser.created_at) }}</span></div>
          <div class="drawerRow"><span>更新时间</span><span>{{ formatDate(selectedUser.updated_at) }}</span></div>
        </div>
      </div>
    </template>
  </el-drawer>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowRight, Search } from '@element-plus/icons-vue'
import { apiCreateGroup, apiGetCurrentUser, apiListUsers, type User } from '../api/agenthub'

const router = useRouter()

const loading = ref(false)
const contacting = ref(false)
const listError = ref('')
const searchKeyword = ref('')
const users = ref<User[]>([])
const selectedUserId = ref('')
const currentUserId = ref('')
const detailOpen = ref(false)

const contactUsers = computed(() => users.value.filter((user) => user.id !== currentUserId.value))

const visibleUsers = computed(() => {
  const query = searchKeyword.value.trim().toLowerCase()
  if (!query) return contactUsers.value
  return contactUsers.value.filter((user) => {
    const haystack = [user.username, user.email, user.display_name || '', user.role, user.status, user.bio || '']
      .join(' ')
      .toLowerCase()
    return haystack.includes(query)
  })
})

const selectedUser = computed(() => users.value.find((user) => user.id === selectedUserId.value) || null)

function displayName(user: User) {
  return user.display_name || user.username || user.email || '未命名联系人'
}

function avatarText(user: User) {
  const label = displayName(user).trim()
  return (label || 'U').slice(0, 1).toUpperCase()
}

function selectUser(userId: string) {
  selectedUserId.value = userId
  detailOpen.value = false
}

async function loadContacts() {
  loading.value = true
  listError.value = ''
  try {
    const [usersResult, currentUserResult] = await Promise.allSettled([apiListUsers(), apiGetCurrentUser()])

    if (usersResult.status === 'fulfilled') {
      users.value = usersResult.value.data
    } else {
      throw usersResult.reason
    }

    if (currentUserResult.status === 'fulfilled') {
      currentUserId.value = currentUserResult.value.data.id
    }

    const firstVisible = visibleUsers.value[0]
    if (!selectedUserId.value || !users.value.some((user) => user.id === selectedUserId.value)) {
      selectedUserId.value = firstVisible?.id || ''
    }
  } catch (error) {
    listError.value = error instanceof Error ? error.message : String(error)
  } finally {
    loading.value = false
  }
}

function scrollToDetails() {
  detailOpen.value = true
}

function formatDate(value: string) {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}

async function contactNow() {
  if (!selectedUser.value || selectedUser.value.id === currentUserId.value) return
  contacting.value = true
  try {
    const result = await apiCreateGroup({
      name: `与${displayName(selectedUser.value)}的单聊`,
      description: null,
      type: 'personal',
      users: [
        {
          user_id: selectedUser.value.id,
          display_name: displayName(selectedUser.value),
          title: null,
        },
      ],
      agents: [],
    })
    await router.push({ name: 'messages', query: { groupId: result.data.id } })
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : String(error))
  } finally {
    contacting.value = false
  }
}

onMounted(loadContacts)
</script>

<style scoped>
.contactsPage {
  height: calc(100vh - 36px);
  display: grid;
  grid-template-columns: 340px minmax(0, 1fr);
  gap: 12px;
  min-width: 0;
}

.contactsListPanel,
.detailPanel {
  min-width: 0;
  background: rgba(255, 255, 255, 0.84);
  border: 1px solid rgba(31, 35, 41, 0.08);
  border-radius: 18px;
  backdrop-filter: blur(10px);
  overflow: hidden;
}

.contactsListPanel {
  display: flex;
  flex-direction: column;
  padding: 16px;
}

.panelHeader {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.eyebrow {
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: rgba(31, 35, 41, 0.48);
}

.panelTitle {
  margin-top: 4px;
  font-size: 22px;
  line-height: 1.2;
  font-weight: 900;
  color: rgba(31, 35, 41, 0.96);
}

.panelSub {
  margin-top: 6px;
  font-size: 12px;
  color: rgba(31, 35, 41, 0.56);
}

.countPill {
  flex: 0 0 auto;
  height: 30px;
  padding: 0 12px;
  border-radius: 999px;
  background: rgba(79, 140, 255, 0.1);
  color: #2563eb;
  font-size: 12px;
  font-weight: 800;
  display: inline-flex;
  align-items: center;
}

.searchBar {
  margin-bottom: 14px;
}

.searchBar :deep(.el-input__wrapper) {
  height: 38px;
  border-radius: 12px;
  box-shadow: none;
  background: rgba(31, 35, 41, 0.04);
}

.searchBar :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px rgba(79, 140, 255, 0.35) inset;
}

.searchIcon {
  color: rgba(31, 35, 41, 0.42);
}

.sectionTitle {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
  font-size: 13px;
  font-weight: 800;
  color: rgba(31, 35, 41, 0.84);
}

.sectionHint {
  color: rgba(31, 35, 41, 0.46);
  font-weight: 600;
}

.stateBlock {
  padding: 12px 4px 4px;
}

.stateError {
  display: grid;
  gap: 10px;
}

.stateTitle {
  font-size: 14px;
  font-weight: 800;
  color: rgba(31, 35, 41, 0.9);
}

.stateText {
  font-size: 13px;
  line-height: 1.6;
  color: rgba(31, 35, 41, 0.58);
  word-break: break-all;
}

.stateAction {
  justify-self: start;
}

.contactList {
  display: grid;
  gap: 8px;
  overflow: auto;
  padding-right: 2px;
}

.contactRow {
  width: 100%;
  border: 0;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.7);
  padding: 12px 12px 12px 10px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 12px;
  text-align: left;
  color: inherit;
  transition:
    background 0.14s ease,
    transform 0.14s ease,
    box-shadow 0.14s ease;
}

.contactRow:hover {
  background: rgba(79, 140, 255, 0.08);
  transform: translateY(-1px);
}

.contactRow.active {
  background: linear-gradient(135deg, rgba(79, 140, 255, 0.14), rgba(79, 140, 255, 0.06));
  box-shadow: inset 0 0 0 1px rgba(79, 140, 255, 0.18);
}

.contactRow.self {
  opacity: 0.9;
}

.avatar,
.detailAvatar {
  flex: 0 0 auto;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: linear-gradient(135deg, #4f8cff, #78a7ff);
  color: #fff;
  font-weight: 900;
}

.avatar {
  width: 40px;
  height: 40px;
  font-size: 15px;
}

.contactMeta {
  min-width: 0;
  flex: 1;
}

.contactTop,
.contactBottom,
.detailNameRow {
  display: flex;
  align-items: center;
  gap: 8px;
}

.contactTop {
  justify-content: space-between;
}

.contactName,
.detailName {
  font-size: 14px;
  font-weight: 800;
  color: rgba(31, 35, 41, 0.94);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tag,
.heroTag {
  flex: 0 0 auto;
  height: 20px;
  padding: 0 8px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 800;
  background: rgba(31, 35, 41, 0.06);
  color: rgba(31, 35, 41, 0.62);
}

.contactBottom {
  margin-top: 4px;
  font-size: 12px;
  color: rgba(31, 35, 41, 0.52);
  flex-wrap: wrap;
}

.contactLine {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.dot {
  color: rgba(31, 35, 41, 0.36);
}

.detailPanel {
  padding: 18px;
}

.detailCard {
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 16px;
  overflow: auto;
}

.detailHero {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 18px;
  border-radius: 20px;
  background:
    radial-gradient(circle at top right, rgba(79, 140, 255, 0.16), transparent 34%),
    linear-gradient(135deg, rgba(255, 255, 255, 0.96), rgba(246, 249, 255, 0.88));
  border: 1px solid rgba(31, 35, 41, 0.08);
}

.detailAvatar {
  width: 72px;
  height: 72px;
  font-size: 28px;
}

.detailHeroMeta {
  min-width: 0;
  flex: 1;
}

.detailUser,
.detailEmail {
  margin-top: 6px;
  font-size: 13px;
  color: rgba(31, 35, 41, 0.58);
  word-break: break-all;
}

.detailArrowBtn {
  width: 42px;
  height: 42px;
  border: 0;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.88);
  color: rgba(31, 35, 41, 0.78);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  box-shadow: inset 0 0 0 1px rgba(31, 35, 41, 0.08);
}

.detailArrowBtn:hover {
  background: rgba(79, 140, 255, 0.1);
  color: #2563eb;
}

.detailSection {
  padding: 18px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.82);
  border: 1px solid rgba(31, 35, 41, 0.08);
}

.detailSectionTitle {
  font-size: 14px;
  font-weight: 900;
  color: rgba(31, 35, 41, 0.9);
  margin-bottom: 12px;
}

.detailGrid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.kv {
  padding: 12px;
  border-radius: 14px;
  background: rgba(31, 35, 41, 0.03);
}

.k {
  font-size: 12px;
  color: rgba(31, 35, 41, 0.48);
}

.v {
  margin-top: 6px;
  font-size: 13px;
  line-height: 1.5;
  color: rgba(31, 35, 41, 0.9);
  word-break: break-all;
}

.bioBox {
  min-height: 120px;
  padding: 14px;
  border-radius: 16px;
  background: rgba(31, 35, 41, 0.03);
  color: rgba(31, 35, 41, 0.82);
  line-height: 1.8;
  white-space: pre-wrap;
}

.detailFooter {
  margin-top: auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
}

.detailTip {
  font-size: 12px;
  color: rgba(31, 35, 41, 0.54);
  line-height: 1.6;
}

.contactBtn {
  min-width: 132px;
  height: 42px;
  border-radius: 14px;
}

.emptyPanel {
  height: 100%;
  display: grid;
  place-items: center;
}

.drawerHero {
  display: flex;
  align-items: center;
  gap: 12px;
  padding-bottom: 16px;
  border-bottom: 1px solid rgba(31, 35, 41, 0.08);
}

.drawerAvatar {
  width: 52px;
  height: 52px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  background: linear-gradient(135deg, #4f8cff, #78a7ff);
  color: #fff;
  font-weight: 900;
  font-size: 20px;
}

.drawerMeta {
  min-width: 0;
  flex: 1;
}

.drawerName {
  font-size: 16px;
  font-weight: 900;
  color: rgba(31, 35, 41, 0.94);
}

.drawerSub {
  margin-top: 6px;
  font-size: 12px;
  color: rgba(31, 35, 41, 0.54);
  word-break: break-all;
}

.drawerSection {
  margin-top: 16px;
}

.drawerTitle {
  font-size: 13px;
  font-weight: 800;
  color: rgba(31, 35, 41, 0.78);
  margin-bottom: 10px;
}

.drawerRows {
  display: grid;
  gap: 8px;
}

.drawerRow {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 12px;
  background: rgba(31, 35, 41, 0.03);
  font-size: 13px;
  color: rgba(31, 35, 41, 0.82);
  word-break: break-all;
}

.drawerRow span:first-child {
  color: rgba(31, 35, 41, 0.48);
  flex: 0 0 auto;
}

.drawerBio {
  padding: 12px;
  border-radius: 12px;
  background: rgba(31, 35, 41, 0.03);
  color: rgba(31, 35, 41, 0.82);
  line-height: 1.7;
  white-space: pre-wrap;
}

@media (max-width: 1200px) {
  .contactsPage {
    grid-template-columns: 300px minmax(0, 1fr);
  }
}

@media (max-width: 960px) {
  .contactsPage {
    grid-template-columns: 1fr;
    height: auto;
  }

  .detailPanel {
    min-height: 520px;
  }
}
</style>
