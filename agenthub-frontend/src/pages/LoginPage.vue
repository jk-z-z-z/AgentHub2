<template>
  <div class="wrap">
    <div class="backdrop"></div>
    <el-card class="card" shadow="never">
      <div class="hero">
        <div class="eyebrow">AgentHub Workspace</div>
        <div class="title">{{ isRegister ? '创建账号' : '登录' }}</div>
        <div class="sub">{{ isRegister ? '注册后会直接进入工作台' : '使用邮箱与密码登录' }}</div>
      </div>

      <div class="modeSwitch">
        <button
          type="button"
          class="modeBtn"
          :class="{ active: !isRegister }"
          @click="switchMode(false)"
        >
          登录
        </button>
        <button
          type="button"
          class="modeBtn"
          :class="{ active: isRegister }"
          @click="switchMode(true)"
        >
          注册
        </button>
      </div>

      <div class="form">
        <el-input
          v-if="isRegister"
          v-model="displayName"
          placeholder="显示名称（可选）"
          size="large"
          @keyup.enter="submit"
        />
        <el-input v-model="email" placeholder="邮箱" size="large" @keyup.enter="submit" />
        <el-input
          v-if="isRegister"
          v-model="username"
          placeholder="用户名"
          size="large"
          @keyup.enter="submit"
        />
        <el-input v-model="password" placeholder="密码" show-password size="large" @keyup.enter="submit" />
        <el-input
          v-if="isRegister"
          v-model="confirmPassword"
          placeholder="确认密码"
          show-password
          size="large"
          @keyup.enter="submit"
        />
        <el-input
          v-if="isRegister"
          v-model="bio"
          type="textarea"
          :rows="3"
          resize="none"
          placeholder="一句话介绍（可选）"
        />
        <el-button type="primary" size="large" :loading="loading" @click="submit">
          {{ isRegister ? '注册并进入' : '登录' }}
        </el-button>
      </div>

      <div v-if="error" class="error">{{ error }}</div>
      <div v-if="!isRegister" class="hint">默认管理员：admin@example.com / admin123456</div>
      <div v-else class="hint">用户名至少 2 位，密码至少 6 位。</div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { apiLogin, apiRegister } from '../api/auth'

const router = useRouter()
const isRegister = ref(false)
const email = ref('admin@example.com')
const password = ref('admin123456')
const username = ref('')
const displayName = ref('')
const confirmPassword = ref('')
const bio = ref('')
const loading = ref(false)
const error = ref('')

function switchMode(nextIsRegister: boolean) {
  isRegister.value = nextIsRegister
  error.value = ''
  if (nextIsRegister) {
    email.value = ''
    password.value = ''
  } else {
    email.value = 'admin@example.com'
    password.value = 'admin123456'
  }
}

async function submit() {
  error.value = ''
  if (isRegister.value) {
    if (!username.value.trim()) {
      error.value = '请输入用户名'
      return
    }
    if (password.value.length < 6) {
      error.value = '密码至少需要 6 位'
      return
    }
    if (password.value !== confirmPassword.value) {
      error.value = '两次输入的密码不一致'
      return
    }
  }
  loading.value = true
  try {
    const res = isRegister.value
      ? await apiRegister({
          email: email.value,
          username: username.value,
          display_name: displayName.value || null,
          password: password.value,
          bio: bio.value,
        })
      : await apiLogin({ email: email.value, password: password.value })
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
  padding: 24px;
  background:
    radial-gradient(circle at top left, color-mix(in srgb, var(--ah-primary) 22%, transparent), transparent 28%),
    radial-gradient(circle at bottom right, color-mix(in srgb, var(--ah-text-strong) 10%, transparent), transparent 22%),
    linear-gradient(135deg, var(--ah-bg-soft), var(--ah-bg));
  position: relative;
  overflow: hidden;
}
.backdrop {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(255, 255, 255, 0.04) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.04) 1px, transparent 1px);
  background-size: 28px 28px;
  mask-image: linear-gradient(180deg, rgba(0, 0, 0, 0.75), transparent 92%);
}
.card {
  position: relative;
  z-index: 1;
  width: min(460px, calc(100vw - 32px));
  border-radius: 28px;
  background: var(--ah-login-surface);
  backdrop-filter: blur(18px);
  border: 1px solid var(--ah-border-soft);
  box-shadow: var(--ah-shadow-lg);
}
.hero {
  display: grid;
  gap: 6px;
}
.eyebrow {
  font-size: 11px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--ah-text-tertiary);
}
.title {
  font-size: 28px;
  line-height: 1.1;
  font-weight: 900;
}
.sub {
  margin-top: 4px;
  color: var(--ah-text-secondary);
  font-size: 13px;
}
.modeSwitch {
  margin-top: 18px;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  padding: 6px;
  border-radius: 18px;
  background: var(--ah-surface-soft);
  border: 1px solid var(--ah-border-soft);
}
.modeBtn {
  appearance: none;
  border: 0;
  background: transparent;
  color: var(--ah-text-secondary);
  height: 42px;
  border-radius: 14px;
  font-size: 14px;
  font-weight: 800;
  cursor: pointer;
  transition:
    background-color 0.18s ease,
    color 0.18s ease,
    transform 0.18s ease;
}
.modeBtn.active {
  background: var(--ah-surface-strong);
  color: var(--ah-text-primary);
  box-shadow: var(--ah-shadow-sm);
}
.form {
  margin-top: 18px;
  display: grid;
  gap: 12px;
}
.error {
  margin-top: 14px;
  color: var(--ah-danger);
  font-size: 12px;
}
.hint {
  margin-top: 14px;
  color: var(--ah-text-tertiary);
  font-size: 12px;
}
</style>
