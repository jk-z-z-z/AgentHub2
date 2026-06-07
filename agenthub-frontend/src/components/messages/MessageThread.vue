<template>
  <div ref="scrollContainerRef" class="chatBody" @scroll="updatePinnedState">
    <div v-if="loading" class="empty">加载中…</div>
    <div v-else-if="!activeGroup" class="empty">从左侧选择会话</div>
    <template v-else>
      <div v-if="messages.length === 0" class="empty">暂无消息</div>
      <div v-for="m in messages" :key="m.id" class="msgRow" :class="sideClass(m)">
        <div class="bubble">
          <div class="msgMeta">{{ senderName(m.sender_member_id) }}</div>
          <div class="msgText">{{ m.content }}</div>
          <div v-if="deliveryResult(m)" class="msgDelivery" :data-status="deliveryStatus(m)">
            <span class="msgDeliveryPill">查看交付结果</span>
            <span v-if="appliedFileCount(m) > 0" class="msgDeliveryPill">已写入 {{ appliedFileCount(m) }} 个文件</span>
            <span class="msgDeliveryPill">{{ validationLabel(m) }}</span>
          </div>
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
      <div ref="bottomAnchorRef" class="bottomAnchor" aria-hidden="true" />
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import type { Group, Member, Message } from '../../api/groups'

const props = defineProps<{
  loading: boolean
  activeGroup: Group | null
  messages: Message[]
  members: Member[]
}>()

const scrollContainerRef = ref<HTMLElement | null>(null)
const bottomAnchorRef = ref<HTMLElement | null>(null)
const pinnedToBottom = ref(true)
const pendingInitialScroll = ref(true)

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

function deliveryResult(message: Message) {
  const meta = messageMeta(message)
  const delivery = meta.delivery_result
  if (!delivery || typeof delivery !== 'object' || Array.isArray(delivery)) return null
  return delivery as { status?: unknown }
}

function deliveryStatus(message: Message) {
  return String(deliveryResult(message)?.status || 'idle')
}

function appliedFileCount(message: Message) {
  const meta = messageMeta(message)
  const applied = meta.applied_files
  return Array.isArray(applied) ? applied.length : 0
}

function validationLabel(message: Message) {
  const delivery = deliveryResult(message)
  const deliveryStatus = String(delivery?.status || '')
  if (deliveryStatus === 'failed' && appliedFileCount(message) === 0) return '未写入文件'
  const meta = messageMeta(message)
  const validation = meta.validation_result
  if (!validation || typeof validation !== 'object' || Array.isArray(validation)) return '未验证'
  return Boolean((validation as { ok?: unknown }).ok) ? '验证通过' : '验证失败'
}

function sideClass(message: Message) {
  const sender = props.members.find((item) => String(item.id) === String(message.sender_member_id))
  if (sender?.kind === 'user') return 'right'
  return 'left'
}

function isNearBottom() {
  const el = scrollContainerRef.value
  if (!el) return true
  return el.scrollHeight - el.scrollTop - el.clientHeight <= 96
}

function updatePinnedState() {
  pinnedToBottom.value = isNearBottom()
}

async function scrollToBottom() {
  await nextTick()
  await new Promise<void>((resolve) => window.requestAnimationFrame(() => resolve()))
  const el = scrollContainerRef.value
  const anchor = bottomAnchorRef.value
  if (!el) return
  anchor?.scrollIntoView({ block: 'end' })
  el.scrollTop = el.scrollHeight
  pinnedToBottom.value = true
  pendingInitialScroll.value = false
}

const lastMessageKey = computed(() => {
  const last = props.messages.at(-1)
  if (!last) return ''
  return `${last.id}:${last.updated_at}:${last.content.length}`
})

watch(
  () => props.activeGroup?.id || '',
  () => {
    pinnedToBottom.value = true
    pendingInitialScroll.value = true
  },
  { flush: 'post' },
)

watch(
  () => [props.activeGroup?.id || '', props.loading, props.messages.length, lastMessageKey.value] as const,
  ([groupId, loading]) => {
    if (!groupId || loading) return
    if (!pendingInitialScroll.value && !pinnedToBottom.value) return
    void scrollToBottom()
  },
  { flush: 'post' },
)

onMounted(() => {
  void scrollToBottom()
})
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
.msgDelivery {
  margin-top: 10px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.msgDeliveryPill {
  display: inline-flex;
  align-items: center;
  min-height: 28px;
  padding: 0 12px;
  border-radius: 999px;
  background: rgba(31, 35, 41, 0.06);
  color: rgba(31, 35, 41, 0.76);
  font-size: 12px;
  font-weight: 700;
}
.msgDelivery[data-status='succeeded'] .msgDeliveryPill {
  background: rgba(32, 122, 50, 0.1);
  color: #207a32;
}
.msgDelivery[data-status='failed'] .msgDeliveryPill {
  background: rgba(220, 38, 38, 0.1);
  color: #b91c1c;
}
.msgDelivery[data-status='partial'] .msgDeliveryPill {
  background: rgba(217, 119, 6, 0.12);
  color: #b45309;
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
.bottomAnchor {
  width: 100%;
  height: 1px;
  flex: 0 0 auto;
}
</style>
