<template>
  <div class="chatComposer">
    <div class="composerMid">
      <div v-if="canMentionAgents && selectedMentions.size > 0" class="mentionChips">
        <span v-for="id in Array.from(selectedMentions)" :key="id" class="chip">
          @{{ mentionNames[id] || id }}
          <button class="chipX" @click="$emit('remove-mention', id)">×</button>
        </span>
      </div>
      <textarea
        :value="draft"
        class="input"
        placeholder="输入消息…"
        rows="1"
        @input="$emit('update:draft', ($event.target as HTMLTextAreaElement).value)"
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
            <div class="msAvatar">
              <el-icon>
                <Monitor />
              </el-icon>
            </div>
            <div class="msName">{{ m.display_name }}</div>
          </div>
          <div v-if="filteredAgentMembers.length === 0" class="msEmpty">无匹配智能体</div>
        </div>
      </div>
    </div>
    <div class="composerActions">
      <button v-if="canMentionAgents" class="toolBtn" @click="$emit('open-mention')" aria-label="选择要@的智能体">
        @
      </button>
      <button class="sendBtn" :disabled="!canSend" @click="$emit('send')" aria-label="发送消息">
        <el-icon>
          <ArrowUp />
        </el-icon>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ArrowUp, Monitor } from '@element-plus/icons-vue'
import type { Member } from '@/api/models.ts'

defineProps<{
  draft: string
  canMentionAgents: boolean
  canSend: boolean
  selectedMentions: Set<string>
  mentionSuggestOpen: boolean
  filteredAgentMembers: Member[]
  mentionNames: Record<string, string>
}>()

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
  margin: 0 18px 18px;
  min-height: 180px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 14px;
  background: rgba(255, 255, 255, 0.96);
  border: 1px solid rgba(31, 35, 41, 0.08);
  border-radius: 22px;
  box-shadow: 0 10px 28px rgba(31, 35, 41, 0.08);
}
.composerMid {
  position: relative;
  min-width: 0;
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 10px;
  flex: 1;
}
.composerActions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}
.toolBtn {
  width: 34px;
  height: 34px;
  border: 0;
  border-radius: 999px;
  background: rgba(31, 35, 41, 0.05);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
}
.input {
  resize: none;
  width: 100%;
  min-height: 118px;
  border: 0;
  border-radius: 16px;
  padding: 10px 2px 4px 2px;
  outline: none;
  background: transparent;
  font-size: 14px;
  line-height: 1.6;
  box-sizing: border-box;
  align-self: stretch;
  flex: 1;
}
.mentionChips {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 2px;
}
.chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
  border-radius: 999px;
  background: rgba(79, 140, 255, 0.12);
  border: 1px solid rgba(79, 140, 255, 0.18);
  font-size: 12px;
  font-weight: 800;
}
.chipX {
  border: 0;
  background: transparent;
  cursor: pointer;
  opacity: 0.7;
  font-weight: 900;
}
.chipX:hover {
  opacity: 1;
}
.mentionSuggest {
  position: absolute;
  left: 0;
  right: 0;
  top: calc(100% + 8px);
  z-index: 10;
  border: 1px solid rgba(31, 35, 41, 0.08);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.98);
  box-shadow: 0 18px 40px rgba(31, 35, 41, 0.1);
  overflow: hidden;
}
.msTitle {
  padding: 10px 12px 0;
  font-size: 12px;
  font-weight: 800;
  color: rgba(31, 35, 41, 0.65);
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
  background: rgba(79, 140, 255, 0.08);
}
.msAvatar {
  width: 28px;
  height: 28px;
  border-radius: 999px;
  background: rgba(79, 140, 255, 0.12);
  display: inline-flex;
  align-items: center;
  justify-content: center;
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
.sendBtn {
  width: 40px;
  height: 40px;
  border: 0;
  border-radius: 999px;
  background: linear-gradient(135deg, #4f8cff, #6d9dff);
  color: #fff;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 8px 18px rgba(79, 140, 255, 0.28);
}
.sendBtn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
  box-shadow: none;
}
</style>
