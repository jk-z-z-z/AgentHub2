<template>
  <el-card class="chatComposer" shadow="never">
    <div class="composerShell">


      <div class="editorArea">
        <div v-if="replyPreview" class="replyBanner">
          <div class="replyBannerBody">
            <div class="replyBannerTitle">回复 {{ replyPreview.senderName }}</div>
            <div class="replyBannerText">{{ replyPreview.content }}</div>
          </div>
          <button type="button" class="replyBannerClose" @click="$emit('clear-reply')">取消</button>
        </div>
        <el-input
          ref="inputRef"
          :model-value="draft"
          class="input"
          type="textarea"
          :autosize="{ minRows: 5, maxRows: 5 }"
          placeholder=""
          @update:model-value="$emit('update:draft', $event)"
          @keydown="$emit('keydown', $event as KeyboardEvent)"
        />

        <div v-if="canMentionAgents && mentionSuggestOpen" class="mentionSuggest">
          <div class="msTitle">选择要 @ 的智能体</div>
          <div class="msList">
            <div
              v-for="m in filteredAgentMembers"
              :key="m.id"
              class="msItem"
              :class="{ active: selectedMentions.has(m.id) }"
              @click="$emit('pick-mention', m.id)"
            >
              <el-avatar class="msAvatar" :size="28">
                {{ avatarText(m.display_name || String(m.id)) }}
              </el-avatar>
              <div class="msName">{{ m.display_name }}</div>
            </div>
            <div v-if="filteredAgentMembers.length === 0" class="msEmpty">无匹配智能体</div>
          </div>
        </div>
      </div>

      <div class="composerActions">
        <div class="toolGroup">
          <el-button class="toolBtn" text aria-label="更多操作">+</el-button>
          <el-button
            v-if="canMentionAgents"
            class="toolBtn"
            text
            @click="$emit('open-mention')"
            aria-label="选择要@的智能体"
          >
            @
          </el-button>
        </div>

        <el-button class="sendBtn" type="primary" :disabled="!canSend" @click="$emit('send')" aria-label="发送消息">
          <el-icon>
            <ArrowUp />
          </el-icon>
        </el-button>
      </div>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { computed, nextTick, ref } from 'vue'
import { ArrowUp } from '@element-plus/icons-vue'
import type { Member } from '@/api/models.ts'

const props = defineProps<{
  draft: string
  canMentionAgents: boolean
  canSend: boolean
  selectedMentions: Set<string>
  mentionSuggestOpen: boolean
  filteredAgentMembers: Member[]
  mentionNames: Record<string, string>
  replyPreview: { senderName: string; content: string } | null
}>()

const inputRef = ref<{ textarea?: HTMLTextAreaElement | null; focus?: () => void } | null>(null)

const showPlaceholder = computed(() => {
  const hasDraft = String(props.draft || '').trim().length > 0
  return !hasDraft && !props.mentionSuggestOpen
})

function avatarText(name: string) {
  return String(name || '@').trim().slice(0, 1).toUpperCase() || '@'
}

async function focusEditor() {
  await nextTick()
  inputRef.value?.focus?.()
  inputRef.value?.textarea?.focus?.()
}

defineExpose({
  focusEditor,
})

defineEmits<{
  (e: 'update:draft', value: string): void
  (e: 'keydown', event: KeyboardEvent): void
  (e: 'open-mention'): void
  (e: 'send'): void
  (e: 'remove-mention', memberId: string): void
  (e: 'pick-mention', memberId: string): void
  (e: 'clear-reply'): void
}>()
</script>

