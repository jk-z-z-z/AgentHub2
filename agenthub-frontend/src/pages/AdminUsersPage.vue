<template>
  <AdminUsersWorkspace
    v-model:q="q"
    :users="users"
    :loading="loading"
    :creating="creating"
    :create-error="createError"
    :form="form"
    @load="load"
    @create="create"
  />
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { apiCreateUser, apiListUsers, type User } from '../api/users'
import AdminUsersWorkspace from '../components/admin-users/AdminUsersWorkspace.vue'

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
