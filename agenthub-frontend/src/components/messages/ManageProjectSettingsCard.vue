<template>
  <section v-if="activeGroup?.type === 'project'" class="projectStack">
    <div class="card">
      <div class="secTitle">添加成员</div>
      <div class="addGrid">
        <el-select v-model="addKindModel" style="width: 120px">
          <el-option label="用户" value="user" />
          <el-option label="智能体" value="agent" />
        </el-select>
        <el-select v-if="addKindModel === 'user'" v-model="addUserIdModel" placeholder="选择用户" filterable clearable>
          <el-option v-for="u in users" :key="u.id" :label="u.display_name || u.username || u.email" :value="String(u.id)" />
        </el-select>
        <el-select v-else v-model="addAgentIdModel" placeholder="选择智能体" filterable clearable>
          <el-option v-for="a in agents" :key="a.id" :label="a.display_name" :value="String(a.id)" />
        </el-select>
        <el-button type="primary" :loading="adding" @click="$emit('add-member')">添加</el-button>
      </div>
    </div>

    <section class="card">
      <div class="secTitle">长期记忆自动提炼配置</div>
      <div v-if="memoryCfgLoading" class="loading">加载配置中…</div>
      <template v-else>
        <div class="kvRow">
          <span class="k">自动提炼</span>
          <span class="v"><el-switch v-model="memoryCfg.enabled" /></span>
        </div>
        <div class="kvRow">
          <span class="k">触发Token</span>
          <span class="v"><el-input-number v-model="memoryCfg.trigger_tokens" :min="200" :step="200" /></span>
        </div>
        <div class="kvRow">
          <span class="k">保留最近</span>
          <span class="v"><el-input-number v-model="memoryCfg.keep_recent_messages" :min="0" :step="1" /></span>
        </div>
        <div class="kvRow">
          <span class="k">最小间隔(s)</span>
          <span class="v"><el-input-number v-model="memoryCfg.min_interval_seconds" :min="0" :step="10" /></span>
        </div>
        <div class="actions">
          <el-button size="small" :loading="memoryCfgSaving" @click="$emit('save-memory-config')">保存配置</el-button>
          <el-button size="small" :loading="memoryCompressing" type="primary" @click="$emit('run-memory-compress')">立即提炼</el-button>
          <el-button size="small" @click="$emit('refresh-memory-status')">刷新状态</el-button>
        </div>
        <div v-if="memoryStatus" class="statusBlock">
          <div>待提炼消息：{{ memoryStatus.pending_message_count }}</div>
          <div>待提炼Token：{{ memoryStatus.pending_tokens }}</div>
          <div>最近压缩到消息ID：{{ memoryStatus.last_message_id }}</div>
          <div>是否达到阈值：{{ memoryStatus.will_trigger ? '是' : '否' }}</div>
        </div>
      </template>
    </section>

    <section class="card">
      <div class="secTitle">群管家配置</div>
      <div v-if="assistantCfgLoading" class="loading">加载中…</div>
      <template v-else>
        <div class="kvRow">
          <span class="k">启用</span>
          <span class="v"><el-switch v-model="assistantEnabledModel" /></span>
        </div>
        <div class="kvRow">
          <span class="k">管家成员</span>
          <span class="v">群内系统角色「管家」</span>
        </div>
        <div class="kvRow">
          <span class="k">Manager ID</span>
          <span class="v">{{ assistantCfg?.manager_member_id || '-' }}</span>
        </div>
        <div class="actions">
          <el-button size="small" :loading="assistantCfgSaving" @click="$emit('save-assistant-config')">保存管家配置</el-button>
        </div>
      </template>
    </section>
  </section>
</template>

<script setup lang="ts">
import type { Agent, Group, MemoryCompressorConfig, MemoryCompressorStatus, User } from '../../api/groups'
import type { GroupAssistantConfig } from '../../api/messages'

const {
  activeGroup,
  users,
  agents,
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
  users: User[]
  agents: Agent[]
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
  (e: 'add-member'): void
  (e: 'save-memory-config'): void
  (e: 'run-memory-compress'): void
  (e: 'refresh-memory-status'): void
  (e: 'save-assistant-config'): void
}>()
</script>

<style scoped>
.projectStack {
  display: grid;
  gap: 12px;
}
.card {
  border: 1px solid rgba(31, 35, 41, 0.06);
  border-radius: 14px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.7);
}
.secTitle {
  font-weight: 900;
  margin-bottom: 10px;
}
.addGrid {
  display: grid;
  grid-template-columns: 120px 1fr 90px;
  gap: 10px;
  align-items: center;
}
.kvRow {
  display: grid;
  grid-template-columns: 72px 1fr;
  gap: 10px;
  font-size: 12px;
  margin-bottom: 6px;
}
.k {
  opacity: 0.6;
  font-weight: 800;
}
.v {
  opacity: 0.9;
  word-break: break-all;
}
.actions {
  display: flex;
  gap: 8px;
  margin-top: 10px;
  flex-wrap: wrap;
}
.loading {
  opacity: 0.7;
  font-size: 12px;
}
.statusBlock {
  margin-top: 10px;
  font-size: 12px;
  opacity: 0.75;
  line-height: 1.6;
}
</style>
