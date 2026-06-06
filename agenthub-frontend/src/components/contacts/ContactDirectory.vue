<template>
  <div class="contactsPage">
    <WorkspacePanel title="通讯录" subtitle="搜索联系人并快速进入会话。">
      <template #actions>
        <el-tag effect="light" type="info">{{ visibleUsers.length }} 人</el-tag>
      </template>

      <div class="listPane">
        <el-input v-model="searchKeywordModel" class="searchBar" placeholder="搜索联系人" clearable>
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
          <el-button class="stateAction" type="primary" plain @click="$emit('load-contacts')">重试</el-button>
        </div>
        <div v-else-if="visibleUsers.length === 0" class="stateBlock emptyState">
          <el-empty description="没有匹配的联系人" />
        </div>
        <el-table
          v-else
          :data="visibleUsers"
          class="contactList"
          height="100%"
          empty-text="没有匹配的联系人"
          highlight-current-row
          :row-class-name="tableRowClassName"
          @row-click="handleRowClick"
        >
          <el-table-column label="" width="58">
            <template #default="{ row }">
              <el-avatar class="avatar" :size="40">{{ avatarText(row) }}</el-avatar>
            </template>
          </el-table-column>
          <el-table-column label="联系人" min-width="180">
            <template #default="{ row }">
              <div class="contactNameRow">
                <div class="contactName">{{ displayName(row) }}</div>
                <el-tag v-if="row.id === currentUserId" size="small" effect="light">我</el-tag>
              </div>
              <div class="contactBottom">
                <span class="contactLine">{{ row.username }}</span>
                <span class="dot">·</span>
                <span class="contactLine">{{ row.role }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <span class="contactLine">{{ row.status }}</span>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </WorkspacePanel>

    <WorkspacePanel title="联系人详情" subtitle="查看联系人的基础信息和个人简介。">
      <template #actions>
        <el-button
          text
          circle
          :icon="ArrowRight"
          :disabled="!selectedUser"
          @click="detailOpenModel = true"
          aria-label="进入详细信息"
        />
      </template>

      <template v-if="selectedUser">
        <div class="detailCard">
          <el-card class="detailHero" shadow="never">
            <div class="detailHeroInner">
              <el-avatar class="detailAvatar" :size="56">{{ avatarText(selectedUser) }}</el-avatar>
              <div class="detailHeroMeta">
                <div class="detailNameRow">
                  <div class="detailName">{{ displayName(selectedUser) }}</div>
                  <el-tag v-if="selectedUser.id === currentUserId" size="small" effect="light">当前账号</el-tag>
                </div>
                <div class="detailUser">{{ selectedUser.username }}</div>
                <div class="detailEmail">{{ selectedUser.email }}</div>
              </div>
            </div>
          </el-card>

          <el-card class="detailSection" shadow="never">
            <template #header>
              <div class="detailSectionTitle">基础信息</div>
            </template>
            <el-descriptions :column="2" border size="small">
              <el-descriptions-item label="用户名">{{ selectedUser.username }}</el-descriptions-item>
              <el-descriptions-item label="邮箱">{{ selectedUser.email }}</el-descriptions-item>
              <el-descriptions-item label="角色">{{ selectedUser.role }}</el-descriptions-item>
              <el-descriptions-item label="状态">{{ selectedUser.status }}</el-descriptions-item>
            </el-descriptions>
          </el-card>

          <el-card class="detailSection" shadow="never">
            <template #header>
              <div class="detailSectionTitle">个人简介</div>
            </template>
            <div class="bioBox">
              <template v-if="selectedUser.bio">
                {{ selectedUser.bio }}
              </template>
              <template v-else>暂无简介。</template>
            </div>
          </el-card>

          <el-card class="detailSection detailFooter" shadow="never">
            <div class="detailTip">立刻联系会创建一个新的单聊会话，并跳转到消息页。</div>
            <el-button
              type="primary"
              class="contactBtn"
              :loading="contacting"
              :disabled="selectedUser.id === currentUserId"
              @click="$emit('contact-now')"
            >
              立刻联系
            </el-button>
          </el-card>
        </div>
      </template>
      <div v-else class="emptyPanel">
        <el-empty description="选择一个联系人查看详情" />
      </div>
    </WorkspacePanel>

    <el-drawer v-model="detailOpenModel" title="联系人详细信息" direction="rtl" size="380px" :destroy-on-close="true">
      <template v-if="selectedUser">
        <div class="drawerHero">
          <el-avatar class="drawerAvatar" :size="52">{{ avatarText(selectedUser) }}</el-avatar>
          <div class="drawerMeta">
            <div class="drawerName">{{ displayName(selectedUser) }}</div>
            <div class="drawerSub">{{ selectedUser.username }}</div>
          </div>
        </div>

        <div class="drawerSection">
          <div class="drawerTitle">基础字段</div>
          <el-descriptions :column="1" border size="small">
            <el-descriptions-item label="用户名">{{ selectedUser.username }}</el-descriptions-item>
            <el-descriptions-item label="邮箱">{{ selectedUser.email }}</el-descriptions-item>
            <el-descriptions-item label="角色">{{ selectedUser.role }}</el-descriptions-item>
            <el-descriptions-item label="状态">{{ selectedUser.status }}</el-descriptions-item>
          </el-descriptions>
        </div>

        <div class="drawerSection">
          <div class="drawerTitle">个人简介</div>
          <div class="drawerBio">{{ selectedUser.bio || '暂无简介。' }}</div>
        </div>

        <div class="drawerSection">
          <div class="drawerTitle">时间信息</div>
          <el-descriptions :column="1" border size="small">
            <el-descriptions-item label="创建时间">{{ formatDate(selectedUser.created_at) }}</el-descriptions-item>
            <el-descriptions-item label="更新时间">{{ formatDate(selectedUser.updated_at) }}</el-descriptions-item>
          </el-descriptions>
        </div>
      </template>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ArrowRight, Search } from '@element-plus/icons-vue'
