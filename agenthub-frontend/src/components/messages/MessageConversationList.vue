<template>
  <el-card class="convPane" shadow="never">
    <template #header>
      <div class="paneHeader">
        <div class="paneTitle">对话</div>
        <el-button class="addBtn" :icon="CirclePlus" text circle @click="$emit('create')" aria-label="新建会话" />
      </div>
    </template>

    <el-scrollbar class="convList">
      <el-empty v-if="loading && groups.length === 0" description="加载中…" />
      <el-empty v-else-if="groups.length === 0" description="暂无会话" />
      <div v-else class="convListInner">
        <button
          v-for="row in groups"
          :key="row.id"
          type="button"
          class="convItem"
          :class="{ active: row.id === activeGroupId }"
          @click="handleRowClick(row)"
        >
          <el-avatar class="avatar" :size="48">{{ avatarText(row.name) }}</el-avatar>
          <div class="convMain">
            <div class="convTop">
              <div class="nameRow">
                <div class="name" :title="row.name">{{ row.name }}</div>
                <span class="typePill typePillInline">{{ groupTypeLabel(row.type) }}</span>
              </div>
              <span v-if="lastTimeMap[row.id]" class="time">{{ lastTimeMap[row.id] }}</span>
            </div>
            <div class="preview" :title="lastPreviewMap[row.id] || '暂无消息'">{{ lastPreviewMap[row.id] || '暂无消息' }}</div>
          </div>
        </button>
      </div>
    </el-scrollbar>
  </el-card>
</template>

<script setup lang="ts">
import { CirclePlus } from '@element-plus/icons-vue'
import type { Group } from '@/api/models.ts'

const props = defineProps<{
  groups: Group[]
  activeGroupId: string
  lastPreviewMap: Record<string, string>
  lastTimeMap: Record<string, string>
  loading: boolean
}>()

const emit = defineEmits<{
  (e: 'select', id: string): void
  (e: 'create'): void
}>()

function avatarText(name: string) {
  const t = (name || '').trim()
  return t ? t.slice(0, 1) : '群'
}

function handleRowClick(row: Group) {
  emit('select', row.id)
}

function groupTypeLabel(type: string) {
  if (type === 'project') return '项目组'
  if (type === 'bootstrap') return '初始化会话'
  return '单聊'
}

</script>

<style scoped>
.convPane {
  background: var(--ah-surface);
  backdrop-filter: blur(10px);
  border: 1px solid var(--ah-border);
  border-radius: 18px;
  overflow: hidden;
  min-width: 0;
  display: flex;
  flex-direction: column;
  padding: 0;
}
.convPane :deep(.el-card__header) {
  padding: 0 16px;
  height: 56px;
  border-bottom: 1px solid var(--ah-border-soft);
}
.convPane :deep(.el-card__body) {
  padding: 0;
  flex: 1;
  min-height: 0;
}
.paneHeader {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.paneTitle {
  font-size: 15px;
  font-weight: 900;
  color: var(--ah-text-primary);
}
.addBtn {
  width: 36px;
  height: 36px;
  color: var(--ah-text-secondary);
}
.convList {
  flex: 1;
  min-height: 0;
}
.convListInner {
  display: grid;
  gap: 10px;
  padding: 12px;
}
.convItem {
  width: 100%;
  display: grid;
  grid-template-columns: 48px minmax(0, 1fr);
  gap: 14px;
  align-items: center;
  padding: 14px 18px;
  min-height: 0;
  border: 1px solid transparent;
  border-radius: 18px;
  background: var(--ah-conv-item-bg, transparent);
  cursor: pointer;
  text-align: left;
  transition:
    background-color 0.18s ease,
    border-color 0.18s ease,
    box-shadow 0.18s ease,
    transform 0.18s ease;
}
.convItem:hover {
  background: var(--ah-conv-item-hover-bg, var(--ah-surface-soft));
}
.convItem.active {
  background: var(--ah-conv-item-active-bg, var(--ah-list-active-bg));
  border-color: var(--ah-conv-item-active-border, var(--ah-list-active-border));
  box-shadow: 0 8px 20px rgba(70, 58, 43, 0.06);
}
.avatar {
  background: var(--ah-avatar-gradient);
  color: var(--ah-icon-dark, var(--ah-text-primary));
  font-weight: 800;
  align-self: start;
}
.convMain {
  min-width: 0;
  display: grid;
  gap: 6px;
  align-content: start;
  padding-block: 2px;
}
.convTop {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  min-width: 0;
}
.nameRow {
  min-width: 0;
  flex: 1 1 auto;
  display: flex;
  align-items: center;
  gap: 8px;
}
.name {
  font-weight: 800;
  font-size: 14px;
  line-height: 1.3;
  min-width: 0;
  flex: 0 1 auto;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  word-break: break-word;
}
.time {
  font-size: 12px;
  color: var(--ah-text-muted);
  line-height: 1;
  flex: 0 0 auto;
  min-width: 0;
  text-align: right;
  padding-top: 1px;
  margin-left: auto;
  white-space: nowrap;
}
.preview {
  font-size: 13px;
  color: var(--ah-text-tertiary);
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  line-height: 1.4;
  min-height: 1.4em;
  word-break: break-word;
}
.typePill {
  display: inline-flex;
  align-items: center;
  height: 24px;
  padding: 0 10px;
  border-radius: 999px;
  background: var(--ah-surface-strong);
  color: var(--ah-text-secondary);
  font-size: 11px;
  font-weight: 700;
  border: 1px solid var(--ah-border-soft);
}
.typePillInline {
  flex: 0 0 auto;
}
</style>
