<template>
  <el-dialog v-model="openModel" title="新建会话" width="520px">
    <div class="createGrid">
      <el-select v-model="createTypeModel" placeholder="会话类型" style="width: 160px">
        <el-option label="项目群聊 (project)" value="project" />
        <el-option label="单聊 (personal)" value="personal" />
      </el-select>
      <el-input v-model="createNameModel" placeholder="会话名称 (group.name)" />
    </div>

    <div style="margin-top: 12px; font-weight: 800">选择成员</div>
    <div class="pickGrid">
      <div class="pickCol" v-if="createTypeModel !== 'personal'">
        <div class="pickTitle">用户</div>
        <el-table :data="users" class="pickList" height="280" empty-text="暂无用户" :row-class-name="userRowClassName" @row-click="handleUserRowClick">
          <el-table-column label="" width="58">
            <template #default="{ row }">
              <div class="pAvatar">{{ (row.display_name || row.username || row.email).slice(0, 1).toUpperCase() }}</div>
            </template>
          </el-table-column>
          <el-table-column label="用户" min-width="140">
            <template #default="{ row }">
              <div class="pName">{{ row.display_name || row.username || row.email }}</div>
            </template>
          </el-table-column>
          <el-table-column label="" width="42" align="right">
            <template #default="{ row }">
              <el-icon v-if="pickedUserIds.has(String(row.id))">
                <Select />
              </el-icon>
            </template>
          </el-table-column>
        </el-table>
      </div>
      <div class="pickCol">
        <div class="pickTitle">智能体</div>
        <el-table :data="agents" class="pickList" height="280" empty-text="暂无智能体" :row-class-name="agentRowClassName" @row-click="handleAgentRowClick">
          <el-table-column label="" width="58">
            <template #default>
              <div class="pAvatar">
                <el-icon>
                  <Monitor />
                </el-icon>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="智能体" min-width="140">
            <template #default="{ row }">
              <div class="pName">{{ row.display_name }}</div>
            </template>
          </el-table-column>
          <el-table-column label="" width="42" align="right">
            <template #default="{ row }">
              <el-icon v-if="pickedAgentIds.has(String(row.id))">
                <Select />
              </el-icon>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>
    <div v-if="createTypeModel === 'personal'" style="margin-top: 8px; opacity: 0.7; font-size: 12px">
      单聊：只需选择 1 个智能体；创建者会自动作为另一成员加入；无需 @ 也会自动触发该智能体回复。
    </div>

    <div v-if="createErr" class="err" style="margin-top: 8px">{{ createErr }}</div>

    <template #footer>
      <el-button @click="openModel = false">取消</el-button>
      <el-button type="primary" :loading="creating" @click="$emit('create')">创建</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { Monitor, Select } from '@element-plus/icons-vue'
import type { Agent, User } from '@/api/models.ts'

const openModel = defineModel<boolean>('open', { required: true })
const createTypeModel = defineModel<'project' | 'personal'>('createType', { required: true })
const createNameModel = defineModel<string>('createName', { required: true })

const props = defineProps<{
  users: User[]
  agents: Agent[]
  pickedUserIds: Set<string>
  pickedAgentIds: Set<string>
  createErr: string
  creating: boolean
}>()

const emit = defineEmits<{
  (e: 'toggle-user', user: User): void
  (e: 'toggle-agent', agent: Agent): void
  (e: 'create'): void
}>()

function handleUserRowClick(row: User) {
  emit('toggle-user', row)
}

function handleAgentRowClick(row: Agent) {
  emit('toggle-agent', row)
}

function userRowClassName({ row }: { row: User }) {
  return props.pickedUserIds.has(String(row.id)) ? 'active' : ''
}

function agentRowClassName({ row }: { row: Agent }) {
  return props.pickedAgentIds.has(String(row.id)) ? 'active' : ''
}
</script>

<style scoped>
.createGrid {
  display: grid;
  grid-template-columns: 160px 1fr;
  gap: 10px;
}
.pickGrid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-top: 10px;
}
.pickCol {
  border: 1px solid rgba(31, 35, 41, 0.08);
  border-radius: 14px;
  overflow: hidden;
}
.pickTitle {
  padding: 10px 12px;
  font-weight: 900;
  border-bottom: 1px solid rgba(31, 35, 41, 0.06);
}
.pickList { width: 100%; }
.pickList :deep(.el-table__row) { cursor: pointer; }
.pickList :deep(.el-table__row.active) { background: rgba(79,140,255,.12); }
.pAvatar {
  width: 36px;
  height: 36px;
  border-radius: 12px;
  display: grid;
  place-items: center;
  background: rgba(31, 35, 41, 0.06);
  font-size: 16px;
}
.pName {
  font-weight: 800;
}
.err {
  color: #d92d20;
  font-size: 12px;
}
</style>
