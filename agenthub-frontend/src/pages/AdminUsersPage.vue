<template>
  <div class="page">
    <div class="header">
      <div class="title">用户管理</div>
      <div class="sub">仅管理员创建用户（后端目前未做权限校验）</div>
    </div>

    <div class="grid">
      <section class="panel">
        <div class="panelTitle">创建用户</div>
        <div class="form">
          <el-input v-model="form.email" placeholder="email" />
          <el-input v-model="form.username" placeholder="username" />
          <el-input v-model="form.display_name" placeholder="display_name (可选)" />
          <el-input v-model="form.password" placeholder="password" show-password />
          <el-input v-model="form.role" placeholder="role" />
          <el-input v-model="form.status" placeholder="status" />
          <el-input v-model="form.bio" placeholder="bio" />
          <el-button type="primary" :loading="creating" @click="create">创建</el-button>
          <div v-if="createError" class="err">{{ createError }}</div>
        </div>
      </section>

      <section class="panel">
        <div class="panelTitle">用户列表</div>
        <div class="toolbar">
          <el-input v-model="q" placeholder="搜索 email/username/display_name" clearable @keyup.enter="load" />
          <el-button @click="load" :loading="loading">刷新</el-button>
        </div>
        <div class="list">
          <div v-for="u in users" :key="u.id" class="row">
            <div class="left">
              <div class="name">{{ u.display_name || u.username }}</div>
              <div class="meta">{{ u.email }} · {{ u.role }} · {{ u.status }}</div>
            </div>
            <div class="id">#{{ u.id }}</div>
          </div>
          <div v-if="!loading && users.length === 0" class="empty">暂无用户</div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { apiCreateUser, apiListUsers, type User } from '../api/agenthub'

const users = ref<User[]>([])
const loading = ref(false)
const q = ref('')

const creating = ref(false)
const createError = ref('')
const form = reactive({
  email: '',
  username: '',
  display_name: '',
  password: '',
  role: 'user',
  status: 'active',
  bio: '',
})

async function load() {
  loading.value = true
  try {
    const res = await apiListUsers(q.value || undefined)
    users.value = res.data
  } finally {
    loading.value = false
  }
}

async function create() {
  createError.value = ''
  creating.value = true
  try {
    await apiCreateUser({
      email: form.email,
      username: form.username,
      display_name: form.display_name || null,
      password: form.password,
      role: form.role,
      status: form.status,
      bio: form.bio,
    })
    await load()
  } catch (e) {
    createError.value = e instanceof Error ? e.message : String(e)
  } finally {
    creating.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.page {
  height: calc(100vh - 36px);
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.header {
  padding: 10px 6px;
}
.title {
  font-size: 18px;
  font-weight: 900;
}
.sub {
  font-size: 12px;
  opacity: 0.65;
  margin-top: 2px;
}
.grid {
  flex: 1;
  display: grid;
  grid-template-columns: 420px 1fr;
  gap: 14px;
  min-height: 0;
}
.panel {
  background: rgba(255, 255, 255, 0.75);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(31, 35, 41, 0.08);
  border-radius: 18px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  min-height: 0;
}
.panelTitle {
  padding: 14px 16px;
  font-weight: 900;
  border-bottom: 1px solid rgba(31, 35, 41, 0.06);
}
.form {
  padding: 14px 16px;
  display: grid;
  gap: 10px;
}
.toolbar {
  padding: 12px 16px;
  display: grid;
  grid-template-columns: 1fr 90px;
  gap: 10px;
  border-bottom: 1px solid rgba(31, 35, 41, 0.06);
}
.list {
  padding: 10px 8px;
  overflow: auto;
  min-height: 0;
}
.row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 12px;
  border-radius: 14px;
}
.row:hover {
  background: rgba(79, 140, 255, 0.06);
}
.name {
  font-weight: 900;
}
.meta {
  font-size: 12px;
  opacity: 0.65;
  margin-top: 2px;
}
.id {
  font-size: 12px;
  opacity: 0.6;
}
.empty {
  padding: 18px 10px;
  opacity: 0.6;
}
.err {
  color: #d92d20;
  font-size: 12px;
}
</style>

