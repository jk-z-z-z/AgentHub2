<template>
  <el-scrollbar class="chatBody">
    <div class="chatStream">
      <el-empty v-if="loading" description="加载中…" />
      <el-empty v-else-if="!activeGroup" description="从左侧选择会话" />
      <template v-else>
        <el-empty v-if="messages.length === 0" description="暂无消息" />
        <div v-for="m in messages" :key="m.id" class="msgRow" :class="sideClass(m)">
          <div class="msgLane">
            <div class="bubbleWrap">
              <div class="msgMeta">{{ senderName(m.sender_member_id) }}</div>
              <div class="bubble" :class="{ rich: isRichMessage(m.content) }">
                <template v-if="isRichMessage(m.content)">
                  <div class="msgLead">{{ extractLead(m.content) }}</div>
                  <div class="msgCard">
                    <div class="msgCardText">{{ extractBody(m.content) }}</div>
                  </div>
                </template>
                <div v-else class="msgText">{{ m.content }}</div>
              </div>
            </div>
          </div>
        </div>
      </template>
    </div>
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

function isRichMessage(content: string) {
  return content.includes('\n\n') || content.length > 160
}

function extractLead(content: string) {
  const trimmed = content.trim()
  const parts = trimmed.split(/\n\n+/)
  if (parts.length <= 1) return trimmed
  return parts[0] || trimmed
}

function extractBody(content: string) {
  const trimmed = content.trim()
  const parts = trimmed.split(/\n\n+/)
  if (parts.length <= 1) return trimmed
  return parts.slice(1).join('\n\n')
}
</script>

<style scoped>
.chatBody {
  flex: 1;
  min-height: 0;
  padding: 24px 24px 16px;
}
.chatStream {
  display: flex;
  flex-direction: column;
  gap: 18px;
  width: min(100%, 840px);
  margin: 0 auto;
  min-height: 100%;
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
.msgLane {
  width: 100%;
  display: flex;
}
.msgRow.left .msgLane {
  justify-content: flex-start;
}
.msgRow.right .msgLane {
  justify-content: flex-end;
}
.bubbleWrap {
  width: min(100%, 720px);
}
.bubble {
  max-width: 78%;
  border-radius: 24px;
  background: var(--ah-chat-bubble-ai);
  border: 1px solid var(--ah-border-soft);
  line-height: 1.6;
  padding: 16px 18px;
  box-shadow: 0 8px 18px rgba(70, 58, 43, 0.04);
}
.msgRow.right .bubble {
  background: var(--ah-chat-bubble-user);
  border-color: var(--ah-chat-bubble-user-border);
}
.msgRow.right .bubbleWrap {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}
.bubble.rich {
  max-width: 82%;
}
.msgMeta {
  font-size: 12px;
  color: var(--ah-text-tertiary);
  margin-bottom: 6px;
  font-weight: 700;
  padding: 0 6px;
}
.msgText {
  white-space: pre-wrap;
  font-size: 15px;
  color: var(--ah-text-primary);
  line-height: 1.7;
}
.msgLead {
  white-space: pre-wrap;
  font-size: 15px;
  color: var(--ah-text-primary);
  line-height: 1.7;
}
.msgCard {
  margin-top: 12px;
  border-top: 1px solid var(--ah-border-soft);
  padding-top: 12px;
}
.msgCardText {
  white-space: pre-wrap;
  font-size: 15px;
  line-height: 1.75;
  color: var(--ah-text-primary);
  background: var(--ah-surface-strong);
  border: 1px solid var(--ah-border-soft);
  border-radius: 18px;
  padding: 14px 16px;
}
</style>
