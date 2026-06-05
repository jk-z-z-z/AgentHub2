<template>
  <el-card class="card" shadow="never">
    <template #header>
      <div class="secTitle">会话信息</div>
    </template>
    <template v-if="activeGroup">
      <el-descriptions :column="1" size="small" border>
        <el-descriptions-item label="名称">{{ activeGroup.name }}</el-descriptions-item>
        <el-descriptions-item label="类型">{{ activeGroup.type }}</el-descriptions-item>
        <el-descriptions-item label="ID">{{ activeGroup.id }}</el-descriptions-item>
      </el-descriptions>
      <div class="actions">
        <el-button type="danger" plain @click="$emit('delete-group')">删除会话</el-button>
      </div>
    </template>
    <el-empty v-else description="未选择会话" />
  </el-card>
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
.card {
  border-radius: 14px;
  margin-bottom: 12px;
  background: rgba(255, 255, 255, 0.7);
}
.secTitle {
  font-weight: 900;
}
.actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
}
</style>
