<template>
  <div ref="scrollContainerRef" class="chatBody" :style="chatStyle" @scroll="updatePinnedState">
    <div v-if="loading" class="empty">加载中…</div>
    <div v-else-if="!activeGroup" class="empty">从左侧选择会话</div>
    <template v-else>
      <div v-if="messages.length === 0" class="empty">暂无消息</div>
      <div
        v-for="m in messages"
        :key="m.id"
        class="msgRow"
        :class="[sideClass(m), { isTarget: highlightedMessageId === String(m.id) }]"
        :data-message-id="String(m.id)"
      >
        <div class="msgAvatar" :class="`is-${sideClass(m)}`" aria-hidden="true">
          {{ senderAvatarText(m.sender_member_id) }}
        </div>
        <div class="msgMain" :class="`is-${sideClass(m)}`">
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
              type="button"
              class="msgReplyBtn"
              :title="'回复这条消息'"
              aria-label="回复这条消息"
              @click="$emit('reply-message', String(m.id))"
            >
              回复
            </button>
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
          <div class="bubbleWrap" :class="`is-${sideClass(m)}`">
            <div class="bubble">
              <div
                v-if="replyPreview(m)"
                class="msgReplyPreview"
                :class="{ isMissing: replyPreview(m)?.missing }"
                role="button"
                tabindex="0"
                @click="openReplyTarget(m)"
                @keydown.enter.prevent="openReplyTarget(m)"
                @keydown.space.prevent="openReplyTarget(m)"
              >
                <div class="msgReplyTop">
                  <div class="msgReplyName">{{ replyPreview(m)?.senderName }}</div>
                  <div class="msgReplyActions">
                    <button
                      v-if="replyPreview(m)?.isLong"
                      type="button"
                      class="msgReplyActionBtn"
                      @click.stop="toggleReplyExpanded(String(m.id))"
                    >
                      {{ isReplyExpanded(String(m.id)) ? '收起' : '展开' }}
                    </button>
                  </div>
                </div>
                <MessageMarkdown
                  class="msgReplyText"
                  :class="{ collapsed: replyPreview(m)?.isLong && !isReplyExpanded(String(m.id)) }"
                  :content="replyPreview(m)?.content || ''"
                />
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
  scrollToMessageId?: string
  chatFontSize?: number
}>()

const emit = defineEmits<{
  (e: 'open-code-diff', messageId: string): void
  (e: 'open-message-events', messageId: string): void
  (e: 'reply-message', messageId: string): void
  (e: 'locate-message', messageId: string): void
  (e: 'scroll-target-handled', messageId: string): void
}>()

const scrollContainerRef = ref<HTMLElement | null>(null)
const bottomAnchorRef = ref<HTMLElement | null>(null)
const pinnedToBottom = ref(true)
const pendingInitialScroll = ref(true)
const expandedReplyIds = ref<Set<string>>(new Set())
const highlightedMessageId = ref('')
const chatStyle = computed(() => ({
  '--ah-chat-font-size': `${Math.max(12, Number(props.chatFontSize || 14))}px`,
  '--ah-chat-reply-font-size': `${Math.max(11, Number(props.chatFontSize || 14) - 1)}px`,
  '--ah-chat-meta-font-size': `${Math.max(11, Number(props.chatFontSize || 14) - 2)}px`,
}))

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

function senderAvatarText(memberId: string) {
  const name = senderName(memberId).trim()
  if (!name) return '?'
  return name.slice(0, 1).toUpperCase()
}

function replyTargetId(message: Message) {
  if (message.reply_to_message_id != null && String(message.reply_to_message_id).trim()) {
    return String(message.reply_to_message_id)
  }
  const meta = messageMeta(message)
  const replyTo = meta.reply_to
  return replyTo == null ? '' : String(replyTo)
}

function replyPreview(message: Message) {
  const targetId = replyTargetId(message)
  if (!targetId) return null
  const target = props.messages.find((item) => String(item.id) === targetId)
  if (!target) {
    return {
      senderName: '原消息',
      content: '点击定位到被回复的消息',
      isLong: false,
      missing: true,
    }
  }
  const content = String(target.content || '').trim()
  const normalized = content.replace(/\s+/g, ' ').trim()
  return {
    senderName: senderName(String(target.sender_member_id)),
    content: content || '空消息',
    isLong: normalized.length > 160 || content.split('\n').length > 5,
    missing: false,
  }
}

function isReplyExpanded(messageId: string) {
  return expandedReplyIds.value.has(String(messageId))
}

function toggleReplyExpanded(messageId: string) {
  const next = new Set(expandedReplyIds.value)
  const normalized = String(messageId)
  if (next.has(normalized)) next.delete(normalized)
  else next.add(normalized)
  expandedReplyIds.value = next
}