<style scoped>
.chatComposer {
  margin: 0 24px 24px;
  padding: 0;
  background: var(--ah-panel-bg);
  border: 1px solid var(--ah-composer-border, var(--ah-border));
  border-radius: 32px;
  box-shadow: 0 8px 24px rgba(70, 58, 43, 0.08);
  overflow: visible;
}
.chatComposer :deep(.el-card__body) {
  padding: 0;
  overflow: visible;
}
.composerShell {
  position: relative;
  min-height: 156px;
  padding: 18px 18px 18px;
}
.composerPlaceholder {
  position: absolute;
  top: 20px;
  left: 18px;
  right: 18px;
  pointer-events: none;
  font-size: 15px;
  line-height: 1.45;
  color: var(--ah-text-tertiary);
}
.editorArea {
  position: relative;
  min-height: 92px;
  padding-right: 74px;
}
.replyBanner {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
  padding: 10px 12px;
  border-radius: 14px;
  background: rgba(120, 104, 82, 0.08);
  border: 1px solid rgba(120, 104, 82, 0.2);
  border-left: 4px solid rgba(120, 104, 82, 0.34);
}
.replyBannerBody {
  min-width: 0;
}
.replyBannerTitle {
  font-size: 12px;
  font-weight: 800;
  color: rgba(72, 62, 49, 0.92);
}
.replyBannerText {
  margin-top: 4px;
  font-size: 13px;
  line-height: 1.5;
  color: rgba(72, 62, 49, 0.8);
  word-break: break-word;
}
.replyBannerClose {
  border: 0;
  background: transparent;
  color: rgba(120, 104, 82, 0.7);
  cursor: pointer;
  font-size: 12px;
}
.replyBannerClose:hover {
  color: rgba(72, 62, 49, 0.9);
}
.input {
  width: 100%;
}
.input :deep(.el-textarea) {
  background: transparent !important;
}
.input :deep(.el-textarea__inner) {
  min-height: 92px;
  border: 0;
  border-radius: 0;
  padding: 0;
  box-shadow: none !important;
  outline: none !important;
  background: transparent !important;
  font-size: 15px;
  line-height: 1.7;
  resize: none;
  appearance: none;
  -webkit-appearance: none;
}
.input :deep(.el-textarea__inner:focus) {
  box-shadow: none !important;
  outline: none !important;
}
.input :deep(.el-textarea__inner:hover) {
  box-shadow: none !important;
}
.input :deep(.el-textarea) {
  border: 0 !important;
  outline: none !important;
}
.input :deep(.el-textarea__wrapper) {
  border: 0 !important;
  box-shadow: none !important;
  background: transparent !important;
}
.input :deep(.el-textarea__inner::placeholder) {
  color: transparent;
}
.mentionSuggest {
  position: absolute;
  left: -10px;
  bottom: calc(100% + 18px);
  z-index: 10;
  width: min(340px, calc(100vw - 72px));
  border: 1px solid var(--ah-border);
  border-radius: 20px;
  background: var(--ah-panel-bg);
  box-shadow: 0 22px 48px rgba(70, 58, 43, 0.16);
  overflow: hidden;
}
.mentionSuggest::after {
  content: '';
  position: absolute;
  left: 162px;
  bottom: -9px;
  width: 18px;
  height: 18px;
  background: var(--ah-panel-bg);
  border-right: 1px solid var(--ah-border);
  border-bottom: 1px solid var(--ah-border);
  transform: rotate(45deg);
}
.msTitle {
  padding: 12px 14px 4px;
  font-size: 12px;
  font-weight: 800;
  color: var(--ah-text-tertiary);
}
.msList {
  padding: 8px;
  max-height: 260px;
  overflow: auto;
  display: grid;
  gap: 4px;
}
.msItem {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 14px;
  cursor: pointer;
  transition: background-color 0.16s ease;
}
.msItem:hover,
.msItem.active {
  background: var(--ah-primary-ghost);
}
.msAvatar {
  border-radius: 999px;
  background: var(--ah-avatar-gradient);
  color: var(--ah-text-primary);
  font-size: 13px;
  font-weight: 800;
  flex-shrink: 0;
}
.msName {
  font-size: 14px;
  font-weight: 700;
  color: var(--ah-text-primary);
}
.msEmpty {
  padding: 14px 8px;
  font-size: 12px;
  opacity: 0.6;
}
.composerActions {
  position: absolute;
  left: 18px;
  right: 18px;
  bottom: 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.toolGroup {
  display: flex;
  align-items: center;
  gap: 10px;
}
.toolBtn {
  width: 40px;
  height: 40px;
  min-width: 40px;
  padding: 0;
  border-radius: 999px;
  border: 1px solid var(--ah-border-soft);
  background: rgba(255, 255, 255, 0.82);
  color: var(--ah-text-primary);
  box-shadow: 0 2px 8px rgba(70, 58, 43, 0.04);
  font-size: 22px;
  font-weight: 500;
}
.toolBtn:hover {
  background: var(--ah-surface-soft);
}
.sendBtn {
  width: 44px;
  min-width: 44px;
  height: 44px;
  border-radius: 999px;
  background: rgba(31, 27, 23, 0.42);
  border-color: rgba(31, 27, 23, 0.06);
  box-shadow: none;
  padding: 0;
}
.sendBtn:not(:disabled) {
  background: rgba(31, 27, 23, 0.46);
}
.sendBtn :deep(.el-icon) {
  font-size: 20px;
}
</style>
