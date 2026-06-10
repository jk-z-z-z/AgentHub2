<template>
  <div ref="scrollContainerRef" class="chatBody" @scroll="updatePinnedState">
    <div v-if="loading" class="empty">加载中…</div>
    <div v-else-if="!activeGroup" class="empty">从左侧选择会话</div>
    <template v-else>
      <div v-if="messages.length === 0" class="empty">暂无消息</div>
      <div v-for="m in messages" :key="m.id" class="msgRow" :class="sideClass(m)">
        <div class="bubble">
          <div class="msgMetaRow" :class="metaRowClass(m)">
            <button
              v-if="sideClass(m) === 'right'"
              type="button"
              class="msgEventBtn"
              :title="'查看事件'"
              aria-label="查看事件"
              @click="$emit('open-message-events', String(m.id))"
            >
              <el-icon>
                <ArrowLeft />
              </el-icon>
            </button>
            <span class="msgMeta">{{ senderName(m.sender_member_id) }}</span>
            <button
              v-if="sideClass(m) === 'left'"
              type="button"
              class="msgEventBtn"
              :title="'查看事件'"
              aria-label="查看事件"
              @click="$emit('open-message-events', String(m.id))"
            >
              <el-icon>
                <ArrowRight />
              </el-icon>
            </button>
          </div>
          <div v-if="thinkingLabel(m)" class="msgThinking">{{ thinkingLabel(m) }}</div>
          <MessageMarkdown v-else class="msgText" :content="m.content" />
          <div v-if="deliveryResult(m)" class="msgDelivery" :data-status="deliveryStatus(m)">
            <span class="msgDeliveryPill">查看交付结果</span>
            <span v-if="appliedFileCount(m) > 0" class="msgDeliveryPill">已写入 {{ appliedFileCount(m) }} 个文件</span>
            <span class="msgDeliveryPill">{{ validationLabel(m) }}</span>
          </div>
          <div v-if="codeDiffMeta(m)" class="msgDelivery" :data-status="codeDiffTone(m)">
            <button
              type="button"
              class="msgDeliveryPill msgDeliveryButton"
              :disabled="codeDiffDisabled(m)"
              @click="$emit('open-code-diff', codeDiffMessageId(m) || String(m.id))"
            >
              {{ codeDiffLabel(m) }}
            </button>
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
import { ArrowLeft, ArrowRight } from '@element-plus/icons-vue'
import type { Group, Member } from '../../api/groups'
import type { Message } from '../../api/messages'
import MessageMarkdown from './MessageMarkdown.vue'

const props = defineProps<{
  loading: boolean
  activeGroup: Group | null
  messages: Message[]
  members: Member[]
  currentUserId: string
}>()

defineEmits<{
  (e: 'open-code-diff', messageId: string): void
  (e: 'open-message-events', messageId: string): void
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

function thinkingLabel(message: Message) {
  const sender = props.members.find((item) => String(item.id) === String(message.sender_member_id))
  if (!sender || String(message.content || '').trim()) return ''
  if (sender.kind === 'agent') return '我正在思考…'
  if (sender.kind === 'system' && sender.display_name === '管家') return '管家正在思考…'
  return ''
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

function codeDiffMeta(message: Message) {
  const meta = messageMeta(message)
  const diff = meta.code_diff
  if (!diff || typeof diff !== 'object' || Array.isArray(diff)) return null
  return diff as { status?: unknown; message_id?: unknown; has_code_changes?: unknown }
}

function codeDiffMessageId(message: Message) {
  const diff = codeDiffMeta(message)
  if (!diff) return ''
  return String(diff.message_id || '')
}

function codeDiffTone(message: Message) {
  const status = String(codeDiffMeta(message)?.status || '')
  if (status === 'ready') return 'succeeded'
  if (status === 'failed') return 'failed'
  if (status === 'no_changes') return 'partial'
  return 'idle'
}

function codeDiffDisabled(message: Message) {
  return String(codeDiffMeta(message)?.status || '') === 'failed'
}

function codeDiffLabel(message: Message) {
  const diff = codeDiffMeta(message)
  const status = String(diff?.status || '')
  if (status === 'ready') return '查看代码 Diff'
  if (status === 'no_changes') return '本轮无代码变更'
  if (status === 'failed') return '代码 Diff 不可用'
  return '查看代码 Diff'
}

function sideClass(message: Message) {
  const sender = props.members.find((item) => String(item.id) === String(message.sender_member_id))
  if (sender?.kind === 'user' && String(sender.user_ref || '') === String(props.currentUserId || '')) return 'right'
  return 'left'
}

function metaRowClass(message: Message) {
  return sideClass(message) === 'right' ? 'is-right' : 'is-left'
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
  padding: 11px 13px;
  border-radius: 16px;
  background: var(--ah-chat-bubble-ai);
  border: 1px solid var(--ah-chat-bubble-border, rgba(31, 35, 41, 0.06));
  line-height: 1.5;
  color: var(--ah-text-primary);
  box-shadow: var(--ah-shadow-sm);
}
.msgMetaRow {
  display: flex;
  align-items: center;
  gap: 4px;
  min-height: 22px;
  margin-bottom: 6px;
}
.msgMetaRow.is-right {
  justify-content: flex-end;
}
.msgMetaRow.is-left {
  justify-content: flex-start;
}
.msgRow.right .bubble {
  background: var(--ah-chat-bubble-user);
  border-color: var(--ah-chat-bubble-user-border);
  color: var(--ah-text-primary);
}
.msgMeta {
  display: inline-flex;
  align-items: center;
  font-size: 12px;
  color: var(--ah-text-secondary);
  line-height: 1;
  white-space: nowrap;
}
.msgRow.right .msgMeta {
  color: var(--ah-text-secondary);
}
.msgEventBtn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  min-width: 22px;
  padding: 0;
  border: 0;
  border-radius: 999px;
  background: transparent;
  color: var(--ah-text-tertiary);
  cursor: pointer;
  opacity: 0.75;
  line-height: 1;
  flex: 0 0 auto;
}
.msgEventBtn:hover {
  background: rgba(31, 35, 41, 0.06);
  opacity: 1;
}
.msgEventBtn :deep(svg) {
  display: block;
}
.msgText {
  font-size: 14px;
  line-height: 1.6;
  overflow-wrap: anywhere;
}
.msgThinking {
  font-size: 13px;
  line-height: 1.6;
  color: var(--ah-text-tertiary);
  font-style: italic;
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
.msgDeliveryButton {
  border: 0;
  cursor: pointer;
}
.msgDeliveryButton:disabled {
  cursor: not-allowed;
  opacity: 0.8;
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
.bottomAnchor {
  width: 100%;
  height: 1px;
  flex: 0 0 auto;
}
</style>
