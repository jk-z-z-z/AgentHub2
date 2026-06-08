<template>
  <section class="section">
    <div class="sectionHeader">
      <div class="sectionTitle">成员管理 · {{ members.length }}</div>
      <el-button size="small" type="primary" @click="$emit('open-add-member')">添加成员</el-button>
    </div>
    <div class="memberList">
      <div v-for="row in members" :key="row.id" class="memberCard">
        <div class="memberAvatar">{{ (row.display_name || '成').slice(0, 1) }}</div>
        <div class="memberMain">
          <div class="mName">{{ row.display_name }}</div>
          <div class="mMeta">{{ row.kind }}</div>
        </div>
        <el-button
          size="small"
          type="danger"
          plain
          @click="$emit('remove-member', row)"
          :disabled="activeGroup?.type === 'personal'"
        >
          移除
        </el-button>
      </div>
    </div>
    <div class="note">
    </div>
  </section>
</template>

<script setup lang="ts">
import type { Group, Member } from '@/api/models.ts'

defineProps<{
  activeGroup: Group | null
  members: Member[]
}>()

defineEmits<{
  (e: 'remove-member', member: Member): void
  (e: 'open-add-member'): void
}>()
</script>

<style scoped>
.section {
  margin-bottom: 22px;
}
.sectionHeader {
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.sectionTitle {
  font-size: 13px;
  font-weight: 900;
  color: var(--ah-text-tertiary);
}
.memberList {
  display: grid;
  gap: 12px;
}
.memberCard {
  display: grid;
  grid-template-columns: 44px minmax(0, 1fr) auto;
  gap: 12px;
  align-items: center;
  padding: 16px 16px;
  border-radius: 24px;
  border: 1px solid var(--ah-border-soft);
  background: var(--ah-surface-soft);
}
.memberAvatar {
  width: 44px;
  height: 44px;
  border-radius: 16px;
  display: grid;
  place-items: center;
  background: var(--ah-avatar-gradient);
  color: var(--ah-icon-dark, var(--ah-text-primary));
  font-weight: 900;
}
.mName {
  font-weight: 900;
  color: var(--ah-text-primary);
}
.mMeta {
  font-size: 12px;
  color: var(--ah-text-tertiary);
  margin-top: 2px;
}
.note {
  color: var(--ah-text-tertiary);
  font-size: 12px;
  margin-top: 12px;
  line-height: 1.6;
}
</style>