import type { User } from '../../api/users'
import WorkspacePanel from '../common/WorkspacePanel.vue'

const searchKeywordModel = defineModel<string>('searchKeyword', { required: true })
const detailOpenModel = defineModel<boolean>('detailOpen', { required: true })

const props = defineProps<{
  loading: boolean
  listError: string
  visibleUsers: User[]
  selectedUser: User | null
  currentUserId: string
  contacting: boolean
}>()

const emit = defineEmits<{
  (e: 'load-contacts'): void
  (e: 'select-user', userId: string): void
  (e: 'contact-now'): void
}>()

function displayName(user: User) {
  return user.display_name || user.username || user.email || '未命名联系人'
}

function avatarText(user: User) {
  const label = displayName(user).trim()
  return (label || 'U').slice(0, 1).toUpperCase()
}

function handleRowClick(row: User) {
  emit('select-user', row.id)
}

function tableRowClassName({ row }: { row: User }) {
  const classes = []
  if (props.selectedUser?.id === row.id) classes.push('active')
  if (row.id === props.currentUserId) classes.push('self')
  return classes.join(' ')
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
</script>

<style scoped>
.contactsPage {
  height: 100%;
  display: grid;
  grid-template-columns: 340px minmax(0, 1fr);
  gap: 12px;
  min-width: 0;
}
.listPane {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
.searchBar {
  margin-bottom: 14px;
}
.searchBar :deep(.el-input__wrapper) {
  height: 38px;
  border-radius: 12px;
  box-shadow: 0 0 0 1px var(--ah-primary-soft-strong) inset;
  background: var(--ah-input-bg);
}
.searchIcon {
  color: var(--ah-text-muted);
}
.sectionTitle {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
  font-size: 13px;
  font-weight: 800;
  color: var(--ah-text-secondary);
}
.sectionHint {
  color: var(--ah-text-muted);
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
  color: var(--ah-text-primary);
}
.stateText {
  font-size: 13px;
  line-height: 1.6;
  color: var(--ah-text-tertiary);
  word-break: break-all;
}
.stateAction {
  justify-self: start;
}
.emptyState,
.emptyPanel {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}
.contactList {
  flex: 1;
  min-height: 0;
}
.contactList :deep(.el-table__row) {
  cursor: pointer;
}
.contactList :deep(.el-table__row.self) {
  opacity: 0.9;
}
.contactList :deep(.el-table__row.active) {
  background: var(--ah-primary-soft);
}
.avatar,
.detailAvatar,
.drawerAvatar {
  background: var(--ah-avatar-gradient);
  color: var(--ah-text-on-primary);
  font-weight: 900;
}
.contactNameRow,
.detailNameRow {
  display: flex;
  align-items: center;
  gap: 8px;
}
.contactNameRow {
  justify-content: space-between;
}
.contactName,
.detailName {
  font-size: 14px;
  font-weight: 800;
  color: var(--ah-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.contactBottom,
.detailUser,
.detailEmail {
  margin-top: 4px;
  color: var(--ah-text-tertiary);
  font-size: 12px;
}
.dot {
  opacity: 0.4;
}
.detailCard {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.detailHero :deep(.el-card__body),
.detailSection :deep(.el-card__body),
.detailFooter :deep(.el-card__body) {
  padding: 14px;
}
.detailHeroInner {
  display: grid;
  grid-template-columns: 56px minmax(0, 1fr);
  gap: 12px;
  align-items: center;
}
.detailSectionTitle {
  font-size: 13px;
  font-weight: 900;
}
.bioBox {
  margin-top: 10px;
  font-size: 13px;
  line-height: 1.7;
  color: var(--ah-text-secondary);
  white-space: pre-wrap;
}
.detailFooter {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.detailTip {
  font-size: 12px;
  color: var(--ah-text-tertiary);
  line-height: 1.5;
}
.contactBtn {
  flex: 0 0 auto;
}
.drawerHero {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 14px;
}
.drawerName {
  font-weight: 900;
}
.drawerSub {
  font-size: 12px;
  color: var(--ah-text-tertiary);
}
.drawerSection {
  margin-top: 14px;
}
.drawerTitle {
  font-size: 13px;
  font-weight: 900;
  margin-bottom: 8px;
}
.drawerBio {
  font-size: 13px;
  line-height: 1.7;
  color: var(--ah-text-secondary);
  white-space: pre-wrap;
}
@media (max-width: 1180px) {
  .contactsPage {
    grid-template-columns: 1fr;
  }
}
</style>
