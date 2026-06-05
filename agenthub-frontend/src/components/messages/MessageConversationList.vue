<template>
  <section class="convPane">
    <div class="paneHeader">
      <el-input v-model="searchModel" class="searchInput" placeholder="搜索" clearable>
        <template #prefix>
          <el-icon class="searchIcon">
            <Search />
          </el-icon>
        </template>
      </el-input>
      <el-button class="addBtn" :icon="CirclePlus" circle plain @click="$emit('create')" aria-label="新建会话" />
    </div>

    <div class="convList">
      <div
        v-for="g in groups"
        :key="g.id"
        class="convItem"
        :class="{ active: g.id === activeGroupId }"
        @click="$emit('select', g.id)"
      >
        <div class="avatar">{{ avatarText(g.name) }}</div>
        <div class="meta">
          <div class="row1">
            <div class="name">{{ g.name }}</div>
            <div class="time">{{ lastTimeMap[g.id] || '' }}</div>
          </div>
          <div class="row2">
            <div class="preview">{{ lastPreviewMap[g.id] || '' }}</div>
            <div class="badge">{{ g.type === 'project' ? '项目组' : '单聊' }}</div>
          </div>
        </div>
      </div>
      <div v-if="!loading && groups.length === 0" class="emptyState">暂无会话</div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { CirclePlus, Search } from '@element-plus/icons-vue'
import type { Group } from '@/api/models.ts'

const searchModel = defineModel<string>('search', { default: '' })

defineProps<{
  groups: Group[]
  activeGroupId: string
  lastPreviewMap: Record<string, string>
  lastTimeMap: Record<string, string>
  loading: boolean
}>()

defineEmits<{
  (e: 'select', id: string): void
  (e: 'create'): void
}>()

function avatarText(name: string) {
  const t = (name || '').trim()
  return t ? t.slice(0, 1) : '群'
}
</script>

<style scoped>
.convPane {
  background: rgba(255, 255, 255, 0.84);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(31, 35, 41, 0.08);
  border-radius: 18px;
  overflow: hidden;
  min-width: 0;
  display: flex;
  flex-direction: column;
}
.paneHeader {
  height: 64px;
  padding: 12px;
  display: flex;
  align-items: center;
  gap: 12px;
  border-bottom: 1px solid rgba(31, 35, 41, 0.06);
}
.searchInput {
  flex: 1;
}
.searchInput :deep(.el-input__wrapper) {
  height: 38px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.92);
  box-shadow: none;
}
.searchInput :deep(.el-input__inner) {
  color: rgba(31, 35, 41, 0.92);
}
.searchIcon {
  font-size: 18px;
}
.addBtn {
  width: 38px;
  height: 38px;
  color: rgba(31, 35, 41, 0.88);
}
.convList {
  padding: 8px;
  display: grid;
  gap: 6px;
  overflow: auto;
  max-height: calc(100% - 60px);
}
.convItem {
  display: grid;
  grid-template-columns: 52px 1fr;
  gap: 10px;
  padding: 12px 10px;
  border-radius: 14px;
  cursor: pointer;
}
.convItem:hover {
  background: rgba(79, 140, 255, 0.06);
}
.convItem.active {
  background: rgba(79, 140, 255, 0.12);
}
.avatar {
  width: 52px;
  height: 52px;
  border-radius: 14px;
  display: grid;
  place-items: center;
  background: linear-gradient(135deg, #4f8cff, #7aa8ff);
  color: #fff;
  font-weight: 800;
  font-size: 16px;
}
.meta .row1 {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.name {
  font-weight: 800;
  font-size: 16px;
}
.time {
  font-size: 12px;
  opacity: 0.55;
}
.row2 {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-top: 5px;
}
.preview {
  font-size: 13px;
  opacity: 0.66;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.badge {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 999px;
  background: rgba(79, 140, 255, 0.14);
  color: #2563eb;
  font-weight: 700;
  white-space: nowrap;
}
.emptyState {
  padding: 16px 4px;
  opacity: 0.6;
  text-align: center;
}
</style>
