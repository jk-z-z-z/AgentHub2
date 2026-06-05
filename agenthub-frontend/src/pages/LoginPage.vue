<template>
  <div class="wrap">
    <div class="card">
      <div class="title">登录</div>
      <div class="sub">使用邮箱与密码登录</div>

      <div class="form">
        <el-input v-model="email" placeholder="邮箱" size="large" />
        <el-input v-model="password" placeholder="密码" show-password size="large" />
        <el-button type="primary" size="large" :loading="loading" @click="submit">登录</el-button>
      </div>

      <div v-if="error" class="error">{{ error }}</div>
      <div class="hint">默认管理员：admin@example.com / admin123456</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { apiLogin } from '../api/auth'

const router = useRouter()
const email = ref('admin@example.com')
const password = ref('admin123456')
const loading = ref(false)
const error = ref('')

async function submit() {
  error.value = ''
  loading.value = true
  try {
    const res = await apiLogin({ email: email.value, password: password.value })
    localStorage.setItem('token', res.data.access_token)
    await router.replace('/messages')
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.wrap {
  height: 100vh;
  display: grid;
  place-items: center;
  background: var(--ah-bg);
}
.card {
  width: 420px;
  border-radius: 16px;
  background: #fff;
  border: 1px solid rgba(31, 35, 41, 0.08);
  padding: 22px;
  box-shadow: 0 14px 44px rgba(31, 35, 41, 0.08);
}
.title {
  font-size: 18px;
  font-weight: 800;
}
.sub {
  margin-top: 4px;
  opacity: 0.7;
  font-size: 12px;
}
.form {
  margin-top: 18px;
  display: grid;
  gap: 10px;
}
.error {
  margin-top: 10px;
  color: #d92d20;
  font-size: 12px;
}
.hint {
  margin-top: 12px;
  opacity: 0.6;
  font-size: 12px;
}
</style>
