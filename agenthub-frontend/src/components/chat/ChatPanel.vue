<script setup lang="ts">
import { computed, ref } from 'vue'

type ChatMessage = {
  id: string
  author: string
  senderKind: 'user' | 'agent' | 'unknown'
  content: string
  ts: string
  side: 'left' | 'right'
}

const props = defineProps<{
  title: string
  badge?: string
  messages: ChatMessage[]
  rightPanelOpen: boolean
}>()

const emit = defineEmits<{
  (e: 'toggle-right-panel'): void
  (e: 'send', text: string): void
}>()

const inputText = ref('')
const canSend = computed(() => inputText.value.trim().length > 0)

function send() {
  const text = inputText.value.trim()
  if (!text) return
  emit('send', text)
  inputText.value = ''
}

function senderTagType(kind: ChatMessage['senderKind']) {
  if (kind === 'agent') return 'success'
  if (kind === 'user') return 'info'
  return 'warning'
}

function senderTagText(kind: ChatMessage['senderKind']) {
  if (kind === 'agent') return 'Agent'
  if (kind === 'user') return '用户'
  return '未知'
}
</script>

<template>
  <main class="chat-pane">
    <header class="chat-header">
      <div class="chat-header-left">
        <div class="chat-title">
          <span class="chat-name">{{ props.title }}</span>
          <el-tag v-if="props.badge" size="small" type="primary">{{ props.badge }}</el-tag>
        </div>
        <div class="chat-subtitle">AgentHub · IM 协作</div>
      </div>

      <div class="chat-header-right">
        <el-space>
          <el-button text>搜索</el-button>
          <el-button text @click="emit('toggle-right-panel')">
            {{ props.rightPanelOpen ? '收起面板' : '展开面板' }}
          </el-button>
        </el-space>
      </div>
    </header>

    <div class="chat-body">
      <div class="msg-list">
        <div v-for="m in props.messages" :key="m.id" class="msg-row" :class="m.side">
          <div class="msg-bubble">
            <div class="msg-meta" :class="m.side">
              <div class="msg-author">{{ m.author }}</div>
              <el-tag size="small" effect="plain" :type="senderTagType(m.senderKind)">
                {{ senderTagText(m.senderKind) }}
              </el-tag>
            </div>
            <div class="msg-content">{{ m.content }}</div>
            <div class="msg-ts">{{ m.ts }}</div>
          </div>
        </div>
      </div>

      <div class="composer">
        <el-input v-model="inputText" placeholder="请输入消息" clearable @keyup.enter="send" />
        <el-button type="primary" :disabled="!canSend" @click="send">发送</el-button>
      </div>
    </div>
  </main>
</template>

<style scoped>
.chat-pane {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 16px;
  border-bottom: 1px solid rgba(15, 23, 42, 0.08);
  background: rgba(255, 255, 255, 0.72);
  backdrop-filter: blur(18px);
}

.chat-title {
  display: flex;
  align-items: center;
  gap: 10px;
}

.chat-name {
  font-size: 18px;
  font-weight: 800;
}

.chat-subtitle {
  margin-top: 4px;
  font-size: 12px;
  color: rgba(15, 23, 42, 0.55);
}

.chat-body {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
}

.msg-list {
  flex: 1;
  overflow: auto;
  padding: 18px 18px 10px;
}

.msg-row {
  display: flex;
  margin-bottom: 12px;
}

.msg-row.left {
  justify-content: flex-start;
}

.msg-row.right {
  justify-content: flex-end;
}

.msg-bubble {
  max-width: min(680px, 78%);
  padding: 12px 14px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.94);
  box-shadow: 0 10px 26px rgba(15, 23, 42, 0.08);
}

.msg-row.right .msg-bubble {
  background: rgba(32, 120, 244, 0.12);
  border: 1px solid rgba(32, 120, 244, 0.18);
}

.msg-author {
  font-weight: 700;
}

.msg-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.msg-meta.right {
  justify-content: flex-end;
}

.msg-content {
  line-height: 1.55;
  white-space: pre-wrap;
}

.msg-ts {
  margin-top: 8px;
  font-size: 12px;
  color: rgba(15, 23, 42, 0.48);
}

.composer {
  display: flex;
  gap: 10px;
  padding: 12px 14px;
  border-top: 1px solid rgba(15, 23, 42, 0.08);
  background: rgba(255, 255, 255, 0.72);
  backdrop-filter: blur(18px);
}
</style>
