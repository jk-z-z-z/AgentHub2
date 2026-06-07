<template>
  <div class="chatBody">
    <div v-if="loading" class="empty">加载中…</div>
    <div v-else-if="!activeGroup" class="empty">从左侧选择会话</div>
    <template v-else>
      <div v-if="messages.length === 0" class="empty">暂无消息</div>
      <div v-for="m in messages" :key="m.id" class="msgRow" :class="sideClass(m)">
        <div class="bubble">
          <div class="msgMeta">{{ senderName(m.sender_member_id) }}</div>
          <div class="msgText">{{ m.content }}</div>
          <div v-if="previewUrl(m) || deployUrl(m)" class="msgActions">
            <a
              v-if="previewUrl(m)"
              class="msgActionLink"
              :href="previewUrl(m) || '#'"
              target="_blank"
              rel="noreferrer"
            >
              打开预览
            </a>
            <a
              v-if="deployUrl(m)"
              class="msgActionLink"
              :href="deployUrl(m) || '#'"
              target="_blank"
              rel="noreferrer"
            >
              打开部署
            </a>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Group, Member, Message } from '../../api/groups'

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

function messageMeta(message: Message) {
  try {
    return JSON.parse(String(message.metadata_json || '{}')) as Record<string, unknown>
  } catch {
    return {}
  }
}

function previewUrl(message: Message) {
  const meta = messageMeta(message)
  const preview = meta.preview_result
  if (!preview || typeof preview !== 'object' || Array.isArray(preview)) return ''
  return String((preview as { url?: unknown }).url || '')
}

function deployUrl(message: Message) {
  const meta = messageMeta(message)
  const deploy = meta.deploy_result
  if (!deploy || typeof deploy !== 'object' || Array.isArray(deploy)) return ''
  return String((deploy as { url?: unknown }).url || '')
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
  overflow: auto;
  padding: 18px 18px 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.empty {
  margin: auto;
  opacity: 0.6;
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
  padding: 10px 12px;
  border-radius: 14px;
  background: #fff;
  border: 1px solid rgba(31, 35, 41, 0.06);
  line-height: 1.5;
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
.msgActions {
  margin-top: 10px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.msgActionLink {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 30px;
  padding: 0 12px;
  border-radius: 999px;
  background: rgba(37, 99, 235, 0.1);
  color: #1d4ed8;
  font-size: 12px;
  font-weight: 700;
  text-decoration: none;
}
.msgActionLink:hover {
  background: rgba(37, 99, 235, 0.16);
}
</style>
