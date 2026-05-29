<script setup lang="ts">
type Conversation = {
  id: string
  title: string
  badge?: string
  lastPreview: string
  lastTime: string
  unread?: number
  avatarText: string
}

defineProps<{
  conversations: Conversation[]
  activeId: string
}>()

const emit = defineEmits<{
  (e: 'select', id: string): void
  (e: 'create-group'): void
}>()
</script>

<template>
  <aside class="conversation-list">
    <div class="list-header">
      <div>
        <div class="list-title">消息</div>
        <div class="list-subtitle">AgentHub 群聊空间</div>
      </div>
      <el-button type="primary" plain size="small" @click="emit('create-group')">建群</el-button>
    </div>

    <div class="list-body">
      <button
        v-for="item in conversations"
        :key="item.id"
        class="conversation-card"
        :class="{ active: item.id === activeId }"
        @click="emit('select', item.id)"
      >
        <div class="avatar">{{ item.avatarText }}</div>
        <div class="meta">
          <div class="meta-top">
            <span class="title">{{ item.title }}</span>
            <span class="time">{{ item.lastTime }}</span>
          </div>
          <div class="meta-bottom">
            <span class="preview">{{ item.lastPreview || '暂无消息' }}</span>
            <el-tag v-if="item.badge" size="small" type="info">{{ item.badge }}</el-tag>
          </div>
        </div>
      </button>
    </div>
  </aside>
</template>

<style scoped>
.conversation-list {
  display: flex;
  flex-direction: column;
  min-width: 0;
  border-right: 1px solid rgba(15, 23, 42, 0.08);
  background: rgba(255, 255, 255, 0.72);
  backdrop-filter: blur(18px);
}

.list-header {
  padding: 18px 18px 12px;
  border-bottom: 1px solid rgba(15, 23, 42, 0.06);
}

.list-title {
  font-size: 20px;
  font-weight: 800;
}

.list-subtitle {
  margin-top: 4px;
  font-size: 12px;
  color: rgba(15, 23, 42, 0.55);
}

.list-body {
  overflow: auto;
  padding: 10px;
}

.conversation-card {
  width: 100%;
  display: flex;
  gap: 12px;
  padding: 12px;
  border: 0;
  background: transparent;
  text-align: left;
  border-radius: 16px;
  margin-bottom: 8px;
}

.conversation-card.active {
  background: rgba(32, 120, 244, 0.1);
}

.avatar {
  width: 44px;
  height: 44px;
  border-radius: 14px;
  background: linear-gradient(135deg, #d9ebff 0%, #a9d0ff 100%);
  color: #123b68;
  display: grid;
  place-items: center;
  font-weight: 700;
}

.meta {
  min-width: 0;
  flex: 1;
}

.meta-top,
.meta-bottom {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.title {
  font-weight: 700;
}

.time,
.preview {
  font-size: 12px;
  color: rgba(15, 23, 42, 0.56);
}

.preview {
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
</style>
