<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import { login } from '@/services/agenthubService'

const router = useRouter()
const loading = ref(false)

const form = reactive({
  email: 'admin@example.com',
  password: 'admin123456',
})

const submit = async () => {
  if (!form.email || !form.password) {
    ElMessage.warning('请输入邮箱和密码')
    return
  }

  loading.value = true
  try {
    const result = await login(form)
    localStorage.setItem('token', result.access_token)
    ElMessage.success('登录成功')
    await router.replace({ name: 'messages' })
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : String(error))
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <div class="login-card">
      <div class="title">AgentHub 登录</div>
      <div class="subtitle">企业内部协作工作台</div>

      <el-form label-position="top" @submit.prevent>
        <el-form-item label="邮箱">
          <el-input v-model="form.email" placeholder="请输入邮箱" />
        </el-form-item>

        <el-form-item label="密码">
          <el-input
            v-model="form.password"
            type="password"
            show-password
            placeholder="请输入密码"
            @keydown.enter="submit"
          />
        </el-form-item>

        <el-button type="primary" class="submit" :loading="loading" @click="submit">登录</el-button>
      </el-form>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  width: 100%;
  height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  background: radial-gradient(circle at 20% 20%, #dbe7ff 0%, #eef3ff 40%, #f7f9ff 100%);
}

.login-card {
  width: 420px;
  background: #fff;
  border: 1px solid #e7ecf6;
  border-radius: 16px;
  box-shadow: 0 16px 40px rgba(38, 83, 186, 0.12);
  padding: 26px;
}

.title {
  font-size: 24px;
  font-weight: 700;
  color: #111827;
}

.subtitle {
  font-size: 13px;
  color: #6b7280;
  margin-top: 4px;
  margin-bottom: 18px;
}

.submit {
  width: 100%;
  margin-top: 6px;
}
</style>
