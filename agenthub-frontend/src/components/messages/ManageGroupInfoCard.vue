<template>
  <section class="card">
    <div class="secTitle">会话信息</div>
    <template v-if="activeGroup">
      <div class="kvRow"><span class="k">名称</span><span class="v">{{ activeGroup.name }}</span></div>
      <div class="kvRow"><span class="k">类型</span><span class="v">{{ activeGroup.type }}</span></div>
      <div class="kvRow"><span class="k">ID</span><span class="v">{{ activeGroup.id }}</span></div>
      <div class="actions">
        <el-button type="danger" plain @click="$emit('delete-group')">删除会话</el-button>
      </div>
    </template>
    <div v-else class="empty">未选择会话</div>
  </section>
</template>

<script setup lang="ts">
import type { Group } from '../../api/groups'

defineProps<{
  activeGroup: Group | null
}>()

defineEmits<{
  (e: 'delete-group'): void
}>()
</script>

<style scoped>
.card {
  border: 1px solid rgba(31, 35, 41, 0.06);
  border-radius: 14px;
  padding: 12px;
  margin-bottom: 12px;
  background: rgba(255, 255, 255, 0.7);
}
.secTitle {
  font-weight: 900;
  margin-bottom: 10px;
}
.kvRow {
  display: grid;
  grid-template-columns: 72px 1fr;
  gap: 10px;
  font-size: 12px;
  margin-bottom: 6px;
}
.k {
  opacity: 0.6;
  font-weight: 800;
}
.v {
  opacity: 0.9;
  word-break: break-all;
}
.actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 10px;
}
.empty {
  padding: 6px 2px;
  opacity: 0.6;
  font-size: 13px;
}
</style>
