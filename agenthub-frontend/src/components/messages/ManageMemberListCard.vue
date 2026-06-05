<template>
  <el-card class="card" shadow="never">
    <template #header>
      <div class="secTitle">成员</div>
    </template>
    <el-table :data="members" size="small" table-layout="fixed" empty-text="暂无成员">
      <el-table-column label="名称" min-width="150">
        <template #default="{ row }">
          <div class="mName">{{ row.display_name }}</div>
          <div class="mMeta">{{ row.kind }} · member#{{ row.id }}</div>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="96" align="right">
        <template #default="{ row }">
          <el-button
            size="small"
            type="danger"
            plain
            @click="$emit('remove-member', row)"
            :disabled="activeGroup?.type === 'personal'"
          >
            移除
          </el-button>
        </template>
      </el-table-column>
    </el-table>
    <div class="note">
      说明：`personal` 会话固定 2 人，不支持成员变更；`project` 会话可增删成员。
    </div>
  </el-card>
</template>

<script setup lang="ts">
import type { Group, Member } from '@/api/models.ts'

defineProps<{
  activeGroup: Group | null
  members: Member[]
}>()

defineEmits<{
  (e: 'remove-member', member: Member): void
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
.mName {
  font-weight: 900;
}
.mMeta {
  font-size: 12px;
  opacity: 0.6;
  margin-top: 2px;
}
.note {
  opacity: 0.65;
  font-size: 12px;
  margin-top: 10px;
  line-height: 1.5;
}
</style>
