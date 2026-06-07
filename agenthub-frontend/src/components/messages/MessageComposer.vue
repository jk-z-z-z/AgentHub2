<template>
  <el-card class="chatComposer" shadow="never">
    <div class="composerShell">
      <div v-if="showPlaceholder" class="composerPlaceholder">
        同步更多项目背景和信息，提升协作效率
      </div>

      <div v-if="canMentionAgents && selectedMentions.size > 0" class="mentionChips">
        <el-tag
          v-for="id in Array.from(selectedMentions)"
          :key="id"
          class="chip"
          effect="light"
          closable
          @close="$emit('remove-mention', id)"
        >
          @{{ mentionNames[id] || id }}
        </el-tag>
      </div>

      <div class="editorArea">
        <el-input
          :model-value="draft"
          class="input"
          type="textarea"
          :autosize="{ minRows: 5, maxRows: 5 }"
          placeholder=""
          @update:model-value="$emit('update:draft', $event)"
          @keydown="$emit('keydown', $event as KeyboardEvent)"
        />

        <div v-if="canMentionAgents && mentionSuggestOpen" class="mentionSuggest">
          <div class="msTitle">@ 提示</div>
          <div class="msList">
            <div
              v-for="m in filteredAgentMembers"
              :key="m.id"
              class="msItem"
              @click="$emit('pick-mention', m.id)"
            >
              <el-avatar class="msAvatar" :size="28">
                <el-icon>
                  <Monitor />
                </el-icon>
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
import { computed } from 'vue'
import { ArrowUp, Monitor } from '@element-plus/icons-vue'
import type { Member } from '@/api/models.ts'

const props = defineProps<{
  draft: string
  canMentionAgents: boolean
  canSend: boolean
  selectedMentions: Set<string>
  mentionSuggestOpen: boolean
  filteredAgentMembers: Member[]
  mentionNames: Record<string, string>
}>()

const showPlaceholder = computed(() => !String(props.draft || '').trim())

defineEmits<{
  (e: 'update:draft', value: string): void
  (e: 'keydown', event: KeyboardEvent): void
  (e: 'open-mention'): void
  (e: 'send'): void
  (e: 'remove-mention', memberId: string): void
  (e: 'pick-mention', memberId: string): void
}>()
</script>

<style scoped>
.chatComposer {
  margin: 0 24px 24px;
  padding: 0;
  background: transparent;
  border: 1px solid var(--ah-composer-border, var(--ah-border));
  border-radius: 32px;
  box-shadow: 0 8px 24px rgba(70, 58, 43, 0.08);
  overflow: hidden;
}
.chatComposer :deep(.el-card__body) {
  padding: 0;
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
.mentionChips {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 8px;
  padding-right: 74px;
}
.chip {
  font-size: 12px;
  font-weight: 800;
}
.editorArea {
  position: relative;
  min-height: 92px;
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
  left: 0;
  right: 0;
  bottom: calc(100% + 10px);
  z-index: 10;
  border: 1px solid var(--ah-border);
  border-radius: 16px;
  background: var(--ah-tooltip-bg);
  box-shadow: var(--ah-tooltip-shadow);
  overflow: hidden;
}
.msTitle {
  padding: 10px 12px 0;
  font-size: 12px;
  font-weight: 800;
  color: var(--ah-text-tertiary);
}
.msList {
  padding: 8px;
  max-height: 180px;
  overflow: auto;
  display: grid;
  gap: 6px;
}
.msItem {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border-radius: 12px;
  cursor: pointer;
}
.msItem:hover {
  background: var(--ah-primary-ghost);
}
.msAvatar {
  border-radius: 999px;
  background: var(--ah-surface-soft);
}
.msName {
  font-size: 13px;
  font-weight: 700;
}
.msEmpty {
  padding: 10px 4px;
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
