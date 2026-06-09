<template>
  <el-dialog
    v-model="openModel"
    class="messageEventDialog"
    title="消息事件"
    width="980px"
    destroy-on-close
    :close-on-click-modal="false"
    @close="$emit('close')"
  >
    <div class="dialogSubTitle">{{ titleText }}</div>
    <div class="dialogBody">
      <div v-if="loading" class="empty">加载中…</div>
      <div v-else-if="error" class="errBox">{{ error }}</div>
      <div v-else-if="!events || events.length === 0" class="empty">这条消息没有可查看的事件</div>
      <div v-else class="eventList">
        <article v-for="event in events" :key="event.id" class="eventCard">
          <div class="eventTop">
            <div class="eventTitle">{{ event.event_type }}</div>
            <div class="eventMeta">#{{ event.seq }} · {{ event.status }}</div>
          </div>
          <div class="eventInfo">
            <span>类别：{{ event.category }}</span>
            <span>时间：{{ formatTime(event.created_at) }}</span>
            <span v-if="event.run_id">Run：{{ event.run_id }}</span>
          </div>
          <pre class="eventPayload">{{ formatPayload(event.payload_json) }}</pre>
        </article>
      </div>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Group, Message, MessageEvent } from '../../api/models'

const props = defineProps<{
  activeGroup: Group | null
  message: Message | null
  events: MessageEvent[]
  loading: boolean
  error: string
}>()

const openModel = defineModel<boolean>('open', { required: true })

defineEmits<{
  (e: 'close'): void
}>()

const titleText = computed(() => {
  if (!props.message) return '消息事件'
  const content = String(props.message.content || '').trim()
  return content ? `消息事件 · ${content.slice(0, 24)}${content.length > 24 ? '…' : ''}` : '消息事件'
})

function formatTime(value?: string | null) {
  if (!value) return '-'
  try {
    return new Date(value).toLocaleString()
  } catch {
    return String(value)
  }
}

function formatPayload(payload: string) {
  if (!payload) return '{}'
  try {
    return JSON.stringify(JSON.parse(payload), null, 2)
  } catch {
    return payload
  }
}
</script>

<style scoped>
.dialogSubTitle {
  margin-top: -8px;
  margin-bottom: 14px;
  font-size: 13px;
  color: var(--ah-text-tertiary);
}
.dialogBody {
  min-height: 180px;
}
.empty,
.errBox {
  padding: 18px 0;
}
.errBox {
  color: #b42318;
}
.eventList {
  display: grid;
  gap: 12px;
}
.eventCard {
  border: 1px solid rgba(31, 35, 41, 0.08);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.86);
  padding: 12px;
}
.eventTop {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}
.eventTitle {
  font-weight: 900;
}
.eventMeta {
  font-size: 12px;
  color: var(--ah-text-tertiary);
  white-space: nowrap;
}
.eventInfo {
  margin-top: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px 14px;
  font-size: 12px;
  color: var(--ah-text-secondary);
}
.eventPayload {
  margin-top: 10px;
  padding: 10px 12px;
  border-radius: 12px;
  background: rgba(31, 35, 41, 0.04);
  color: var(--ah-text-primary);
  font-size: 12px;
  line-height: 1.6;
  white-space: pre-wrap;
  overflow: auto;
}
</style>
