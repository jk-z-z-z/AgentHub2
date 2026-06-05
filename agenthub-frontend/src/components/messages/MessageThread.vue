<template>
  <el-scrollbar class="chatBody">
    <el-empty v-if="loading" description="加载中…" />
    <el-empty v-else-if="!activeGroup" description="从左侧选择会话" />
    <template v-else>
      <el-empty v-if="messages.length === 0" description="暂无消息" />
      <div v-for="m in messages" :key="m.id" class="msgRow" :class="sideClass(m)">
        <el-card class="bubble" shadow="never">
          <div class="msgMeta">{{ senderName(m.sender_member_id) }}</div>
          <div class="msgText">{{ m.content }}</div>
        </el-card>
      </div>
    </template>
  </el-scrollbar>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Group, Member, Message } from '@/api/models.ts'

const props = defineProps<{
  loading: boolean
  activeGroup: Group | null
  messages: Message[]
  members: Member[]
}>()

const memberNameMap = computed(() => {
  const out: Record<string, string> = {}
  for (const member of props.members) {
    out[String(member.id)] = member.display_name || String(member.id)
  }
  return out
})

function senderName(memberId: string) {
  return memberNameMap.value[String(memberId)] || String(memberId)
}

function sideClass(message: Message) {
  const sender = props.members.find((item) => String(item.id) === String(message.sender_member_id))
  if (sender?.kind === 'user') return 'right'
  return 'left'
}
</script>

<style scoped>
.chatBody {
  flex: 1;
  min-height: 0;
  padding: 18px 18px 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.msgRow {
  display: flex;
}
.msgRow.left {
  justify-content: flex-start;
}
.msgRow.right {
  justify-content: flex-end;
}
.bubble {
  max-width: 72%;
  border-radius: 14px;
  background: #fff;
  border: 1px solid rgba(31, 35, 41, 0.06);
  line-height: 1.5;
}
.bubble :deep(.el-card__body) {
  padding: 10px 12px;
}
.msgRow.right .bubble {
  background: rgba(79, 140, 255, 0.14);
  border-color: rgba(79, 140, 255, 0.18);
}
.msgMeta {
  font-size: 12px;
  opacity: 0.6;
  margin-bottom: 4px;
}
.msgText {
  white-space: pre-wrap;
}
</style>