async function scrollToMessage(messageId: string) {
  const targetId = String(messageId || '').trim()
  if (!targetId) return
  await nextTick()
  const container = scrollContainerRef.value
  if (!container) return
  const target = container.querySelector(`[data-message-id="${targetId}"]`) as HTMLElement | null
  if (!target) {
    emit('locate-message', targetId)
    return
  }
  target.scrollIntoView({ behavior: 'smooth', block: 'center' })
  highlightedMessageId.value = targetId
  window.setTimeout(() => {
    if (highlightedMessageId.value === targetId) highlightedMessageId.value = ''
  }, 1800)
}

function openReplyTarget(message: Message) {
  void scrollToMessage(replyTargetId(message))
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
  () => String(props.scrollToMessageId || '').trim(),
  async (messageId) => {
    if (!messageId) return
    const container = scrollContainerRef.value
    await nextTick()
    const target = container?.querySelector(`[data-message-id="${messageId}"]`) as HTMLElement | null
    if (!target) return
    await scrollToMessage(messageId)
    emit('scroll-target-handled', messageId)
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
  align-items: flex-start;
  gap: 10px;
}
.msgRow.left {
  justify-content: flex-start;
}
.msgRow.right {
  justify-content: flex-end;
  flex-direction: row-reverse;
}
.msgRow.isTarget .bubble {
  outline: 2px solid rgba(217, 119, 6, 0.34);
  box-shadow: 0 0 0 6px rgba(245, 158, 11, 0.12);
}
.msgAvatar {
  width: 34px;
  height: 34px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 34px;
  font-size: 13px;
  font-weight: 800;
  color: #fff;
  box-shadow: var(--ah-shadow-sm);
  user-select: none;
}
.msgAvatar.is-left {
  background: linear-gradient(135deg, #8b7355, #b08968);
}
.msgAvatar.is-right {
  background: linear-gradient(135deg, #c26d1f, #e7a24d);
}
.msgMain {
  display: flex;
  flex-direction: column;
  min-width: 0;
  max-width: min(72%, 820px);
}
.msgMain.is-right {
  align-items: flex-end;
}
.msgMain.is-left {
  align-items: flex-start;
}
.bubbleWrap {
  display: flex;
  width: 100%;
}
.bubbleWrap.is-right {
  justify-content: flex-end;
}
.bubbleWrap.is-left {
  justify-content: flex-start;
}
.bubble {
  max-width: 100%;
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
  margin-bottom: 5px;
  padding: 0 2px;
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
  font-size: var(--ah-chat-meta-font-size, 12px);
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
  font-size: var(--ah-chat-font-size, 14px);
  line-height: 1.6;
  overflow-wrap: anywhere;
}
.msgThinking {
  font-size: var(--ah-chat-reply-font-size, 13px);
  line-height: 1.6;
  color: var(--ah-text-tertiary);
  font-style: italic;
}
.msgReplyBtn {
  margin-left: 8px;
  border: 0;
  background: transparent;
  color: var(--ah-text-tertiary);
  font-size: var(--ah-chat-meta-font-size, 12px);
  cursor: pointer;
  transition: color 0.16s ease;
}
.msgReplyBtn:hover {
  color: var(--ah-text-secondary);
}
.msgReplyPreview {
  margin: 8px 0 10px;
  padding: 10px 12px;
  border: 1px solid rgba(128, 108, 84, 0.16);
  border-left: 3px solid rgba(128, 108, 84, 0.42);
  border-radius: 12px;
  background: rgba(128, 108, 84, 0.06);
  cursor: pointer;
  transition: background 0.16s ease, border-color 0.16s ease;
}
.msgReplyPreview:hover {
  background: rgba(128, 108, 84, 0.1);
  border-color: rgba(128, 108, 84, 0.24);
}
.msgReplyPreview.isMissing {
  border-style: dashed;
}
.msgReplyTop {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.msgReplyActions {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.msgReplyName {
  font-size: var(--ah-chat-meta-font-size, 12px);
  font-weight: 700;
  color: var(--ah-text-secondary);
}
.msgReplyActionBtn {
  border: 0;
  background: transparent;
  color: var(--ah-text-tertiary);
  cursor: pointer;
  font-size: var(--ah-chat-meta-font-size, 12px);
  padding: 0;
}
.msgReplyActionBtn:hover {
  color: var(--ah-text-secondary);
}
.msgReplyText {
  margin-top: 8px;
  font-size: var(--ah-chat-reply-font-size, 13px);
  color: var(--ah-text-primary);
  line-height: 1.45;
  word-break: break-word;
}
.msgReplyText.collapsed {
  max-height: 118px;
  overflow: hidden;
  mask-image: linear-gradient(to bottom, black 72%, transparent 100%);
  -webkit-mask-image: linear-gradient(to bottom, black 72%, transparent 100%);
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
