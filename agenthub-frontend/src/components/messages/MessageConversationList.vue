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

    <el-table
      :data="groups"
      class="convList"
      height="100%"
      empty-text="暂无会话"
      :row-class-name="tableRowClassName"
      @row-click="handleRowClick"
    >
      <el-table-column label="" width="64">
        <template #default="{ row }">
          <div class="avatar">{{ avatarText(row.name) }}</div>
        </template>
      </el-table-column>
      <el-table-column label="会话" min-width="160">
        <template #default="{ row }">
          <div class="name">{{ row.name }}</div>
          <div class="preview">{{ lastPreviewMap[row.id] || '' }}</div>
        </template>
      </el-table-column>
      <el-table-column label="时间" width="88" align="right">
        <template #default="{ row }">
          <span class="time">{{ lastTimeMap[row.id] || '' }}</span>
        </template>
      </el-table-column>
      <el-table-column label="类型" width="90" align="right">
        <template #default="{ row }">
          <span class="badge">{{ row.type === 'project' ? '项目组' : '单聊' }}</span>
        </template>
      </el-table-column>
    </el-table>
  </section>
</template>

<script setup lang="ts">
import { CirclePlus, Search } from '@element-plus/icons-vue'
import type { Group } from '@/api/models.ts'

const searchModel = defineModel<string>('search', { default: '' })

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

function tableRowClassName({ row }: { row: Group }) {
  return row.id === props.activeGroupId ? 'active' : ''
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
  height: 100%;
}
.convList :deep(.el-table__row) {
  cursor: pointer;
}
.convList :deep(.el-table__row.active) {
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
.name {
  font-weight: 800;
  font-size: 16px;
}
.time {
  font-size: 12px;
  opacity: 0.55;
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
</style>
