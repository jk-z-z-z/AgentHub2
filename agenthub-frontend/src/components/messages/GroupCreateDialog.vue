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
        <div class="pickList">
          <div v-for="u in users" :key="u.id" class="pickItem" @click="$emit('toggle-user', u)">
            <div class="pAvatar">{{ (u.display_name || u.username || u.email).slice(0, 1).toUpperCase() }}</div>
            <div class="pName">{{ u.display_name || u.username || u.email }}</div>
            <div class="pCheck">
              <el-icon v-if="pickedUserIds.has(String(u.id))">
                <Select />
              </el-icon>
            </div>
          </div>
        </div>
      </div>
      <div class="pickCol">
        <div class="pickTitle">智能体</div>
        <div class="pickList">
          <div v-for="a in agents" :key="a.id" class="pickItem" @click="$emit('toggle-agent', a)">
            <div class="pAvatar">
              <el-icon>
                <Monitor />
              </el-icon>
            </div>
            <div class="pName">{{ a.display_name }}</div>
            <div class="pCheck">
              <el-icon v-if="pickedAgentIds.has(String(a.id))">
                <Select />
              </el-icon>
            </div>
          </div>
        </div>
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
import type { Agent, User } from '../../api/groups'

const openModel = defineModel<boolean>('open', { required: true })
const createTypeModel = defineModel<'project' | 'personal'>('createType', { required: true })
const createNameModel = defineModel<string>('createName', { required: true })

defineProps<{
  users: User[]
  agents: Agent[]
  pickedUserIds: Set<string>
  pickedAgentIds: Set<string>
  createErr: string
  creating: boolean
}>()

defineEmits<{
  (e: 'toggle-user', user: User): void
  (e: 'toggle-agent', agent: Agent): void
  (e: 'create'): void
}>()
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
.pickList {
  max-height: 280px;
  overflow: auto;
}
.pickItem {
  display: grid;
  grid-template-columns: 36px 1fr 20px;
  align-items: center;
  gap: 10px;
  padding: 10px 10px;
  cursor: pointer;
}
.pickItem:hover {
  background: rgba(79, 140, 255, 0.06);
}
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
.pCheck {
  color: #2f6bff;
  display: flex;
  justify-content: center;
  font-size: 16px;
}
.err {
  color: #d92d20;
  font-size: 12px;
}
</style>
