<template>
  <div class="sidePanel">
    <div class="sideHeader">
      <div>
        <div class="sideTitle">聊天管理</div>
        <div class="sideSubtitle">{{ activeGroup?.name || '未选择会话' }}</div>
      </div>
      <el-button class="sideCloseBtn" :icon="Close" circle text @click="$emit('close')" aria-label="关闭聊天管理" />
    </div>

    <el-scrollbar class="sideBody" v-if="activeGroup">
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
  background: rgba(255, 255, 255, 0.84);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(31, 35, 41, 0.08);
  border-radius: 18px;
  overflow: hidden;
  min-width: 0;
}
.sideHeader {
  height: 58px;
  padding: 0 16px;
  border-bottom: 1px solid rgba(31, 35, 41, 0.06);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex: 0 0 auto;
}
.sideTitle {
  font-size: 16px;
  font-weight: 900;
}
.sideSubtitle {
  margin-top: 2px;
  font-size: 12px;
  color: rgba(31, 35, 41, 0.58);
}
.sideCloseBtn {
  width: 32px;
  height: 32px;
  border-radius: 10px;
  color: rgba(31, 35, 41, 0.8);
}
.sideBody {
  flex: 1;
  min-height: 0;
  padding: 12px;
}
.sideEmpty {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}
.errBox {
  margin-top: 12px;
  color: #d92d20;
  font-size: 12px;
}
</style>
