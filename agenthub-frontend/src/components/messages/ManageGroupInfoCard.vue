<template>
  <section class="section">
    <div class="sectionTitle">会话信息</div>
    <template v-if="activeGroup">
      <div class="settingCard">
        <div class="infoRow">
          <span class="label">名称</span>
          <span class="value">{{ activeGroup.name }}</span>
        </div>
        <div class="infoRow">
          <span class="label">类型</span>
          <span class="value">{{ activeGroup.type }}</span>
        </div>
        <div class="infoRow">
          <span class="label">ID</span>
          <span class="value mono">{{ activeGroup.id }}</span>
        </div>
      </div>
      <div class="actions">
        <el-button type="danger" plain @click="$emit('delete-group')">删除会话</el-button>
      </div>
    </template>
    <el-empty v-else description="未选择会话" />
  </section>
</template>

<script setup lang="ts">
import type { Group } from '@/api/models.ts'

defineProps<{
  activeGroup: Group | null
}>()

defineEmits<{
  (e: 'delete-group'): void
}>()
</script>

<style scoped>
.section {
  margin-bottom: 22px;
}
.sectionTitle {
  margin-bottom: 12px;
  font-size: 13px;
  font-weight: 900;
  color: var(--ah-text-tertiary);
}
.settingCard {
  border: 1px solid var(--ah-border-soft);
  border-radius: 24px;
  background: var(--ah-surface-soft);
  padding: 10px 18px;
}
.infoRow {
  display: grid;
  grid-template-columns: 72px minmax(0, 1fr);
  gap: 12px;
  align-items: center;
  min-height: 48px;
  border-bottom: 1px solid var(--ah-border-soft);
}
.infoRow:last-child {
  border-bottom: 0;
}
.label {
  font-size: 13px;
  font-weight: 800;
  color: var(--ah-text-tertiary);
}
.value {
  min-width: 0;
  color: var(--ah-text-primary);
  font-size: 14px;
  font-weight: 700;
  word-break: break-all;
}
.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, Liberation Mono, monospace;
}
.actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
}
</style>
