<template>
  <div class="page">
    <div class="grid">
      <WorkspacePanel title="创建用户">
        <div class="form">
          <el-input v-model="form.email" placeholder="email" />
          <el-input v-model="form.username" placeholder="username" />
          <el-input v-model="form.display_name" placeholder="display_name (可选)" />
          <el-input v-model="form.password" placeholder="password" show-password />
          <el-input v-model="form.role" placeholder="role" />
          <el-input v-model="form.status" placeholder="status" />
          <el-input v-model="form.bio" placeholder="bio" />
          <el-button type="primary" :loading="creating" @click="$emit('create')">创建</el-button>
          <div v-if="createError" class="err">{{ createError }}</div>
        </div>
      </WorkspacePanel>

      <WorkspacePanel title="用户列表">
        <template #actions>
          <el-button @click="$emit('load')" :loading="loading">刷新</el-button>
        </template>

        <div class="listPane">
          <el-input
            v-model="queryModel"
            class="searchBar"
            placeholder="搜索 email/username/display_name"
            clearable
            @keyup.enter="$emit('load')"
          />

          <el-table :data="users" empty-text="暂无用户" class="list" height="100%">
            <el-table-column label="名称" min-width="160">
              <template #default="{ row }">
                <div class="name">{{ row.display_name || row.username }}</div>
                <div class="meta">{{ row.email }}</div>
              </template>
            </el-table-column>
            <el-table-column prop="role" label="角色" width="100" />
            <el-table-column prop="status" label="状态" width="100" />
            <el-table-column label="ID" width="100" align="right">
              <template #default="{ row }">
                <span class="id">#{{ row.id }}</span>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </WorkspacePanel>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { User } from '../../api/users'
import WorkspacePanel from '../common/WorkspacePanel.vue'

const queryModel = defineModel<string>('q', { required: true })

defineProps<{
  users: User[]
  loading: boolean
  creating: boolean
  createError: string
  form: {
    email: string
    username: string
    display_name: string
    password: string
    role: string
    status: string
    bio: string
  }
}>()

defineEmits<{
  (e: 'load'): void
  (e: 'create'): void
}>()
</script>

<style scoped>
.page { height: 100%; display:flex; flex-direction:column; gap:14px; }
.grid { flex:1; display:grid; grid-template-columns:420px 1fr; gap:14px; min-height:0; }
.form { padding:14px 16px; display:grid; gap:10px; }
.listPane { flex:1; min-height:0; display:flex; flex-direction:column; }
.searchBar { margin-bottom: 12px; }
.list { min-height:0; flex:1; }
.name { font-weight:900; }
.meta { font-size:12px; opacity:.65; margin-top:2px; }
.id { font-size:12px; opacity:.6; }
.err { color: var(--ah-danger); font-size:12px; }
</style>
