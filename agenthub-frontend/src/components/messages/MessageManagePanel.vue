<template>
  <div class="sidePanel">
    <div class="sideHeader">
      <div>
        <div class="sideTitle">{{ activeGroup?.type === 'project' ? '项目设置' : '会话设置' }}</div>
        <div class="sideSubtitle">{{ activeGroup?.name || '未选择会话' }}</div>
      </div>
      <el-button class="sideCloseBtn" :icon="Close" circle text @click="$emit('close')" aria-label="关闭聊天管理" />
    </div>

    <el-scrollbar class="sideBody" v-if="activeGroup">
      <div class="groupHero">
        <div class="groupAvatar">{{ (activeGroup.name || '项').slice(0, 1) }}</div>
        <div class="groupName">{{ activeGroup.name }}</div>
        <div class="groupMeta">{{ activeGroup.type === 'project' ? '项目群聊' : '单聊会话' }}</div>
      </div>

      <ManageGroupInfoCard :active-group="activeGroup" @delete-group="$emit('delete-group')" />

      <ManageMemberListCard
        :active-group="activeGroup"
        :members="members"
        @remove-member="$emit('remove-member', $event)"
      />

      <ManageProjectSettingsCard
        :active-group="activeGroup"
        :users="users"
        :agents="agents"
        :adding="adding"
        :memory-cfg-loading="memoryCfgLoading"
        :memory-cfg-saving="memoryCfgSaving"
        :memory-compressing="memoryCompressing"
        :memory-cfg="memoryCfg"
        :memory-status="memoryStatus"
        :assistant-cfg-loading="assistantCfgLoading"
        :assistant-cfg-saving="assistantCfgSaving"
        :assistant-cfg="assistantCfg"
        v-model:add-kind="addKindModel"
        v-model:add-user-id="addUserIdModel"
        v-model:add-agent-id="addAgentIdModel"
        v-model:assistant-enabled="assistantEnabledModel"
        @add-member="$emit('add-member')"
        @save-memory-config="$emit('save-memory-config')"
        @run-memory-compress="$emit('run-memory-compress')"
        @refresh-memory-status="$emit('refresh-memory-status')"
        @save-assistant-config="$emit('save-assistant-config')"
      />

      <div v-if="manageErr" class="errBox">{{ manageErr }}</div>
    </el-scrollbar>

    <el-scrollbar v-else class="sideBody">
      <div class="sideEmpty">
        <div class="empty">未选择会话</div>
      </div>
    </el-scrollbar>
  </div>
</template>

<script setup lang="ts">
import { Close } from '@element-plus/icons-vue'
import type { Agent, Group, MemoryCompressorConfig, MemoryCompressorStatus, Member, User } from '@/api/models.ts'
import type { GroupAssistantConfig } from '@/api/models.ts'
import ManageGroupInfoCard from './ManageGroupInfoCard.vue'
import ManageMemberListCard from './ManageMemberListCard.vue'
import ManageProjectSettingsCard from './ManageProjectSettingsCard.vue'

const {
  activeGroup,
  members,
  users,
  agents,
  manageErr,
  adding,
  memoryCfgLoading,
  memoryCfgSaving,
  memoryCompressing,
  memoryCfg,
  memoryStatus,
  assistantCfgLoading,
  assistantCfgSaving,
  assistantCfg,
} = defineProps<{
  activeGroup: Group | null
  members: Member[]
  users: User[]
  agents: Agent[]
  manageErr: string
  adding: boolean
  memoryCfgLoading: boolean
  memoryCfgSaving: boolean
  memoryCompressing: boolean
  memoryCfg: MemoryCompressorConfig
  memoryStatus: MemoryCompressorStatus | null
  assistantCfgLoading: boolean
  assistantCfgSaving: boolean
  assistantCfg: GroupAssistantConfig | null
}>()

const addKindModel = defineModel<'user' | 'agent'>('addKind', { required: true })
const addUserIdModel = defineModel<string>('addUserId', { required: true })
const addAgentIdModel = defineModel<string>('addAgentId', { required: true })
const assistantEnabledModel = defineModel<boolean>('assistantEnabled', { required: true })

defineEmits<{
  (e: 'close'): void
  (e: 'delete-group'): void
  (e: 'remove-member', member: Member): void
  (e: 'add-member'): void
  (e: 'save-memory-config'): void
  (e: 'run-memory-compress'): void
  (e: 'refresh-memory-status'): void
  (e: 'save-assistant-config'): void
}>()
</script>

<style scoped>
.sidePanel {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--ah-surface);
  backdrop-filter: blur(10px);
  border: 1px solid var(--ah-border);
  border-radius: 26px;
  overflow: hidden;
  min-width: 0;
  box-shadow: var(--ah-shadow-md);
}
.sideHeader {
  min-height: 74px;
  padding: 14px 20px;
  border-bottom: 1px solid var(--ah-border-soft);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex: 0 0 auto;
}
.sideTitle {
  font-size: 18px;
  font-weight: 900;
}
.sideSubtitle {
  margin-top: 4px;
  font-size: 12px;
  color: var(--ah-text-tertiary);
}
.sideCloseBtn {
  width: 40px;
  height: 40px;
  border-radius: 14px;
  color: var(--ah-text-secondary);
  background: var(--ah-surface-soft);
}
.sideBody {
  flex: 1;
  min-height: 0;
  padding: 22px 22px 24px;
}
.sideEmpty {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}
.groupHero {
  display: grid;
  justify-items: center;
  gap: 10px;
  padding: 8px 0 22px;
}
.groupAvatar {
  width: 80px;
  height: 80px;
  border-radius: 28px;
  display: grid;
  place-items: center;
  background: var(--ah-avatar-gradient);
  color: var(--ah-icon-dark, var(--ah-text-primary));
  font-size: 30px;
  font-weight: 900;
  border: 1px solid var(--ah-border-soft);
}
.groupName {
  font-size: 18px;
  font-weight: 900;
  color: var(--ah-text-primary);
}
.groupMeta {
  font-size: 13px;
  color: var(--ah-text-tertiary);
}
.errBox {
  margin-top: 12px;
  color: var(--ah-danger);
  font-size: 12px;
}
</style>
