<template>
  <section class="card">
    <div class="secTitle">成员</div>
    <div class="memberList">
      <div v-for="m in members" :key="m.id" class="memberRow">
        <div class="mLeft">
          <div class="mName">{{ m.display_name }}</div>
          <div class="mMeta">{{ m.kind }} · member#{{ m.id }}</div>
        </div>
        <div class="mRight">
          <el-button size="small" type="danger" plain @click="$emit('remove-member', m)" :disabled="activeGroup?.type === 'personal'">
            移除
          </el-button>
        </div>
      </div>
      <div v-if="members.length === 0" class="empty">暂无成员</div>
    </div>
    <div class="note">
      说明：`personal` 会话固定 2 人，不支持成员变更；`project` 会话可增删成员。
    </div>
  </section>
</template>

<script setup lang="ts">
import type { Group, Member } from '../../api/groups'

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
.memberList {
  display: grid;
  gap: 8px;
}
.memberRow {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border: 1px solid rgba(31, 35, 41, 0.06);
  border-radius: 12px;
  padding: 10px;
}
.mName {
  font-weight: 900;
}
.mMeta {
  font-size: 12px;
  opacity: 0.6;
  margin-top: 2px;
}
.empty {
  padding: 6px 2px;
  opacity: 0.6;
  font-size: 13px;
}
.note {
  opacity: 0.65;
  font-size: 12px;
  margin-top: 10px;
  line-height: 1.5;
}
</style>
